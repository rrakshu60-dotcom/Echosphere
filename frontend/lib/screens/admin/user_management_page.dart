import 'package:echosphere/constants/themes.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_button.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_chip.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_container.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:echosphere/screens/announcements/approval_queue_page.dart';
import 'package:echosphere/screens/announcements/speaker_queue_page.dart';
import 'package:echosphere/screens/admin/announcement_management_page.dart';
import 'package:echosphere/screens/admin/audit_logs_page.dart';
import 'package:echosphere/utils/navigation_helper.dart';
import 'package:echosphere/utils/usn_parser.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:dio/dio.dart';

class UserManagementPage extends StatefulWidget {
  const UserManagementPage({super.key});

  @override
  State<UserManagementPage> createState() => _UserManagementPageState();
}

class _UserManagementPageState extends State<UserManagementPage> {
  final AuthController authController = Get.find<AuthController>();
  final TextEditingController searchController = TextEditingController();

  List<Map<String, dynamic>> users = [];
  bool isLoading = true;
  String? errorMessage;
  String selectedRoleFilter = 'All';
  String searchQuery = '';

  List<String> get dynamicRoles {
    final defaultList = [
      'All',
      'Student',
      'Teacher',
      'HoD',
      'College Admin',
      'Principal',
      'Dev Admin',
    ];
    final present = users
        .map((u) => (u['role'] ?? 'Student').toString())
        .where((r) => r.isNotEmpty)
        .toSet();
    final result = <String>[...defaultList];
    for (final r in present) {
      if (!result.contains(r)) result.add(r);
    }
    return result;
  }

  // Who may create, change or delete which accounts; the server enforces the same rules.
  // Every staff role can view the whole directory. HoDs and Teachers only change their own department.
  static const Map<String, List<String>> _manageableByRole = {
    'College Admin': ['Student', 'Teacher', 'HoD'],
    'Admin': ['Student', 'Teacher', 'HoD'],
    'Principal': ['Student', 'Teacher', 'HoD'],
    'HoD': ['Student', 'Teacher'],
    'Teacher': ['Student'],
  };
  static const Set<String> _departmentScopedRoles = {'HoD', 'Teacher'};

  String get _myRole => authController.currentUser.value?.role ?? 'Student';

  bool get _isDepartmentScoped => _departmentScopedRoles.contains(_myRole);

  /// Roles this user may create, give or manage.
  List<String> get _assignableRoles {
    if (AuthController.getRoleLevel(_myRole) >= AuthController.getRoleLevel('Dev Admin')) {
      return AuthController.availableRoles;
    }
    final allowed = _manageableByRole[_myRole] ?? const <String>[];
    if (_isDepartmentScoped && authController.currentUser.value?.departmentId == null) return const [];
    return AuthController.availableRoles.where(allowed.contains).toList();
  }

  /// Whether this user may change or delete the given account (never their own).
  bool _canManageUser(Map<String, dynamic> u) {
    final me = authController.currentUser.value;
    if (me == null || u['id'] == me.id) return false;
    if (!_assignableRoles.contains((u['role'] ?? 'Student').toString())) return false;
    return !_isDepartmentScoped || u['department_id'] == me.departmentId;
  }

  String _apiError(Object e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map && data['detail'] != null) return data['detail'].toString();
    }
    return e.toString().replaceFirst('Exception: ', '');
  }

  @override
  void initState() {
    super.initState();
    _fetchUsers();
  }

  Future<void> _fetchUsers() async {
    setState(() {
      isLoading = true;
      errorMessage = null;
    });
    try {
      final res = await EchosphereApiService().getUsers();
      setState(() {
        users = res.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        isLoading = false;
        errorMessage = null;
      });
    } catch (e) {
      debugPrint('Live user fetch error: $e');
      String msg = 'Unable to connect to the campus user service. Please verify server connectivity or administrator credentials.';
      if (e is DioException) {
        if (e.response?.statusCode == 401 || e.response?.statusCode == 403) {
          msg = 'Access Denied: You do not have administrative privileges to manage campus accounts.';
        } else if (e.response?.data != null && e.response?.data is Map && (e.response?.data as Map)['detail'] != null) {
          msg = (e.response?.data as Map)['detail'].toString();
        } else if (e.type == DioExceptionType.connectionTimeout ||
            e.type == DioExceptionType.receiveTimeout ||
            e.type == DioExceptionType.connectionError) {
          msg = 'Connection failed: The backend server is unreachable. Please verify network connectivity or host status.';
        }
      }
      setState(() {
        users = [];
        isLoading = false;
        errorMessage = msg;
      });
    }
  }

  List<Map<String, dynamic>> get filteredUsers {
    final q = searchQuery.toLowerCase().trim();
    return users.where((u) {
      final name = (u['full_name'] ?? '').toString().toLowerCase();
      final identifier = ((u['official_email'] ?? u['usn'] ?? u['employee_id']) ?? '').toString().toLowerCase();
      final dept = (u['department'] ?? '').toString().toLowerCase();
      final section = (u['section'] ?? '').toString().toLowerCase();
      final role = (u['role'] ?? 'Student').toString();

      final matchesQuery = q.isEmpty ||
          name.contains(q) ||
          identifier.contains(q) ||
          dept.contains(q) ||
          section.contains(q) ||
          role.toLowerCase().contains(q);
      final matchesRole = selectedRoleFilter == 'All' || role.toLowerCase() == selectedRoleFilter.toLowerCase();

      return matchesQuery && matchesRole;
    }).toList();
  }

  void _showCreateUserDialog() {
    final nameCtrl = TextEditingController();
    final idCtrl = TextEditingController();
    final sectionCtrl = TextEditingController(text: 'A');
    final passwordCtrl = TextEditingController(text: 'EchoSphere@123');
    final roles = _assignableRoles;
    if (roles.isEmpty) return;
    String roleVal = roles.contains('Student') ? 'Student' : roles.first;
    final ownDept = authController.currentUser.value?.department;
    String deptVal = _isDepartmentScoped ? (ownDept ?? 'CSE') : 'CSE';
    int semesterVal = 5;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) => EchoSphereDialog(
          title: 'Create User Account',
          contentWidget: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('User Role', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 6),
                EchoSphereDropdown(
                  label: 'Role',
                  icon: Icons.badge,
                  selectedItem: DropdownItem(value: roleVal, text: roleVal),
                  items: roles
                      .map((r) => DropdownItem(value: r, text: r))
                      .toList(),
                  onChanged: (item) => setDlgState(() => roleVal = item.value),
                ),
                const SizedBox(height: 14),

                const Text('Full Name', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(
                    hintText: 'e.g. John Doe',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 14),

                Text(
                  roleVal == 'Student' ? 'USN (University Seat Number)' : 'Official Email / Employee ID',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                ),
                const SizedBox(height: 6),
                TextField(
                  controller: idCtrl,
                  onChanged: (_) => setDlgState(() {}),
                  decoration: InputDecoration(
                    hintText: roleVal == 'Student' ? 'e.g. 1DB23IS045 or 1DB23EC088' : 'e.g. teacher@echosphere.edu',
                    border: const OutlineInputBorder(),
                    helperText: _isDepartmentScoped
                        ? 'Department: ${ownDept ?? "your department"} (you can only add accounts to your own department)'
                        : roleVal == 'Student' && idCtrl.text.isNotEmpty
                            ? 'Auto-Detected Department: ${detectDepartmentFromUsn(idCtrl.text)}'
                            : null,
                    helperStyle: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                if (roleVal == 'Student') ...[
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Semester', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                            const SizedBox(height: 6),
                            EchoSphereDropdown(
                              label: 'Semester',
                              icon: Icons.numbers,
                              selectedItem: DropdownItem(value: semesterVal.toString(), text: 'Semester $semesterVal'),
                              items: List.generate(8, (i) => DropdownItem(value: (i + 1).toString(), text: 'Semester ${i + 1}')),
                              onChanged: (item) => setDlgState(() => semesterVal = int.parse(item.value)),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Section (e.g. A, B, C)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                            const SizedBox(height: 6),
                            TextField(
                              controller: sectionCtrl,
                              textCapitalization: TextCapitalization.characters,
                              decoration: const InputDecoration(
                                hintText: 'e.g. A, B, C',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                ],

                const Text('Initial Password', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(
                  controller: passwordCtrl,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          onConfirm: () async {
            final name = nameCtrl.text.trim();
            final idText = idCtrl.text.trim();
            final pwdText = passwordCtrl.text.trim();
            final sectionText = sectionCtrl.text.trim().toUpperCase();

            if (name.isEmpty || idText.isEmpty) {
              errorSnackBar('Please fill in all required fields.');
              return;
            }

            final email = idText.contains('@') ? idText : '$idText@echosphere.edu';
            final pass = pwdText.isNotEmpty ? pwdText : 'EchoSphere@2026';
            final assignedDept = roleVal == 'Student' && !_isDepartmentScoped ? detectDepartmentFromUsn(idText) : deptVal;
            final chosenSection = sectionText.isNotEmpty ? sectionText : 'A';

            try {
              final created = await EchosphereApiService().createUser(
                fullName: name,
                officialEmail: email,
                password: pass,
                roleName: roleVal,
                usn: roleVal == 'Student' ? idText : null,
                employeeId: roleVal != 'Student' ? idText : null,
                semester: roleVal == 'Student' ? semesterVal : null,
                section: roleVal == 'Student' ? chosenSection : null,
              );
              setState(() {
                users.add(created);
              });
              snackBar('Account created successfully for $name ($roleVal - $assignedDept, Sec $chosenSection)!');
              _fetchUsers();
            } catch (e) {
              debugPrint('Create user error: $e');
              errorSnackBar('Could not create the account: ${_apiError(e)}');
            }
          },
        ),
      ),
    );
  }

  void _showRoleChangeDialog(Map<String, dynamic> u) {
    final roles = _assignableRoles;
    if (roles.isEmpty) return;
    String currentRole = u['role'] ?? 'Student';
    if (!roles.contains(currentRole)) currentRole = roles.first;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => EchoSphereDialog(
          title: 'Change User Role',
          contentWidget: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Select new role for ${u['full_name']}:', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: roles.map((role) {
                    final isSel = currentRole == role;
                    return ChoiceChip(
                      label: Text(role, style: TextStyle(fontSize: 12, color: isSel ? Colors.white : null)),
                      selected: isSel,
                      selectedColor: Theme.of(context).colorScheme.primary,
                      onSelected: (selected) {
                        if (selected) {
                          setDialogState(() => currentRole = role);
                        }
                      },
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
          onConfirm: () async {
            final userId = u['id'];
            if (userId != null && userId is int) {
              try {
                await EchosphereApiService().updateUserRole(userId, roleName: currentRole);
                setState(() {
                  u['role'] = currentRole;
                });
                snackBar('User role updated to $currentRole.');
              } catch (e) {
                errorSnackBar('Failed to update role: ${_apiError(e)}');
              }
            }
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = authController.currentUser.value;
    final isStudent = authController.isStudent;

    if (isStudent || user == null) {
      final canPop = ModalRoute.of(context)?.canPop ?? false;
      return SubPagePopScope(
        fallbackRoute: '/home',
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            leading: canPop ? const EchoSphereBackButton(fallbackRoute: '/home') : null,
            title: const EchoSphereText(
              text: 'Access Restricted',
              size: 16,
              variant: TextVariant.bold,
            ),
          ),
          body: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: EchoSphereContainer(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary.withOpacity(0.12),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.gpp_bad_rounded,
                        size: 48,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                    const SizedBox(height: 16),
                    const EchoSphereText(
                      text: 'User Directory & Account Management',
                      size: 16,
                      variant: TextVariant.bold,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      "I don't have the authority to display the administrative user directory and role management console. Please consult your college administrator.",
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.onSurface.withOpacity(0.7),
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 20),
                    EchoSphereButton(
                      onTap: () {
                        if (canPop) {
                          Navigator.of(context).pop();
                        } else {
                          Get.offAllNamed('/home');
                        }
                      },
                      child: const EchoSphereText(
                        text: 'Return to Dashboard',
                        size: 12,
                        variant: TextVariant.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    final canCreate = _assignableRoles.isNotEmpty;
    final isAdminRole = (user.role == 'Dev Admin' || user.role == 'Developer' || user.role == 'College Admin' || user.role == 'Principal' || user.role == 'HoD');

    return SubPagePopScope(
      fallbackRoute: '/home',
      child: Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const EchoSphereBackButton(fallbackRoute: '/home'),
                      const SizedBox(width: 4),
                      Icon(Icons.manage_accounts_rounded, size: 22, color: theme.colorScheme.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'User Accounts',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: theme.colorScheme.onSurface,
                              ),
                            ),
                            Text(
                              isLoading
                                  ? 'Updating campus directory...'
                                  : '${users.length} registered \u2022 ${filteredUsers.length} shown',
                              style: TextStyle(
                                fontSize: 11,
                                color: theme.colorScheme.onSurface.withOpacity(0.55),
                              ),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                        padding: EdgeInsets.zero,
                        icon: const Icon(Icons.refresh_rounded, size: 20),
                        tooltip: 'Refresh directory',
                        onPressed: isLoading ? null : _fetchUsers,
                      ),
                      if (canCreate) ...[
                        const SizedBox(width: 6),
                        EchoSphereButton(
                          height: 34,
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          onTap: _showCreateUserDialog,
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.person_add_rounded, size: 15),
                              SizedBox(width: 4),
                              Text('Create', style: TextStyle(fontSize: 12)),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                  if (isAdminRole) ...[
                    const SizedBox(height: 6),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      physics: const BouncingScrollPhysics(),
                      child: Row(
                        children: [
                          IconButton(
                            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                            padding: const EdgeInsets.all(6),
                            icon: const Icon(Icons.sensors_rounded, size: 18),
                            tooltip: 'Speaker Hardware Queue',
                            onPressed: () => Navigator.of(context).push(
                              MaterialPageRoute(builder: (_) => const SpeakerQueuePage()),
                            ),
                          ),
                          IconButton(
                            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                            padding: const EdgeInsets.all(6),
                            icon: const Icon(Icons.fact_check_rounded, size: 18),
                            tooltip: 'Approval Queue',
                            onPressed: () => Navigator.of(context).push(
                              MaterialPageRoute(builder: (_) => const ApprovalQueuePage()),
                            ),
                          ),
                          IconButton(
                            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                            padding: const EdgeInsets.all(6),
                            icon: const Icon(Icons.auto_fix_high_rounded, size: 18),
                            tooltip: 'Notice Moderation',
                            onPressed: () => Navigator.of(context).push(
                              MaterialPageRoute(builder: (_) => const AnnouncementManagementPage()),
                            ),
                          ),
                          if (canOpenAuditLogs(user.role))
                            IconButton(
                              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                              padding: const EdgeInsets.all(6),
                              icon: const Icon(Icons.shield_outlined, size: 18),
                              tooltip: 'Audit & Logs',
                              onPressed: () => Get.toNamed('/audit-logs?tab=signIns'),
                            ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const Divider(height: 1),

            // Search and Role Filters
            Padding(
              padding: const EdgeInsets.all(12.0),
              child: Column(
                children: [
                  TextField(
                    controller: searchController,
                    onChanged: (val) => setState(() => searchQuery = val),
                    decoration: InputDecoration(
                      isDense: true,
                      hintText: 'Search users...',
                      hintStyle: TextStyle(
                        fontSize: 13,
                        color: theme.colorScheme.onSurface.withOpacity(0.5),
                      ),
                      prefixIcon: Padding(
                        padding: const EdgeInsets.only(left: 12, right: 8),
                        child: Icon(Icons.search, size: 20, color: theme.colorScheme.primary),
                      ),
                      prefixIconConstraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                      filled: true,
                      fillColor: theme.colorScheme.primary.withOpacity(0.12),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: theme.colorScheme.primary.withOpacity(0.25), width: 1),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: theme.colorScheme.primary.withOpacity(0.25), width: 1),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: theme.colorScheme.primary, width: 1.5),
                      ),
                      contentPadding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                  ),
                  const SizedBox(height: 10),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    physics: const BouncingScrollPhysics(),
                    child: Row(
                      children: dynamicRoles.map((r) {
                        final isSel = selectedRoleFilter.toLowerCase() == r.toLowerCase();
                        final count = r == 'All'
                            ? users.length
                            : users.where((u) => (u['role'] ?? '').toString().toLowerCase() == r.toLowerCase()).length;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8.0),
                          child: EchoSphereChip(
                            label: '$r ($count)',
                            isSelected: isSel,
                            onSelected: (val) {
                              if (val) setState(() => selectedRoleFilter = r);
                            },
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),

            // User List
            Expanded(
              child: isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : errorMessage != null
                      ? RefreshIndicator(
                          onRefresh: _fetchUsers,
                          child: SingleChildScrollView(
                            physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
                            child: Container(
                              alignment: Alignment.center,
                              padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 48.0),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(18),
                                    decoration: BoxDecoration(
                                      color: (theme.brightness == Brightness.dark
                                              ? EchoSpherePalette.darkDestructive
                                              : EchoSpherePalette.lightDestructive)
                                          .withOpacity(0.12),
                                      shape: BoxShape.circle,
                                      border: Border.all(
                                        color: (theme.brightness == Brightness.dark
                                                ? EchoSpherePalette.darkDestructive
                                                : EchoSpherePalette.lightDestructive)
                                            .withOpacity(0.25),
                                        width: 1.5,
                                      ),
                                    ),
                                    child: Icon(
                                      Icons.cloud_off_rounded,
                                      size: 42,
                                      color: theme.brightness == Brightness.dark
                                          ? EchoSpherePalette.darkDestructive
                                          : EchoSpherePalette.lightDestructive,
                                    ),
                                  ),
                                  const SizedBox(height: 18),
                                  Text(
                                    'Failed to Load Campus Users',
                                    style: TextStyle(
                                      fontSize: 17,
                                      fontWeight: FontWeight.bold,
                                      color: theme.colorScheme.onSurface,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  ConstrainedBox(
                                    constraints: const BoxConstraints(maxWidth: 380),
                                    child: Text(
                                      errorMessage!,
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                        fontSize: 13,
                                        height: 1.4,
                                        color: theme.colorScheme.onSurface.withOpacity(0.65),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 24),
                                  EchoSphereButton(
                                    height: 42,
                                    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                                    onTap: _fetchUsers,
                                    child: const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.refresh_rounded, size: 18),
                                        SizedBox(width: 8),
                                        Flexible(
                                          child: Text(
                                            'Retry Connection',
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        )
                      : filteredUsers.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24.0),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.person_search_rounded, size: 48, color: theme.colorScheme.onSurface.withOpacity(0.3)),
                                const SizedBox(height: 12),
                                Text(
                                  searchQuery.isNotEmpty || selectedRoleFilter != 'All'
                                      ? 'No campus members match your search filter.'
                                      : 'No campus accounts found.',
                                  style: TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: theme.colorScheme.onSurface.withOpacity(0.7),
                                  ),
                                ),
                                if (searchQuery.isNotEmpty || selectedRoleFilter != 'All') ...[
                                  const SizedBox(height: 12),
                                  TextButton.icon(
                                    onPressed: () {
                                      setState(() {
                                        searchController.clear();
                                        searchQuery = '';
                                        selectedRoleFilter = 'All';
                                      });
                                    },
                                    icon: const Icon(Icons.clear_all_rounded, size: 16),
                                    label: const Text('Clear Filters'),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _fetchUsers,
                          child: ListView.builder(
                            physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
                            padding: const EdgeInsets.all(12.0),
                            itemCount: filteredUsers.length,
                            itemBuilder: (ctx, i) {
                              final u = filteredUsers[i];
                              final canManage = _canManageUser(u);

                              return Padding(
                                padding: const EdgeInsets.only(bottom: 8.0),
                                child: UserAccountTile(
                                  user: u,
                                  canManage: canManage,
                                  onRoleTap: () => _showRoleChangeDialog(u),
                                  onActiveChanged: (val) async {
                                    try {
                                      await EchosphereApiService().updateUserRole(u['id'] as int, isActive: val);
                                      setState(() {
                                        u['is_active'] = val;
                                      });
                                      snackBar(
                                        'User ${u['full_name']} ${val ? "Activated" : "Disabled"}.',
                                      );
                                    } catch (e) {
                                      debugPrint('Update user active status: $e');
                                      errorSnackBar('Could not update the account: ${_apiError(e)}');
                                    }
                                  },
                                  onDelete: () {
                                    showDialog(
                                      context: context,
                                      builder: (ctx) => EchoSphereDialog(
                                        title: 'Delete User',
                                        confirmText: 'Delete Account',
                                        message: 'Are you sure you want to delete user account for ${u['full_name']}? This action cannot be undone.',
                                        onConfirm: () async {
                                          final userId = u['id'];
                                          if (userId is! int) return;
                                          try {
                                            await EchosphereApiService().deleteUser(userId);
                                          } catch (e) {
                                            debugPrint('Delete user error: $e');
                                            errorSnackBar('Could not delete the account: ${_apiError(e)}');
                                            return;
                                          }
                                          setState(() {
                                            users.removeWhere((item) => item['id'] == u['id']);
                                          });
                                          snackBar('User account deleted successfully.');
                                        },
                                      ),
                                    );
                                  },
                                ),
                              );
                            },
                          ),
                        ),
            ),
          ],
        ),
      ),
    ),
    );
  }
}


/// One row in the user list: avatar, name, role chip, ID line and (for managers) active switch and delete.
class UserAccountTile extends StatelessWidget {
  final Map<String, dynamic> user;
  final bool canManage;
  final VoidCallback? onRoleTap;
  final ValueChanged<bool>? onActiveChanged;
  final VoidCallback? onDelete;

  const UserAccountTile({
    super.key,
    required this.user,
    required this.canManage,
    this.onRoleTap,
    this.onActiveChanged,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final u = user;
    final bool isActive = u['is_active'] ?? true;
    final identifier = u['usn'] ?? u['official_email'] ?? u['employee_id'] ?? 'N/A';

    return EchoSphereContainer(
      padding: const EdgeInsets.all(12.0),
      child: Row(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: theme.colorScheme.primary.withOpacity(0.18),
            child: Builder(
              builder: (_) {
                final rawName = (u['full_name'] as String?)?.trim() ?? '';
                final initial = rawName.isNotEmpty ? rawName[0].toUpperCase() : 'U';
                return Text(
                  initial,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                    color: theme.colorScheme.primary,
                  ),
                );
              },
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // The name gets the full width; the role chip sits on its own line below it,
                // so neither is squeezed on 320px screens.
                Text(
                  u['full_name'] ?? 'User',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 4),
                Tooltip(
                  message: canManage ? 'Click to change role' : 'Role: ${u['role'] ?? "Student"}',
                  child: EchoSphereChip(
                    label: u['role'] ?? 'Student',
                    icon: canManage ? Icons.edit_rounded : null,
                    isSelected: true,
                    onSelected: (_) {
                      if (canManage) onRoleTap?.call();
                    },
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'ID: $identifier \u2022 Dept: ${u['department'] ?? "CSE"}${u['section'] != null ? " \u2022 Sec: ${u['section']}" : ""}${u['semester'] != null ? " (Sem ${u['semester']})" : ""}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 11,
                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                  ),
                ),
              ],
            ),
          ),
          if (canManage) ...[
            const SizedBox(width: 4),
            // Stacked so the name keeps most of the row width on narrow screens.
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Transform.scale(
                  scale: 0.85,
                  child: Switch(
                    value: isActive,
                    activeColor: theme.colorScheme.primary,
                    onChanged: onActiveChanged,
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.delete_outline_rounded, size: 20, color: theme.colorScheme.error),
                  tooltip: 'Delete User Account',
                  onPressed: onDelete,
                ),
              ],
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: (isActive ? theme.colorScheme.primary : theme.colorScheme.error).withOpacity(0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: (isActive ? theme.colorScheme.primary : theme.colorScheme.error).withOpacity(0.3),
                  width: 0.8,
                ),
              ),
              child: Text(
                isActive ? 'Active' : 'Inactive',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  color: isActive ? theme.colorScheme.primary : theme.colorScheme.error,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
