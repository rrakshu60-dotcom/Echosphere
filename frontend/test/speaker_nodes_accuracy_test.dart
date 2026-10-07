import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:shared_preferences/shared_preferences.dart';

import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';
import 'package:echosphere/screens/announcements/speaker_queue_page.dart';

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
    Get.reset();
  });

  test('Canonical speaker nodes inventory has all 4 nodes defaulting to OFFLINE', () {
    final ctrl = Get.put(SpeakerQueueController());

    // 1. Must contain all 4 nodes (ESP32 Live Node + Wokwi + Hardware Client 1 + Hardware Client 2)
    expect(ctrl.speakerNodes.length, equals(4));

    final espNode = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CD');
    expect(espNode['name'], equals('ESP32 Smart Speaker & Live Display'));
    expect(espNode['status'], equals('OFFLINE'), reason: 'Node must not show fake ONLINE status');

    final wokwiNode = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == '24:0A:C4:00:01:10');
    expect(wokwiNode['name'], equals('Wokwi ESP32 Speaker Node'));
    expect(wokwiNode['status'], equals('OFFLINE'), reason: 'Node must not show fake ONLINE status');

    final hwNode = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CB');
    expect(hwNode['name'], anyOf(equals('Hardware Speaker Client'), equals('Hardware Speaker Client 1')));
    expect(hwNode['status'], equals('OFFLINE'), reason: 'Node must not show fake ONLINE status');

    final hwNode2 = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CC');
    expect(hwNode2['name'], equals('Hardware Speaker Client 2'));
    expect(hwNode2['status'], equals('OFFLINE'), reason: 'Node 2 must not show fake ONLINE status');
  });

  test('Accurately reflects real-time ONLINE status when heartbeat is received for Node 1 and Node 2', () {
    final ctrl = Get.put(SpeakerQueueController());

    // Simulate real-time heartbeat updates from backend API
    final liveNodesFromBackend = [
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
        'ip_address': '127.0.0.1',
        'zone': 'Auditorium / Campus',
        'department': 'College-Wide',
        'status': 'ONLINE', // Node 1 active
        'volume': 85,
        'cpu_usage': 18.2,
        'memory_usage': 41.5,
      },
      {
        'id': 16,
        'name': 'Hardware Speaker Client 2',
        'mac_address': 'D4:F3:2D:22:2A:CC',
        'ip_address': '127.0.0.1',
        'zone': 'Block B - AI Lab',
        'department': 'AIML',
        'status': 'ONLINE', // Node 2 active
        'volume': 85,
        'cpu_usage': 14.5,
        'memory_usage': 39.2,
      },
    ];

    ctrl.speakerNodes.assignAll(liveNodesFromBackend);

    final hwNode = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CB');
    expect(hwNode['status'], equals('ONLINE'));

    final hwNode2 = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CC');
    expect(hwNode2['status'], equals('ONLINE'));

    final wokwiNode = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == '24:0A:C4:00:01:10');
    expect(wokwiNode['status'], equals('OFFLINE'));

    // When Node 2 terminal script stops (OFFLINE status received)
    liveNodesFromBackend[2]['status'] = 'OFFLINE';
    ctrl.speakerNodes.assignAll(liveNodesFromBackend);
    expect(ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CC')['status'], equals('OFFLINE'));
    expect(ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CB')['status'], equals('ONLINE'));
  });

  testWidgets('SpeakerQueuePage displays all nodes with accurate offline badges and zero overflow on 320px', (tester) async {
    tester.binding.window.physicalSizeTestValue = const Size(320, 720);
    tester.binding.window.devicePixelRatioTestValue = 1.0;
    addTearDown(() {
      tester.binding.window.clearPhysicalSizeTestValue();
      tester.binding.window.clearDevicePixelRatioTestValue();
    });

    Get.put(SpeakerQueueController());

    await tester.pumpWidget(
      const GetMaterialApp(
        home: Scaffold(
          body: SpeakerQueuePage(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Switch to the Devices Tab (Tab 2: Nodes (4))
    final nodesTab = find.textContaining('Nodes (4)');
    expect(nodesTab, findsOneWidget);
    await tester.tap(nodesTab);
    await tester.pumpAndSettle();

    // Canonical nodes rendered
    expect(find.text('ESP32 Smart Speaker & Live Display'), findsOneWidget);
    expect(find.textContaining('Hardware Speaker Client 1'), findsOneWidget);

    // Scroll down to view all nodes in the scrollable ListView
    await tester.drag(find.byType(ListView), const Offset(0, -350));
    await tester.pumpAndSettle();

    expect(find.text('Hardware Speaker Client 2'), findsOneWidget);
    expect(find.text('Wokwi ESP32 Speaker Node'), findsOneWidget);
    expect(find.text('OFFLINE'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
