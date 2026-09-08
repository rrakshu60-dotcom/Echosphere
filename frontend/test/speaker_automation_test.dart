import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/screens/announcements/create_announcement_dialog.dart';

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.reset();
    final authController = Get.put(AuthController());
    authController.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'System Administrator',
      officialEmail: 'admin@echosphere.edu',
      role: 'Dev Admin',
      department: 'AIML',
    );
    Get.put(AnnouncementController());
  });

  testWidgets('CreateAnnouncementDialog toggles speaker announcement and node selection',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () {
                showDialog(
                  context: context,
                  builder: (_) => const CreateAnnouncementDialog(),
                );
              },
              child: const Text('Open Dialog'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open Dialog'));
    await tester.pumpAndSettle();

    final earlyExc = tester.takeException();
    if (earlyExc != null) {
      debugPrint('EARLY EXCEPTION ON OPEN DIALOG: $earlyExc');
    }

    // Verify Speaker Announcement chip exists
    final speakerChip = find.text('Speaker Announcement');
    expect(speakerChip, findsOneWidget);

    // Scroll into view and toggle Speaker Announcement
    await tester.ensureVisible(speakerChip);
    await tester.pumpAndSettle();
    await tester.tap(speakerChip);
    await tester.pumpAndSettle();

    // Verify Target Speaker Node section appears
    expect(find.textContaining('Target Speaker Node'), findsOneWidget);
    expect(find.text('All Nodes (College-Wide)'), findsOneWidget);

    // Ensure zero overflow errors
    final exc = tester.takeException();
    if (exc != null && exc is FlutterError) {
      for (final diag in exc.diagnostics) {
        debugPrint('DIAG: ${diag.toString()}');
      }
    }
    expect(exc, isNull);
  });
}
