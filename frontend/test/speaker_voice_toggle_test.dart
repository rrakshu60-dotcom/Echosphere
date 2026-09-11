import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/speaker_queue_controller.dart';
import 'package:anymex/controllers/echosphere_ai_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/controllers/settings/settings.dart';
import 'package:anymex/screens/announcements/create_announcement_dialog.dart';
import 'package:anymex/screens/announcements/announcement_detail_page.dart';
import 'package:anymex/screens/admin/announcement_management_page.dart';

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
    Get.put(AuthController());
    Get.put(EchosphereAiController());
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('CreateAnnouncementDialog displays Male/Female voice toggle when Speaker Announcement is selected on 320px screen', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Dr. Faculty Admin',
      role: 'Dev Admin',
      department: 'CSE',
    );
    Get.put(AnnouncementController());
    Get.put(SpeakerQueueController());

    await tester.pumpWidget(createTestApp(const CreateAnnouncementDialog()));
    await tester.pumpAndSettle();

    // Verify dialog loaded
    expect(find.text('Create & Schedule Announcement'), findsOneWidget);

    // Find the 'Speaker Announcement' chip
    final speakerChipFinder = find.widgetWithText(FilterChip, 'Speaker Announcement');
    expect(speakerChipFinder, findsOneWidget);

    // Initially, voice selection should not be visible because deliverSpeaker is false
    expect(find.text('Female Voice'), findsNothing);
    expect(find.text('Male Voice'), findsNothing);

    // Scroll to and select 'Speaker Announcement'
    await tester.ensureVisible(speakerChipFinder);
    await tester.pumpAndSettle();
    await tester.tap(speakerChipFinder);
    await tester.pumpAndSettle();

    // Voice options should now be visible
    expect(find.text('Female Voice'), findsOneWidget);
    expect(find.text('Male Voice'), findsOneWidget);

    // Tap 'Male Voice'
    await tester.tap(find.text('Male Voice'));
    await tester.pumpAndSettle();

    // Verify Male chip is selected
    final maleChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Male Voice'));
    expect(maleChip.selected, isTrue);

    // Tap back to 'Female Voice'
    await tester.tap(find.text('Female Voice'));
    await tester.pumpAndSettle();

    final femaleChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Female Voice'));
    expect(femaleChip.selected, isTrue);

    // No layout overflow
    expect(tester.takeException(), isNull);
  });

  testWidgets('AnnouncementDetailPage Modify dialog allows toggling Speaker Notice and Male/Female voice on 320px screen', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Dr. Principal',
      role: 'Principal',
      department: 'AIML',
    );
    Get.put(AnnouncementController());

    final sampleNotice = AnnouncementModel(
      id: 501,
      title: 'Annual Sports Meet 2026',
      description: 'Campus sports registrations open starting tomorrow morning.',
      priority: 'NORMAL',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'Physical Education Dept',
      department: 'Sports',
      category: 'Sports',
      createdAt: DateTime.now(),
      deliverSpeaker: false,
      speakerVoice: 'female',
    );

    await tester.pumpWidget(createTestApp(AnnouncementDetailPage(announcement: sampleNotice)));
    await tester.pumpAndSettle();

    // Look for 'Modify' button
    final modifyBtn = find.text('Modify');
    expect(modifyBtn, findsOneWidget);

    await tester.ensureVisible(modifyBtn);
    await tester.pumpAndSettle();
    await tester.tap(modifyBtn);
    await tester.pumpAndSettle();

    // Modify Announcement dialog should appear
    expect(find.text('Modify Announcement'), findsOneWidget);

    // Find 'Speaker Notice' filter chip
    final speakerNoticeChip = find.widgetWithText(FilterChip, 'Speaker Notice');
    expect(speakerNoticeChip, findsOneWidget);

    // Initially deliverSpeaker is false so voice chips are hidden
    expect(find.text('Male Voice'), findsNothing);

    // Scroll to and tap 'Speaker Notice'
    await tester.ensureVisible(speakerNoticeChip);
    await tester.pumpAndSettle();
    await tester.tap(speakerNoticeChip);
    await tester.pumpAndSettle();

    // Now voice selection chips should appear
    final femaleChipFinder = find.text('Female Voice');
    final maleChipFinder = find.text('Male Voice');
    expect(femaleChipFinder, findsOneWidget);
    expect(maleChipFinder, findsOneWidget);

    // Scroll to and toggle to Male Voice
    await tester.ensureVisible(maleChipFinder);
    await tester.pumpAndSettle();
    await tester.tap(maleChipFinder);
    await tester.pumpAndSettle();

    final maleChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Male Voice'));
    expect(maleChip.selected, isTrue);

    // Confirm update
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
  });

  testWidgets('AnnouncementManagementPage Modify dialog includes Speaker Notice & Male/Female voice toggle on 320px screen', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Admin User',
      role: 'Dev Admin',
      department: 'CSE',
    );
    final annController = Get.put(AnnouncementController());

    final sampleNotice = AnnouncementModel(
      id: 601,
      title: 'Campus Hackathon Briefing',
      description: 'Orientation session for upcoming 24-hour smart campus hackathon.',
      priority: 'HIGH',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'Admin User',
      department: 'CSE',
      category: 'Events',
      createdAt: DateTime.now(),
      deliverSpeaker: true,
      speakerVoice: 'female',
    );
    annController.setAnnouncements([sampleNotice]);

    await tester.pumpWidget(createTestApp(const AnnouncementManagementPage()));
    await tester.pumpAndSettle();

    // Find and tap edit icon on the notice card
    final editIcon = find.byIcon(Icons.edit_rounded);
    expect(editIcon, findsAtLeastNWidgets(1));
    await tester.tap(editIcon.first);
    await tester.pumpAndSettle();

    // Check dialog opens
    expect(find.text('Modify Announcement'), findsOneWidget);

    // Since deliverSpeaker is already true, voice chips should be visible immediately
    final femaleChipFinder = find.text('Female Voice');
    final maleChipFinder = find.text('Male Voice');
    expect(femaleChipFinder, findsOneWidget);
    expect(maleChipFinder, findsOneWidget);

    // Scroll to and toggle to Male Voice
    await tester.ensureVisible(maleChipFinder);
    await tester.pumpAndSettle();
    await tester.tap(maleChipFinder);
    await tester.pumpAndSettle();

    final maleChip = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Male Voice'));
    expect(maleChip.selected, isTrue);

    // Tap confirm
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
  });
}
