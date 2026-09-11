import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:anymex/services/echosphere_api_service.dart';

class TtsAudioService extends GetxService {
  static TtsAudioService get instance {
    if (!Get.isRegistered<TtsAudioService>()) {
      return Get.put(TtsAudioService(), permanent: true);
    }
    return Get.find<TtsAudioService>();
  }

  final AudioPlayer _player = AudioPlayer();
  final EchosphereApiService _api = EchosphereApiService();

  final Rx<int?> currentAnnouncementId = Rx<int?>(null);
  final RxBool isPlaying = false.obs;
  final RxBool isBuffering = false.obs;
  final Rx<Duration> position = Duration.zero.obs;
  final Rx<Duration> duration = Duration.zero.obs;
  final RxString engine = 'AI Voice'.obs;
  final RxString voiceName = 'Indian Female'.obs;
  final RxString statusMessage = ''.obs;

  // Voice Customization Controls
  final RxString selectedGender = 'female'.obs; // 'female' | 'male'
  final RxString selectedAccent = 'indian'.obs; // 'indian' | 'american' | 'british'
  final RxString readMode = 'full'.obs; // 'full' | 'summary'
  final RxBool includeChime = true.obs; // Intro audio chime on/off
  final RxString selectedChime = 'auto'.obs; // 'auto' | 'urgent_academic' | 'events_sports' | 'emergency' | 'standard'
  final RxString activeChimeTag = 'standard'.obs;
  final RxString selectedLanguage = 'en'.obs; // 'en' | 'kn' | 'hi' | 'te' | 'ta'

  StreamSubscription? _stateSub;
  StreamSubscription? _posSub;
  StreamSubscription? _durSub;
  StreamSubscription? _completeSub;

  @override
  void onInit() {
    super.onInit();
    _initListeners();
  }

  void _initListeners() {
    _stateSub = _player.onPlayerStateChanged.listen((state) {
      isPlaying.value = (state == PlayerState.playing);
      if (state == PlayerState.playing) {
        isBuffering.value = false;
      }
    });

    _posSub = _player.onPositionChanged.listen((pos) {
      position.value = pos;
    });

    _durSub = _player.onDurationChanged.listen((dur) {
      duration.value = dur;
      isBuffering.value = false;
    });

    _completeSub = _player.onPlayerComplete.listen((_) {
      isPlaying.value = false;
      position.value = Duration.zero;
      isBuffering.value = false;
    });
  }

  bool isAnnouncementPlaying(int id) {
    return currentAnnouncementId.value == id && isPlaying.value;
  }

  bool isAnnouncementActive(int id) {
    return currentAnnouncementId.value == id;
  }

  Future<void> setVoiceConfig({
    String? gender,
    String? accent,
    String? mode,
    bool? chimeEnabled,
    String? chimeType,
  }) async {
    bool changed = false;
    if (gender != null && gender != selectedGender.value) {
      selectedGender.value = gender;
      changed = true;
    }
    if (accent != null && accent != selectedAccent.value) {
      selectedAccent.value = accent;
      changed = true;
    }
    if (mode != null && mode != readMode.value) {
      readMode.value = mode;
      changed = true;
    }
    if (chimeEnabled != null && chimeEnabled != includeChime.value) {
      includeChime.value = chimeEnabled;
      changed = true;
    }
    if (chimeType != null && chimeType != selectedChime.value) {
      selectedChime.value = chimeType;
      changed = true;
    }

    if (changed && currentAnnouncementId.value != null && isPlaying.value) {
      final activeId = currentAnnouncementId.value!;
      await stop();
      await playAnnouncement(activeId);
    }
  }

  Future<void> toggleChime(bool val) => setVoiceConfig(chimeEnabled: val);
  Future<void> setChimeType(String chime) => setVoiceConfig(chimeType: chime);

  Future<void> setLanguage(String lang) async {
    final clean = lang.trim().toLowerCase();
    if (selectedLanguage.value != clean) {
      selectedLanguage.value = clean;
      if (currentAnnouncementId.value != null && isPlaying.value) {
        final activeId = currentAnnouncementId.value!;
        await stop();
        await playAnnouncement(activeId);
      }
    }
  }

  Future<void> previewChime(String chimeType) async {
    try {
      await stop();
      final url = _api.getChimePreviewUrl(chimeType);
      await _player.play(UrlSource(url));
    } catch (e) {
      debugPrint('[TTS] Error previewing chime: $e');
    }
  }

  Future<void> playAnnouncement(int id, {String? directUrl}) async {
    try {
      // Toggle if already selected
      if (currentAnnouncementId.value == id && directUrl == null) {
        if (isPlaying.value) {
          await pause();
          return;
        } else {
          await resume();
          return;
        }
      }

      // Stop previous track
      await stop();
      currentAnnouncementId.value = id;
      isBuffering.value = true;
      position.value = Duration.zero;
      duration.value = Duration.zero;

      String? streamUrl = directUrl;

      final chimeParam = selectedChime.value == 'auto' ? null : selectedChime.value;
      final langParam = selectedLanguage.value;

      if (streamUrl == null || streamUrl.isEmpty) {
        final audioMeta = await _api.getAnnouncementAudio(
          id,
          gender: selectedGender.value,
          accent: selectedAccent.value,
          isSummary: (readMode.value == 'summary'),
          includeChime: includeChime.value,
          chime: chimeParam,
          lang: langParam,
        );
        if (audioMeta != null) {
          final rawUrl = audioMeta['audio_url']?.toString() ?? '';
          engine.value = 'AI Voice';
          voiceName.value = audioMeta['voice']?.toString() ?? '${selectedAccent.value.capitalize} ${selectedGender.value.capitalize}';
          activeChimeTag.value = audioMeta['chime']?.toString() ?? 'standard';
          if (rawUrl.startsWith('http')) {
            streamUrl = rawUrl;
          } else if (rawUrl.isNotEmpty) {
            streamUrl = '${_api.hostUrl}$rawUrl';
          }
        }
      }

      // Fallback to direct stream route if meta failed
      if (streamUrl == null || streamUrl.isEmpty) {
        streamUrl = _api.getStreamUrlForAnnouncement(
          id,
          gender: selectedGender.value,
          accent: selectedAccent.value,
          isSummary: (readMode.value == 'summary'),
          includeChime: includeChime.value,
          chime: chimeParam,
          lang: langParam,
        );
      }

      debugPrint('[TTS] Streaming audio from: $streamUrl');
      await _player.play(UrlSource(streamUrl));
    } catch (e) {
      debugPrint('[TTS Error] Failed to play announcement: $e');
      isBuffering.value = false;
      isPlaying.value = false;
      currentAnnouncementId.value = null;
    }
  }

  Future<void> playCustomText(String text) async {
    try {
      await stop();
      isBuffering.value = true;
      currentAnnouncementId.value = -1; // -1 denotes ad-hoc custom text

      final meta = await _api.synthesizeSpeech(
        text,
        gender: selectedGender.value,
        accent: selectedAccent.value,
      );
      if (meta != null) {
        final rawUrl = meta['audio_url']?.toString() ?? '';
        engine.value = 'AI Voice';
        final url = rawUrl.startsWith('http') ? rawUrl : '${_api.hostUrl}$rawUrl';
        await _player.play(UrlSource(url));
      } else {
        isBuffering.value = false;
        currentAnnouncementId.value = null;
      }
    } catch (e) {
      debugPrint('[TTS Error] Failed custom text synthesis: $e');
      isBuffering.value = false;
      isPlaying.value = false;
      currentAnnouncementId.value = null;
    }
  }

  Future<void> pause() async {
    try {
      await _player.pause();
    } catch (_) {}
  }

  Future<void> resume() async {
    try {
      await _player.resume();
    } catch (_) {}
  }

  Future<void> stop() async {
    try {
      await _player.stop();
      currentAnnouncementId.value = null;
      isPlaying.value = false;
      isBuffering.value = false;
      position.value = Duration.zero;
    } catch (_) {}
  }

  Future<void> seek(Duration pos) async {
    try {
      await _player.seek(pos);
    } catch (_) {}
  }

  @override
  void onClose() {
    _stateSub?.cancel();
    _posSub?.cancel();
    _durSub?.cancel();
    _completeSub?.cancel();
    _player.dispose();
    super.onClose();
  }
}
