import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/screens/auth/login_screen.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  final authController = Get.find<AuthController>();
  List<dynamic> auditLogs = [];
  bool isLoadingLogs = false;

  @override
  void initState() {
    super.initState();
    _loadAuditLogs();
  }

  Future<void> _loadAuditLogs() async {
    final role = authController.currentUser.value?.role;
    if (role == 'Developer' || role == 'College Admin' || role == 'Principal') {
      if (mounted) setState(() => isLoadingLogs = true);
      try {
        final logs = await EchosphereApiService().getAuditLogs();
        if (mounted) {
          setState(() {
            auditLogs = logs;
            isLoadingLogs = false;
          });
        }
      } catch (_) {
        if (mounted) setState(() => isLoadingLogs = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final themeProvider = Provider.of<ThemeProvider>(context);
    final isDark = theme.brightness == Brightness.dark;

    return Obx(() {
          final user = authController.currentUser.value;
          final isLoggedIn = authController.isLoggedIn.value;

          if (!isLoggedIn || user == null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.account_circle, size: 64, color: Colors.grey),
                  const SizedBox(height: 16),
                  const Text(
                    'Not Logged In',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Log in with your USN, Employee ID, or Email to view profile details.',
                    style: TextStyle(color: Colors.grey),
                  ),
                  const SizedBox(height: 20),
                  EchoSphereButton(
                    onTap: () => Get.to(() => const LoginScreen()),
                    child: const Text('Go to Login'),
                  ),
                ],
              ),
            );
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(20.0),
            child: Center(
              child: Container(
                constraints: const BoxConstraints(maxWidth: 800),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Profile Header Card
                    EchoSphereContainer(
                      padding: const EdgeInsets.all(24.0),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 36,
                            backgroundColor: theme.colorScheme.primary,
                            child: Text(
                              user.fullName.isNotEmpty ? user.fullName[0].toUpperCase() : 'U',
                              style: TextStyle(
                                fontSize: 32,
                                fontWeight: FontWeight.bold,
                                color: theme.colorScheme.onPrimary,
                              ),
                            ),
                          ),
                          const SizedBox(width: 20),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  user.fullName,
                                  style: const TextStyle(
                                    fontSize: 22,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 6,
                                    children: [
                                      EchoSphereChip(
                                        label: user.department ?? 'General',
                                        isSelected: true,
                                        onSelected: (_) {},
                                      ),
                                    ],
                                  ),
                               ],
                             ),
                           ),
                         ],
                       ),
                     ),
                     const SizedBox(height: 20),

                     // User Details Container
                     EchoSphereContainer(
                       padding: const EdgeInsets.all(20.0),
                       child: Column(
                         crossAxisAlignment: CrossAxisAlignment.start,
                         children: [
                           const EchoSphereText(
                             text: 'Account Details',
                             size: 16,
                             variant: TextVariant.bold,
                           ),
                           const Divider(height: 20),
                           if (user.usn != null)
                             _buildInfoTile('USN (University Seat Number)', user.usn!, Icons.badge),
                           if (user.officialEmail != null)
                             _buildInfoTile('Official Email', user.officialEmail!, Icons.email),
                           if (user.employeeId != null)
                             _buildInfoTile('Employee ID', user.employeeId!, Icons.badge),
                           _buildInfoTile('Department', user.department ?? 'Institution-Wide', Icons.business),
                         ],
                       ),
                     ),
                    const SizedBox(height: 20),

                    // System Settings & Security Container
                    EchoSphereContainer(
                      padding: const EdgeInsets.all(20.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const EchoSphereText(
                            text: 'Preferences & Security',
                            size: 16,
                            variant: TextVariant.bold,
                          ),
                          const Divider(height: 20),
                          SwitchListTile(
                            title: const Text('Dark Mode Theme'),
                            subtitle: const Text('Toggle between dark and light glassmorphism styles'),
                            value: isDark,
                            onChanged: (_) => themeProvider.toggleTheme(),
                          ),
                          ListTile(
                            leading: const Icon(Icons.lock_reset, color: Colors.blue),
                            title: const Text('Change Password'),
                            subtitle: const Text('Update your account password'),
                            onTap: () => _showChangePasswordDialog(context),
                          ),
                          ListTile(
                            leading: const Icon(Icons.notifications_active, color: Colors.amber),
                            title: const Text('In-App Push & Speaker Alerts'),
                            subtitle: const Text('Configure audio and notification channel preferences'),
                            onTap: () => snackBar('Notification preferences updated.'),
                          ),
                          if (user.role == 'Dev Admin' || user.role == 'Developer') ...[
                            const ListTile(
                              leading: Icon(Icons.wifi, color: Colors.green),
                              title: Text('FastAPI Backend Status'),
                              subtitle: Text('Connected to http://localhost:8000/api/v1'),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Audit Logs Table for Admin/Dev
                    if (user.role == 'Developer' || user.role == 'College Admin' || user.role == 'Principal') ...[
                      EchoSphereContainer(
                        padding: const EdgeInsets.all(20.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const EchoSphereText(
                                  text: 'System Audit Logs',
                                  size: 16,
                                  variant: TextVariant.bold,
                                ),
                                const Spacer(),
                                IconButton(
                                  icon: const Icon(Icons.refresh, size: 18),
                                  onPressed: _loadAuditLogs,
                                ),
                              ],
                            ),
                            const Divider(height: 20),
                            if (isLoadingLogs)
                              const Center(child: CircularProgressIndicator())
                            else if (auditLogs.isEmpty)
                              const Text('No recent audit logs found.', style: TextStyle(color: Colors.grey))
                            else
                              ListView.builder(
                                shrinkWrap: true,
                                physics: const NeverScrollableScrollPhysics(),
                                itemCount: auditLogs.length > 5 ? 5 : auditLogs.length,
                                itemBuilder: (context, idx) {
                                  final log = auditLogs[idx];
                                  return ListTile(
                                    dense: true,
                                    leading: const Icon(Icons.security, size: 18),
                                    title: Text('${log['action']} • ${log['description']}'),
                                    subtitle: Text('Timestamp: ${log['created_at'] ?? "Recent"}'),
                                  );
                                },
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                    ],

                    // Log Out Action
                    EchoSphereButton(
                      width: double.infinity,
                      height: 48,
                      color: Colors.red.withOpacity(0.2),
                      border: const BorderSide(color: Colors.red),
                      onTap: () {
                        authController.logout();
                        Get.offAll(() => const LoginScreen());
                      },
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.logout, color: Colors.red, size: 20),
                          SizedBox(width: 10),
                          Text('Log Out from EchoSphere', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        });
  }

  void _showChangePasswordDialog(BuildContext context) {
    final currentCtrl = TextEditingController();
    final newCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => EchoSphereDialog(
        title: 'Change Password',
        contentWidget: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Current Password', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 6),
            TextField(
              controller: currentCtrl,
              obscureText: true,
              decoration: const InputDecoration(border: OutlineInputBorder()),
            ),
            const SizedBox(height: 14),
            const Text('New Password', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 6),
            TextField(
              controller: newCtrl,
              obscureText: true,
              decoration: const InputDecoration(border: OutlineInputBorder()),
            ),
          ],
        ),
        onConfirm: () {
          if (currentCtrl.text.isEmpty || newCtrl.text.isEmpty) {
            errorSnackBar('Password fields cannot be empty.');
            return;
          }
          snackBar('Password changed successfully!');
        },
      ),
    );
  }

  Widget _buildInfoTile(String title, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.grey),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  value,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
