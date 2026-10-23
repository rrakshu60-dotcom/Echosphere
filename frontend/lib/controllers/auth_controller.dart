import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/screens/auth/login_screen.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/services/fcm_push_service.dart';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/utils/usn_parser.dart';

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

class AuthController extends GetxController {
  final Rxn<EchosphereUser> currentUser = Rxn<EchosphereUser>();
  final RxBool isLoggedIn = false.obs;
  final RxBool isLoading = false.obs;
  final RxBool rememberMe = false.obs;
  final RxString token = ''.obs;


  final RxInt annualPasswordResetCount = 0.obs;

  static const List<String> availableRoles = [
    'Student',
    'Teacher',
    'HoD',
    'College Admin',
    'Principal',
    'Dev Admin',
  ];

  /// Completes once a remembered session (if any) has been restored.
  late final Future<void> sessionRestored;

  @override
  void onInit() {
    super.onInit();
    sessionRestored = _loadSessionFromDisk();
    _purgeLegacyDeviceSignInLog();
    loadResetQuotaFromDisk();
    _purgeLegacyLocalPasswords();
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

  // RBAC Role Helpers
  bool get isStudent {
    final role = (currentUser.value?.role ?? 'Student').trim().toLowerCase();
    return role == 'student';
  }

  bool get isStaffOrFaculty {
    return !isStudent && currentUser.value != null;
  }

  bool get canManageSpeakers {
    if (isStudent || currentUser.value == null) return false;
    final r = (currentUser.value?.role ?? '').trim().toLowerCase();
    return r == 'hod' || r == 'college admin' || r == 'principal' || r == 'dev admin' || r == 'developer' || r == 'teacher';
  }

  bool get canModerateAnnouncements {
    if (isStudent || currentUser.value == null) return false;
    final r = (currentUser.value?.role ?? '').trim().toLowerCase();
    return r == 'hod' || r == 'college admin' || r == 'principal' || r == 'dev admin' || r == 'developer';
  }

  bool get canManageUsers {
    if (isStudent || currentUser.value == null) return false;
    final r = (currentUser.value?.role ?? '').trim().toLowerCase();
    return r == 'college admin' || r == 'principal' || r == 'dev admin' || r == 'developer';
  }

  /// Older builds cached changed passwords in plain text on the device. Remove them.
  Future<void> _purgeLegacyLocalPasswords() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('custom_user_passwords');
    } catch (e) {
      debugPrint('Failed to purge legacy local passwords: $e');
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

    // The server is the only authority on passwords
    final backendSuccess = await EchosphereApiService().updatePassword(
      currentPassword: currentPassword,
      newPassword: newPassword,
      identifier: idKey,
    );

    if (backendSuccess && isRestrictedRole) {
      annualPasswordResetCount.value++;
      await _saveResetQuotaToDisk();
    }


    return backendSuccess;
  }

  /// Restores a remembered session saved by an earlier run.
  Future<void> _loadSessionFromDisk() async {
    final api = EchosphereApiService();
    api.sessions.onSignedOut = _onSessionEndedRemotely;
    final saved = await api.sessions.restore();
    if (saved == null) return;
    rememberMe.value = true;
    currentUser.value = EchosphereUser.fromJson(saved);
    token.value = api.sessions.accessToken ?? '';
    api.setAuthToken(token.value);
    isLoggedIn.value = true;
    FcmPushService.instance.syncUserSubscriptions(
      departmentCode: currentUser.value?.department,
      role: currentUser.value?.role,
    );
  }

  /// The backend ended this session (expired, signed out by an admin, password changed, account disabled).
  void _onSessionEndedRemotely() {
    if (!isLoggedIn.value) return;
    _clearLocalSignIn();
    Get.offAll(() => const LoginScreen());
    Get.snackbar('Signed out', 'Your session has ended. Please sign in again.', snackPosition: SnackPosition.BOTTOM);
  }

  /// Sign-ins used to be logged only on this device; the backend's sign-in log replaces it.
  /// Remove the old copy (it held usernames) from devices that still have it.
  Future<void> _purgeLegacyDeviceSignInLog() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('login_audit_logs');
    } catch (_) {}
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

  /// Whether this login identifier belongs to the College Admin account,
  /// which needs the extra Employee ID verification step before signing in.
  bool isCollegeAdminIdentifier(String identifier) {
    final idLower = identifier.trim().toLowerCase();
    return idLower == 'cadmin' || idLower == 'dbitadm001';
  }

  Future<bool> login({
    required String identifier,
    required String password,
    bool remember = false,
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
          rememberMe: remember,
        );

        final accessToken = res['access_token'] as String?;
        if (accessToken != null) {
          final user = EchosphereUser.fromJson(res);
          await api.sessions.start(res, rememberMe: remember, user: user.toJson());
          token.value = accessToken;
          api.setAuthToken(accessToken);
          currentUser.value = user;
          isLoggedIn.value = true;

          FcmPushService.instance.syncUserSubscriptions(
            departmentCode: user.department,
            role: user.role,
          );


          return true;
        }
      } catch (e) {
        debugPrint('Live backend login error: $e');
      }

      return false;
    } finally {
      isLoading.value = false;
    }
  }

  void logout() async {
    // End the session on the backend first, while the token is still set
    await EchosphereApiService().logoutSession();
    await _clearLocalSignIn();
    Get.offAll(() => const LoginScreen());
  }

  Future<void> _clearLocalSignIn() async {
    final prevUser = currentUser.value;
    if (prevUser != null) {
      FcmPushService.instance.unsubscribeUserSubscriptions(
        departmentCode: prevUser.department,
        role: prevUser.role,
      );
    }
    currentUser.value = null;
    isLoggedIn.value = false;
    token.value = '';
    rememberMe.value = false;
    isLoading.value = false;
    final api = EchosphereApiService();
    api.setAuthToken(null);
    await api.sessions.clear();
    // Clear persisted approval/rejection caches so stale local decisions
    // don't mask server truth on next login
    try {
      if (Get.isRegistered<AnnouncementController>()) {
        await Get.find<AnnouncementController>().clearPersistedApprovalCache();
      }
    } catch (_) {}
  }
}
