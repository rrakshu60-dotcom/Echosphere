import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/speaker_queue_controller.dart';
import 'package:anymex/screens/announcements/speaker_queue_page.dart';

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
  });

  tearDown(() {
    if (Get.isRegistered<SpeakerQueueController>()) {
      Get.find<SpeakerQueueController>().cancelAllTimers();
    }
    Get.reset();
  });

  testWidgets('SpeakerQueuePage shows Access Restricted screen for Student role', (WidgetTester tester) async {
    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 99,
      fullName: 'Student John',
      role: 'Student',
    );

    await tester.pumpWidget(
      const GetMaterialApp(
        home: SpeakerQueuePage(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Access Restricted'), findsOneWidget);
    expect(find.textContaining('authority to display the smart speaker dashboard'), findsOneWidget);
  });

  testWidgets('SpeakerQueuePage renders tabs and dialogs for authorized Admin role', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Admin User',
      role: 'Dev Admin',
    );

    await tester.pumpWidget(
      const GetMaterialApp(
        home: SpeakerQueuePage(),
      ),
    );
    await tester.pumpAndSettle();

    // Verify Speaker Queue tab is visible
    expect(find.textContaining('Queue'), findsWidgets);
    expect(find.textContaining('Nodes'), findsWidgets);

    // Tap on Nodes Tab
    await tester.tap(find.textContaining('Nodes'));
    await tester.pumpAndSettle();

    // Verify Hardware Devices view is rendered
    expect(find.textContaining('Connected Microcontroller Nodes'), findsOneWidget);
    expect(find.text('Add Node'), findsOneWidget);

    // Tap on Add Node button to open dialog
    await tester.tap(find.text('Add Node'));
    await tester.pumpAndSettle();

    // Verify dialog opened
    expect(find.text('Register Hardware Speaker Node'), findsOneWidget);

    // Close dialog
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();

    // Switch back to Speaker Queue Tab
    await tester.tap(find.textContaining('Queue').first);
    await tester.pumpAndSettle();

    // Tap on EMERGENCY button
    await tester.tap(find.text('EMERGENCY'));
    await tester.pumpAndSettle();

    // Verify Emergency dialog opened
    expect(find.text('Emergency Speaker Override'), findsOneWidget);

    // Close emergency dialog
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
  });

  testWidgets('SpeakerQueuePage operates with zero overflow on compact 320px screen', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Admin User',
      role: 'Dev Admin',
    );

    await tester.pumpWidget(
      const GetMaterialApp(
        home: SpeakerQueuePage(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(SpeakerQueuePage), findsOneWidget);
  });
}
