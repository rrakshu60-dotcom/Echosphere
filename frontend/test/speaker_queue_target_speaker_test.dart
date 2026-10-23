import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';
import 'package:echosphere/screens/announcements/speaker_queue_page.dart';
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

  testWidgets('each queued notice shows its full target speaker name and the server-reported status at 320px',
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

    // Speaker 2 is missing from the app's node list; the queue item itself says where it goes.
    final item = serverQueueItem(id: 8, announcementId: 801, title: 'Library timing change')
      ..['speaker_node_id'] = 23
      ..['speaker_node_mac'] = '20:50:0D:4F:FA:E8'
      ..['speaker_node_name'] = 'ESP32 Speaker 2'
      ..['speaker_node_status'] = 'ONLINE';
    queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: [item]);
    await tester.pump(const Duration(milliseconds: 500));

    final chip = find.text('ESP32 Speaker 2 \u2022 ONLINE');
    expect(chip, findsOneWidget);
    expect(tester.renderObject<RenderParagraph>(chip).didExceedMaxLines, isFalse);
    expect(tester.takeException(), isNull);
  });
}
