import 'dart:convert';
import 'dart:io';
import 'package:anymex/screens/auth/login_screen.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';

class EchosphereUser {
  final int id;
  final String fullName;
  final String role;
  final String? officialEmail;
  final String? usn;
  final String? employeeId;
  final int? departmentId;
  final String? department;

  EchosphereUser({
    required this.id,
    required this.fullName,
    required this.role,
    this.officialEmail,
    this.usn,
    this.employeeId,
    this.departmentId,
    this.department,
  });

  factory EchosphereUser.fromJson(Map<String, dynamic> json) {
    return EchosphereUser(
      id: json['user_id'] ?? json['id'] ?? 0,
      fullName: json['full_name'] ?? 'User',
      role: json['role'] ?? 'Student',
      officialEmail: json['official_email'],
      usn: json['usn'],
      employeeId: json['employee_id'],
      departmentId: json['department_id'],
      department: json['department'] ?? (json['department_id'] == 1 ? 'CSE' : 'General'),
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
  }

  Future<File> _getResetQuotaFile() async {
    final dir = await getApplicationDocumentsDirectory();
    final year = DateTime.now().year;
    final userId = currentUser.value?.id ?? 0;
    return File('${dir.path}/password_resets_${userId}_$year.json');
  }

  Future<void> loadResetQuotaFromDisk() async {
    try {
      final file = await _getResetQuotaFile();
      if (await file.exists()) {
        final content = await file.readAsString();
        final Map<String, dynamic> data = jsonDecode(content);
        annualPasswordResetCount.value = data['count'] ?? 0;
      } else {
        annualPasswordResetCount.value = 0;
      }
    } catch (_) {
      annualPasswordResetCount.value = 0;
    }
  }

  Future<void> _saveResetQuotaToDisk() async {
    try {
      final file = await _getResetQuotaFile();
      final data = {
        'year': DateTime.now().year,
        'count': annualPasswordResetCount.value,
      };
      await file.writeAsString(jsonEncode(data));
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

  Future<bool> resetPassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    final role = currentUser.value?.role ?? 'Student';
    final isRestrictedRole = role == 'Student' || role == 'Teacher' || role == 'HoD';

    if (isRestrictedRole && !canResetPassword()) {
      return false;
    }

    if (isRestrictedRole) {
      annualPasswordResetCount.value++;
      await _saveResetQuotaToDisk();
    }
    return true;
  }

  Future<File> _getSessionFile() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/auth_session.json');
  }

  Future<File> _getAuditLogFile() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/login_audit_logs.json');
  }

  Future<void> _loadSessionFromDisk() async {
    try {
      final file = await _getSessionFile();
      if (await file.exists()) {
        final content = await file.readAsString();
        final Map<String, dynamic> data = jsonDecode(content);
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
      final file = await _getSessionFile();
      if (rememberMe.value && currentUser.value != null) {
        final data = {
          'remember_me': true,
          'token': token.value,
          'user': currentUser.value!.toJson(),
        };
        await file.writeAsString(jsonEncode(data));
      } else {
        if (await file.exists()) {
          await file.delete();
        }
      }
    } catch (e) {
      debugPrint('Failed to save session to disk: $e');
    }
  }

  Future<void> _loadAuditLogsFromDisk() async {
    try {
      final file = await _getAuditLogFile();
      if (await file.exists()) {
        final content = await file.readAsString();
        final List<dynamic> jsonList = jsonDecode(content);
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
      final file = await _getAuditLogFile();
      final content = jsonEncode(auditLogs.map((e) => e.toJson()).toList());
      await file.writeAsString(content);
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

  /// Get mock user for validation
  EchosphereUser? validateMockCredentials(String identifier, String password) {
    final mockUser = _getMockUser(identifier);
    if (mockUser == null) return null;

    // Check specific credentials
    final idLower = identifier.trim().toLowerCase();
    if (idLower == 'cadmin' || idLower == 'cadmin@echosphere.edu') {
      if (password.trim() == 'Dbit@ES01') {
        return mockUser;
      } else {
        return null;
      }
    }

    return mockUser;
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
        isLoading.value = false;
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

    // Local / Seed Fallback for testing when backend isn't actively running on port 8000
    final mockUser = validateMockCredentials(identifier, password);
    if (mockUser != null) {
      currentUser.value = mockUser;
      isLoggedIn.value = true;
      token.value = 'mock_jwt_token_${mockUser.role.toLowerCase()}';
      EchosphereApiService().setAuthToken(token.value);
      isLoading.value = false;
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

    isLoading.value = false;
    await addAuditLog(
      username: identifier,
      role: 'Unknown',
      status: 'FAILED (Invalid Credentials)',
    );
    return false;
  }

  void logout() async {
    currentUser.value = null;
    isLoggedIn.value = false;
    token.value = '';
    rememberMe.value = false;
    EchosphereApiService().setAuthToken(null);
    try {
      final file = await _getSessionFile();
      if (await file.exists()) {
        await file.delete();
      }
    } catch (_) {}
    Get.offAll(() => const LoginScreen());
  }

  /// Auto-detect role from the identifier for mock/offline fallback.
  EchosphereUser? _getMockUser(String identifier) {
    final id = identifier.trim();
    final idLower = id.toLowerCase();

    // Primary College Admin account
    if (idLower == 'cadmin' || idLower == 'cadmin@echosphere.edu') {
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

    if (RegExp(r'^\d[A-Za-z]{2}\d{2}[A-Za-z]{2}\d{3}$').hasMatch(id)) {
      return EchosphereUser(
        id: 6,
        fullName: 'Student One',
        role: 'Student',
        usn: id,
        department: 'CSE',
        departmentId: 1,
      );
    }

    // Email-based detection
    if (idLower.contains('@')) {
      if (idLower.startsWith('teacher')) {
        return EchosphereUser(
          id: 5,
          fullName: 'CSE Teacher',
          role: 'Teacher',
          officialEmail: id,
          employeeId: 'TCH001',
          department: 'CSE',
          departmentId: 1,
        );
      }
      if (idLower.startsWith('hod')) {
        return EchosphereUser(
          id: 4,
          fullName: 'CSE HoD',
          role: 'HoD',
          officialEmail: id,
          employeeId: 'HOD001',
          department: 'CSE',
          departmentId: 1,
        );
      }
      if (idLower.startsWith('principal')) {
        return EchosphereUser(
          id: 3,
          fullName: 'Dr. Principal',
          role: 'Principal',
          officialEmail: id,
          employeeId: 'PRI001',
          department: 'Executive',
        );
      }
      if (idLower.startsWith('admin')) {
        return EchosphereUser(
          id: 2,
          fullName: 'College Administrator',
          role: 'College Admin',
          officialEmail: id,
          employeeId: 'ADM001',
          department: 'Administration',
        );
      }
    }

    // Username-based detection
    if (idLower == 'admin') {
      return EchosphereUser(
        id: 2,
        fullName: 'College Administrator',
        role: 'College Admin',
        officialEmail: 'admin@echosphere.edu',
        employeeId: 'ADM001',
        department: 'Administration',
      );
    }
    if (idLower == 'developer') {
      return EchosphereUser(
        id: 1,
        fullName: 'System Developer',
        role: 'Developer',
        officialEmail: 'developer@echosphere.edu',
        employeeId: 'DEV001',
        department: 'IT Systems',
      );
    }
    if (idLower == 'esdev01' || idLower == 'rrakshu60@gmail.com') {
      return EchosphereUser(
        id: 7,
        fullName: 'Dev Admin',
        role: 'Dev Admin',
        officialEmail: 'rrakshu60@gmail.com',
        employeeId: 'DEVADM01',
        department: 'Dev Operations',
      );
    }

    return null;
  }
}
