import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/theme.dart';
import 'package:echosphere/controllers/settings/settings.dart';
import 'package:echosphere/screens/home/home_dashboard_widgets.dart';
import 'package:echosphere/services/tts_audio_service.dart';
import 'package:echosphere/widgets/home_mini_tts_player_bar.dart';

Widget createTestApp(Widget child) {
  return ChangeNotifierProvider(
    create: (_) => ThemeProvider(),
    child: GetMaterialApp(
      theme: ThemeData.light(),
      darkTheme: ThemeData.dark(),
      home: Scaffold(body: child),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.reset();
    Get.put(Settings());
    Get.put(AnnouncementController());
  });

  tearDown(() async {
    if (Get.isRegistered<TtsAudioService>()) {
      await TtsAudioService.instance.stop();
    }
  });

  testWidgets('AnnouncementFeedCard Listen button toggles to Stop when playing and tapping Stop halts playback', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final audio = TtsAudioService.instance;

    final notice = AnnouncementModel(
      id: 301,
      title: 'Department Seminar on AI Robotics',
      description: 'The department is conducting a high-level seminar on AI Robotics in auditorium 2.',
      priority: 'NORMAL',
      emergencyLevel: 'NORMAL',
      status: 'PUBLISHED',
      creatorName: 'Prof. Sharma',
      department: 'AIML',
      category: 'Seminars',
      createdAt: DateTime.now(),
      aiSummary: 'Department seminar on AI Robotics in auditorium 2.',
    );

    await tester.pumpWidget(createTestApp(
      SingleChildScrollView(
        child: AnnouncementFeedCard(
          notice: notice,
          index: 0,
        ),
      ),
    ));
    await tester.pumpAndSettle();

    // 1. Initially, Listen button is present
    expect(find.text('Listen'), findsOneWidget);
    expect(find.text('Stop'), findsNothing);

    // 2. Simulate audio service playing this announcement
    audio.currentAnnouncementId.value = 301;
    audio.isPlaying.value = true;
    await tester.pumpAndSettle();

    // 3. Now the button on the card should display "Stop"
    expect(find.text('Stop'), findsOneWidget);
    expect(find.text('Listen'), findsNothing);
    expect(tester.takeException(), isNull);

    // 4. Tap "Stop" on the card
    await tester.tap(find.text('Stop'));
    await tester.pumpAndSettle();

    // 5. Playback should be stopped immediately
    expect(audio.isPlaying.value, isFalse);
    expect(audio.currentAnnouncementId.value, isNull);
    expect(find.text('Listen'), findsOneWidget);
    expect(find.text('Stop'), findsNothing);
  });

  testWidgets('HomeMiniTtsPlayerBar appears when audio active and allows stopping audio from home screen', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 800); // 320px compact screen for Zero Overflow constraint
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final audio = TtsAudioService.instance;

    await tester.pumpWidget(createTestApp(
      const Column(
        children: [
          Expanded(child: Center(child: Text('Home Content'))),
          HomeMiniTtsPlayerBar(),
        ],
      ),
    ));
    await tester.pumpAndSettle();

    // 1. When inactive, mini player should be collapsed (SizedBox.shrink)
    expect(find.byType(HomeMiniTtsPlayerBar), findsOneWidget);
    expect(find.text('AI Summary'), findsNothing);
    expect(find.text('Notice Audio'), findsNothing);

    // 2. Activate audio playback
    audio.currentAnnouncementId.value = 405;
    audio.activeAnnouncementTitle.value = 'Annual Sports Day Postponed to Monday';
    audio.readMode.value = 'full';
    audio.isPlaying.value = true;
    await tester.pumpAndSettle();

    // 3. Now mini player should be visible with title and controls
    expect(find.text('Annual Sports Day Postponed to Monday'), findsOneWidget);
    expect(find.text('Notice Audio'), findsOneWidget);
    expect(find.byIcon(Icons.pause_circle_filled_rounded), findsOneWidget);
    expect(find.byIcon(Icons.stop_circle_outlined), findsOneWidget);
    expect(tester.takeException(), isNull); // Zero overflow on 320px

    // 4. Tap stop button on the mini player
    await tester.tap(find.byIcon(Icons.stop_circle_outlined));
    await tester.pumpAndSettle();

    // 5. Audio stopped and mini player dismissed
    expect(audio.isPlaying.value, isFalse);
    expect(audio.currentAnnouncementId.value, isNull);
    expect(find.text('Annual Sports Day Postponed to Monday'), findsNothing);
  });
}
