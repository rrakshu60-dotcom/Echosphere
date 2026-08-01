import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/screens/auth/login_screen.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  final authController = Get.find<AuthController>();

  final currentPasswordCtrl = TextEditingController();
  final newPasswordCtrl = TextEditingController();
  final confirmPasswordCtrl = TextEditingController();

  bool isObscureCurrent = true;
  bool isObscureNew = true;
  bool isObscureConfirm = true;

  @override
  void initState() {
    super.initState();
    authController.loadResetQuotaFromDisk();
  }

  @override
  void dispose() {
    currentPasswordCtrl.dispose();
    newPasswordCtrl.dispose();
    confirmPasswordCtrl.dispose();
    super.dispose();
  }

  void _handleResetPassword() async {
    final current = currentPasswordCtrl.text.trim();
    final newPass = newPasswordCtrl.text.trim();
    final confirmPass = confirmPasswordCtrl.text.trim();

    if (current.isEmpty || newPass.isEmpty || confirmPass.isEmpty) {
      errorSnackBar('Please fill in all password fields.');
      return;
    }

    if (newPass != confirmPass) {
      errorSnackBar('New password and confirm password do not match.');
      return;
    }

    if (newPass.length < 6) {
      errorSnackBar('New password must be at least 6 characters long.');
      return;
    }

    final user = authController.currentUser.value;
    final role = user?.role ?? 'Student';
    final isRestricted = role == 'Student' || role == 'Teacher' || role == 'HoD';

    if (isRestricted && !authController.canResetPassword()) {
      errorSnackBar(
        'Annual Limit Reached: You have used all 5 password resets for calendar year ${DateTime.now().year}. Please contact College Admin for assistance.',
      );
      return;
    }

    final success = await authController.resetPassword(
      currentPassword: current,
      newPassword: newPass,
    );

    if (success) {
      currentPasswordCtrl.clear();
      newPasswordCtrl.clear();
      confirmPasswordCtrl.clear();

      final remaining = 5 - authController.annualPasswordResetCount.value;
      snackBar(
        isRestricted
            ? 'Password reset successfully! ($remaining / 5 annual resets remaining)'
            : 'Executive password updated successfully!',
        title: 'Password Updated',
      );
    } else {
      errorSnackBar('Failed to update password. Please check your credentials.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

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

      final role = user.role;
      final isRestricted = role == 'Student' || role == 'Teacher' || role == 'HoD';

      return SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Center(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 800),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 1. Profile Header Card
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
                            const SizedBox(height: 6),
                            Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: [
                                EchoSphereChip(
                                  label: user.role,
                                  isSelected: true,
                                  onSelected: (_) {},
                                ),
                                EchoSphereChip(
                                  label: user.department ?? 'General',
                                  isSelected: false,
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

                // 2. Personal & Account Details Container
                EchoSphereContainer(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const EchoSphereText(
                        text: 'Personal & Account Details',
                        size: 16,
                        variant: TextVariant.bold,
                      ),
                      const Divider(height: 20),
                      _buildInfoTile('Full Name', user.fullName, Icons.person_outline),
                      _buildInfoTile('User Role', user.role, Icons.badge_outlined),
                      if (user.officialEmail != null)
                        _buildInfoTile('Official Email', user.officialEmail!, Icons.email_outlined),
                      if (user.usn != null)
                        _buildInfoTile('University Seat Number (USN)', user.usn!, Icons.pin_drop_outlined),
                      if (user.employeeId != null)
                        _buildInfoTile('Official Employee ID', user.employeeId!, Icons.badge),
                      _buildInfoTile('Department', user.department ?? 'Institution-Wide', Icons.business_outlined),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // 3. Reset Password Container
                EchoSphereContainer(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.lock_reset_rounded, color: Colors.purple, size: 22),
                          const SizedBox(width: 8),
                          const EchoSphereText(
                            text: 'Reset Account Password',
                            size: 16,
                            variant: TextVariant.bold,
                          ),
                          const Spacer(),
                          // Quota Badge
                          Obx(() {
                            final used = authController.annualPasswordResetCount.value;
                            if (isRestricted) {
                              final isMax = used >= 5;
                              return Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: isMax ? Colors.red.withOpacity(0.15) : Colors.purple.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(14),
                                  border: Border.all(color: isMax ? Colors.red : Colors.purple),
                                ),
                                child: Text(
                                  'Resets Used: $used / 5 this year',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: isMax ? Colors.red : Colors.purple,
                                  ),
                                ),
                              );
                            } else {
                              return Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: Colors.green.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(14),
                                  border: Border.all(color: Colors.green),
                                ),
                                child: const Text(
                                  'Unlimited Resets',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.green,
                                  ),
                                ),
                              );
                            }
                          }),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        isRestricted
                            ? 'Policy Rule: Maximum 5 password resets allowed per calendar year for Students, Teachers & HoDs.'
                            : 'Executive Account: Unlimited password reset privileges active.',
                        style: TextStyle(
                          fontSize: 12,
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      const Divider(height: 24),

                      // Password Reset Form Fields
                      TextField(
                        controller: currentPasswordCtrl,
                        obscureText: isObscureCurrent,
                        decoration: InputDecoration(
                          labelText: 'Current Password',
                          prefixIcon: const Icon(Icons.lock_outline, size: 20),
                          suffixIcon: IconButton(
                            icon: Icon(isObscureCurrent ? Icons.visibility_off : Icons.visibility, size: 20),
                            onPressed: () => setState(() => isObscureCurrent = !isObscureCurrent),
                          ),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                      const SizedBox(height: 14),

                      TextField(
                        controller: newPasswordCtrl,
                        obscureText: isObscureNew,
                        decoration: InputDecoration(
                          labelText: 'New Password',
                          prefixIcon: const Icon(Icons.key_outlined, size: 20),
                          suffixIcon: IconButton(
                            icon: Icon(isObscureNew ? Icons.visibility_off : Icons.visibility, size: 20),
                            onPressed: () => setState(() => isObscureNew = !isObscureNew),
                          ),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                      const SizedBox(height: 14),

                      TextField(
                        controller: confirmPasswordCtrl,
                        obscureText: isObscureConfirm,
                        decoration: InputDecoration(
                          labelText: 'Confirm New Password',
                          prefixIcon: const Icon(Icons.check_circle_outline, size: 20),
                          suffixIcon: IconButton(
                            icon: Icon(isObscureConfirm ? Icons.visibility_off : Icons.visibility, size: 20),
                            onPressed: () => setState(() => isObscureConfirm = !isObscureConfirm),
                          ),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                      const SizedBox(height: 18),

                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.purple,
                          foregroundColor: Colors.white,
                          minimumSize: const Size(double.infinity, 46),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        onPressed: _handleResetPassword,
                        icon: const Icon(Icons.lock_reset, size: 20),
                        label: const Text(
                          'Update Account Password',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // 4. Log Out Action Button
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
                      Text(
                        'Log Out from EchoSphere',
                        style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
                      ),
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

  Widget _buildInfoTile(String title, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.purple.withOpacity(0.8)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontSize: 11, color: Colors.grey),
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
