import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/echosphere_ai_controller.dart';
import 'package:anymex/screens/announcements/create_announcement_dialog.dart';
import 'package:anymex/services/echosphere_api_service.dart';

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.reset();
    final authController = Get.put(AuthController());
    authController.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Prof. Anitha Sharma',
      officialEmail: 'anitha@echosphere.edu',
      role: 'Teacher',
      department: 'CSE',
    );
    Get.put(AnnouncementController());
    Get.put(EchosphereAiController());
  });

  tearDown(() {
    Get.reset();
  });

  group('Audience Pre-Flight Check API & Fallback', () {
    test('EchosphereApiService detects overly broad audience for department notice', () async {
      final api = EchosphereApiService();

      final res = await api.checkAudienceMismatch(
        title: 'Operating Systems Lab Exam',
        content: 'All 3rd Year CSE students must report to CS Lab 1 for practicals.',
        selectedAudience: 'Entire College',
      );

      expect(res['has_mismatch'], isTrue);
      final suggested = (res['suggested_audiences'] as List).map((e) => e.toString()).toList();
      expect(suggested.contains('CSE Department') || suggested.contains('3rd Year Students'), isTrue);
      expect(res['warning_message'], contains('Entire College'));
    });

    test('EchosphereApiService allows legitimate college-wide announcements without warning', () async {
      final api = EchosphereApiService();

      final res = await api.checkAudienceMismatch(
        title: 'Institutional Holiday Announcement: Kannada Rajyotsava',
        content: 'The college campus will remain closed on Friday. All classes suspended.',
        selectedAudience: 'Entire College',
      );

      expect(res['has_mismatch'], isFalse);
      expect(res['suggested_audiences'], isEmpty);
    });
  });

  group('CreateAnnouncementDialog Audience Pre-Flight UI & Zero Overflow', () {
    testWidgets('Renders Audience Recommendation card and narrows audience on 1-tap chip on 320px screen',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 700);
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
                child: const Text('Open Dialog'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open Dialog'));
      await tester.pumpAndSettle();

      // Enter draft content targeting CSE Department while audience is 'Entire College'
      final textFields = find.byType(TextField);
      expect(textFields, findsNWidgets(2)); // Title and Description

      await tester.enterText(textFields.first, 'CSE Machine Learning Workshop');
      await tester.enterText(textFields.last, 'All CSE Department students must register for the upcoming deep learning lab workshop.');
      await tester.pumpAndSettle();

      // Verify Audience Recommendation (Anti-Spam Guard) card is displayed
      expect(find.text('Audience Recommendation (Anti-Spam Guard)'), findsOneWidget);
      expect(find.text('1-Tap Audience Narrowing:'), findsOneWidget);

      final narrowChip = find.textContaining('Narrow to: CSE Department');
      expect(narrowChip, findsOneWidget);

      // Scroll so chip is visible within viewport on 320px compact screen
      await tester.ensureVisible(narrowChip);
      await tester.pumpAndSettle();

      // Tap on the 1-tap Narrowing chip
      await tester.tap(narrowChip);
      await tester.pumpAndSettle();

      // Verify audience warning is dismissed and audience narrowed
      expect(find.text('Audience Recommendation (Anti-Spam Guard)'), findsNothing);

      // Verify zero layout overflow occurred on 320px screen
      expect(tester.takeException(), isNull);
    });
  });
}
