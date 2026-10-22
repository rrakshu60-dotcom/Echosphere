import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/echosphere_ai_controller.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
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
    Get.put(EchosphereAiController());
  });

  tearDown(() {
    if (Get.isRegistered<SpeakerQueueController>()) {
      Get.find<SpeakerQueueController>().cancelAllTimers();
    }
    Get.reset();
    Get.testMode = true;
  });

  group('Speaker Queue Continuous Slot Rotation & Emergency Override Verification', () {
    test('1. Max Repeats: the repeat count and round come from the backend schedule', () {
      Get.put(AnnouncementController());
      final queueCtrl = Get.put(SpeakerQueueController());

      queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: [
        serverQueueItem(id: 1, announcementId: 101, title: 'Semester Exam Time Table Released', priority: 'HIGH', hasRepeat: true, maxRepeats: 5, totalPlayedCount: 2),
        serverQueueItem(id: 2, announcementId: 102, title: 'Lost and found keys', priority: 'LOW', queuePosition: 2, hasRepeat: true, maxRepeats: 4, totalPlayedCount: 0),
      ]);

      final exam = queueCtrl.queueItems.firstWhere((q) => q['announcement_id'] == 101);
      expect(exam['has_repeat'], isTrue);
      expect(exam['max_repeats'], 5);
      expect(exam['played_count'], 2);
      expect(exam['repeat_round'], 3);
      expect(exam['is_repeat'], isTrue);

      final keys = queueCtrl.queueItems.firstWhere((q) => q['announcement_id'] == 102);
      expect(keys['max_repeats'], 4);
      expect(keys['repeat_round'], 1);
      expect(keys['is_repeat'], isFalse);
    });

    test('2. Continuous 5-Notice Round-Robin Rotation in 15-Minute Slot', () {
      Get.put(AnnouncementController());
      final queueCtrl = Get.put(SpeakerQueueController());

      List<Map<String, dynamic>> snapshot(List<int> order, Map<int, int> played, int playingId) => [
            for (var i = 0; i < order.length; i++)
              serverQueueItem(
                id: order[i],
                announcementId: 200 + order[i],
                title: 'Notice ${order[i]}',
                status: order[i] == playingId ? 'Playing' : 'Queued',
                queuePosition: i + 1,
                hasRepeat: true,
                maxRepeats: 999,
                totalPlayedCount: played[order[i]] ?? 0,
                speakerConfirmed: order[i] == playingId,
                speakerElapsedSeconds: order[i] == playingId ? 0 : null,
              ),
          ];

      // Round 1: notice 1 is playing, 2-5 wait.
      queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: snapshot([1, 2, 3, 4, 5], {}, 1));
      expect(queueCtrl.queueItems.map((q) => q['title']).toList(), ['Notice 1', 'Notice 2', 'Notice 3', 'Notice 4', 'Notice 5']);
      expect(queueCtrl.activeTitle, 'Notice 1');

      // Backend re-queues notice 1 at the back after it plays; notice 2 plays.
      queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: snapshot([2, 3, 4, 5, 1], {1: 1}, 2));
      expect(queueCtrl.queueItems.map((q) => q['title']).toList(), ['Notice 2', 'Notice 3', 'Notice 4', 'Notice 5', 'Notice 1']);
      expect(queueCtrl.activeTitle, 'Notice 2');

      // After all five played once, notice 1 plays round 2.
      queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: snapshot([1, 2, 3, 4, 5], {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}, 1));
      final first = queueCtrl.queueItems.first;
      expect(queueCtrl.activeTitle, 'Notice 1');
      expect(first['repeat_round'], 2);
      expect(first['played_count'], 1);
    });

    test('3. Emergency Override: Earthquake alert overrides ALL 5 notices and loops exclusively for entire slot', () async {
      final queueCtrl = Get.put(SpeakerQueueController());
      queueCtrl.queueItems.clear();

      // 5 regular notices queued
      final regularNotices = [
        {'id': 301, 'announcement_id': 301, 'title': 'Sem Exam Notice', 'priority': 'HIGH', 'has_repeat': true, 'played_count': 0},
        {'id': 302, 'announcement_id': 302, 'title': 'Volleyball Selection', 'priority': 'NORMAL', 'has_repeat': true, 'played_count': 0},
        {'id': 303, 'announcement_id': 303, 'title': 'Lost Keys in Canteen', 'priority': 'LOW', 'has_repeat': true, 'played_count': 0},
        {'id': 304, 'announcement_id': 304, 'title': 'Guest Lecture', 'priority': 'NORMAL', 'has_repeat': true, 'played_count': 0},
        {'id': 305, 'announcement_id': 305, 'title': 'Fee Payment Reminder', 'priority': 'HIGH', 'has_repeat': true, 'played_count': 0},
      ];
      queueCtrl.queueItems.assignAll(regularNotices);
      queueCtrl.activeIndex.value = 0;
      queueCtrl.isPlaying.value = true;

      // An Emergency notice (Earthquake Alert) appears!
      final earthquakeNotice = {
        'id': 999,
        'announcement_id': 999,
        'title': 'URGENT: Earthquake Alert - Evacuate Building!',
        'priority': 'EMERGENCY',
        'has_repeat': true,
        'played_count': 0,
        'status': 'Queued',
      };
      queueCtrl.queueItems.add(earthquakeNotice);

      // Current notice finishes playback -> Emergency preemption kicks in!
      await queueCtrl.completeCurrentPlayback();

      // Verify: Earthquake notice immediately took index 0 (Active slot)!
      expect(queueCtrl.activeIndex.value, equals(0));
      expect(queueCtrl.activeTitle, contains('Earthquake Alert'));
      expect(queueCtrl.queueItems[0]['status'], equals('Playing'));

      // Verify: ALL other regular notices are PAUSED and suppressed!
      for (int i = 1; i < queueCtrl.queueItems.length; i++) {
        expect(queueCtrl.queueItems[i]['status'], equals('Paused'),
            reason: 'All non-emergency notices must be paused during emergency lockdown');
      }

      // Emergency notice finishes round 1 -> Loops continuously for the entire slot!
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.activeIndex.value, equals(0));
      expect(queueCtrl.activeTitle, contains('Earthquake Alert'));
      expect(queueCtrl.isPlaying.value, isTrue);

      // Verify: Even in round 2 and round 3, earthquake notice continues alone!
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.activeTitle, contains('Earthquake Alert'));
    });

    test('4. Clean UI: No stuck intermission and active title displays true announcement title', () async {
      final queueCtrl = Get.put(SpeakerQueueController());
      queueCtrl.queueItems.clear();

      final notice = {
        'id': 401,
        'announcement_id': 401,
        'title': 'Semester Examination Time Table',
        'department': 'CSE',
        'node_name': 'Block A Corridor',
        'duration_seconds': 15,
        'status': 'Playing',
        'has_repeat': true,
        'played_count': 0,
      };
      queueCtrl.queueItems.add(notice);
      queueCtrl.activeIndex.value = 0;

      // Active title must be the real announcement title, never "Intermission (12s)"
      expect(queueCtrl.activeTitle, equals('Semester Examination Time Table'));
      expect(queueCtrl.activeSubtitle, equals('CSE • Block A Corridor'));

      // Background refreshQueue polling must never replace the title with an intermission countdown
      await queueCtrl.refreshQueue(silent: true);
      expect(queueCtrl.activeTitle, equals('Semester Examination Time Table'));
    });
  });
}
