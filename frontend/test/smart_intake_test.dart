import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/settings/settings.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/controllers/echosphere_ai_controller.dart';
import 'package:anymex/screens/announcements/create_announcement_dialog.dart';
import 'package:anymex/widgets/custom_widgets/voice_dictation_sheet.dart';
import 'package:anymex/services/echosphere_api_service.dart';

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
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.reset();
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

    test('ocrDocumentToNotice fallback parses document filename and returns structured circular', () async {
      final api = EchosphereApiService();
      final res = await api.ocrDocumentToNotice(
        fileBytes: [1, 2, 3, 4],
        mimeType: 'application/pdf',
        filename: 'campus_placement_drive_guidelines.pdf',
      );

      expect(res['title'].toString().toLowerCase(), contains('placement'));
      expect(res['suggested_category'], 'Placement');
      expect(res['reference_number'], contains('CIR'));
      expect(res['content'], contains('institutional document'));
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

      expect(find.text('🎙️ Voice Notice Dictation'), findsOneWidget);
      expect(find.byIcon(Icons.mic_none_rounded), findsOneWidget);
      expect(find.text('Pick Audio File'), findsOneWidget);
      expect(find.text('✨ Transform into Official Circular'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  group('CreateAnnouncementDialog AI Fast Intake Studio & Zero Overflow on 320px', () {
    testWidgets('renders AI Fast Intake Studio with Voice Dictate and Scan OCR buttons on 320px screen without overflow', (tester) async {
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
      expect(find.byKey(const Key('scan_ocr_button')), findsOneWidget);
      expect(find.text('🎙️ Voice Dictate'), findsOneWidget);
      expect(find.text('📄 Scan / OCR Notice'), findsOneWidget);

      expect(tester.takeException(), isNull);
    });
  });
}



