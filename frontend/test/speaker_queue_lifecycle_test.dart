import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/speaker_queue_controller.dart';
import 'package:anymex/screens/announcements/speaker_queue_page.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Dev Administrator',
      role: 'Dev Admin',
      department: 'AIML',
    );
  });

  tearDown(() {
    if (Get.isRegistered<SpeakerQueueController>()) {
      Get.find<SpeakerQueueController>().cancelAllTimers();
    }
    Get.reset();
    Get.testMode = true;
  });

  test('Speaker notice creation immediately links to SpeakerQueue and appears in queue list',
      () async {
    final annCtrl = Get.put(AnnouncementController());
    annCtrl.rxAnnouncements.clear();
    final queueCtrl = Get.put(SpeakerQueueController());
    queueCtrl.queueItems.clear();

    // Initially queue is empty
    expect(queueCtrl.queueItems.isEmpty, isTrue);

    // Create and publish a speaker notice
    await annCtrl.createAnnouncement(
      title: 'Annual Sports Meet 2026 Announcement',
      description: 'All athletes must assemble at the main ground by 9:00 AM.',
      department: 'College-Wide',
      category: 'Sports',
      priority: 'HIGH',
      creatorRole: 'Dev Admin',
      creatorName: 'Dev Administrator',
      deliverSpeaker: true,
      speakerNodeId: 1,
    );

    // Verify AnnouncementController has the notice marked with deliverSpeaker
    final createdNotice = annCtrl.allAnnouncements.firstWhere((a) => a.title.contains('Annual Sports Meet'));
    expect(createdNotice.deliverSpeaker, isTrue);
    expect(createdNotice.playedOnSpeaker, isFalse);

    // Queue syncs
    await queueCtrl.refreshQueue(silent: true);

    // Verify SpeakerQueueController now contains the notice
    expect(queueCtrl.queueItems.length, 1);
    expect(queueCtrl.queueItems.first['title'], 'Annual Sports Meet 2026 Announcement');
    expect(queueCtrl.activeTitle, 'Annual Sports Meet 2026 Announcement');
  });

  test('Speaker notice plays once and is automatically removed from queue upon completion',
      () async {
    final annCtrl = Get.put(AnnouncementController());
    annCtrl.rxAnnouncements.clear();
    final queueCtrl = Get.put(SpeakerQueueController());
    queueCtrl.queueItems.clear();

    // Create a speaker notice
    await annCtrl.createAnnouncement(
      title: 'Lab Maintenance Alert',
      description: 'The AI & Robotics lab will remain closed for maintenance.',
      department: 'AIML',
      category: 'Academic',
      priority: 'MEDIUM',
      creatorRole: 'Dev Admin',
      creatorName: 'Dev Administrator',
      deliverSpeaker: true,
      speakerNodeId: 1,
    );

    await queueCtrl.refreshQueue(silent: true);
    expect(queueCtrl.queueItems.length, 1);

    // Start playback
    await queueCtrl.togglePlayPause(index: 0);
    expect(queueCtrl.isPlaying.value, isTrue);
    expect(queueCtrl.queueItems.first['status'], 'Playing');

    // Simulate elapsed progress
    queueCtrl.currentElapsedSeconds.value = 5;
    expect(queueCtrl.currentElapsedFormatted, '00:05');
    expect(queueCtrl.currentTotalFormatted, '00:10');

    // Complete playback (simulating timer reaching total duration)
    await queueCtrl.completeCurrentPlayback();

    // Verify notice has been marked as played in AnnouncementController
    final playedNotice = annCtrl.allAnnouncements.firstWhere((a) => a.title.contains('Lab Maintenance Alert'));
    expect(playedNotice.playedOnSpeaker, isTrue);

    // Verify the played notice has been REMOVED from the speaker queue list
    expect(queueCtrl.queueItems.isEmpty, isTrue);
    expect(queueCtrl.isPlaying.value, isFalse);
    expect(queueCtrl.activeTitle, 'No active speaker announcement');
  });

  test('Multiple speaker notices play sequentially and remove each one upon completion',
      () async {
    final annCtrl = Get.put(AnnouncementController());
    annCtrl.rxAnnouncements.clear();
    final queueCtrl = Get.put(SpeakerQueueController());
    queueCtrl.queueItems.clear();

    // Notice 1
    await annCtrl.createAnnouncement(
      title: 'Notice Alpha: Morning Bell',
      description: 'Classes begin in 5 minutes.',
      department: 'College-Wide',
      category: 'General',
      priority: 'LOW',
      creatorRole: 'Dev Admin',
      creatorName: 'Dev Administrator',
      deliverSpeaker: true,
    );

    // Notice 2
    await annCtrl.createAnnouncement(
      title: 'Notice Beta: Workshop Registration',
      description: 'Last day to register for the AI workshop.',
      department: 'CSE',
      category: 'Academic',
      priority: 'HIGH',
      creatorRole: 'Dev Admin',
      creatorName: 'Dev Administrator',
      deliverSpeaker: true,
    );

    await queueCtrl.refreshQueue(silent: true);
    expect(queueCtrl.queueItems.length, 2);

    // Notice Alpha is active first (first notice queued)
    expect(queueCtrl.activeTitle, 'Notice Alpha: Morning Bell');

    // Play Notice Alpha and complete it
    await queueCtrl.completeCurrentPlayback();

    // Notice Alpha is now completed and removed from queue! Notice Beta is next:
    expect(queueCtrl.queueItems.length, 1);
    expect(queueCtrl.activeTitle, 'Notice Beta: Workshop Registration');

    // Complete Notice Beta
    await queueCtrl.completeCurrentPlayback();

    // Notice Beta is now completed and removed from queue! All notices have played once and are removed.
    expect(queueCtrl.queueItems.isEmpty, isTrue);
    expect(queueCtrl.isPlaying.value, isFalse);
  });

  testWidgets('SpeakerQueuePage renders live progress bar and controls with zero overflow on 320px screen',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final annCtrl = Get.put(AnnouncementController());
    annCtrl.rxAnnouncements.clear();
    final queueCtrl = Get.put(SpeakerQueueController());
    queueCtrl.queueItems.clear();

    await annCtrl.createAnnouncement(
      title: 'Emergency Drill in 10 Minutes',
      description: 'Please calmly evacuate via the nearest stairway.',
      department: 'College-Wide',
      category: 'Emergency',
      priority: 'EMERGENCY',
      creatorRole: 'Dev Admin',
      creatorName: 'Dev Administrator',
      deliverSpeaker: true,
    );
    await queueCtrl.refreshQueue(silent: true);

    await tester.pumpWidget(
      const GetMaterialApp(
        home: SpeakerQueuePage(),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 100));

    // Verify title is rendered on the page
    expect(find.text('Emergency Drill in 10 Minutes'), findsWidgets);

    // Tap Play button if available
    final playBtn = find.text('Play');
    if (playBtn.evaluate().isNotEmpty) {
      await tester.tap(playBtn.first);
      await tester.pump(const Duration(milliseconds: 100));
    }

    // Progress bar and countdown are visible
    expect(find.byType(LinearProgressIndicator), findsWidgets);
    expect(find.textContaining('/'), findsWidgets);

    // Verify no layout overflow
    final exc = tester.takeException();
    expect(exc, isNull);
  });
}
