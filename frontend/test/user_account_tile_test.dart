import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/settings/settings.dart';
import 'package:echosphere/controllers/theme.dart';
import 'package:echosphere/screens/admin/user_management_page.dart';

const _longName = 'Administrator Account Holder';

Map<String, dynamic> _user({String role = 'Dev Admin', bool active = true}) => {
      'id': 7,
      'full_name': _longName,
      'role': role,
      'official_email': 'admin@echosphere.edu',
      'department': 'CSE',
      'is_active': active,
    };

Future<void> _pumpTile(WidgetTester tester, double width, Widget tile) async {
  tester.view.physicalSize = Size(width, 800);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  await tester.pumpWidget(ChangeNotifierProvider(
    create: (_) => ThemeProvider(),
    child: GetMaterialApp(
      home: Scaffold(body: Padding(padding: const EdgeInsets.all(12), child: tile)),
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

  for (final width in [320.0, 800.0]) {
    testWidgets('UserAccountTile gives the name room and shows the role at ${width.toInt()}px', (tester) async {
      await _pumpTile(
        tester,
        width,
        UserAccountTile(user: _user(), canManage: true, onRoleTap: () {}, onActiveChanged: (_) {}, onDelete: () {}),
      );
      expect(tester.takeException(), isNull);

      final tileWidth = tester.getSize(find.byType(UserAccountTile)).width;
      final nameWidth = tester.getSize(find.text(_longName)).width;
      // The name must not be squeezed by the role chip: at 320px it used to get ~60px ("Admin ...").
      expect(nameWidth, greaterThanOrEqualTo(tileWidth * 0.45));
      final roleWidth = tester.getSize(find.text('Dev Admin')).width;
      expect(roleWidth, greaterThan(40), reason: 'role label must stay readable, not shrink to its icon');
    });
  }

  testWidgets('UserAccountTile wires role, active switch and delete for managers', (tester) async {
    var roleTaps = 0, deletes = 0;
    bool? activeValue;
    await _pumpTile(
      tester,
      320,
      UserAccountTile(
        user: _user(),
        canManage: true,
        onRoleTap: () => roleTaps++,
        onActiveChanged: (v) => activeValue = v,
        onDelete: () => deletes++,
      ),
    );

    await tester.tap(find.text('Dev Admin'));
    await tester.tap(find.byType(Switch));
    await tester.tap(find.byTooltip('Delete User Account'));
    await tester.pump();

    expect(roleTaps, 1);
    expect(activeValue, isFalse);
    expect(deletes, 1);
  });

  testWidgets('UserAccountTile shows a read-only status badge for non-managers', (tester) async {
    await _pumpTile(tester, 320, UserAccountTile(user: _user(active: false), canManage: false));
    expect(tester.takeException(), isNull);
    expect(find.byType(Switch), findsNothing);
    expect(find.byTooltip('Delete User Account'), findsNothing);
    expect(find.text('Inactive'), findsOneWidget);
  });
}
