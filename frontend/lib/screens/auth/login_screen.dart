import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/screens/home_page.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final AuthController authController = Get.find<AuthController>();

  final TextEditingController identifierController = TextEditingController();
  final TextEditingController passwordController = TextEditingController();

  bool isObscure = true;
  bool rememberMe = true;

  Future<void> _handleLogin() async {
    final identifier = identifierController.text.trim();
    final password = passwordController.text.trim();

    if (identifier.isEmpty || password.isEmpty) {
      errorSnackBar('Please enter your credentials.');
      return;
    }

    // Check if initial credentials match
    final validatedUser = authController.validateMockCredentials(identifier, password);
    if (validatedUser == null) {
      errorSnackBar('Login failed. Please check your credentials.');
      await authController.addAuditLog(
        username: identifier,
        role: 'Unknown',
        status: 'FAILED (Invalid Username/Password)',
      );
      return;
    }

    // Secondary Verification for College Admin role
    if (validatedUser.role == 'College Admin') {
      _showEmployeeIdVerificationDialog(context, validatedUser, identifier, password);
      return;
    }

    // Standard Login
    final success = await authController.login(
      identifier: identifier,
      password: password,
      remember: rememberMe,
    );

    if (success) {
      final user = authController.currentUser.value;
      snackBar(
        'Welcome back, ${user?.fullName}!',
        title: 'Logged in as ${user?.role ?? "User"}',
      );
      Get.offAll(() => const HomePage());
    } else {
      errorSnackBar('Login failed. Please check your credentials.');
    }
  }

  void _showEmployeeIdVerificationDialog(
    BuildContext context,
    EchosphereUser targetUser,
    String identifier,
    String password,
  ) {
    final empIdCtrl = TextEditingController();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.purple.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.security_rounded, color: Colors.purple, size: 24),
            ),
            const SizedBox(width: 10),
            const Expanded(
              child: Text(
                'Executive Verification',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Welcome ${targetUser.fullName}. As per EchoSphere security policy, enter your Official Employee ID to access the College Admin Dashboard:',
              style: const TextStyle(fontSize: 12, height: 1.4),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: empIdCtrl,
              autofocus: true,
              decoration: InputDecoration(
                labelText: 'Official Employee ID',
                hintText: 'e.g. DBITADM001 or ADM001',
                prefixIcon: const Icon(Icons.badge_outlined, size: 20),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.purple,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: () async {
              final enteredEmpId = empIdCtrl.text.trim();
              if (enteredEmpId.isEmpty) {
                errorSnackBar('Please enter your Employee ID.');
                return;
              }

              // Verify Employee ID against registered user employee ID (case insensitive)
              final registeredEmpId = targetUser.employeeId ?? 'DBITADM001';
              if (enteredEmpId.toLowerCase() != registeredEmpId.toLowerCase()) {
                Navigator.pop(ctx);
                errorSnackBar('Access Denied: Invalid Employee ID verification code.');
                await authController.addAuditLog(
                  username: identifier,
                  role: 'College Admin',
                  status: 'FAILED (Invalid Employee ID: $enteredEmpId)',
                  employeeId: enteredEmpId,
                );
                return;
              }

              Navigator.pop(ctx);
              final success = await authController.login(
                identifier: identifier,
                password: password,
                remember: rememberMe,
                employeeIdVerification: enteredEmpId,
              );

              if (success) {
                snackBar(
                  'Employee ID verified! Welcome ${targetUser.fullName}.',
                  title: 'College Admin Authenticated',
                );
                Get.offAll(() => const HomePage());
              }
            },
            child: const Text('Verify & Enter'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    identifierController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDesktop = MediaQuery.of(context).size.width > 700;

    return Scaffold(
        body: SafeArea(
      child: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              theme.colorScheme.surface,
              theme.colorScheme.primary.withOpacity(0.15),
              theme.colorScheme.surface,
            ],
          ),
        ),
        child: Center(
          child: SingleChildScrollView(
            padding:
                const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
            child: Container(
              width: isDesktop ? 440 : double.infinity,
              padding: const EdgeInsets.all(28.0),
              decoration: BoxDecoration(
                color: theme.colorScheme.surface.withOpacity(0.95),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: theme.colorScheme.primary.withOpacity(0.25),
                  width: 1.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: theme.colorScheme.primary.withOpacity(0.08),
                    blurRadius: 40,
                    spreadRadius: 2,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  // App Logo & Header
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: theme.colorScheme.primary.withOpacity(0.15),
                    ),
                    child: Icon(
                      Icons.campaign,
                      size: 42,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'EchoSphere',
                    style: TextStyle(
                      fontFamily: 'Poppins-Bold',
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.onSurface,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Smart AI-Powered College Announcement System',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  ),
                  const SizedBox(height: 32),

                  // Identifier Field (USN / Email / Username)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'USN, Email, or Username',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface.withOpacity(0.9),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: identifierController,
                    textInputAction: TextInputAction.next,
                    decoration: InputDecoration(
                      hintText: 'e.g. 1EC22CS001 or admin@echosphere.edu',
                      prefixIcon: const Icon(Icons.person_outline, size: 20),
                      filled: true,
                      fillColor: theme.colorScheme.surfaceContainerHighest
                          .withOpacity(0.3),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),

                  // Password Field
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'Password',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface.withOpacity(0.9),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: passwordController,
                    obscureText: isObscure,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _handleLogin(),
                    decoration: InputDecoration(
                      hintText: 'Enter password',
                      prefixIcon: const Icon(Icons.lock_outline, size: 20),
                      suffixIcon: IconButton(
                        icon: Icon(
                          isObscure ? Icons.visibility : Icons.visibility_off,
                          size: 20,
                        ),
                        onPressed: () => setState(() => isObscure = !isObscure),
                      ),
                      filled: true,
                      fillColor: theme.colorScheme.surfaceContainerHighest
                          .withOpacity(0.3),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Remember Me Checkbox
                  Row(
                    children: [
                      SizedBox(
                        height: 22,
                        width: 22,
                        child: Checkbox(
                          value: rememberMe,
                          onChanged: (val) {
                            setState(() {
                              rememberMe = val ?? true;
                            });
                          },
                          activeColor: theme.colorScheme.primary,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      GestureDetector(
                        onTap: () {
                          setState(() {
                            rememberMe = !rememberMe;
                          });
                        },
                        child: Text(
                          'Remember Me',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: theme.colorScheme.onSurface.withOpacity(0.85),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),

                  // Login Button
                  Obx(() => SizedBox(
                        width: double.infinity,
                        height: 48,
                        child: ElevatedButton(
                          onPressed: authController.isLoading.value
                              ? null
                              : _handleLogin,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: theme.colorScheme.primary,
                            foregroundColor: theme.colorScheme.onPrimary,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
                            elevation: 2,
                          ),
                          child: authController.isLoading.value
                              ? const SizedBox(
                                  width: 22,
                                  height: 22,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2, color: Colors.white),
                                )
                              : const Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.login, size: 20),
                                    SizedBox(width: 10),
                                    Text(
                                      'Sign In',
                                      style: TextStyle(
                                        fontSize: 15,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                        ),
                      )),
                  const SizedBox(height: 16),

                  const SizedBox(height: 12),

                  // Forgot Password Button
                  TextButton(
                    onPressed: () => _showForgotPasswordDialog(context),
                    child: Text(
                      'Forgot Password?',
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.primary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),

                  Text(
                    'Your role will be detected automatically upon login.',
                    style: TextStyle(
                      fontSize: 12,
                      color: theme.colorScheme.onSurface.withOpacity(0.5),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ));
  }

  void _showForgotPasswordDialog(BuildContext context) {
    final idCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Password Recovery'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter your USN, Official Email, or Username:',
              style: TextStyle(fontSize: 13),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: idCtrl,
              decoration: const InputDecoration(
                hintText: 'e.g. 1EC22CS001 or teacher@echosphere.edu',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.blue.withOpacity(0.3)),
              ),
              child: const Text(
                '• Student Recovery: Contact your Department Faculty or HoD to request a reset.\n'
                '• Faculty Recovery: A reset link will be sent to your registered official email.\n'
                '• Admin Recovery: Requires backend administrator intervention.',
                style: TextStyle(fontSize: 11, height: 1.5, color: Colors.blue),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
          ElevatedButton(
            onPressed: () {
              final id = idCtrl.text.trim();
              if (id.isEmpty) {
                errorSnackBar('Please enter your identifier.');
                return;
              }
              Navigator.pop(ctx);
              snackBar('Password reset instructions initiated for $id.');
            },
            child: const Text('Submit Request'),
          ),
        ],
      ),
    );
  }
}
