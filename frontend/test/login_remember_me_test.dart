import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/settings/settings.dart';
import 'package:echosphere/controllers/theme.dart';
import 'package:echosphere/screens/auth/login_screen.dart';

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.put(Settings());
    Get.put(AuthController());
  });

  tearDown(Get.reset);

  testWidgets('"Remember me" starts unticked, so sessions end within 12 hours unless chosen', (tester) async {
    tester.view.physicalSize = const Size(400, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(ChangeNotifierProvider(
      create: (_) => ThemeProvider(),
      child: const GetMaterialApp(home: LoginScreen()),
    ));
    await tester.pump(const Duration(seconds: 1));

    expect(tester.widget<Checkbox>(find.byType(Checkbox).first).value, isFalse);
    expect(Get.find<AuthController>().rememberMe.value, isFalse);
  });
}
