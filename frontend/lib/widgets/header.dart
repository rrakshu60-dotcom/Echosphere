import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/screens/auth/login_screen.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/screens/admin/announcement_management_page.dart';
import 'package:anymex/screens/admin/user_management_page.dart';
import 'package:anymex/screens/announcements/approval_queue_page.dart';
import 'package:anymex/screens/announcements/speaker_queue_page.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';

enum PageType { manga, anime, home, novel, library, extensions }

class Header extends StatelessWidget {
  final PageType type;
  const Header({super.key, required this.type});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final themeProvider = Provider.of<ThemeProvider>(context);
    final authController = Get.find<AuthController>();
    final isDark = theme.brightness == Brightness.dark;

    final screenWidth = MediaQuery.of(context).size.width;
    final isMobile = screenWidth <= 650;

    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: isMobile ? 12.0 : 16.0,
        vertical: 8.0,
      ),
      child: Row(
        children: [
          // Theme Toggle
          IconButton(
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
            padding: EdgeInsets.zero,
            icon: Icon(
              isDark ? Icons.light_mode : Icons.dark_mode,
              size: isMobile ? 18 : 20,
            ),
            onPressed: () => themeProvider.toggleTheme(),
          ),
          const Spacer(),

          // Centered Logo & Branding
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withOpacity(0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.campaign,
                  color: theme.colorScheme.primary,
                  size: isMobile ? 20 : 22,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'EchoSphere',
                style: TextStyle(
                  fontFamily: 'Poppins-Bold',
                  fontSize: isMobile ? 17 : 19,
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
          ),
          const Spacer(),

          // User Profile & Role Info
          Obx(() {
            final user = authController.currentUser.value;
            if (user == null || !authController.isLoggedIn.value) {
              return EchoSphereButton(
                height: 32,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                onTap: () => Get.to(() => const LoginScreen()),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.login, size: isMobile ? 14 : 16),
                    if (!isMobile) ...[
                      const SizedBox(width: 4),
                      const Text('Login', style: TextStyle(fontSize: 12)),
                    ],
                  ],
                ),
              );
            }

            final isExecutive = user.role == 'Principal' || user.role == 'Developer' || user.role == 'College Admin';
            final isHoD = user.role == 'HoD';

            return Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (isExecutive) ...[
                  IconButton(
                    tooltip: 'Admin Control Hub',
                    constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
                    padding: EdgeInsets.zero,
                    icon: const Icon(Icons.admin_panel_settings_rounded, color: Colors.amber, size: 20),
                    onPressed: () => _showAdminHubSheet(context, user.role),
                  ),
                ] else if (isHoD) ...[
                  IconButton(
                    tooltip: 'Approval Queue',
                    constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
                    padding: EdgeInsets.zero,
                    icon: const Icon(Icons.fact_check_rounded, color: Colors.orange, size: 20),
                    onPressed: () => Get.to(() => const ApprovalQueuePage()),
                  ),
                ],
              ],
            );
          }),
        ],
      ),
    );
  }

  void _showAdminHubSheet(BuildContext context, String role) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.admin_panel_settings_rounded, color: Colors.amber, size: 22),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Admin Control Hub',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const Divider(height: 20),
              ListTile(
                leading: const Icon(Icons.auto_fix_high_rounded, color: Colors.amber),
                title: const Text('Notice Moderation & Management'),
                subtitle: const Text('Edit, reschedule, or revoke any announcement'),
                onTap: () {
                  Navigator.pop(ctx);
                  Get.to(() => const AnnouncementManagementPage());
                },
              ),
              ListTile(
                leading: const Icon(Icons.fact_check_rounded, color: Colors.orange),
                title: const Text('Approval Queue'),
                subtitle: const Text('Review and approve teacher announcements'),
                onTap: () {
                  Navigator.pop(ctx);
                  Get.to(() => const ApprovalQueuePage());
                },
              ),
              ListTile(
                leading: const Icon(Icons.volume_up_rounded, color: Colors.blue),
                title: const Text('Speaker Announcement Queue'),
                subtitle: const Text('Manage live speaker broadcasts'),
                onTap: () {
                  Navigator.pop(ctx);
                  Get.to(() => const SpeakerQueuePage());
                },
              ),
              ListTile(
                leading: const Icon(Icons.manage_accounts_rounded, color: Colors.purple),
                title: const Text('User Accounts & Permissions'),
                subtitle: const Text('Manage student & faculty access'),
                onTap: () {
                  Navigator.pop(ctx);
                  Get.to(() => const UserManagementPage());
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
