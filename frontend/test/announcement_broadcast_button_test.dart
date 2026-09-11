import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/speaker_queue_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/controllers/settings/settings.dart';
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
    Get.reset();
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});

    Get.put(Settings());
    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Dev Administrator',
      role: 'Dev Admin',
      department: 'AIML',
    );
  });

  tearDown(() {
    if (Get.isRegistered<AnnouncementController>()) {
      Get.find<AnnouncementController>().dispose();
    }
    if (Get.isRegistered<SpeakerQueueController>()) {
      Get.find<SpeakerQueueController>().cancelAllTimers();
    }
    Get.reset();
    Get.testMode = true;
  });

  testWidgets('Broadcast to Speakers button in AnnouncementDetailPage enqueues notice and plays if idle',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(800, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final annCtrl = Get.put(AnnouncementController());
    annCtrl.rxAnnouncements.clear();
    final queueCtrl = Get.put(SpeakerQueueController());
    queueCtrl.queueItems.clear();

    final testNotice = AnnouncementModel(
      id: 101,
      title: 'Urgent Campus Advisory',
      description: 'Classes in Block B will resume tomorrow morning at 8:30 AM.',
      department: 'College-Wide',
      category: 'General',
      priority: 'HIGH',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'Dev Administrator',
      creatorRole: 'Dev Admin',
      createdAt: DateTime.now(),
      deliverSpeaker: false,
      playedOnSpeaker: false,
    );
    annCtrl.rxAnnouncements.add(testNotice);

    await tester.pumpWidget(createTestApp(AnnouncementDetailPage(announcement: testNotice)));
    await tester.pumpAndSettle();

    // Verify "Broadcast to Speakers" button is present
    final broadcastBtn = find.text('Broadcast to Speakers');
    expect(broadcastBtn, findsOneWidget);

    // Tap Broadcast to Speakers
    await tester.ensureVisible(broadcastBtn);
    await tester.pumpAndSettle();
    await tester.tap(broadcastBtn);
    await tester.pumpAndSettle();

    // Verify SpeakerQueueController received the notice and marked it as Playing
    expect(queueCtrl.queueItems.length, 1);
    expect(queueCtrl.queueItems.first['title'], 'Urgent Campus Advisory');
    expect(queueCtrl.queueItems.first['status'], 'Playing');
    expect(queueCtrl.isPlaying.value, isTrue);

    // Verify AnnouncementController marked it as deliverSpeaker
    final updatedNotice = annCtrl.allAnnouncements.firstWhere((a) => a.id == 101);
    expect(updatedNotice.deliverSpeaker, isTrue);
  });

  testWidgets('Broadcasting while another notice is playing enqueues second notice behind active notice',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(800, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final annCtrl = Get.put(AnnouncementController());
    annCtrl.rxAnnouncements.clear();
    final queueCtrl = Get.put(SpeakerQueueController());
    queueCtrl.queueItems.clear();

    // First notice is already playing in the queue
    final firstNotice = AnnouncementModel(
      id: 201,
      title: 'First Active Announcement',
      description: 'First announcement content.',
      department: 'College-Wide',
      category: 'General',
      priority: 'NORMAL',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'Dev Administrator',
      creatorRole: 'Dev Admin',
      createdAt: DateTime.now(),
      deliverSpeaker: true,
      playedOnSpeaker: false,
    );
    annCtrl.rxAnnouncements.add(firstNotice);
    await queueCtrl.broadcastAnnouncement(firstNotice);

    expect(queueCtrl.isPlaying.value, isTrue);
    expect(queueCtrl.queueItems.first['status'], 'Playing');

    // Second notice
    final secondNotice = AnnouncementModel(
      id: 202,
      title: 'Second Queued Announcement',
      description: 'Second announcement content.',
      department: 'College-Wide',
      category: 'General',
      priority: 'HIGH',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'Dev Administrator',
      creatorRole: 'Dev Admin',
      createdAt: DateTime.now(),
      deliverSpeaker: false,
      playedOnSpeaker: false,
    );
    annCtrl.rxAnnouncements.add(secondNotice);

    // Now open AnnouncementDetailPage for secondNotice
    await tester.pumpWidget(createTestApp(AnnouncementDetailPage(announcement: secondNotice)));
    await tester.pumpAndSettle();

    final broadcastBtn = find.text('Broadcast to Speakers');
    expect(broadcastBtn, findsOneWidget);

    await tester.ensureVisible(broadcastBtn);
    await tester.pumpAndSettle();
    await tester.tap(broadcastBtn);
    await tester.pumpAndSettle();

    // Verify queue now has 2 items: first is Playing, second is Queued
    expect(queueCtrl.queueItems.length, 2);
    expect(queueCtrl.queueItems[0]['title'], 'First Active Announcement');
    expect(queueCtrl.queueItems[0]['status'], 'Playing');
    expect(queueCtrl.queueItems[1]['title'], 'Second Queued Announcement');
    expect(queueCtrl.queueItems[1]['status'], 'Queued');
    expect(queueCtrl.queueItems[1]['queue_position'], 2);
  });
}
