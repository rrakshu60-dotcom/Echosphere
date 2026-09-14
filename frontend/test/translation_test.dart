import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/settings/settings.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/theme.dart';
import 'package:echosphere/controllers/echosphere_ai_controller.dart';
import 'package:echosphere/screens/home/home_dashboard_widgets.dart';

Widget createTestApp(Widget home) {
  return ChangeNotifierProvider(
    create: (_) => ThemeProvider(),
    child: GetMaterialApp(
      home: Scaffold(body: home),
    ),
  );
}

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.reset();
    Get.put(Settings());
    final authController = Get.put(AuthController());
    authController.currentUser.value = EchosphereUser(
      id: 101,
      fullName: 'Rahul Sharma',
      officialEmail: 'rahul.ci23@echosphere.edu',
      role: 'Student',
      department: 'AIML',
      semester: 5,
      usn: '1DB23CI079',
    );
    Get.put(AnnouncementController());
    Get.put(EchosphereAiController());
  });

  tearDown(() {
    Get.reset();
  });

  group('AnnouncementFeedCard Zero Overflow on 320px & Translation Removal', () {
    testWidgets('renders AnnouncementFeedCard without overflow on 320px screen', (tester) async {
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final notice = AnnouncementModel(
        id: 20,
        title: 'Workshop on Artificial Intelligence',
        description: 'Hands-on training session for engineering students in Room 302.',
        category: 'Workshop',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        department: 'AIML',
        targetAudience: 'All Students',
        status: 'PUBLISHED',
        creatorName: 'Faculty Incharge',
        creatorRole: 'Teacher',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(
        createTestApp(
          SingleChildScrollView(
            child: AnnouncementFeedCard(notice: notice, index: 0),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify title and description are rendered
      expect(find.text('Workshop on Artificial Intelligence'), findsOneWidget);
      expect(find.text('Read Details \u2192'), findsOneWidget);
      expect(find.text('Add to Calendar'), findsOneWidget);

      // Verify Translate chip is completely removed per user instruction
      expect(find.text('Translate'), findsNothing);
      expect(find.text('Translate:'), findsNothing);

      // Verify card was rendered and zero overflow occurred
      expect(tester.takeException(), isNull);
    });
  });
}
