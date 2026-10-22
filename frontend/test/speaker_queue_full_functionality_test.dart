import 'package:flutter/material.dart';
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
    Get.reset();
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
  });

  tearDown(() {
    if (Get.isRegistered<SpeakerQueueController>()) {
      Get.find<SpeakerQueueController>().cancelAllTimers();
    }
    Get.reset();
  });

  group('SpeakerQueuePage & Controller Full Functionality Suite', () {
    testWidgets('1. Access Control: Student sees restricted screen, Admin sees dashboard', (tester) async {
      final auth = Get.put(AuthController());

      // Student
      auth.currentUser.value = EchosphereUser(
        id: 99,
        fullName: 'Student Doe',
        role: 'Student',
        department: 'CSE',
      );

      await tester.pumpWidget(
        const GetMaterialApp(
          home: Scaffold(body: SpeakerQueuePage()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Access Restricted'), findsOneWidget);
      expect(find.text('Return to Dashboard'), findsOneWidget);

      // Admin
      auth.currentUser.value = EchosphereUser(
        id: 1,
        fullName: 'Dev Administrator',
        role: 'Dev Admin',
        department: 'CSE',
      );

      await tester.pumpWidget(
        const GetMaterialApp(
          home: Scaffold(body: SpeakerQueuePage()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Smart Speaker System'), findsOneWidget);
      expect(find.textContaining('Queue'), findsWidgets);
      expect(find.textContaining('Nodes'), findsWidgets);
    });

    testWidgets('2. Queue Tab: Displays active notice, playback controls, and removes notice upon completion', (tester) async {
      final auth = Get.put(AuthController());
      auth.currentUser.value = EchosphereUser(
        id: 1,
        fullName: 'Dev Admin',
        role: 'Dev Admin',
        department: 'CSE',
      );

      Get.put(AnnouncementController());
      final queueCtrl = Get.put(SpeakerQueueController());

      await tester.pumpWidget(
        const GetMaterialApp(
          home: Scaffold(body: SpeakerQueuePage()),
        ),
      );
      await tester.pump(const Duration(milliseconds: 500));

      // Backend: the notice is playing on the speaker.
      queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: [
        serverQueueItem(id: 3, announcementId: 301, title: 'Campus Emergency Drill Notice', status: 'Playing', durationSeconds: 20, speakerConfirmed: true, speakerElapsedSeconds: 2),
      ]);
      await tester.pump(const Duration(milliseconds: 500));
      expect(find.text('Campus Emergency Drill Notice'), findsWidgets);
      expect(queueCtrl.isPlaying.value, isTrue);
      expect(queueCtrl.queueItems.first['status'], 'Playing');

      // Backend: the user paused it, so the item is Held.
      queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: [
        serverQueueItem(id: 3, announcementId: 301, title: 'Campus Emergency Drill Notice', status: 'Held', durationSeconds: 20),
      ]);
      await tester.pump(const Duration(milliseconds: 500));
      expect(queueCtrl.isPlaying.value, isFalse);
      expect(queueCtrl.userPausedOrStopped.value, isTrue);
      expect(find.text('Campus Emergency Drill Notice'), findsWidgets);

      // Backend: playback completed, the queue is empty.
      queueCtrl.applyServerSnapshot(nodes: serverSpeakerNodes, queue: const []);
      await tester.pump(const Duration(milliseconds: 500));
      expect(queueCtrl.queueItems.isEmpty, isTrue);
      expect(find.text('Speaker Queue is Empty'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('3. Nodes Tab: Displays 2 canonical nodes, live telemetry, and control actions with zero overflow on 320px', (tester) async {
      tester.binding.window.physicalSizeTestValue = const Size(320, 720);
      tester.binding.window.devicePixelRatioTestValue = 1.0;
      addTearDown(() {
        tester.binding.window.clearPhysicalSizeTestValue();
        tester.binding.window.clearDevicePixelRatioTestValue();
      });

      final auth = Get.put(AuthController());
      auth.currentUser.value = EchosphereUser(
        id: 1,
        fullName: 'Dev Admin',
        role: 'Dev Admin',
        department: 'CSE',
      );

      final queueCtrl = Get.put(SpeakerQueueController());

      // Set live statuses: Wokwi OFFLINE, Hardware Client ONLINE
      queueCtrl.speakerNodes.assignAll([
        {
          'id': 14,
          'name': 'Wokwi ESP32 Speaker Node',
          'mac_address': '24:0A:C4:00:01:10',
          'ip_address': '10.0.1.15',
          'zone': 'Block A - CSE Quad',
          'department': 'CSE',
          'status': 'OFFLINE',
          'volume': 90,
          'cpu_usage': 0.0,
          'memory_usage': 0.0,
        },
        {
          'id': 15,
          'name': 'Hardware Speaker Client',
          'mac_address': 'D4:F3:2D:22:2A:CB',
          'ip_address': '192.168.88.10',
          'zone': 'Auditorium / Campus',
          'department': 'Auditorium',
          'status': 'ONLINE',
          'volume': 85,
          'cpu_usage': 18.2,
          'memory_usage': 41.5,
        },
      ]);

      await tester.pumpWidget(
        const GetMaterialApp(
          home: Scaffold(body: SpeakerQueuePage()),
        ),
      );
      await tester.pumpAndSettle();

      // Switch to Nodes Tab
      final nodesTab = find.textContaining('Nodes (2)');
      expect(nodesTab, findsOneWidget);
      await tester.tap(nodesTab);
      await tester.pumpAndSettle();

      // Verify canonical nodes rendered
      expect(find.text('Wokwi ESP32 Speaker Node'), findsOneWidget);
      expect(find.text('Hardware Speaker Client'), findsOneWidget);

      // Verify accurate status badges
      expect(find.text('OFFLINE'), findsOneWidget);
      expect(find.text('ONLINE'), findsOneWidget);

      // Test Diagnostic Test Tone click
      final testToneButtons = find.byTooltip('Test Tone');
      expect(testToneButtons, findsNWidgets(2));
      await tester.tap(testToneButtons.first);
      await tester.pumpAndSettle();

      // Test Restart Node click
      final restartButtons = find.byTooltip('Restart Node');
      expect(restartButtons, findsNWidgets(2));
      await tester.tap(restartButtons.first);
      await tester.pumpAndSettle();

      // Test Add Node dialog
      final addNodeBtn = find.text('Add Node');
      expect(addNodeBtn, findsOneWidget);
      await tester.tap(addNodeBtn);
      await tester.pumpAndSettle();

      expect(find.text('Register Hardware Speaker Node'), findsOneWidget);
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      // Ensure zero overflow
      expect(tester.takeException(), isNull);
    });

    testWidgets('4. Emergency Override dialog opens and submits emergency broadcast', (tester) async {
      final auth = Get.put(AuthController());
      auth.currentUser.value = EchosphereUser(
        id: 1,
        fullName: 'Dev Admin',
        role: 'Dev Admin',
        department: 'CSE',
      );

      Get.put(SpeakerQueueController());

      await tester.pumpWidget(
        const GetMaterialApp(
          home: Scaffold(body: SpeakerQueuePage()),
        ),
      );
      await tester.pumpAndSettle();

      // Tap EMERGENCY button in top bar
      final emergencyBtn = find.byTooltip('EMERGENCY');
      expect(emergencyBtn, findsOneWidget);
      await tester.tap(emergencyBtn);
      await tester.pumpAndSettle();

      expect(find.text('Emergency Speaker Override'), findsOneWidget);

      // Enter emergency text and trigger
      await tester.enterText(find.byType(TextField).last, 'Tornado warning in effect. Take cover.');
      final broadcastBtn = find.text('BROADCAST NOW');
      expect(broadcastBtn, findsOneWidget);
      await tester.tap(broadcastBtn);
      await tester.pumpAndSettle();

      expect(find.text('Emergency Speaker Override'), findsNothing);
    });
  });
}
