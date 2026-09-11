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
import 'package:anymex/screens/home/home_dashboard_widgets.dart';
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
      id: 101,
      fullName: 'Rahul Sharma',
      officialEmail: 'rahul.ci23@echosphere.edu',
      role: 'Student',
      department: 'AIML',
      semester: 5,
      usn: '1DB23CI079',
    );
    Get.put(AnnouncementController());
    Get.put(EchosphereAiController());
  });

  tearDown(() {
    Get.reset();
  });

  group('Regional Language Translation Service & Client Fallback', () {
    test('translateAnnouncement returns valid Kannada script and preserves entities', () async {
      final api = EchosphereApiService();
      final res = await api.translateAnnouncement(
        id: 1,
        targetLanguage: 'kn',
        title: 'Examination Schedule Notice',
        content: 'Internal assessment examination for 5th Sem AIML students in Room 302.',
        summary: 'IA-1 exams begin next week.',
      );

      expect(res['target_language'], 'kn');
      expect(res['language_name'], 'Kannada');
      expect(res['native_name'], 'ಕನ್ನಡ');

      // Check Kannada Unicode script range (\u0C80-\u0CFF)
      expect(RegExp(r'[\u0C80-\u0CFF]').hasMatch(res['translated_content']), isTrue);
      // Entity preservation
      expect(res['translated_content'].contains('AIML') || res['translated_content'].contains('302'), isTrue);
    });

    test('translateAnnouncement returns valid Hindi script', () async {
      final api = EchosphereApiService();
      final res = await api.translateAnnouncement(
        id: 2,
        targetLanguage: 'hi',
        title: 'Technical Workshop Notice',
        content: 'Workshop for all students in the Auditorium.',
      );

      expect(res['target_language'], 'hi');
      expect(res['language_name'], 'Hindi');
      // Check Devanagari Unicode script range (\u0900-\u097F)
      expect(RegExp(r'[\u0900-\u097F]').hasMatch(res['translated_content']), isTrue);
    });

    test('translateAnnouncement returns valid Telugu script', () async {
      final api = EchosphereApiService();
      final res = await api.translateAnnouncement(
        id: 3,
        targetLanguage: 'te',
        title: 'College Holiday Notice',
        content: 'Campus closed tomorrow, classes suspended.',
      );

      expect(res['target_language'], 'te');
      expect(res['language_name'], 'Telugu');
      // Check Telugu Unicode script range (\u0C00-\u0C7F)
      expect(RegExp(r'[\u0C00-\u0C7F]').hasMatch(res['translated_content']), isTrue);
    });

    test('translateAnnouncement returns valid Tamil script', () async {
      final api = EchosphereApiService();
      final res = await api.translateAnnouncement(
        id: 4,
        targetLanguage: 'ta',
        title: 'Campus Placement Drive Notice',
        content: 'Placement interviews in Placement Cell.',
      );

      expect(res['target_language'], 'ta');
      expect(res['language_name'], 'Tamil');
      // Check Tamil Unicode script range (\u0B80-\u0BFF)
      expect(RegExp(r'[\u0B80-\u0BFF]').hasMatch(res['translated_content']), isTrue);
    });

    test('translateAnnouncement returns English unchanged', () async {
      final api = EchosphereApiService();
      final res = await api.translateAnnouncement(
        id: 5,
        targetLanguage: 'en',
        title: 'English Title',
        content: 'English content text.',
      );

      expect(res['target_language'], 'en');
      expect(res['translated_title'], 'English Title');
      expect(res['translated_content'], 'English content text.');
    });
  });

  group('AnnouncementFeedCard Translate Chip & Zero Overflow on 320px', () {
    testWidgets('renders Translate chip and opens quick language modal without overflow on 320px', (tester) async {
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final notice = AnnouncementModel(
        id: 20,
        title: 'Workshop on Artificial Intelligence',
        description: 'Hands-on training session for engineering students in Room 302.',
        category: 'Workshop',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        department: 'AIML',
        targetAudience: 'All Students',
        status: 'PUBLISHED',
        creatorName: 'Faculty Incharge',
        creatorRole: 'Teacher',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(
        createTestApp(
          SingleChildScrollView(
            child: AnnouncementFeedCard(notice: notice, index: 0),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify Translate chip is visible in the action bar
      expect(find.text('Translate'), findsOneWidget);

      // Tap Translate chip to open modal bottom sheet
      await tester.tap(find.text('Translate'));
      await tester.pumpAndSettle();

      // Verify modal sheet appears with language choices
      expect(find.text('Translate Notice'), findsOneWidget);
      expect(find.text('Select Regional Language:'), findsOneWidget);
      expect(find.text('🇮🇳 ಕನ್ನಡ'), findsOneWidget);

      // Select Kannada
      await tester.tap(find.text('🇮🇳 ಕನ್ನಡ'));
      await tester.pumpAndSettle();

      // Verify card was translated and zero overflow occurred
      expect(tester.takeException(), isNull);
    });
  });
}
