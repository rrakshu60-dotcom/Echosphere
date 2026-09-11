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
  final RxString engine = 'Kokoro-82M'.obs;
  final RxString voiceName = 'American Female'.obs;
  final RxString statusMessage = ''.obs;

  // Voice Customization Controls
  final RxString selectedGender = 'female'.obs; // 'female' | 'male'
  final RxString selectedAccent = 'american'.obs; // 'american' | 'indian' | 'british'
  final RxString readMode = 'full'.obs; // 'full' | 'summary'
  final RxBool includeChime = true.obs; // Intro audio chime on/off
  final RxString selectedChime = 'auto'.obs; // 'auto' | 'urgent_academic' | 'events_sports' | 'emergency' | 'standard'
  final RxString activeChimeTag = 'standard'.obs;
  final RxString selectedLanguage = 'en'.obs; // 'en' | 'kn' | 'hi' | 'te' | 'ta'

  // Tracking what configuration is currently loaded into the player
  String? _lastPlayedGender;
  String? _lastPlayedAccent;
  String? _lastPlayedMode;

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
      _lastPlayedGender = null;
      _lastPlayedAccent = null;
      _lastPlayedMode = null;
    });
  }

  bool isAnnouncementPlaying(int id) {
    return currentAnnouncementId.value == id && isPlaying.value;
  }

  bool isAnnouncementActive(int id) {
    return currentAnnouncementId.value == id;
  }

  String? _activeTitle;
  String? _activeContent;
  String? _activeSummary;

  Future<void> setVoiceConfig({
    String? gender,
    String? accent,
    String? mode,
    bool? chimeEnabled,
    String? chimeType,
    String? summary,
    int? announcementId,
    String? title,
    String? content,
    bool startPlaying = false,
  }) async {
    bool voiceChanged = false;
    if (gender != null && gender != selectedGender.value) {
      selectedGender.value = gender;
      voiceChanged = true;
    }
    if (accent != null && accent != selectedAccent.value) {
      selectedAccent.value = accent;
      voiceChanged = true;
    }
    if (mode != null && mode != readMode.value) {
      readMode.value = mode;
      voiceChanged = true;
    }
    if (chimeEnabled != null && chimeEnabled != includeChime.value) {
      includeChime.value = chimeEnabled;
    }
    if (chimeType != null && chimeType != selectedChime.value) {
      selectedChime.value = chimeType;
    }
    if (title != null && title.isNotEmpty) _activeTitle = title;
    if (content != null && content.isNotEmpty) _activeContent = content;
    if (summary != null && summary.isNotEmpty) _activeSummary = summary;

    voiceName.value = '${selectedAccent.value.capitalize} ${selectedGender.value.capitalize}';

    final targetId = announcementId ?? currentAnnouncementId.value;

    if (targetId != null) {
      // If voice configuration changed while playing, switch voice immediately
      if ((voiceChanged && (isPlaying.value || _player.state == PlayerState.playing)) || startPlaying) {
        await stop();
        await playAnnouncement(
          targetId,
          title: _activeTitle,
          content: _activeContent,
          summary: _activeSummary,
        );
      } else if (voiceChanged) {
        // Pre-warm the newly chosen voice in background so tapping Play has 0s latency
        prewarmAnnouncement(
          targetId,
          title: _activeTitle,
          content: _activeContent,
          summary: _activeSummary,
        );
      }
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

  // In-Memory Audio URL Cache for instant 0-latency playback
  final Map<String, String> _urlCache = {};

  bool _isContaminatedVoice(String url, String expectedGender) {
    final lower = url.toLowerCase();
    if (expectedGender == 'male' &&
        (lower.contains('female') ||
            lower.contains('jenny') ||
            lower.contains('neerja') ||
            lower.contains('sonia'))) {
      return true;
    }
    if (expectedGender == 'female' &&
        (lower.contains('_male') ||
            lower.contains('guyneural') ||
            lower.contains('prabhat') ||
            lower.contains('ryan'))) {
      return true;
    }
    return false;
  }

  /// Pre-warms synthesized speech in the background on page load
  /// so tapping "Listen to Notice" starts playback instantly with ZERO latency.
  Future<void> prewarmAnnouncement(
    int id, {
    String? title,
    String? content,
    String? summary,
  }) async {
    try {
      if (title != null) _activeTitle = title;
      if (content != null) _activeContent = content;
      if (summary != null && summary.isNotEmpty) _activeSummary = summary;

      // 1. Prewarm notice audio for currently selected gender
      await _prewarmGenderVoice(id, selectedGender.value,
          title: _activeTitle, content: _activeContent, summary: _activeSummary);

      // 2. Also prewarm opposite gender in background for instantaneous switching
      final altGender = selectedGender.value == 'female' ? 'male' : 'female';
      _prewarmGenderVoice(id, altGender,
          title: _activeTitle, content: _activeContent, summary: _activeSummary);
    } catch (e) {
      debugPrint('[TTS Pre-warm note] $e');
    }
  }

  Future<void> _prewarmGenderVoice(
    int id,
    String gender, {
    String? title,
    String? content,
    String? summary,
  }) async {
    try {
      // 1. Prewarm full notice audio under ..._full
      final fullKey = '${id}_${selectedAccent.value}_${gender}_full';
      final fullText = (content != null && content.isNotEmpty)
          ? (title != null ? '$title. $content' : content)
          : (title ?? '');
      if (!_urlCache.containsKey(fullKey) && fullText.isNotEmpty) {
        final meta = await _api.synthesizeSpeech(
          fullText,
          gender: gender,
          accent: selectedAccent.value,
        );
        if (meta != null && meta['audio_url'] != null) {
          final rawUrl = meta['audio_url'].toString();
          final url = rawUrl.startsWith('http') ? rawUrl : '${_api.hostUrl}$rawUrl';
          if (!_isContaminatedVoice(url, gender)) {
            _urlCache[fullKey] = url;
            debugPrint('[TTS Pre-warm Full ($gender)] Ready for notice #$id (0s latency): $url');
          }
        }
      }

      // 2. Prewarm summary audio under ..._summary (Generating with Qwen if needed)
      final sumKey = '${id}_${selectedAccent.value}_${gender}_summary';
      if (!_urlCache.containsKey(sumKey)) {
        String? sumText = summary;
        if ((sumText == null || sumText.isEmpty) && content != null && content.isNotEmpty) {
          try {
            sumText = await _api.summarizeContent(content);
            _activeSummary = sumText;
          } catch (_) {}
        }
        if (sumText != null && sumText.isNotEmpty) {
          final meta = await _api.synthesizeSpeech(
            sumText,
            gender: gender,
            accent: selectedAccent.value,
          );
          if (meta != null && meta['audio_url'] != null) {
            final rawUrl = meta['audio_url'].toString();
            final url = rawUrl.startsWith('http') ? rawUrl : '${_api.hostUrl}$rawUrl';
            if (!_isContaminatedVoice(url, gender)) {
              _urlCache[sumKey] = url;
              debugPrint('[TTS Pre-warm Summary ($gender)] Ready for notice #$id: $url');
            }
          }
        }
      }
    } catch (e) {
      debugPrint('[TTS Pre-warm Voice ($gender) note] $e');
    }
  }

  Future<void> playAnnouncement(
    int id, {
    String? title,
    String? content,
    String? summary,
    String? directUrl,
    String? forceMode,
  }) async {
    try {
      _activeTitle = title ?? _activeTitle;
      _activeContent = content ?? _activeContent;
      if (summary != null && summary.isNotEmpty) {
        _activeSummary = summary;
      }
      final targetMode = forceMode ?? readMode.value;
      if (forceMode != null) {
        readMode.value = forceMode;
      }

      final sameNotice = currentAnnouncementId.value == id;
      final sameVoice = _lastPlayedGender == selectedGender.value &&
                        _lastPlayedAccent == selectedAccent.value &&
                        _lastPlayedMode == targetMode;

      // Toggle Pause/Resume only if playing the exact same announcement with the EXACT same voice configuration
      if (sameNotice && sameVoice && directUrl == null && forceMode == null) {
        if (isPlaying.value) {
          await pause();
          return;
        } else {
          await resume();
          return;
        }
      }

      // Stop previous track before switching voice / announcement
      await stop();
      currentAnnouncementId.value = id;
      isBuffering.value = true;
      position.value = Duration.zero;
      duration.value = Duration.zero;
      voiceName.value = '${selectedAccent.value.capitalize} ${selectedGender.value.capitalize}';

      // When summary mode is active, make sure we have the Qwen summary
      if (readMode.value == 'summary' && (_activeSummary == null || _activeSummary!.trim().isEmpty)) {
        statusMessage.value = 'Generating AI Summary...';
        try {
          if (_activeContent != null && _activeContent!.trim().isNotEmpty) {
            debugPrint('[TTS] Generating AI summary using Qwen model before synthesis...');
            _activeSummary = await _api.summarizeContent(_activeContent!);
          } else if (id > 0) {
            _activeSummary = await _api.summarizeAnnouncement(id);
          }
        } catch (e) {
          debugPrint('[TTS] Failed to generate AI summary with Qwen: $e');
        }
      }

      String? streamUrl = directUrl;
      // Discard directUrl if it is contaminated with the wrong gender
      if (streamUrl != null && _isContaminatedVoice(streamUrl, selectedGender.value)) {
        streamUrl = null;
      }

      final cacheKey = '${id}_${selectedAccent.value}_${selectedGender.value}_${readMode.value}';

      // 1. FASTEST: Instant Memory Cache (0 ms latency)
      if (streamUrl == null && _urlCache.containsKey(cacheKey)) {
        final cached = _urlCache[cacheKey];
        if (cached != null && !_isContaminatedVoice(cached, selectedGender.value)) {
          streamUrl = cached;
          debugPrint('[TTS] Instant memory cache hit for notice #$id ($cacheKey): $streamUrl');
        } else {
          _urlCache.remove(cacheKey);
        }
      }

      // 2. High-speed direct synthesis via Kokoro / Edge-TTS
      if (streamUrl == null || streamUrl.isEmpty) {
        String textToSpeak = '';
        if (readMode.value == 'summary') {
          // Strictly speak the Qwen AI Summary — NEVER the full body text!
          if (_activeSummary != null && _activeSummary!.trim().isNotEmpty) {
            textToSpeak = _activeSummary!.trim();
          } else if (_activeTitle != null && _activeTitle!.isNotEmpty) {
            textToSpeak = 'Summary of ${_activeTitle!}.';
          }
        } else {
          textToSpeak = (_activeContent != null && _activeContent!.isNotEmpty)
              ? (_activeTitle != null ? '$_activeTitle. $_activeContent' : _activeContent!)
              : (_activeTitle ?? '');
        }

        if (textToSpeak.isNotEmpty) {
          debugPrint('[TTS] Synthesis path for notice #$id (${readMode.value} mode, ${selectedGender.value})...');
          final meta = await _api.synthesizeSpeech(
            textToSpeak,
            gender: selectedGender.value,
            accent: selectedAccent.value,
          );
          if (meta != null && meta['audio_url'] != null) {
            final rawUrl = meta['audio_url'].toString();
            final fullUrl = rawUrl.startsWith('http') ? rawUrl : '${_api.hostUrl}$rawUrl';
            if (!_isContaminatedVoice(fullUrl, selectedGender.value)) {
              streamUrl = fullUrl;
              engine.value = meta['engine']?.toString() ?? 'Kokoro-82M';
              voiceName.value = '${selectedAccent.value.capitalize} ${selectedGender.value.capitalize}';
              _urlCache[cacheKey] = streamUrl;
            }
          }
        }
      }

      // 3. Fallback to stream route if text was not provided
      if (streamUrl == null || streamUrl.isEmpty) {
        final audioMeta = await _api.getAnnouncementAudio(
          id,
          gender: selectedGender.value,
          accent: selectedAccent.value,
          isSummary: (readMode.value == 'summary'),
          includeChime: includeChime.value,
          chime: selectedChime.value == 'auto' ? null : selectedChime.value,
          lang: selectedLanguage.value,
        );
        if (audioMeta != null) {
          final rawUrl = audioMeta['audio_url']?.toString() ?? '';
          final fileName = audioMeta['file_name']?.toString() ?? '';
          final fullUrl = rawUrl.startsWith('http') ? rawUrl : '${_api.hostUrl}$rawUrl';
          final isLegacyBeep = fileName.endsWith('.wav') &&
              (fileName.contains('indian') || !fileName.contains(selectedAccent.value));

          if (!isLegacyBeep && fullUrl.isNotEmpty && !_isContaminatedVoice(fullUrl, selectedGender.value)) {
            streamUrl = fullUrl;
            engine.value = audioMeta['engine']?.toString() ?? 'Kokoro-82M';
            voiceName.value = '${selectedAccent.value.capitalize} ${selectedGender.value.capitalize}';
            _urlCache[cacheKey] = streamUrl;
          }
        }
      }

      if (streamUrl == null || streamUrl.isEmpty) {
        streamUrl = _api.getStreamUrlForAnnouncement(
          id,
          gender: selectedGender.value,
          accent: selectedAccent.value,
          isSummary: (readMode.value == 'summary'),
          includeChime: includeChime.value,
          chime: selectedChime.value == 'auto' ? null : selectedChime.value,
          lang: selectedLanguage.value,
        );
      }

      if (streamUrl.isNotEmpty) {
        debugPrint('[TTS] Streaming audio ($voiceName): $streamUrl');
        _lastPlayedGender = selectedGender.value;
        _lastPlayedAccent = selectedAccent.value;
        _lastPlayedMode = readMode.value;
        await _player.play(UrlSource(streamUrl));
      }
    } catch (e) {
      debugPrint('[TTS Error] Failed to play announcement: $e');
      isBuffering.value = false;
      isPlaying.value = false;
      currentAnnouncementId.value = null;
      _lastPlayedGender = null;
      _lastPlayedAccent = null;
      _lastPlayedMode = null;
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
      _lastPlayedGender = null;
      _lastPlayedAccent = null;
      _lastPlayedMode = null;
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
