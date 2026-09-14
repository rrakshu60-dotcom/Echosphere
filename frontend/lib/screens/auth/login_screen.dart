import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/screens/home_page.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_animated_logo.dart';
import 'package:echosphere/widgets/custom_widgets/privacy_policy_dialog.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
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

  @override
  void initState() {
    super.initState();
    authController.isLoading.value = false;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        authController.isLoading.value = false;
      }
    });
  }

  Future<void> _handleLogin() async {
    authController.isLoading.value = false;
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
        title: 'Login Successful',
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
      builder: (ctx) {
        final theme = Theme.of(ctx);
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withOpacity(0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.security_rounded, color: theme.colorScheme.primary, size: 24),
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
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'College Admin login requires authorization by a registered Staff, Teacher, or HoD. Input your Official Employee ID:',
                  style: TextStyle(fontSize: 12, height: 1.4),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: empIdCtrl,
                  autofocus: true,
                  decoration: InputDecoration(
                    labelText: 'Official Staff Employee ID',
                    hintText: 'e.g. DBITAIMLT022022, DBITADM001, PRI001, DEVADM01',
                    prefixIcon: const Icon(Icons.badge_outlined, size: 20),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: theme.colorScheme.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            onPressed: () async {
              final enteredEmpId = empIdCtrl.text.trim();
              if (enteredEmpId.isEmpty) {
                errorSnackBar('Please enter your Staff Employee ID.');
                return;
              }

              // Check if entered Employee ID belongs to any registered staff member in the database
              final isValidStaff = authController.isRegisteredStaffEmployeeId(enteredEmpId);
              if (!isValidStaff) {
                Navigator.pop(ctx);
                errorSnackBar(
                  'Access Denied: Employee ID \'$enteredEmpId\' is not registered to any Teacher, HoD, or Staff in the database.',
                );
                await authController.addAuditLog(
                  username: identifier,
                  role: 'College Admin',
                  status: 'FAILED (Unrecognized Staff Employee ID: $enteredEmpId)',
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
                  'Staff Employee ID ($enteredEmpId) Authorized!',
                  title: 'College Admin Access Granted',
                );
                Get.offAll(() => const HomePage());
              }
            },
            child: const Text('Verify & Enter'),
          ),
        ],
      );
    },
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
    final isDark = theme.brightness == Brightness.dark;
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
            colors: isDark
                ? [
                    theme.colorScheme.surface,
                    theme.colorScheme.primary.withOpacity(0.08),
                    theme.colorScheme.surface,
                  ]
                : const [
                    Color(0xFFF8F9FA),
                    Color(0xFFF1F5F9),
                    Color(0xFFF8F9FA),
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
                color: isDark ? theme.colorScheme.surface.withOpacity(0.95) : Colors.white,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: isDark ? theme.colorScheme.outline : const Color(0xFFE2E8F0),
                  width: 1.0,
                ),
                boxShadow: [
                  BoxShadow(
                    color: isDark
                        ? Colors.black.withOpacity(0.5)
                        : const Color(0xFF0F172A).withOpacity(0.04),
                    blurRadius: 32,
                    spreadRadius: -4,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  // App Logo & Header
                  const EchoSphereAnimatedLogo(size: 56),
                  const SizedBox(height: 16),
                  Text(
                    'EchoSphere',
                    style: TextStyle(
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
                      color: isDark ? theme.colorScheme.onSurface.withOpacity(0.7) : const Color(0xFF475569),
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
                        color: isDark ? theme.colorScheme.onSurface.withOpacity(0.9) : const Color(0xFF1E293B),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: identifierController,
                    textInputAction: TextInputAction.next,
                    decoration: InputDecoration(
                      hintText: 'e.g. 1DB23CI079, CAdmin, or ESDev01',
                      hintStyle: TextStyle(
                        fontSize: 13,
                        color: isDark ? theme.colorScheme.onSurface.withOpacity(0.5) : const Color(0xFF64748B),
                      ),
                      prefixIcon: const Icon(Icons.person_outline, size: 20),
                      filled: true,
                      fillColor: isDark
                          ? theme.colorScheme.surfaceContainerHighest.withOpacity(0.3)
                          : const Color(0xFFF8FAFC),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                          color: isDark ? theme.colorScheme.outline : const Color(0xFFCBD5E1),
                          width: 1.0,
                        ),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                          color: isDark ? theme.colorScheme.outline : const Color(0xFFCBD5E1),
                          width: 1.0,
                        ),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                          color: theme.colorScheme.primary,
                          width: 1.5,
                        ),
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
                        color: isDark ? theme.colorScheme.onSurface.withOpacity(0.9) : const Color(0xFF1E293B),
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
                      hintStyle: TextStyle(
                        fontSize: 13,
                        color: isDark ? theme.colorScheme.onSurface.withOpacity(0.5) : const Color(0xFF64748B),
                      ),
                      prefixIcon: const Icon(Icons.lock_outline, size: 20),
                      suffixIcon: IconButton(
                        icon: Icon(
                          isObscure ? Icons.visibility : Icons.visibility_off,
                          size: 20,
                        ),
                        onPressed: () => setState(() => isObscure = !isObscure),
                      ),
                      filled: true,
                      fillColor: isDark
                          ? theme.colorScheme.surfaceContainerHighest.withOpacity(0.3)
                          : const Color(0xFFF8FAFC),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                          color: isDark ? theme.colorScheme.outline : const Color(0xFFCBD5E1),
                          width: 1.0,
                        ),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                          color: isDark ? theme.colorScheme.outline : const Color(0xFFCBD5E1),
                          width: 1.0,
                        ),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                          color: theme.colorScheme.primary,
                          width: 1.5,
                        ),
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
                  const SizedBox(height: 12),

                  // Google Play Required Privacy Policy & Terms Link
                  InkWell(
                    onTap: () => showEchoSpherePrivacyPolicy(context),
                    borderRadius: BorderRadius.circular(8),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                      child: Text(
                        'Privacy Policy & Institutional Data Safety',
                        style: TextStyle(
                          fontSize: 11,
                          color: theme.colorScheme.primary.withOpacity(0.8),
                          decoration: TextDecoration.underline,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
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
    int currentStep = 0; // 0 = Request Token, 1 = Verify Token, 2 = Set New Password
    final idCtrl = TextEditingController();
    final tokenCtrl = TextEditingController();
    final newPassCtrl = TextEditingController();
    final confirmPassCtrl = TextEditingController();
    bool isSubmitting = false;
    bool obscureNew = true;
    bool obscureConfirm = true;
    String verifiedIdentifier = '';
    String verifiedToken = '';
    String? statusMessage;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) {
          final theme = Theme.of(context);

          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                Icon(Icons.lock_reset_rounded, color: theme.colorScheme.primary, size: 22),
                const SizedBox(width: 8),
                Text(
                  currentStep == 0
                      ? 'Password Recovery'
                      : currentStep == 1
                          ? 'Verify Reset Token'
                          : 'Set New Password',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Step Indicator
                  Row(
                    children: [
                      _buildStepDot(0, 'ID', currentStep, theme),
                      Expanded(
                        child: Container(
                          height: 2,
                          color: currentStep >= 1 ? theme.colorScheme.primary : theme.colorScheme.outline.withOpacity(0.3),
                        ),
                      ),
                      _buildStepDot(1, 'Token', currentStep, theme),
                      Expanded(
                        child: Container(
                          height: 2,
                          color: currentStep >= 2 ? theme.colorScheme.primary : theme.colorScheme.outline.withOpacity(0.3),
                        ),
                      ),
                      _buildStepDot(2, 'Password', currentStep, theme),
                    ],
                  ),
                  const SizedBox(height: 16),

                  if (statusMessage != null) ...[
                    Container(
                      padding: const EdgeInsets.all(10),
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: theme.colorScheme.primary.withOpacity(0.25)),
                      ),
                      child: Text(
                        statusMessage!,
                        style: TextStyle(fontSize: 11, color: theme.colorScheme.primary, fontWeight: FontWeight.w500),
                      ),
                    ),
                  ],

                  if (currentStep == 0) ...[
                    const Text(
                      'Enter your Employee ID, USN, or Official Email:',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    TextField(
                      controller: idCtrl,
                      decoration: InputDecoration(
                        hintText: 'e.g. 1DB23CI079 or admin@echosphere.edu',
                        prefixIcon: Icon(Icons.badge_outlined, size: 20, color: theme.colorScheme.primary),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary.withOpacity(0.06),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'A secure password recovery token will be dispatched to your registered institutional account.',
                        style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.7)),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () => setDlgState(() => currentStep = 1),
                        child: Text(
                          'Already have a reset token?',
                          style: TextStyle(fontSize: 11, color: theme.colorScheme.primary, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ),
                  ] else if (currentStep == 1) ...[
                    const Text(
                      'Enter Verification Token:',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Enter the secure token received for your account.',
                      style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.65)),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: tokenCtrl,
                      decoration: InputDecoration(
                        hintText: 'e.g. 4a8f9c1b',
                        prefixIcon: Icon(Icons.vpn_key_rounded, size: 20, color: theme.colorScheme.primary),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: () => setDlgState(() => currentStep = 0),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.arrow_back_rounded, size: 13, color: theme.colorScheme.primary),
                            const SizedBox(width: 4),
                            Text('Back to Identifier', style: TextStyle(fontSize: 11, color: theme.colorScheme.primary)),
                          ],
                        ),
                      ),
                    ),
                  ] else if (currentStep == 2) ...[
                    Text(
                      'Resetting password for: $verifiedIdentifier',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: theme.colorScheme.primary),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: newPassCtrl,
                      obscureText: obscureNew,
                      decoration: InputDecoration(
                        labelText: 'New Password',
                        prefixIcon: Icon(Icons.lock_outline_rounded, size: 20, color: theme.colorScheme.primary),
                        suffixIcon: IconButton(
                          icon: Icon(obscureNew ? Icons.visibility_off_outlined : Icons.visibility_outlined, size: 18),
                          onPressed: () => setDlgState(() => obscureNew = !obscureNew),
                        ),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: confirmPassCtrl,
                      obscureText: obscureConfirm,
                      decoration: InputDecoration(
                        labelText: 'Confirm New Password',
                        prefixIcon: Icon(Icons.lock_outline_rounded, size: 20, color: theme.colorScheme.primary),
                        suffixIcon: IconButton(
                          icon: Icon(obscureConfirm ? Icons.visibility_off_outlined : Icons.visibility_outlined, size: 18),
                          onPressed: () => setDlgState(() => obscureConfirm = !obscureConfirm),
                        ),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: isSubmitting ? null : () => Navigator.pop(ctx),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                onPressed: isSubmitting
                    ? null
                    : () async {
                        if (currentStep == 0) {
                          final id = idCtrl.text.trim();
                          if (id.isEmpty) {
                            errorSnackBar('Please enter your USN, Employee ID, or Email.');
                            return;
                          }
                          setDlgState(() => isSubmitting = true);
                          try {
                            final res = await EchosphereApiService().forgotPassword(id);
                            setDlgState(() {
                              isSubmitting = false;
                              currentStep = 1;
                              statusMessage = res['message']?.toString() ?? 'Recovery token generated. Check your email or enter token below.';
                            });
                          } catch (e) {
                            setDlgState(() => isSubmitting = false);
                            errorSnackBar('Request failed: ${e.toString().replaceAll("Exception: ", "")}');
                          }
                        } else if (currentStep == 1) {
                          final tok = tokenCtrl.text.trim();
                          if (tok.isEmpty) {
                            errorSnackBar('Please enter the reset token.');
                            return;
                          }
                          setDlgState(() => isSubmitting = true);
                          try {
                            final res = await EchosphereApiService().verifyResetToken(tok);
                            setDlgState(() {
                              isSubmitting = false;
                              verifiedToken = tok;
                              verifiedIdentifier = res['identifier']?.toString() ?? idCtrl.text.trim();
                              currentStep = 2;
                              statusMessage = 'Token verified! Please set your new password.';
                            });
                          } catch (e) {
                            setDlgState(() => isSubmitting = false);
                            errorSnackBar('Token invalid: ${e.toString().replaceAll("Exception: ", "")}');
                          }
                        } else if (currentStep == 2) {
                          final p1 = newPassCtrl.text;
                          final p2 = confirmPassCtrl.text;
                          if (p1.isEmpty || p1.length < 6) {
                            errorSnackBar('Password must be at least 6 characters long.');
                            return;
                          }
                          if (p1 != p2) {
                            errorSnackBar('Passwords do not match.');
                            return;
                          }
                          setDlgState(() => isSubmitting = true);
                          try {
                            final res = await EchosphereApiService().resetPassword(verifiedToken, p1);
                            if (ctx.mounted) Navigator.pop(ctx);
                            if (verifiedIdentifier.isNotEmpty) {
                              identifierController.text = verifiedIdentifier;
                            }
                            snackBar(res['message']?.toString() ?? 'Password successfully reset! Please sign in.');
                          } catch (e) {
                            setDlgState(() => isSubmitting = false);
                            errorSnackBar('Reset failed: ${e.toString().replaceAll("Exception: ", "")}');
                          }
                        }
                      },
                child: isSubmitting
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                    : Text(
                        currentStep == 0
                            ? 'Request Token'
                            : currentStep == 1
                                ? 'Verify Token'
                                : 'Set Password',
                      ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildStepDot(int step, String label, int currentStep, ThemeData theme) {
    final isDone = currentStep > step;
    final isCurrent = currentStep == step;
    final color = isDone || isCurrent ? theme.colorScheme.primary : theme.colorScheme.outline.withOpacity(0.4);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 22,
          height: 22,
          decoration: BoxDecoration(
            color: isDone ? color : (isCurrent ? color.withOpacity(0.15) : Colors.transparent),
            shape: BoxShape.circle,
            border: Border.all(color: color, width: 2),
          ),
          child: Center(
            child: isDone
                ? const Icon(Icons.check, size: 14, color: Colors.white)
                : Text(
                    '${step + 1}',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: isCurrent ? color : theme.colorScheme.onSurface.withOpacity(0.5),
                    ),
                  ),
          ),
        ),
        const SizedBox(height: 3),
        Text(
          label,
          style: TextStyle(
            fontSize: 9,
            fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
            color: isCurrent ? color : theme.colorScheme.onSurface.withOpacity(0.5),
          ),
        ),
      ],
    );
  }
}
