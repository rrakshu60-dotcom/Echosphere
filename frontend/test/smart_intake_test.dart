import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/settings/settings.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/theme.dart';
import 'package:echosphere/controllers/echosphere_ai_controller.dart';
import 'package:echosphere/screens/announcements/create_announcement_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/voice_dictation_sheet.dart';
import 'package:echosphere/services/echosphere_api_service.dart';

Widget createTestApp(Widget home) {
  return ChangeNotifierProvider(
    create: (_) => ThemeProvider(),
    child: GetMaterialApp(
      home: Scaffold(body: home),
    ),
  );
}

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

  group('Smart Notice Intake Service Client Fallback', () {
    test('voiceToNotice fallback extracts category, priority, and audience from spoken text', () async {
      final api = EchosphereApiService();
      final res = await api.voiceToNotice(
        rawTranscript: 'Tomorrow 3rd year CSE lab exam in Turing Lab is postponed to Friday. Make sure to bring hall tickets.',
      );

      expect(res['title'], isNotEmpty);
      expect(res['suggested_category'], anyOf('Examination', 'Academic'));
      expect(res['suggested_priority'], anyOf('HIGH', 'URGENT', 'NORMAL'));
      expect(res['suggested_audience'], anyOf('CSE Department', '3rd Year Students', 'Entire College'));
      expect(res['content'], contains('Turing Lab'));
      expect(res['transcription'], contains('Turing Lab'));
    });
  });

  group('VoiceDictationSheet UI & Zero Overflow on 320px', () {
    testWidgets('renders VoiceDictationSheet with mic, input field, and action button on 320px screen without overflow', (tester) async {
      tester.view.physicalSize = const Size(320, 720);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        createTestApp(
          const Scaffold(
            body: VoiceDictationSheet(),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Voice Notice Dictation'), findsOneWidget);
      expect(find.byIcon(Icons.mic_none_rounded), findsOneWidget);
      expect(find.text('Pick Audio File'), findsOneWidget);
      expect(find.text('Transform into Official Circular'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  group('CreateAnnouncementDialog AI Fast Intake Studio & Zero Overflow on 320px', () {
    testWidgets('renders AI Fast Intake Studio with Voice Dictate and without the removed AI tools on 320px screen without overflow', (tester) async {
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

      // Verify AI Fast Intake Studio container and buttons exist
      expect(find.text('AI Fast Intake Studio'), findsOneWidget);
      expect(find.byKey(const Key('voice_dictate_button')), findsOneWidget);
      expect(find.text('Voice Dictate'), findsOneWidget);
      expect(find.text('AI Auto-Draft'), findsOneWidget);
      // Removed on the owner's decision (2026-10-27): document OCR, grammar and AI expand.
      expect(find.byKey(const Key('scan_ocr_button')), findsNothing);
      expect(find.text('Scan / OCR Notice'), findsNothing);
      expect(find.text('Grammar'), findsNothing);
      expect(find.text('AI Expand'), findsNothing);

      expect(tester.takeException(), isNull);
    });

    testWidgets('renders AI Fast Intake Studio with Voice Dictate and without the removed AI tools on tablet width without overflow', (tester) async {
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

      // Verify AI Fast Intake Studio container and buttons exist
      expect(find.text('AI Fast Intake Studio'), findsOneWidget);
      expect(find.byKey(const Key('voice_dictate_button')), findsOneWidget);
      expect(find.text('Voice Dictate'), findsOneWidget);
      expect(find.text('AI Auto-Draft'), findsOneWidget);
      // Removed on the owner's decision (2026-10-27): document OCR, grammar and AI expand.
      expect(find.byKey(const Key('scan_ocr_button')), findsNothing);
      expect(find.text('Scan / OCR Notice'), findsNothing);
      expect(find.text('Grammar'), findsNothing);
      expect(find.text('AI Expand'), findsNothing);

      expect(tester.takeException(), isNull);
    });
  });
}



