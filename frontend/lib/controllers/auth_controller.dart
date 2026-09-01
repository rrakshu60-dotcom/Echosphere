import 'dart:convert';
import 'package:anymex/screens/auth/login_screen.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:anymex/utils/usn_parser.dart';

class EchosphereUser {
  final int id;
  final String fullName;
  final String role;
  final String? officialEmail;
  final String? usn;
  final String? employeeId;
  final int? departmentId;
  final String? department;
  final int? semester;
  final String? section;

  EchosphereUser({
    required this.id,
    required this.fullName,
    required this.role,
    this.officialEmail,
    this.usn,
    this.employeeId,
    this.departmentId,
    this.department,
    this.semester,
    this.section,
  });

  factory EchosphereUser.fromJson(Map<String, dynamic> json) {
    final usnVal = json['usn'] as String?;
    final detectedDept = usnVal != null ? detectDepartmentFromUsn(usnVal) : 'AIML';
    return EchosphereUser(
      id: json['user_id'] ?? json['id'] ?? 0,
      fullName: json['full_name'] ?? 'User',
      role: json['role'] ?? 'Student',
      officialEmail: json['official_email'],
      usn: usnVal,
      employeeId: json['employee_id'],
      departmentId: json['department_id'],
      department: json['department'] ?? (json['role'] == 'Student' || usnVal != null ? detectedDept : 'General'),
      semester: json['semester'] as int? ?? 5,
      section: json['section'] as String? ?? 'A',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'full_name': fullName,
      'role': role,
      'official_email': officialEmail,
      'usn': usn,
      'employee_id': employeeId,
      'department_id': departmentId,
      'department': department,
      'semester': semester,
      'section': section,
    };
  }
}

class LoginLogEntry {
  final String timestamp;
  final String username;
  final String role;
  final String location;
  final String status;
  final String? employeeId;

  LoginLogEntry({
    required this.timestamp,
    required this.username,
    required this.role,
    required this.location,
    required this.status,
    this.employeeId,
  });

  Map<String, dynamic> toJson() => {
        'timestamp': timestamp,
        'username': username,
        'role': role,
        'location': location,
        'status': status,
        'employee_id': employeeId,
      };

  factory LoginLogEntry.fromJson(Map<String, dynamic> json) => LoginLogEntry(
        timestamp: json['timestamp'] ?? '',
        username: json['username'] ?? '',
        role: json['role'] ?? '',
        location: json['location'] ?? '',
        status: json['status'] ?? '',
        employeeId: json['employee_id'],
      );
}

class AuthController extends GetxController {
  final Rxn<EchosphereUser> currentUser = Rxn<EchosphereUser>();
  final RxBool isLoggedIn = false.obs;
  final RxBool isLoading = false.obs;
  final RxBool rememberMe = true.obs;
  final RxString token = ''.obs;

  final RxList<LoginLogEntry> auditLogs = <LoginLogEntry>[].obs;

  final RxInt annualPasswordResetCount = 0.obs;

  static const List<String> availableRoles = [
    'Student',
    'Teacher',
    'HoD',
    'College Admin',
    'Principal',
    'Dev Admin',
  ];

  @override
  void onInit() {
    super.onInit();
    _loadSessionFromDisk();
    _loadAuditLogsFromDisk();
    loadResetQuotaFromDisk();
    _loadCustomPasswordsFromDisk();
  }

  Future<void> loadResetQuotaFromDisk() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final year = DateTime.now().year;
      final userId = currentUser.value?.id ?? 0;
      final count = prefs.getInt('password_resets_${userId}_$year') ?? 0;
      annualPasswordResetCount.value = count;
    } catch (_) {
      annualPasswordResetCount.value = 0;
    }
  }

  Future<void> _saveResetQuotaToDisk() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final year = DateTime.now().year;
      final userId = currentUser.value?.id ?? 0;
      await prefs.setInt('password_resets_${userId}_$year', annualPasswordResetCount.value);
    } catch (_) {}
  }

  bool canResetPassword() {
    final role = currentUser.value?.role ?? 'Student';
    // College Admin, Principal, and Dev Admin have NO restrictions
    if (role == 'College Admin' || role == 'Principal' || role == 'Dev Admin' || role == 'Developer') {
      return true;
    }
    // Students, Teachers, and HoDs have a 5 reset limit per year
    return annualPasswordResetCount.value < 5;
  }

  final RxMap<String, String> _customUserPasswords = <String, String>{}.obs;

  Future<void> _loadCustomPasswordsFromDisk() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString('custom_user_passwords');
      if (raw != null) {
        final Map<String, dynamic> data = jsonDecode(raw);
        data.forEach((k, v) {
          _customUserPasswords[k.toString()] = v.toString();
        });
      }
    } catch (e) {
      debugPrint('Failed to load custom passwords: $e');
    }
  }

  Future<void> _saveCustomPasswordsToDisk() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('custom_user_passwords', jsonEncode(_customUserPasswords));
    } catch (e) {
      debugPrint('Failed to save custom passwords: $e');
    }
  }

  Future<bool> resetPassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    final user = currentUser.value;
    if (user == null) return false;

    final role = user.role;
    final isRestrictedRole = role == 'Student' || role == 'Teacher' || role == 'HoD';

    if (isRestrictedRole && !canResetPassword()) {
      return false;
    }

    final idKey = user.officialEmail ?? user.usn ?? user.employeeId ?? user.fullName;

    // Validate current password locally
    final mockCheck = validateMockCredentials(idKey, currentPassword);
    if (mockCheck == null) {
      debugPrint('Current password validation failed for user: $idKey');
    }

    // Call live backend endpoint
    final backendSuccess = await EchosphereApiService().updatePassword(
      currentPassword: currentPassword,
      newPassword: newPassword,
      identifier: idKey,
    );

    // Save custom password locally for instant UI responsiveness & offline authentication
    final keys = [
      user.fullName.toLowerCase(),
      if (user.officialEmail != null) user.officialEmail!.toLowerCase(),
      if (user.usn != null) user.usn!.toLowerCase(),
      if (user.employeeId != null) user.employeeId!.toLowerCase(),
    ];

    for (final k in keys) {
      _customUserPasswords[k] = newPassword;
    }
    await _saveCustomPasswordsToDisk();

    if (isRestrictedRole) {
      annualPasswordResetCount.value++;
      await _saveResetQuotaToDisk();
    }

    await addAuditLog(
      username: user.fullName,
      role: user.role,
      status: backendSuccess ? 'SUCCESS (Password Updated on Backend)' : 'SUCCESS (Password Updated Locally)',
      employeeId: user.employeeId,
    );

    return true;
  }

  Future<void> _loadSessionFromDisk() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString('auth_session');
      if (raw != null) {
        final Map<String, dynamic> data = jsonDecode(raw);
        final isRemembered = data['remember_me'] == true;
        if (isRemembered && data['user'] != null) {
          rememberMe.value = true;
          currentUser.value = EchosphereUser.fromJson(data['user']);
          token.value = data['token'] ?? '';
          isLoggedIn.value = true;
          EchosphereApiService().setAuthToken(token.value);
        }
      }
    } catch (e) {
      debugPrint('Failed to load session from disk: $e');
    }
  }

  Future<void> _saveSessionToDisk() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (rememberMe.value && currentUser.value != null) {
        final data = {
          'remember_me': true,
          'token': token.value,
          'user': currentUser.value!.toJson(),
        };
        await prefs.setString('auth_session', jsonEncode(data));
      } else {
        await prefs.remove('auth_session');
      }
    } catch (e) {
      debugPrint('Failed to save session to disk: $e');
    }
  }

  Future<void> _loadAuditLogsFromDisk() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString('login_audit_logs');
      if (raw != null) {
        final List<dynamic> jsonList = jsonDecode(raw);
        auditLogs.value = jsonList.map((j) => LoginLogEntry.fromJson(j)).toList();
      } else {
        auditLogs.value = [
          LoginLogEntry(
            timestamp: DateFormat('yyyy-MM-dd HH:mm:ss').format(DateTime.now().subtract(const Duration(hours: 2))),
            username: 'CAdmin',
            role: 'College Admin',
            location: 'Bangalore Campus Node (Main Admin Block • 192.168.1.105)',
            status: 'SUCCESS (Employee ID Verified)',
            employeeId: 'DBITADM001',
          ),
          LoginLogEntry(
            timestamp: DateFormat('yyyy-MM-dd HH:mm:ss').format(DateTime.now().subtract(const Duration(hours: 5))),
            username: '1db23ci079',
            role: 'Student',
            location: 'Bangalore Campus Wi-Fi (Academic Block B • 192.168.2.14)',
            status: 'LOGIN SUCCESS',
          ),
        ];
        await _saveAuditLogsToDisk();
      }
    } catch (e) {
      debugPrint('Error loading audit logs: $e');
    }
  }

  Future<void> _saveAuditLogsToDisk() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final content = jsonEncode(auditLogs.map((e) => e.toJson()).toList());
      await prefs.setString('login_audit_logs', content);
    } catch (e) {
      debugPrint('Error saving audit logs: $e');
    }
  }

  Future<void> addAuditLog({
    required String username,
    required String role,
    required String status,
    String? employeeId,
  }) async {
    final now = DateFormat('yyyy-MM-dd HH:mm:ss').format(DateTime.now());
    const location = 'Bangalore Campus Node (Main Admin Block • 192.168.1.105)';

    final entry = LoginLogEntry(
      timestamp: now,
      username: username,
      role: role,
      location: location,
      status: status,
      employeeId: employeeId,
    );

    auditLogs.insert(0, entry);
    await _saveAuditLogsToDisk();
  }

  static int getRoleLevel(String role) {
    switch (role) {
      case 'Dev Admin':
      case 'Developer':
        return 6;
      case 'Principal':
        return 5;
      case 'College Admin':
        return 4;
      case 'HoD':
        return 3;
      case 'Teacher':
        return 2;
      case 'Student':
      default:
        return 1;
    }
  }

  bool hasMinimumRole(String requiredRole) {
    final currentRoleName = currentUser.value?.role ?? 'Student';
    return getRoleLevel(currentRoleName) >= getRoleLevel(requiredRole);
  }

  /// Validates if an employee ID belongs to any registered staff, teacher, HoD, or admin in the database.
  bool isRegisteredStaffEmployeeId(String empId) {
    final cleanId = empId.trim().toUpperCase();
    if (cleanId.isEmpty) return false;

    // Registered staff employee IDs from database seeders
    const registeredStaffIds = [
      'DBITADM001',
      'DEVADM01',
      'PRI001',
      'DBITAIMLT022022',
    ];

    if (registeredStaffIds.contains(cleanId)) return true;

    // Pattern matching for any official staff/teacher/HoD/admin employee IDs
    if (cleanId.startsWith('DBIT') ||
        cleanId.startsWith('EMP') ||
        cleanId.startsWith('TCH') ||
        cleanId.startsWith('HOD') ||
        cleanId.startsWith('PRI') ||
        cleanId.startsWith('ADM') ||
        cleanId.startsWith('DEV')) {
      return true;
    }

    return false;
  }

  /// Get mock user for validation with strict password checking for ALL roles.
  EchosphereUser? validateMockCredentials(String identifier, String password) {
    final mockUser = _getMockUser(identifier);
    if (mockUser == null) return null;

    final idLower = identifier.trim().toLowerCase();
    final pwTrimmed = password.trim();

    final customPw = _customUserPasswords[idLower] ??
        (mockUser.officialEmail != null ? _customUserPasswords[mockUser.officialEmail!.toLowerCase()] : null) ??
        (mockUser.usn != null ? _customUserPasswords[mockUser.usn!.toLowerCase()] : null) ??
        (mockUser.employeeId != null ? _customUserPasswords[mockUser.employeeId!.toLowerCase()] : null) ??
        _customUserPasswords[mockUser.fullName.toLowerCase()];

    if (customPw != null) {
      return pwTrimmed == customPw ? mockUser : null;
    }

    // 1. College Admin (Primary)
    if (idLower == 'cadmin' || idLower == 'dbitadm001') {
      return pwTrimmed == 'Dbit@ES01' ? mockUser : null;
    }

    // 2. Dev Admin
    if (idLower == 'esdev01' || idLower == 'devadm01' || idLower == 'developer') {
      return pwTrimmed == 'rakshitha@1228' ? mockUser : null;
    }

    // 3. Principal
    if (idLower == 'principal' || idLower == 'principal@echosphere.edu' || idLower == 'pri001') {
      return pwTrimmed == 'Principal@123' ? mockUser : null;
    }

    // 4. Student (Rakshitha S)
    if (idLower == '1db23ci079' ||
        idLower == '1db23ci079@echosphere.edu' ||
        idLower == 'rakshitha s' ||
        idLower == 'rakshitha.s' ||
        idLower == 'rakshitha') {
      return pwTrimmed == 'rakshitha@1228' ? mockUser : null;
    }

    // 5. Teacher (Dr. B Kursheed)
    if (idLower == 'dbitaimlt022022' ||
        idLower == 'b.kursheed@echosphere.edu' ||
        idLower == 'dr. b kursheed' ||
        idLower == 'kursheed') {
      return pwTrimmed == 'Kursh@2022' ? mockUser : null;
    }

    // 6. HoD (Dr. AIML HoD)
    if (idLower == 'hod_aiml' ||
        idLower == 'hod.aiml@echosphere.edu' ||
        idLower == 'hod001' ||
        idLower == 'hod') {
      return pwTrimmed == 'Hod@123' ? mockUser : null;
    }

    // Deny login if password does not match any recognized credentials
    return null;
  }

  Future<bool> login({
    required String identifier,
    required String password,
    bool remember = true,
    String? employeeIdVerification,
  }) async {
    rememberMe.value = remember;
    isLoading.value = true;
    try {
      try {
        final api = EchosphereApiService();
        final res = await api.login(
          identifier: identifier,
          password: password,
        );

        final accessToken = res['access_token'] as String?;
        if (accessToken != null) {
          token.value = accessToken;
          api.setAuthToken(accessToken);

          final user = EchosphereUser.fromJson(res);
          currentUser.value = user;
          isLoggedIn.value = true;
          await _saveSessionToDisk();

          await addAuditLog(
            username: user.fullName,
            role: user.role,
            status: 'SUCCESS (API Login)',
            employeeId: user.employeeId,
          );

          return true;
        }
      } catch (e) {
        debugPrint('Live backend login error, using local validation if match: $e');
      }

      // Local / Seed Fallback for testing
      final mockUser = validateMockCredentials(identifier, password);
      if (mockUser != null) {
        currentUser.value = mockUser;
        isLoggedIn.value = true;
        token.value = 'mock_jwt_token_${mockUser.role.toLowerCase()}';
        EchosphereApiService().setAuthToken(token.value);
        await _saveSessionToDisk();

        await addAuditLog(
          username: mockUser.fullName,
          role: mockUser.role,
          status: employeeIdVerification != null
              ? 'SUCCESS (Employee ID Verified: $employeeIdVerification)'
              : 'LOGIN SUCCESS',
          employeeId: mockUser.employeeId ?? employeeIdVerification,
        );

        return true;
      }

      await addAuditLog(
        username: identifier,
        role: 'Unknown',
        status: 'FAILED (Invalid Credentials)',
      );
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  void logout() async {
    currentUser.value = null;
    isLoggedIn.value = false;
    token.value = '';
    rememberMe.value = false;
    isLoading.value = false;
    EchosphereApiService().setAuthToken(null);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('auth_session');
    } catch (_) {}
    Get.offAll(() => const LoginScreen());
  }

  /// Auto-detect role from the identifier for mock/offline fallback.
  EchosphereUser? _getMockUser(String identifier) {
    final id = identifier.trim();
    final idLower = id.toLowerCase();

    // Email login is disabled for administrative roles (College Admin & Dev Admin)
    // Primary College Admin account (Username: cadmin/CAdmin or Employee ID: DBITADM001)
    if (idLower == 'cadmin' || idLower == 'dbitadm001') {
      return EchosphereUser(
        id: 12,
        fullName: 'College Admin (Primary)',
        role: 'College Admin',
        officialEmail: 'cadmin@echosphere.edu',
        employeeId: 'DBITADM001',
        department: 'Administration',
      );
    }

    // USN / Identity pattern matching (case insensitive)
    if (idLower == '1db23ci079' || idLower == 'rakshitha s' || idLower == 'rakshitha.s' || idLower == 'rakshitha') {
      return EchosphereUser(
        id: 10,
        fullName: 'Rakshitha S',
        role: 'Student',
        usn: '1DB23CI079',
        officialEmail: '1db23ci079@echosphere.edu',
        department: 'AIML',
        departmentId: 5,
      );
    }

    if (idLower == 'dbitaimlt022022' || idLower == 'dr. b kursheed' || idLower == 'b.kursheed@echosphere.edu' || idLower == 'kursheed') {
      return EchosphereUser(
        id: 11,
        fullName: 'Dr. B Kursheed',
        role: 'Teacher',
        employeeId: 'DBITAIMLT022022',
        officialEmail: 'b.kursheed@echosphere.edu',
        department: 'AIML',
        departmentId: 5,
      );
    }

    if (idLower == 'hod_aiml' || idLower == 'hod.aiml@echosphere.edu' || idLower == 'hod001' || idLower == 'hod') {
      return EchosphereUser(
        id: 15,
        fullName: 'Dr. AIML HoD',
        role: 'HoD',
        employeeId: 'HOD001',
        officialEmail: 'hod.aiml@echosphere.edu',
        department: 'AIML',
        departmentId: 5,
      );
    }

    // Email & role detection for Principal
    if (idLower == 'principal' || idLower == 'principal@echosphere.edu') {
      return EchosphereUser(
        id: 3,
        fullName: 'Dr. Principal',
        role: 'Principal',
        officialEmail: 'principal@echosphere.edu',
        employeeId: 'PRI001',
        department: 'Executive',
      );
    }

    // Dev Admin account (Username/Employee ID: ESDev01)
    if (idLower == 'esdev01' || idLower == 'devadm01' || idLower == 'developer') {
      return EchosphereUser(
        id: 7,
        fullName: 'Dev Admin',
        role: 'Dev Admin',
        officialEmail: 'rrakshu60@gmail.com',
        employeeId: 'ESDev01',
        department: 'Dev Operations',
      );
    }

    return null;
  }
}
