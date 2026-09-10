import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/controllers/settings/settings.dart';
import 'package:anymex/screens/home/home_dashboard_widgets.dart';
import 'package:anymex/screens/announcements/announcement_detail_page.dart';

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
    Get.put(Settings());
    Get.put(AnnouncementController());
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('AnnouncementFeedCard renders AI Summarize button and Listen button on 320px screen with zero overflow', (WidgetTester tester) async {
    // 320px screen width constraint testing
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final noticeWithSummary = AnnouncementModel(
      id: 201,
      title: 'VTU Semester Registration Guidelines',
      description: 'All 6th and 8th semester students must submit their elective options and pay lab fees before Friday.',
      priority: 'HIGH',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'Academic Office',
      department: 'CSE',
      category: 'Academics',
      createdAt: DateTime.now(),
      aiSummary: 'Elective registration and lab fee payments must be completed by Friday evening.',
    );

    await tester.pumpWidget(createTestApp(
      SingleChildScrollView(
        child: AnnouncementFeedCard(
          notice: noticeWithSummary,
          index: 0,
        ),
      ),
    ));
    await tester.pumpAndSettle();

    // Verify AI Summary banner is initially shown
    expect(find.text('AI Summary'), findsOneWidget);
    expect(find.text('Elective registration and lab fee payments must be completed by Friday evening.'), findsOneWidget);

    // Verify "Hide Summary" button exists
    expect(find.text('Hide Summary'), findsOneWidget);

    // Verify Kokoro TTS "Listen" button exists side-by-side
    expect(find.text('Listen'), findsOneWidget);

    // Verify Read Details button exists
    expect(find.text('Read Details →'), findsOneWidget);

    // Verify zero layout overflow error
    expect(tester.takeException(), isNull);

    // Tap "Hide Summary" to toggle off
    await tester.tap(find.text('Hide Summary'));
    await tester.pumpAndSettle();

    // Banner should be hidden and button text should be "View Summary"
    expect(find.text('AI Summary'), findsNothing);
    expect(find.text('View Summary'), findsOneWidget);

    // Tap "View Summary" to toggle on
    await tester.tap(find.text('View Summary'));
    await tester.pumpAndSettle();

    expect(find.text('AI Summary'), findsOneWidget);
    expect(find.text('Hide Summary'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('AnnouncementFeedCard without summary shows AI Summarize and handles tap', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final noticeWithoutSummary = AnnouncementModel(
      id: 202,
      title: 'Annual Tech Fest Ideathon',
      description: 'Submit your team project proposals for the inter-college hackathon by end of this week.',
      priority: 'NORMAL',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'Student Club',
      department: 'ISE',
      category: 'Events',
      createdAt: DateTime.now(),
      aiSummary: null,
    );

    await tester.pumpWidget(createTestApp(
      SingleChildScrollView(
        child: AnnouncementFeedCard(
          notice: noticeWithoutSummary,
          index: 0,
        ),
      ),
    ));
    await tester.pumpAndSettle();

    // Verify "AI Summarize" button is displayed
    expect(find.text('AI Summarize'), findsOneWidget);
    expect(find.text('Listen'), findsOneWidget);

    // Tap "AI Summarize" button
    await tester.tap(find.text('AI Summarize'));
    await tester.pump();

    // Pump and settle to complete API fallback / mock summary
    await tester.pumpAndSettle();

    // Zero overflow
    expect(tester.takeException(), isNull);
  });

  testWidgets('AnnouncementDetailPage displays distinct Qwen AI Summary box and NoticeAudioPlayerBar', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Student User',
      role: 'Student',
      department: 'AIML',
    );

    final notice = AnnouncementModel(
      id: 203,
      title: 'AI Lab Renovation Schedule',
      description: 'The GPU cluster lab will remain closed for maintenance this Saturday.',
      priority: 'NORMAL',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'System Admin',
      department: 'AIML',
      category: 'Academics',
      createdAt: DateTime.now(),
      aiSummary: 'GPU cluster lab is closed this Saturday for maintenance.',
    );

    await tester.pumpWidget(createTestApp(
      AnnouncementDetailPage(announcement: notice),
    ));
    await tester.pumpAndSettle();

    // Verify AI Summary title
    expect(find.text('AI Summary'), findsOneWidget);
    expect(find.text('GPU cluster lab is closed this Saturday for maintenance.'), findsOneWidget);

    // Verify audio player bar is also mounted separately
    expect(find.text('Listen to Notice (Neural TTS)'), findsOneWidget);

    expect(tester.takeException(), isNull);
  });
}
