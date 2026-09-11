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
      fullName: 'Dr. Ramesh Kumar',
      officialEmail: 'ramesh@echosphere.edu',
      role: 'Teacher',
      department: 'Civil Engineering',
    );
    Get.put(AnnouncementController());
    Get.put(EchosphereAiController());
  });

  tearDown(() {
    Get.reset();
  });

  group('Schedule Conflict Detection API & Fallback', () {
    test('EchosphereApiService detects venue collision and returns alternatives', () async {
      final api = EchosphereApiService();

      final res = await api.checkScheduleConflict(
        title: 'Civil Department Symposium',
        content: 'Hands-on symposium in Seminar Hall B on Oct 25, 2:30 PM.',
      );

      expect(res['has_conflict'], isTrue);
      final conflicts = res['conflicts'] as List;
      expect(conflicts.isNotEmpty, isTrue);

      final first = conflicts.first as Map;
      expect(first['conflicting_venue'], equals('Seminar Hall B'));
      expect(first['conflicting_notice_id'], equals(214));
      expect(first['conflict_message'], contains('Seminar Hall B'));

      final alternatives = res['suggested_alternatives'] as List;
      expect(alternatives.length, greaterThanOrEqualTo(2));
      expect(alternatives.any((a) => a['slot_type'] == 'same_day_later'), isTrue);
      expect(alternatives.any((a) => a['slot_type'] == 'alternative_venue'), isTrue);
    });

    test('EchosphereApiService returns no conflict for free slots', () async {
      final api = EchosphereApiService();

      final res = await api.checkScheduleConflict(
        title: 'Morning Lab Session',
        content: 'Routine lab session in Computer Lab 3 on Dec 10, 10:00 AM.',
      );

      expect(res['has_conflict'], isFalse);
      expect(res['conflicts'], isEmpty);
    });
  });

  group('CreateAnnouncementDialog Conflict Pre-Flight UI & Zero Overflow', () {
    testWidgets('Renders Schedule Conflict card and handles 1-tap alternative slot application on 320px screen',
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

      // Enter draft content that causes a venue collision in Seminar Hall B on Oct 25
      final textFields = find.byType(TextField);
      expect(textFields, findsNWidgets(2)); // Title and Description

      await tester.enterText(textFields.first, 'Civil Dept National Symposium 2026');
      await tester.enterText(textFields.last, 'Annual tech symposium in Seminar Hall B on Oct 25, 2:30 PM with guest speakers.');
      await tester.pumpAndSettle();

      // Verify Schedule Conflict Detected card is displayed
      expect(find.text('Schedule Conflict Detected'), findsOneWidget);
      expect(find.textContaining('1 Overlap'), findsOneWidget);
      expect(find.textContaining('Seminar Hall B'), findsWidgets);
      expect(find.text('Suggest Alternative Time Slots:'), findsOneWidget);

      // Verify alternative time slot chips appear
      final altChip = find.textContaining('Same Day, Later');
      expect(altChip, findsOneWidget);

      // Scroll so chip is visible within viewport on 320px screen
      await tester.ensureVisible(altChip);
      await tester.pumpAndSettle();

      // Tap on the alternative time slot chip
      await tester.tap(altChip);
      await tester.pumpAndSettle();

      // Verify conflict card is cleared and text updated
      expect(find.text('Schedule Conflict Detected'), findsNothing);
      expect(find.textContaining('[Rescheduled:'), findsOneWidget);

      // Verify zero layout overflow occurred on 320px screen
      expect(tester.takeException(), isNull);
    });
  });
}
