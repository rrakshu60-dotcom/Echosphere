import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';
import 'package:echosphere/screens/announcements/speaker_queue_page.dart';
import 'support/server_queue.dart';

/// Owner decision 2026-10-23: the queue moves by itself, so manual next / previous / advance controls are gone,
/// and the live microphone (no speaker ever played it) was removed.
void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
  });

  tearDown(() {
    if (Get.isRegistered<SpeakerQueueController>()) {
      Get.find<SpeakerQueueController>().cancelAllTimers();
    }
    Get.reset();
  });

  testWidgets('the speaker queue has no manual next/previous/advance controls and no live microphone', (tester) async {
    tester.view.physicalSize = const Size(400, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    Get.put(AuthController()).currentUser.value =
        EchosphereUser(id: 1, fullName: 'Dev Admin', role: 'Dev Admin', department: 'CSE');
    Get.put(AnnouncementController());
    final queueCtrl = Get.put(SpeakerQueueController());

    await tester.pumpWidget(const GetMaterialApp(home: Scaffold(body: SpeakerQueuePage())));
    await tester.pump(const Duration(milliseconds: 500));
    queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: [
      serverQueueItem(id: 1, announcementId: 101, title: 'First notice', status: 'Playing', speakerConfirmed: true, hasRepeat: true, maxRepeats: 5, totalPlayedCount: 1),
      serverQueueItem(id: 2, announcementId: 102, title: 'Second notice', queuePosition: 2),
    ]);
    await tester.pump(const Duration(milliseconds: 500));

    for (final tip in ['Previous', 'Skip to Next', 'Advance Hardware Queue', 'Trigger Next Repeat Round Now']) {
      expect(find.byTooltip(tip), findsNothing, reason: '"$tip" must be gone');
    }
    expect(find.text('LIVE MIC PA'), findsNothing);
    expect(find.text('EMERGENCY'), findsOneWidget); // the emergency button stays
    expect(tester.takeException(), isNull);
  });
}
