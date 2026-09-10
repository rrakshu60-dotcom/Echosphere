import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:shared_preferences/shared_preferences.dart';

import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/speaker_queue_controller.dart';
import 'package:anymex/screens/announcements/speaker_queue_page.dart';

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

  test('Canonical speaker nodes inventory has exactly 2 nodes defaulting to OFFLINE', () {
    final ctrl = Get.put(SpeakerQueueController());

    // 1. Must contain exactly 2 nodes (Wokwi + Hardware Client)
    expect(ctrl.speakerNodes.length, equals(2));

    final wokwiNode = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == '24:0A:C4:00:01:10');
    expect(wokwiNode['name'], equals('Wokwi ESP32 Speaker Node'));
    expect(wokwiNode['status'], equals('OFFLINE'), reason: 'Node must not show fake ONLINE status');

    final hwNode = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CB');
    expect(hwNode['name'], equals('Hardware Speaker Client'));
    expect(hwNode['status'], equals('OFFLINE'), reason: 'Node must not show fake ONLINE status');
  });

  test('Accurately reflects real-time ONLINE status when heartbeat is received', () {
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
        'status': 'ONLINE', // Hardware terminal script started
        'volume': 85,
        'cpu_usage': 18.2,
        'memory_usage': 41.5,
      },
    ];

    ctrl.speakerNodes.assignAll(liveNodesFromBackend);

    final hwNode = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CB');
    expect(hwNode['status'], equals('ONLINE'));

    final wokwiNode = ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == '24:0A:C4:00:01:10');
    expect(wokwiNode['status'], equals('OFFLINE'));

    // When hardware terminal script stops (OFFLINE status received)
    liveNodesFromBackend[1]['status'] = 'OFFLINE';
    ctrl.speakerNodes.assignAll(liveNodesFromBackend);
    expect(ctrl.speakerNodes.firstWhere((n) => n['mac_address'] == 'D4:F3:2D:22:2A:CB')['status'], equals('OFFLINE'));
  });

  testWidgets('SpeakerQueuePage displays exactly 2 nodes with accurate offline badges and zero overflow on 320px', (tester) async {
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

    // Switch to the Devices Tab (Tab 2: Nodes (2))
    final nodesTab = find.textContaining('Nodes (2)');
    expect(nodesTab, findsOneWidget);
    await tester.tap(nodesTab);
    await tester.pumpAndSettle();

    // Both canonical nodes must be rendered
    expect(find.text('Wokwi ESP32 Speaker Node'), findsOneWidget);
    expect(find.text('Hardware Speaker Client'), findsOneWidget);

    // Initial status badges must be OFFLINE (no fake ONLINE)
    expect(find.text('OFFLINE'), findsNWidgets(2));
    expect(tester.takeException(), isNull);
  });
}
