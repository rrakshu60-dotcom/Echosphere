import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/controllers/announcement_controller.dart';
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

  group('Speaker Queue Repeat Multiplicity & Intermission Glitch Verification', () {
    test('1. Priority Classification & Max Repeats: High (3x), Normal (2x), Low (1x), Emergency (Continuous)', () {
      final aiCtrl = Get.find<EchosphereAiController>();
      final queueCtrl = Get.put(SpeakerQueueController());

      // Test 1A: Semester Exam Notice -> HIGH Priority -> 3 Repeats
      final highRec = aiCtrl.recommendPriorityAndCategory(
        'Semester Exam Time Table Released',
        'Final semester examination timetable has been published on the notice board.',
        userRole: 'Teacher',
      );
      expect(highRec['priority'], equals('HIGH'));
      final highItem = {
        'id': 101,
        'title': 'Semester Exam Time Table Released',
        'priority': highRec['priority'],
        'has_repeat': true,
      };
      expect(queueCtrl.getNoticeMaxRepeats(highItem), equals(3));

      // Test 1B: Volleyball Selection Notice -> NORMAL Priority -> 2 Repeats
      final normalRec = aiCtrl.recommendPriorityAndCategory(
        'Volley ball selection trials',
        'College volleyball team selection trials at the indoor sports ground.',
        userRole: 'Teacher',
      );
      expect(normalRec['priority'], equals('NORMAL'));
      final normalItem = {
        'id': 102,
        'title': 'Volley ball selection trials',
        'priority': normalRec['priority'],
        'has_repeat': true,
      };
      expect(queueCtrl.getNoticeMaxRepeats(normalItem), equals(2));

      // Test 1C: Lost and Found Notice -> LOW Priority -> 1 Repeat
      final lowRec = aiCtrl.recommendPriorityAndCategory(
        'Lost and found keys',
        'Lost a bunch of keys near the campus canteen yesterday.',
        userRole: 'Teacher',
      );
      expect(lowRec['priority'], equals('LOW'));
      final lowItem = {
        'id': 103,
        'title': 'Lost and found keys',
        'priority': lowRec['priority'],
        'has_repeat': true,
      };
      expect(queueCtrl.getNoticeMaxRepeats(lowItem), equals(1));

      // Test 1D: Emergency Notice -> EMERGENCY Priority -> 999999 Continuous Loop
      final emergItem = {
        'id': 104,
        'title': 'Campus Fire Emergency Evacuation',
        'priority': 'EMERGENCY',
        'has_repeat': true,
      };
      expect(queueCtrl.getNoticeMaxRepeats(emergItem), equals(999999));
    });

    test('2. Multi-Tier Repeat Lifecycle: High plays 3 times, Medium plays 2 times, Low plays 1 time', () async {
      final annCtrl = Get.put(AnnouncementController());
      annCtrl.rxAnnouncements.clear();
      final queueCtrl = Get.put(SpeakerQueueController());
      queueCtrl.queueItems.clear();

      // Enqueue Low notice (1x cap)
      final lowItem = {
        'id': 201,
        'announcement_id': 201,
        'title': 'Lost and found keys in canteen',
        'priority': 'LOW',
        'duration_seconds': 15,
        'status': 'Playing',
        'has_repeat': true,
        'repeat_round': 1,
        'played_count': 0,
      };

      // Enqueue Medium notice (2x cap)
      final medItem = {
        'id': 202,
        'announcement_id': 202,
        'title': 'Volley ball selection trials',
        'priority': 'NORMAL',
        'duration_seconds': 15,
        'status': 'Queued',
        'has_repeat': true,
        'repeat_round': 1,
        'played_count': 0,
      };

      // Enqueue High notice (3x cap)
      final highItem = {
        'id': 203,
        'announcement_id': 203,
        'title': 'Sem exam timetable published',
        'priority': 'HIGH',
        'duration_seconds': 15,
        'status': 'Queued',
        'has_repeat': true,
        'repeat_round': 1,
        'played_count': 0,
      };

      queueCtrl.queueItems.assignAll([lowItem, medItem, highItem]);
      queueCtrl.activeIndex.value = 0;
      queueCtrl.isPlaying.value = true;

      // Play Low notice: Round 1 (1x cap -> finished after 1 play!)
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.queueItems.any((q) => q['id'] == 201), isFalse,
          reason: 'Low notice should be removed after 1st playback (cap = 1x)');

      // Play Medium notice: Round 1 (2x cap -> re-queued for Round 2)
      expect(queueCtrl.queueItems[0]['id'], equals(202));
      await queueCtrl.completeCurrentPlayback();
      final reMed = queueCtrl.queueItems.firstWhere((q) => q['id'] == 202);
      expect(reMed['played_count'], equals(1));
      expect(reMed['repeat_round'], equals(2));

      // Play High notice: Round 1 (3x cap -> re-queued for Round 2)
      expect(queueCtrl.queueItems[0]['id'], equals(203));
      await queueCtrl.completeCurrentPlayback();
      final reHigh = queueCtrl.queueItems.firstWhere((q) => q['id'] == 203);
      expect(reHigh['played_count'], equals(1));
      expect(reHigh['repeat_round'], equals(2));

      // Now Medium notice plays Round 2 (cap = 2x -> completed and removed!)
      expect(queueCtrl.queueItems[0]['id'], equals(202));
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.queueItems.any((q) => q['id'] == 202), isFalse,
          reason: 'Medium notice should be removed after 2nd playback (cap = 2x)');

      // High notice plays Round 2 (cap = 3x -> re-queued for Round 3)
      expect(queueCtrl.queueItems[0]['id'], equals(203));
      await queueCtrl.completeCurrentPlayback();
      final reHighRound3 = queueCtrl.queueItems.firstWhere((q) => q['id'] == 203);
      expect(reHighRound3['played_count'], equals(2));
      expect(reHighRound3['repeat_round'], equals(3));

      // High notice plays Round 3 (cap = 3x -> completed and removed!)
      expect(queueCtrl.queueItems[0]['id'], equals(203));
      await queueCtrl.completeCurrentPlayback();
      expect(queueCtrl.queueItems.isEmpty, isTrue,
          reason: 'All repeat schedules completed according to exact priority quotas!');
    });

    test('3. Intermission Safety: Elapsed seconds reset to 0 and polling does not prematurely complete round 2', () async {
      final queueCtrl = Get.put(SpeakerQueueController());
      queueCtrl.queueItems.clear();

      // Simulate a repeat notice that just completed Round 1
      final repeatNotice = {
        'id': 301,
        'announcement_id': 301,
        'title': 'Volley ball selection trials',
        'priority': 'NORMAL',
        'duration_seconds': 15,
        'status': 'Queued',
        'has_repeat': true,
        'repeat_round': 2,
        'played_count': 1,
      };
      queueCtrl.queueItems.add(repeatNotice);

      // Verify that during intermission, elapsed seconds are 0
      queueCtrl.isIntermission.value = true;
      queueCtrl.intermissionSecondsRemaining.value = 15;
      queueCtrl.currentElapsedSeconds.value = 0;

      // Simulate refreshQueue() polling while intermission is actively ticking
      // Ensure refreshQueue does not accidentally mark notice as Playing and run playback timer
      await queueCtrl.refreshQueue(silent: true);

      expect(queueCtrl.isIntermission.value, isTrue,
          reason: 'Intermission must not be cancelled or interrupted by background polling');
      expect(queueCtrl.currentElapsedSeconds.value, equals(0),
          reason: 'currentElapsedSeconds must remain 0 during intermission');

      // Now simulate intermission expiring and moving to Round 2
      queueCtrl.isIntermission.value = false;
      queueCtrl.togglePlayPause(index: 0);

      expect(queueCtrl.isPlaying.value, isTrue);
      expect(queueCtrl.currentElapsedSeconds.value, equals(0),
          reason: 'Second round must start fresh at 0 seconds, preventing premature 1-second completion');
      expect(queueCtrl.currentTotalDuration.value, equals(15));
    });
  });
}
