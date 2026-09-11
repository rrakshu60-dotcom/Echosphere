import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/controllers/settings/settings.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/services/tts_audio_service.dart';
import 'package:anymex/widgets/notice_audio_player_bar.dart';

Widget createTestApp(Widget home) {
  return ChangeNotifierProvider(
    create: (_) => ThemeProvider(),
    child: GetMaterialApp(
      home: Scaffold(body: home),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});

    const globalChannel = MethodChannel('xyz.luan/audioplayers.global');
    const playerChannel = MethodChannel('xyz.luan/audioplayers');

    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(globalChannel, (MethodCall methodCall) async {
      return 1;
    });
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(playerChannel, (MethodCall methodCall) async {
      return 1;
    });

    Get.put(Settings());
    Get.put(AnnouncementController());
    Get.put(TtsAudioService());
  });

  tearDown(() {
    const globalChannel = MethodChannel('xyz.luan/audioplayers.global');
    const playerChannel = MethodChannel('xyz.luan/audioplayers');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(globalChannel, null);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(playerChannel, null);
    Get.reset();
  });

  group('TtsAudioService & Chime URLs', () {
    test('TtsAudioService configures chime parameters', () async {
      final audio = TtsAudioService.instance;

      expect(audio.includeChime.value, isTrue);
      expect(audio.selectedChime.value, equals('auto'));

      await audio.setVoiceConfig(chimeEnabled: false);
      expect(audio.includeChime.value, isFalse);

      await audio.setVoiceConfig(chimeEnabled: true, chimeType: 'urgent_academic');
      expect(audio.includeChime.value, isTrue);
      expect(audio.selectedChime.value, equals('urgent_academic'));
    });

    test('EchosphereApiService constructs proper audio stream URLs with chime parameters', () {
      final api = EchosphereApiService();

      final urlWithChime = api.getStreamUrlForAnnouncement(
        42,
        gender: 'male',
        accent: 'american',
        includeChime: true,
        chime: 'urgent_academic',
      );

      expect(urlWithChime, contains('/announcements/42/audio'));
      expect(urlWithChime, contains('include_chime=true'));
      expect(urlWithChime, contains('chime=urgent_academic'));

      final urlNoChime = api.getStreamUrlForAnnouncement(
        42,
        includeChime: false,
      );
      expect(urlNoChime, contains('include_chime=false'));

      final previewUrl = api.getChimePreviewUrl('events_sports');
      expect(previewUrl, contains('/announcements/chimes/events_sports/preview'));
    });
  });

  group('NoticeAudioPlayerBar UI & Zero Overflow', () {
    testWidgets('NoticeAudioPlayerBar renders chime chip and operates on 320px screen with zero overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 700);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestApp(
        const SingleChildScrollView(
          child: Padding(
            padding: EdgeInsets.all(12.0),
            child: NoticeAudioPlayerBar(
              announcementId: 501,
              title: 'Examination Schedule Release',
              hasAiSummary: true,
            ),
          ),
        ),
      ));
      await tester.pumpAndSettle();

      // Verify voice controls and chime chip render
      expect(find.text('♀ Female'), findsOneWidget);
      expect(find.text('♂ Male'), findsOneWidget);
      expect(find.text('🇮🇳 Indian'), findsOneWidget);
      expect(find.text('📄 Full Notice'), findsOneWidget);
      expect(find.text('✨ AI Summary'), findsOneWidget);
      expect(find.textContaining('🔔 Chime:'), findsOneWidget);

      // Verify zero layout overflow
      expect(tester.takeException(), isNull);
    });

    testWidgets('Tapping Chime chip opens Broadcast Intro Chimes bottom sheet with zero overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 700);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestApp(
        const SingleChildScrollView(
          child: Padding(
            padding: EdgeInsets.all(12.0),
            child: NoticeAudioPlayerBar(
              announcementId: 502,
              title: 'Annual Sports Fest 2026',
              hasAiSummary: false,
            ),
          ),
        ),
      ));
      await tester.pumpAndSettle();

      // Tap on the Chime chip
      final chimeChip = find.textContaining('🔔 Chime:');
      expect(chimeChip, findsOneWidget);
      await tester.tap(chimeChip);
      await tester.pumpAndSettle();

      // Verify bottom sheet opened
      expect(find.text('Broadcast Intro Chimes'), findsOneWidget);
      expect(find.text('⚡ AI Auto-Select'), findsOneWidget);
      expect(find.text('🔔 Professional Double-Beep'), findsOneWidget);
      expect(find.text('🎉 Upbeat Acoustic Ding'), findsOneWidget);
      expect(find.text('🚨 Sweeping Siren Pulse'), findsOneWidget);
      expect(find.text('🎵 Gentle Campus Chime'), findsOneWidget);

      // Verify zero layout overflow occurred in sheet
      expect(tester.takeException(), isNull);
    });
  });
}
