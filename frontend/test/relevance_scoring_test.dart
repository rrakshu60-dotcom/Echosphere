import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/echosphere_ai_controller.dart';
import 'package:anymex/screens/home/home_dashboard_widgets.dart';
import 'package:anymex/services/echosphere_api_service.dart';

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.reset();
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

  group('Contextual Relevance Scoring Service & Fallback', () {
    test('calculateRelevanceFallback assigns high score and reasons for matching student', () {
      final api = EchosphereApiService();
      final userProfile = {
        'role': 'Student',
        'department': 'AIML',
        'semester': 5,
        'usn': '1DB23CI079',
      };
      final notices = [
        {
          'id': 1,
          'title': '5th Sem AIML Internal Assessment Examination',
          'description': 'Schedule for 5th semester AIML IA-1 exams in lab 3.',
          'department': 'AIML',
          'target_audience': '3rd Year Students',
          'category': 'Examination',
          'priority': 'HIGH',
        },
        {
          'id': 2,
          'title': 'Civil Engineering Survey Camp for 1st Year',
          'description': 'Field surveying practice for 1st semester civil students.',
          'department': 'CIVIL',
          'target_audience': '1st Year Students',
          'category': 'Workshop',
          'priority': 'NORMAL',
        }
      ];

      final scores = api.calculateRelevanceFallback(userProfile, notices);
      expect(scores.length, 2);

      // Match item
      final match = scores[0];
      expect(match['score'], greaterThanOrEqualTo(0.70));
      expect(match['is_highly_relevant'], isTrue);
      final reasons = (match['reasons'] as List).map((e) => e.toString()).toList();
      expect(reasons.any((r) => r.contains('AIML')), isTrue);
      expect(reasons.any((r) => r.contains('Semester 5') || r.contains('Examination')), isTrue);

      // Mismatch item
      final mismatch = scores[1];
      expect(mismatch['score'], lessThanOrEqualTo(0.40));
      expect(mismatch['is_highly_relevant'], isFalse);
    });

    test('calculateRelevanceFallback boosts emergency alert for all profiles', () {
      final api = EchosphereApiService();
      final userProfile = {
        'role': 'Student',
        'department': 'ME',
        'semester': 3,
      };
      final notices = [
        {
          'id': 3,
          'title': 'Emergency Campus Closure Notice',
          'description': 'Severe rainfall alert, college closed for all staff and students.',
          'department': 'General',
          'category': 'Emergency',
          'priority': 'EMERGENCY',
          'emergency_level': 'CRITICAL',
        }
      ];

      final scores = api.calculateRelevanceFallback(userProfile, notices);
      expect(scores.first['score'], greaterThanOrEqualTo(0.60));
      expect(scores.first['is_highly_relevant'], isTrue);
    });
  });

  group('AnnouncementFeedCard Relevance UI & Zero Overflow', () {
    testWidgets('Renders Relevant to You badge and displays criteria dialog on tap on 320px screen',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 700);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final notice = AnnouncementModel(
        id: 99,
        title: 'AIML 5th Sem Special Hackathon & Lab Exam',
        description: 'Mandatory participation for AIML semester 5 students in lab 4.',
        department: 'AIML',
        targetAudience: '3rd Year Students',
        category: 'Academic',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. Ramesh Rao',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(
        GetMaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: AnnouncementFeedCard(
                notice: notice,
                index: 0,
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify "🎯 Relevant to You" badge is displayed
      final badgeFinder = find.text('🎯 Relevant to You');
      expect(badgeFinder, findsOneWidget);

      // Verify zero layout overflow exception
      expect(tester.takeException(), isNull);

      // Tap the badge to view criteria insights
      await tester.tap(badgeFinder);
      await tester.pumpAndSettle();

      // Verify bottom sheet opened with Personalized Relevance details
      expect(find.text('Personalized Relevance'), findsOneWidget);
      expect(find.text('Why this notice was prioritized for you:'), findsOneWidget);

      // Verify zero layout overflow inside modal on 320px screen
      expect(tester.takeException(), isNull);
    });
  });
}
