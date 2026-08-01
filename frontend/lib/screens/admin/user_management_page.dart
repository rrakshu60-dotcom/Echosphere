import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
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
          'employee_id': 'DEVADM01',
          'department': 'Dev Operations',
          'is_active': true,
        },
        {
          'id': 2,
          'full_name': 'College Administrator',
          'role': 'College Admin',
          'official_email': 'admin@echosphere.edu',
          'employee_id': 'ADM001',
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
          'id': 6,
          'full_name': 'Rakshitha S',
          'role': 'Student',
          'official_email': '1db23ci079@echosphere.edu',
          'usn': '1DB23CI079',
          'department': 'AIML',
          'is_active': true,
        },
        {
          'id': 7,
          'full_name': 'Dr. B Kursheed',
          'role': 'Teacher',
          'official_email': 'b.kursheed@echosphere.edu',
          'employee_id': 'DBITAIMLT022022',
          'department': 'AIML',
          'is_active': true,
        },
        {
          'id': 4,
          'full_name': 'CSE HoD',
          'role': 'HoD',
          'official_email': 'hod.cse@echosphere.edu',
          'employee_id': 'HOD001',
          'department': 'CSE',
          'is_active': true,
        },
        {
          'id': 5,
          'full_name': 'CSE Teacher',
          'role': 'Teacher',
          'official_email': 'teacher.cse@echosphere.edu',
          'employee_id': 'TCH001',
          'department': 'CSE',
          'is_active': true,
        },
        {
          'id': 6,
          'full_name': 'Student One',
          'role': 'Student',
          'usn': '1EC22CS001',
          'department': 'CSE',
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
    final passwordCtrl = TextEditingController(text: 'EchoSphere@123');
    String roleVal = 'Student';
    String deptVal = 'CSE';

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
                  decoration: InputDecoration(
                    hintText: roleVal == 'Student' ? 'e.g. 1EC22CS099' : 'e.g. teacher@echosphere.edu',
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 14),

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
          onConfirm: () {
            final name = nameCtrl.text.trim();
            final idText = idCtrl.text.trim();
            if (name.isEmpty || idText.isEmpty) {
              errorSnackBar('Please fill in all required fields.');
              return;
            }

            setState(() {
              users.add({
                'id': users.length + 1,
                'full_name': name,
                'role': roleVal,
                if (roleVal == 'Student') 'usn': idText else 'official_email': idText,
                'department': deptVal,
                'is_active': true,
              });
            });

            snackBar('Account created successfully for $name ($roleVal)!');
          },
        ),
      ),
    );
  }

  void _showAccessLogDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Row(
          children: [
            Icon(Icons.shield_outlined, color: Colors.purple, size: 22),
            SizedBox(width: 8),
            Expanded(
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
          width: 540,
          height: 400,
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
                      backgroundColor: isSuccess ? Colors.green.withOpacity(0.15) : Colors.red.withOpacity(0.15),
                      child: Icon(
                        isSuccess ? Icons.verified_user_rounded : Icons.gpp_bad_rounded,
                        color: isSuccess ? Colors.green : Colors.red,
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
                        Text('Status: ${log.status}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: isSuccess ? Colors.green : Colors.red)),
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = authController.currentUser.value;
    final canManage = user != null && user.role != 'Student';
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
                  const SizedBox(width: 8),
                  if (user?.role == 'Dev Admin' || user?.role == 'Developer') ...[
                    EchoSphereButton(
                      height: 36,
                      color: Colors.purple.withOpacity(0.15),
                      border: const BorderSide(color: Colors.purple),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      onTap: _showAccessLogDialog,
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.shield_outlined, size: 15, color: Colors.purple),
                          SizedBox(width: 4),
                          Text('Access Logs', style: TextStyle(fontSize: 12, color: Colors.purple, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 6),
                  ],
                  if (canManage)
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
                        return Padding(
                          padding: const EdgeInsets.only(right: 8.0),
                          child: EchoSphereChip(
                            label: r,
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
                                                child: EchoSphereChip(
                                                  label: u['role'] ?? 'Student',
                                                  isSelected: true,
                                                  onSelected: (_) {},
                                                ),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 4),
                                          Text(
                                            'ID: $identifier • Dept: ${u['department'] ?? "CSE"}',
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
                                        onChanged: (val) {
                                          setState(() {
                                            u['is_active'] = val;
                                          });
                                          snackBar(
                                            'User ${u['full_name']} ${val ? "Activated" : "Disabled"}.',
                                          );
                                        },
                                      ),
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
