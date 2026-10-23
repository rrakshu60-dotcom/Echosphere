import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';
import 'package:echosphere/screens/announcements/speaker_queue_page.dart';
import 'package:echosphere/utils/campus_time.dart';
import 'support/server_queue.dart';

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

  testWidgets('repeat badges show the next round in Kolkata time, in theme colours, without overflow at 320px',
      (tester) async {
    tester.view.physicalSize = const Size(320, 720);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    Get.put(AuthController()).currentUser.value =
        EchosphereUser(id: 1, fullName: 'Dev Admin', role: 'Dev Admin', department: 'CSE');
    Get.put(AnnouncementController());
    final queueCtrl = Get.put(SpeakerQueueController());

    await tester.pumpWidget(const GetMaterialApp(home: Scaffold(body: SpeakerQueuePage())));
    await tester.pump(const Duration(milliseconds: 500));

    // As the server sends it: UTC without a zone
    final next = DateTime.now().toUtc().add(const Duration(minutes: 10));
    final serverText = next.toIso8601String().replaceAll('Z', '');
    final item = serverQueueItem(
      id: 7,
      announcementId: 701,
      title: 'Examination hall change for the second year students',
      status: 'Queued',
      hasRepeat: true,
      maxRepeats: 10,
      totalPlayedCount: 2,
    )
      ..['next_repeat_at'] = serverText
      ..['scheduled_time'] = serverText;
    queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: [item]);
    await tester.pump(const Duration(milliseconds: 500));

    final day = campusDayOffset(next) == 0 ? 'Today' : 'Tomorrow';
    final nextLabel = find.text('Next: $day, ${formatCampusTime(next, 'hh:mm a')}');
    expect(nextLabel, findsOneWidget);
    expect(find.text('Repeat Round 3 of 10'), findsOneWidget);

    final theme = Theme.of(tester.element(nextLabel));
    expect(tester.widget<Text>(nextLabel).style?.color, theme.colorScheme.primary);
    expect(tester.takeException(), isNull); // no RenderFlex overflow
  });
}
