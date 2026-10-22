import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';
import 'support/server_queue.dart';

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

  test('Single-play speaker notice published now does NOT repeat in queue after playback finishes', () {
    Get.put(AnnouncementController());
    final queueCtrl = Get.put(SpeakerQueueController());

    queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: [
      serverQueueItem(id: 7, announcementId: 701, title: 'Workshop on Edge Computing', status: 'Playing', speakerConfirmed: true, speakerElapsedSeconds: 1),
    ]);
    expect(queueCtrl.queueItems.length, 1);
    expect(queueCtrl.queueItems.first['has_repeat'], isFalse);
    expect(queueCtrl.queueItems.first['max_repeats'], 1);

    // Backend: finished and gone. Later polls keep returning an empty queue.
    for (var poll = 0; poll < 3; poll++) {
      queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: const []);
      expect(queueCtrl.queueItems.isEmpty, isTrue);
      expect(queueCtrl.isPlaying.value, isFalse);
    }
  });

  test('Temporary ID is reconciled with backend ID without spawning duplicate items in SpeakerQueue',
      () async {
    final annCtrl = Get.put(AnnouncementController());
    annCtrl.rxAnnouncements.clear();
    final queueCtrl = Get.put(SpeakerQueueController());
    queueCtrl.queueItems.clear();

    const tempId = 1740001234567;
    const realBackendId = 301;

    // Simulate initial local announcement with temporary ID
    final tempAnn = AnnouncementModel(
      id: tempId,
      title: 'Library Hours Extended',
      description: 'The central library will remain open until 10 PM.',
      department: 'College-Wide',
      category: 'General',
      creatorName: 'Dev Administrator',
      priority: 'NORMAL',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      createdAt: DateTime.now(),
      deliverSpeaker: true,
      speakerNodeId: 1,
      durationSeconds: 15,
      playedOnSpeaker: false,
    );

    annCtrl.rxAnnouncements.add(tempAnn);
    await queueCtrl.refreshQueue(silent: true);

    expect(queueCtrl.queueItems.length, 1);
    expect(queueCtrl.queueItems.first['id'], tempId);

    // Reconcile ID from backend response
    queueCtrl.replaceTemporaryId(tempId, realBackendId);

    expect(queueCtrl.queueItems.length, 1);
    expect(queueCtrl.queueItems.first['id'], realBackendId);
    expect(queueCtrl.queueItems.first['announcement_id'], realBackendId);

    // Syncing again with backend ID must not create a duplicate
    final realAnn = tempAnn.copyWith(id: realBackendId);
    annCtrl.rxAnnouncements[0] = realAnn;
    await queueCtrl.refreshQueue(silent: true);

    expect(queueCtrl.queueItems.length, 1);
  });
}
