import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';

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

  test('Single-play speaker notice published now does NOT repeat in queue after playback finishes',
      () async {
    final annCtrl = Get.put(AnnouncementController());
    annCtrl.rxAnnouncements.clear();
    final queueCtrl = Get.put(SpeakerQueueController());
    queueCtrl.queueItems.clear();

    // 1. Create a single-play speaker announcement (repeatData = null)
    await annCtrl.createAnnouncement(
      title: 'Workshop on Edge Computing',
      description: 'Registration starts at 10:00 AM at the Seminar Hall.',
      department: 'CSE',
      category: 'Academic',
      priority: 'HIGH',
      creatorRole: 'Dev Admin',
      creatorName: 'Dev Administrator',
      deliverSpeaker: true,
      speakerNodeId: 1,
      repeatSchedule: null,
    );

    // Initial queue sync
    await queueCtrl.refreshQueue(silent: true);

    // Queue must have exactly 1 item
    expect(queueCtrl.queueItems.length, 1);
    expect(queueCtrl.queueItems.first['title'], 'Workshop on Edge Computing');
    expect(queueCtrl.queueItems.first['has_repeat'], isFalse);

    // 2. Start playback
    await queueCtrl.togglePlayPause(index: 0);
    expect(queueCtrl.isPlaying.value, isTrue);
    expect(queueCtrl.queueItems.first['status'], 'Playing');

    // 3. Complete playback
    await queueCtrl.completeCurrentPlayback();

    // Queue must now be empty
    expect(queueCtrl.queueItems.isEmpty, isTrue);
    expect(queueCtrl.isPlaying.value, isFalse);

    // 4. Repeated syncs and polls must NOT re-enqueue the completed single notice
    await queueCtrl.refreshQueue(silent: true);
    expect(queueCtrl.queueItems.isEmpty, isTrue);

    // Simulate another poll timer trigger
    await queueCtrl.refreshQueue(silent: true);
    expect(queueCtrl.queueItems.isEmpty, isTrue);
    expect(queueCtrl.isPlaying.value, isFalse);
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
