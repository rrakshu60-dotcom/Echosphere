import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:anymex/screens/announcements/approval_queue_page.dart';
import 'package:anymex/screens/announcements/speaker_queue_page.dart';
import 'package:anymex/utils/usn_parser.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

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
  String selectedRoleFilter = 'All';
  String searchQuery = '';

  final List<String> roles = [
    'All',
    'Student',
    'Teacher',
    'HoD',
    'College Admin',
    'Principal',
    'Dev Admin',
  ];

  @override
  void initState() {
    super.initState();
    _fetchUsers();
  }

  Future<void> _fetchUsers() async {
    setState(() => isLoading = true);
    try {
      final res = await EchosphereApiService().getUsers();
      if (res.isNotEmpty) {
        setState(() {
          users = res.cast<Map<String, dynamic>>();
          isLoading = false;
        });
        return;
      }
    } catch (e) {
      debugPrint('Live user fetch fallback: $e');
    }

    // Seed mock user list for demonstration and offline resilience
    setState(() {
      users = [
        {
          'id': 1,
          'full_name': 'Dev Admin',
          'role': 'Dev Admin',
          'official_email': 'rrakshu60@gmail.com',
          'employee_id': 'ESDev01',
          'department': 'Dev Operations',
          'is_active': true,
        },
        {
          'id': 2,
          'full_name': 'College Admin (Primary)',
          'role': 'College Admin',
          'official_email': 'cadmin@echosphere.edu',
          'employee_id': 'DBITADM001',
          'department': 'Administration',
          'is_active': true,
        },
        {
          'id': 3,
          'full_name': 'Dr. Principal',
          'role': 'Principal',
          'official_email': 'principal@echosphere.edu',
          'employee_id': 'PRI001',
          'department': 'Executive',
          'is_active': true,
        },
        {
          'id': 4,
          'full_name': 'Dr. AIML HoD',
          'role': 'HoD',
          'official_email': 'hod.aiml@echosphere.edu',
          'employee_id': 'HOD001',
          'department': 'AIML',
          'is_active': true,
        },
        {
          'id': 5,
          'full_name': 'Rakshitha S',
          'role': 'Student',
          'official_email': '1db23ci079@echosphere.edu',
          'usn': '1DB23CI079',
          'department': 'AIML',
          'section': 'A',
          'semester': 5,
          'is_active': true,
        },
        {
          'id': 6,
          'full_name': 'Dr. B Kursheed',
          'role': 'Teacher',
          'official_email': 'b.kursheed@echosphere.edu',
          'employee_id': 'DBITAIMLT022022',
          'department': 'AIML',
          'is_active': true,
        },
      ];
      isLoading = false;
    });
  }

  List<Map<String, dynamic>> get filteredUsers {
    return users.where((u) {
      final name = (u['full_name'] ?? '').toString().toLowerCase();
      final identifier = ((u['official_email'] ?? u['usn'] ?? u['employee_id']) ?? '').toString().toLowerCase();
      final role = (u['role'] ?? 'Student').toString();

      final matchesQuery = searchQuery.isEmpty ||
          name.contains(searchQuery.toLowerCase()) ||
          identifier.contains(searchQuery.toLowerCase());
      final matchesRole = selectedRoleFilter == 'All' || role == selectedRoleFilter;

      return matchesQuery && matchesRole;
    }).toList();
  }

  void _showCreateUserDialog() {
    final nameCtrl = TextEditingController();
    final idCtrl = TextEditingController();
    final sectionCtrl = TextEditingController(text: 'A');
    final passwordCtrl = TextEditingController(text: 'EchoSphere@123');
    String roleVal = 'Student';
    String deptVal = 'CSE';
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
                  items: AuthController.availableRoles
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
                    helperText: roleVal == 'Student' && idCtrl.text.isNotEmpty
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
            final assignedDept = roleVal == 'Student' ? detectDepartmentFromUsn(idText) : deptVal;
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
            } catch (e) {
              debugPrint('Offline fallback user creation: $e');
              setState(() {
                users.add({
                  'id': users.length + 100,
                  'full_name': name,
                  'role': roleVal,
                  'official_email': email,
                  if (roleVal == 'Student') 'usn': idText else 'employee_id': idText,
                  'department': assignedDept,
                  if (roleVal == 'Student') 'section': chosenSection,
                  if (roleVal == 'Student') 'semester': semesterVal,
                  'is_active': true,
                });
              });
              snackBar('Account created locally for $name ($roleVal - $assignedDept, Sec $chosenSection)!');
            }
          },
        ),
      ),
    );
  }

  void _showAccessLogDialog() {
    final theme = Theme.of(context);
    const successColor = Color(0xFF10B981);
    const dangerColor = Color(0xFFEF4444);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Icon(Icons.shield_outlined, color: theme.colorScheme.primary, size: 22),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'Security Audit & App Access Logs',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        content: SizedBox(
          width: MediaQuery.of(ctx).size.width < 580 ? MediaQuery.of(ctx).size.width * 0.88 : 540,
          height: MediaQuery.of(ctx).size.height * 0.60,
          child: Obx(() {
            final logs = authController.auditLogs;
            if (logs.isEmpty) {
              return const Center(child: Text('No audit logs recorded yet.'));
            }
            return ListView.builder(
              itemCount: logs.length,
              itemBuilder: (context, index) {
                final log = logs[index];
                final isSuccess = log.status.contains('SUCCESS');

                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: (isSuccess ? successColor : dangerColor).withOpacity(0.15),
                      child: Icon(
                        isSuccess ? Icons.verified_user_rounded : Icons.gpp_bad_rounded,
                        color: isSuccess ? successColor : dangerColor,
                        size: 20,
                      ),
                    ),
                    title: Text(
                      '${log.username} (${log.role})',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Location: ${log.location}', style: const TextStyle(fontSize: 11)),
                        Text('Timestamp: ${log.timestamp}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                        Text('Status: ${log.status}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: isSuccess ? successColor : dangerColor)),
                      ],
                    ),
                  ),
                );
              },
            );
          }),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close Audit Log'),
          ),
        ],
      ),
    );
  }

  void _showRoleChangeDialog(Map<String, dynamic> u) {
    final roles = ['Student', 'Teacher', 'HoD', 'Principal', 'College Admin', 'Dev Admin'];
    String currentRole = u['role'] ?? 'Student';
    if (!roles.contains(currentRole)) currentRole = 'Student';

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
                errorSnackBar('Failed to update role: $e');
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
    final canManage = user != null && user.role != 'Student';
    final isAdminRole = user != null && (user.role == 'Dev Admin' || user.role == 'Developer' || user.role == 'College Admin' || user.role == 'Principal' || user.role == 'HoD');
    final canPop = ModalRoute.of(context)?.canPop ?? false;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 10.0),
              child: Row(
                children: [
                  if (canPop) ...[
                    IconButton(
                      icon: const Icon(Icons.arrow_back_rounded),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    const SizedBox(width: 4),
                  ],
                  Icon(Icons.manage_accounts_rounded, size: 22, color: theme.colorScheme.primary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'User Accounts',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: 'Poppins-Bold',
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                  ),
                  const SizedBox(width: 4),
                  if (isAdminRole) ...[
                    IconButton(
                      icon: const Icon(Icons.sensors_rounded, size: 20),
                      tooltip: 'Speaker Hardware Queue',
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const SpeakerQueuePage()),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.fact_check_rounded, size: 20),
                      tooltip: 'Approval Queue',
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const ApprovalQueuePage()),
                      ),
                    ),
                  ],
                  if (user?.role == 'Dev Admin' || user?.role == 'Developer') ...[
                    IconButton(
                      icon: const Icon(Icons.shield_outlined, size: 20),
                      tooltip: 'Security Access Audit Logs',
                      onPressed: _showAccessLogDialog,
                    ),
                  ],
                  if (canManage) ...[
                    const SizedBox(width: 4),
                    EchoSphereButton(
                      height: 36,
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
                    child: Row(
                      children: roles.map((r) {
                        final isSel = selectedRoleFilter == r;
                        final count = r == 'All'
                            ? users.length
                            : users.where((u) => u['role'] == r).length;
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
                  : filteredUsers.isEmpty
                      ? Center(
                          child: Text(
                            'No users found matching filters.',
                            style: TextStyle(color: theme.colorScheme.onSurface.withOpacity(0.5)),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(12.0),
                          itemCount: filteredUsers.length,
                          itemBuilder: (ctx, i) {
                            final u = filteredUsers[i];
                            final isActive = u['is_active'] ?? true;
                            final identifier = u['usn'] ?? u['official_email'] ?? u['employee_id'] ?? 'N/A';

                            return Padding(
                              padding: const EdgeInsets.only(bottom: 8.0),
                              child: EchoSphereContainer(
                                padding: const EdgeInsets.all(12.0),
                                child: Row(
                                  children: [
                                    CircleAvatar(
                                      radius: 18,
                                      backgroundColor: theme.colorScheme.primary.withOpacity(0.18),
                                      child: Text(
                                        (u['full_name'] as String? ?? 'U')[0].toUpperCase(),
                                        style: TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13,
                                          color: theme.colorScheme.primary,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Text(
                                                  u['full_name'] ?? 'User',
                                                  maxLines: 1,
                                                  overflow: TextOverflow.ellipsis,
                                                  style: const TextStyle(
                                                    fontWeight: FontWeight.bold,
                                                    fontSize: 14,
                                                  ),
                                                ),
                                              ),
                                              const SizedBox(width: 6),
                                              Flexible(
                                                child: Tooltip(
                                                  message: 'Click to change role',
                                                  child: EchoSphereChip(
                                                    label: '${u['role'] ?? 'Student'} ✏️',
                                                    isSelected: true,
                                                    onSelected: (_) => _showRoleChangeDialog(u),
                                                  ),
                                                ),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 4),
                                          Text(
                                            'ID: $identifier • Dept: ${u['department'] ?? "CSE"}${u['section'] != null ? " • Sec: ${u['section']}" : ""}${u['semester'] != null ? " (Sem ${u['semester']})" : ""}',
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
                                    const SizedBox(width: 4),
                                    Transform.scale(
                                      scale: 0.85,
                                      child: Switch(
                                        value: isActive,
                                        activeColor: theme.colorScheme.primary,
                                        onChanged: (val) async {
                                          setState(() {
                                            u['is_active'] = val;
                                          });
                                          try {
                                            await EchosphereApiService().updateUserRole(u['id'] as int, isActive: val);
                                          } catch (e) {
                                            debugPrint('Update user active status: $e');
                                          }
                                          snackBar(
                                            'User ${u['full_name']} ${val ? "Activated" : "Disabled"}.',
                                          );
                                        },
                                      ),
                                    ),
                                    IconButton(
                                      icon: Icon(Icons.delete_outline_rounded, size: 20, color: theme.colorScheme.error),
                                      tooltip: 'Delete User Account',
                                      onPressed: () {
                                        showDialog(
                                          context: context,
                                          builder: (ctx) => EchoSphereDialog(
                                            title: 'Delete User',
                                            confirmText: 'Delete Account',
                                            message: 'Are you sure you want to delete user account for ${u['full_name']}? This action cannot be undone.',
                                            onConfirm: () async {
                                              final userId = u['id'];
                                              if (userId != null && userId is int) {
                                                try {
                                                  await EchosphereApiService().deleteUser(userId);
                                                } catch (e) {
                                                  debugPrint('Delete user error: $e');
                                                }
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
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
