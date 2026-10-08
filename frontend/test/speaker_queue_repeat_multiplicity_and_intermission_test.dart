import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/echosphere_ai_controller.dart';
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
    test('1. Max Repeats: All notices rotate continuously (999999) throughout repeat time window', () {
      final queueCtrl = Get.put(SpeakerQueueController());

      final examNotice = {
        'id': 101,
        'title': 'Semester Exam Time Table Released',
        'priority': 'HIGH',
        'has_repeat': true,
      };
      expect(queueCtrl.getNoticeMaxRepeats(examNotice), equals(999999));

      final sportsNotice = {
        'id': 102,
        'title': 'Volley ball selection trials',
        'priority': 'NORMAL',
        'has_repeat': true,
      };
      expect(queueCtrl.getNoticeMaxRepeats(sportsNotice), equals(999999));

      final lostFoundNotice = {
        'id': 103,
        'title': 'Lost and found keys',
        'priority': 'LOW',
        'has_repeat': true,
      };
      expect(queueCtrl.getNoticeMaxRepeats(lostFoundNotice), equals(999999));

      final earthquakeNotice = {
        'id': 104,
        'title': 'Earthquake Alert - Evacuate Immediately',
        'priority': 'EMERGENCY',
        'has_repeat': true,
      };
      expect(queueCtrl.getNoticeMaxRepeats(earthquakeNotice), equals(999999));
    });

    test('2. Continuous 5-Notice Round-Robin Rotation in 15-Minute Slot', () async {
      final queueCtrl = Get.put(SpeakerQueueController());
      queueCtrl.queueItems.clear();

      // Teacher creates 5 notices for a 15-minute repeating time slot (e.g. 11:00-11:15)
      final n1 = {'id': 201, 'announcement_id': 201, 'title': 'Notice 1: Exam Timetable', 'priority': 'HIGH', 'has_repeat': true, 'played_count': 0};
      final n2 = {'id': 202, 'announcement_id': 202, 'title': 'Notice 2: Sports Trials', 'priority': 'NORMAL', 'has_repeat': true, 'played_count': 0};
      final n3 = {'id': 203, 'announcement_id': 203, 'title': 'Notice 3: Lost and Found', 'priority': 'LOW', 'has_repeat': true, 'played_count': 0};
      final n4 = {'id': 204, 'announcement_id': 204, 'title': 'Notice 4: Placement Drive', 'priority': 'HIGH', 'has_repeat': true, 'played_count': 0};
      final n5 = {'id': 205, 'announcement_id': 205, 'title': 'Notice 5: Library Returns', 'priority': 'NORMAL', 'has_repeat': true, 'played_count': 0};

      queueCtrl.queueItems.assignAll([n1, n2, n3, n4, n5]);
      queueCtrl.activeIndex.value = 0;
      queueCtrl.isPlaying.value = true;

      // Notice 1 plays (Round 1) -> re-queued to the back
      expect(queueCtrl.activeTitle, contains('Notice 1: Exam Timetable'));
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.queueItems.last['id'], equals(201));
      expect(queueCtrl.queueItems.last['repeat_round'], equals(2));

      // Notice 2 plays (Round 1) -> re-queued to the back
      expect(queueCtrl.activeTitle, contains('Notice 2: Sports Trials'));
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.queueItems.last['id'], equals(202));

      // Notice 3 plays (Round 1) -> re-queued to the back
      expect(queueCtrl.activeTitle, contains('Notice 3: Lost and Found'));
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.queueItems.last['id'], equals(203));

      // Notice 4 plays (Round 1) -> re-queued to the back
      expect(queueCtrl.activeTitle, contains('Notice 4: Placement Drive'));
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.queueItems.last['id'], equals(204));

      // Notice 5 plays (Round 1) -> re-queued to the back
      expect(queueCtrl.activeTitle, contains('Notice 5: Library Returns'));
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.queueItems.last['id'], equals(205));

      // Now Notice 1 plays Round 2! Full cycle completed and continuous rotation proceeds!
      expect(queueCtrl.activeTitle, contains('Notice 1: Exam Timetable'));
      expect(queueCtrl.queueItems[0]['repeat_round'], equals(2));
      await queueCtrl.completeCurrentPlayback();

      // Notice 2 plays Round 2!
      expect(queueCtrl.activeTitle, contains('Notice 2: Sports Trials'));
      expect(queueCtrl.queueItems[0]['repeat_round'], equals(2));
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
