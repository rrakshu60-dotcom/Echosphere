import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/settings/settings.dart';
import 'package:echosphere/controllers/theme.dart';
import 'package:echosphere/widgets/admin_workspace_bar.dart';

Future<void> _pump(WidgetTester tester, String role, {double width = 320}) async {
  tester.view.physicalSize = Size(width, 800);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  await tester.pumpWidget(ChangeNotifierProvider(
    create: (_) => ThemeProvider(),
    child: GetMaterialApp(
      getPages: [
        GetPage(name: '/', page: () => Scaffold(body: Padding(padding: const EdgeInsets.all(16), child: AdminWorkspaceBar(role: role)))),
        GetPage(name: '/audit-logs', page: () => const Scaffold(body: Text('AUDIT PAGE'))),
      ],
    ),
  ));
  await tester.pumpAndSettle();
}

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.put(Settings());
  });
  tearDown(Get.reset);

  for (final role in ['Dev Admin', 'College Admin']) {
    for (final width in [320.0, 900.0]) {
      testWidgets('$role sees Audit & Logs with no overflow at ${width.toInt()}px', (tester) async {
        await _pump(tester, role, width: width);
        expect(find.text('Audit & Logs'), findsOneWidget);
        for (final title in ['Notice Hub', 'User Hub', 'Smart Speakers']) {
          expect(find.text(title), findsOneWidget);
        }
        expect(tester.takeException(), isNull);
      });
    }
  }

  for (final role in ['Principal', 'HoD', 'Teacher']) {
    testWidgets('$role does not see Audit & Logs', (tester) async {
      await _pump(tester, role);
      expect(find.text('Audit & Logs'), findsNothing);
      expect(find.text('Notice Hub'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('the Audit & Logs tile opens the audit page', (tester) async {
    await _pump(tester, 'Dev Admin');
    await tester.tap(find.text('Audit & Logs'));
    await tester.pumpAndSettle();
    expect(find.text('AUDIT PAGE'), findsOneWidget);
  });
}
