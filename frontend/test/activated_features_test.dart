import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/controllers/settings/settings.dart';
import 'package:anymex/screens/announcements/announcement_detail_page.dart';
import 'package:anymex/screens/announcements/archive_page.dart';
import 'package:anymex/screens/admin/announcement_management_page.dart';
import 'package:anymex/screens/admin/user_management_page.dart';

Widget createTestApp(Widget home) {
  return ChangeNotifierProvider(
    create: (_) => ThemeProvider(),
    child: GetMaterialApp(
      home: home,
    ),
  );
}

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.put(Settings());
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('AnnouncementDetailPage renders dynamic attachments & Archive button for Admin', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'Dr. Principal',
      role: 'Principal',
      department: 'AIML',
    );

    Get.put(AnnouncementController());

    final sampleNotice = AnnouncementModel(
      id: 101,
      title: 'End-Semester Exam Schedule 2026',
      description: 'Official schedule for end semester theory and practical exams.',
      priority: 'HIGH',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'Examination Section',
      department: 'College-Wide',
      category: 'Exams',
      createdAt: DateTime.now(),
      attachments: ['Exam_TimeTable_Final.pdf', 'Lab_Batches_AIML.xlsx'],
    );

    await tester.pumpWidget(createTestApp(AnnouncementDetailPage(announcement: sampleNotice)));
    await tester.pumpAndSettle();

    // Verify dynamic attachments rendered
    expect(find.text('Exam_TimeTable_Final.pdf'), findsOneWidget);
    expect(find.text('Lab_Batches_AIML.xlsx'), findsOneWidget);

    // Verify Archive action button is present for Principal
    expect(find.text('Archive'), findsOneWidget);

    // Scroll to and tap Archive button and verify dialog opens
    await tester.ensureVisible(find.text('Archive'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Archive'));
    await tester.pumpAndSettle();

    expect(find.text('Archive Announcement?'), findsOneWidget);
    expect(find.text('Archive Reason'), findsOneWidget);
  });

  testWidgets('ArchivePage renders dynamic attachments and operates cleanly', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    Get.put(AuthController());
    final annController = Get.put(AnnouncementController());

    annController.setAnnouncements([
      AnnouncementModel(
        id: 202,
        title: 'Archived Symposium Guidelines',
        description: 'Historical archive notice regarding the national technical symposium.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'ARCHIVED',
        creatorName: 'Dr. AIML HoD',
        department: 'AIML',
        category: 'Events',
        createdAt: DateTime.now().subtract(const Duration(days: 30)),
        attachments: ['Symposium_Guidelines.pdf'],
      ),
    ]);

    await tester.pumpWidget(createTestApp(const ArchivePage()));
    await tester.pumpAndSettle();

    expect(find.text('Notice Archive'), findsOneWidget);
    expect(find.text('Archived Symposium Guidelines'), findsOneWidget);
    expect(find.text('Symposium_Guidelines.pdf'), findsOneWidget);
  });

  testWidgets('UserManagementPage renders Notice Moderation button and operates on 320px screen', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'System Developer',
      role: 'Dev Admin',
    );

    await tester.pumpWidget(createTestApp(const UserManagementPage()));
    await tester.pumpAndSettle();

    // Verify title and moderation shortcut icon
    expect(find.text('User Accounts'), findsOneWidget);
    expect(find.byTooltip('Notice Moderation'), findsOneWidget);
    expect(find.byTooltip('Security Access Audit Logs'), findsOneWidget);

    // Verify zero overflow on 320px
    expect(tester.takeException(), isNull);
  });

  testWidgets('AnnouncementManagementPage operates with zero overflow on 320px compact mobile screen', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'System Developer',
      role: 'Dev Admin',
    );

    final annController = Get.put(AnnouncementController());
    annController.setAnnouncements([
      AnnouncementModel(
        id: 301,
        title: 'Emergency Lab Maintenance',
        description: 'Notice of unscheduled power down in network security laboratory.',
        priority: 'EMERGENCY',
        emergencyLevel: 'CRITICAL',
        status: 'PUBLISHED',
        creatorName: 'Network Admin',
        department: 'CSE',
        category: 'Maintenance',
        createdAt: DateTime.now(),
      ),
    ]);

    await tester.pumpWidget(createTestApp(const AnnouncementManagementPage()));
    await tester.pumpAndSettle();

    expect(find.text('Notice Management & Moderation'), findsOneWidget);
    expect(find.text('Emergency Lab Maintenance'), findsOneWidget);

    // Verify zero layout overflow error
    expect(tester.takeException(), isNull);

    // Now tap Modify button to open the Modify Announcement dialog
    await tester.ensureVisible(find.text('Modify'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Modify'));
    await tester.pumpAndSettle();

    // Verify Modify dialog opened
    expect(find.text('Modify Announcement'), findsOneWidget);
    expect(find.text('Title'), findsOneWidget);
    expect(find.text('Description / Content'), findsOneWidget);

    // Verify zero layout overflow error on 320px screen with dialog open
    expect(tester.takeException(), isNull);
  });

  testWidgets('AnnouncementDetailPage Modify dialog opens with zero overflow on 320px compact mobile screen', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 1,
      fullName: 'System Developer',
      role: 'Dev Admin',
    );

    Get.put(AnnouncementController());

    final sampleNotice = AnnouncementModel(
      id: 401,
      title: 'Lab Maintenance Notice',
      description: 'Scheduled maintenance of server racks and cooling units.',
      priority: 'HIGH',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'System Developer',
      department: 'CSE',
      category: 'Maintenance',
      createdAt: DateTime.now(),
    );

    await tester.pumpWidget(createTestApp(AnnouncementDetailPage(announcement: sampleNotice)));
    await tester.pumpAndSettle();

    // Verify zero layout overflow on 320px compact screen for AnnouncementDetailPage
    expect(tester.takeException(), isNull);

    // Scroll to and tap Modify button
    await tester.ensureVisible(find.text('Modify'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Modify'));
    await tester.pumpAndSettle();

    // Verify Modify dialog opened
    expect(find.text('Modify Announcement'), findsOneWidget);
    expect(find.text('Title'), findsOneWidget);
    expect(find.text('Description / Content'), findsOneWidget);

    // Verify zero layout overflow on 320px compact screen with dialog open
    expect(tester.takeException(), isNull);
  });
}
