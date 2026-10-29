import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/settings/settings.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/echosphere_ai_controller.dart';
import 'package:echosphere/screens/announcements/create_announcement_dialog.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.put(Settings());
    final authController = Get.put(AuthController());
    authController.currentUser.value = EchosphereUser(
      id: 201,
      fullName: 'Prof. Ramesh Rao',
      officialEmail: 'ramesh.rao@echosphere.edu',
      role: 'Teacher',
      department: 'AIML',
    );
    Get.put(AnnouncementController());
    Get.put(EchosphereAiController());
  });

  tearDown(() {
    Get.reset();
  });

  group('CreateAnnouncementDialog AI tools & Zero Overflow on 320px', () {
    testWidgets('renders AI Auto-Draft without voice dictation or the other removed AI tools on 320px screen without overflow', (tester) async {
      tester.view.physicalSize = const Size(320, 720);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        GetMaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (_) => const CreateAnnouncementDialog(),
                  );
                },
                child: const Text('Open Create Dialog'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open Create Dialog'));
      await tester.pumpAndSettle();

      expect(find.text('AI Auto-Draft'), findsOneWidget);
      // Removed on the owner's decision (2026-10-29): voice dictation.
      expect(find.text('AI Fast Intake Studio'), findsNothing);
      expect(find.byKey(const Key('voice_dictate_button')), findsNothing);
      expect(find.text('Voice Dictate'), findsNothing);
      // Removed on the owner's decision (2026-10-27): document OCR, grammar and AI expand.
      expect(find.byKey(const Key('scan_ocr_button')), findsNothing);
      expect(find.text('Scan / OCR Notice'), findsNothing);
      expect(find.text('Grammar'), findsNothing);
      expect(find.text('AI Expand'), findsNothing);

      expect(tester.takeException(), isNull);
    });

    testWidgets('renders AI Auto-Draft without voice dictation or the other removed AI tools on tablet width without overflow', (tester) async {
      tester.view.physicalSize = const Size(1024, 768);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        GetMaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (_) => const CreateAnnouncementDialog(),
                  );
                },
                child: const Text('Open Create Dialog'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open Create Dialog'));
      await tester.pumpAndSettle();

      expect(find.text('AI Auto-Draft'), findsOneWidget);
      // Removed on the owner's decision (2026-10-29): voice dictation.
      expect(find.text('AI Fast Intake Studio'), findsNothing);
      expect(find.byKey(const Key('voice_dictate_button')), findsNothing);
      expect(find.text('Voice Dictate'), findsNothing);
      // Removed on the owner's decision (2026-10-27): document OCR, grammar and AI expand.
      expect(find.byKey(const Key('scan_ocr_button')), findsNothing);
      expect(find.text('Scan / OCR Notice'), findsNothing);
      expect(find.text('Grammar'), findsNothing);
      expect(find.text('AI Expand'), findsNothing);

      expect(tester.takeException(), isNull);
    });
  });
}



