import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/services/echosphere_realtime_service.dart';
import 'package:echosphere/services/tts_audio_service.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';

class SpeakerQueueController extends GetxController {
  final EchosphereApiService _apiService = EchosphereApiService();

  final RxList<Map<String, dynamic>> queueItems = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> speakerNodes = <Map<String, dynamic>>[].obs;

  final RxBool isPlaying = false.obs;
  final RxInt activeIndex = 0.obs;
  final RxInt currentElapsedSeconds = 0.obs;
  final RxInt currentTotalDuration = 15.obs;

  final RxBool isLoading = false.obs;
  final RxString errorMessage = ''.obs;

  static const int broadcastGapSeconds = 15;
  final RxBool isIntermission = false.obs;
  final RxInt intermissionSecondsRemaining = 0.obs;

  /// Controls whether this device plays audio aloud for the queue (default: false to prioritize physical hardware speaker)
  final RxBool enableLocalAudioPreview = false.obs;

  /// Tracks user explicit pause or stop so background pollers never force-play
  final RxBool userPausedOrStopped = false.obs;

  /// True only once the physical speaker has started pulling the notice audio
  /// (reported by the backend). The progress bar moves only while this is true.
  final RxBool speakerConfirmed = false.obs;

  /// Server-reported elapsed playback seconds and the local moment it was received.
  /// Elapsed time is re-derived from these, so device clock differences never matter.
  double _serverElapsedAtSync = 0;
  DateTime? _serverElapsedSyncedAt;

  void _syncServerElapsed(double? elapsedSeconds) {
    if (elapsedSeconds == null) {
      _serverElapsedSyncedAt = null;
      _serverElapsedAtSync = 0;
      currentElapsedSeconds.value = 0;
      return;
    }
    _serverElapsedAtSync = elapsedSeconds;
    _serverElapsedSyncedAt = DateTime.now();
    currentElapsedSeconds.value = elapsedSeconds.floor().clamp(0, currentTotalDuration.value);
  }

  /// Set of announcement IDs explicitly dismissed or removed by the user in this session
  final Set<int> dismissedAnnouncementIds = <int>{};

  /// Set of announcement IDs that have finished single broadcast and should never repeat
  final Set<int> completedSinglePlayAnnouncementIds = <int>{};

  Future<void> _loadPersistedCompletedIds() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final list = prefs.getStringList('echosphere_completed_speaker_queue_ids') ?? [];
      completedSinglePlayAnnouncementIds.addAll(list.map((e) => int.tryParse(e)).whereType<int>());
    } catch (_) {}
  }

  Future<void> _savePersistedCompletedIds() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList(
        'echosphere_completed_speaker_queue_ids',
        completedSinglePlayAnnouncementIds.map((e) => e.toString()).toList(),
      );
    } catch (_) {}
  }

  /// Replaces a temporary local announcement ID with the real backend-assigned ID in-place
  void replaceTemporaryId(int oldId, int newId) {
    bool changed = false;
    for (var item in queueItems) {
      if (item['id'] == oldId || item['announcement_id'] == oldId) {
        item['id'] = newId;
        item['announcement_id'] = newId;
        item['audio_url'] = '/static/audio_streams/announcement_$newId.mp3';
        changed = true;
      }
    }
    if (dismissedAnnouncementIds.remove(oldId)) {
      dismissedAnnouncementIds.add(newId);
    }
    if (completedSinglePlayAnnouncementIds.remove(oldId)) {
      completedSinglePlayAnnouncementIds.add(newId);
      _savePersistedCompletedIds();
    }
    if (changed) {
      queueItems.refresh();
    }
  }

  Timer? _playbackTimer;
  Timer? _pollTimer;
  Timer? _intermissionTimer;
  StreamSubscription? _realtimeSubscription;

  // Fallback initial speaker nodes: Canonical nodes (ESP32 Live Node + Wokwi + Hardware Clients 1 & 2)
  static final List<Map<String, dynamic>> defaultSpeakerNodes = [
    {
      'id': 13,
      'name': 'ESP32 Smart Speaker & Live Display',
      'mac_address': 'D4:F3:2D:22:2A:CD',
      'ip_address': '192.168.1.100',
      'zone': 'Campus Main Corridor',
      'department': 'College-Wide',
      'status': 'OFFLINE',
      'volume': 90,
      'cpu_usage': 0.0,
      'memory_usage': 0.0,
    },
    {
      'id': 8,
      'name': 'Hardware Speaker Client 1',
      'mac_address': 'D4:F3:2D:22:2A:CB',
      'ip_address': '127.0.0.1',
      'zone': 'Auditorium / Campus',
      'department': 'College-Wide',
      'status': 'OFFLINE',
      'volume': 85,
      'cpu_usage': 0.0,
      'memory_usage': 0.0,
    },
    {
      'id': 9,
      'name': 'Hardware Speaker Client 2',
      'mac_address': 'D4:F3:2D:22:2A:CC',
      'ip_address': '127.0.0.1',
      'zone': 'Block B - AI Lab',
      'department': 'AIML',
      'status': 'OFFLINE',
      'volume': 85,
      'cpu_usage': 0.0,
      'memory_usage': 0.0,
    },
    {
      'id': 12,
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
  ];

  @override
  void onInit() {
    super.onInit();
    _loadPersistedCompletedIds();
    speakerNodes.assignAll(defaultSpeakerNodes);
    refreshQueue();

    // Auto-poll to keep remote state and nodes in sync (skip in testMode)
    if (!Get.testMode) {
      _pollTimer = Timer.periodic(const Duration(seconds: 4), (_) {
        refreshQueue(silent: true);
      });

      // Realtime multi-device WebSocket listener for 0-latency instant UI synchronization
      try {
        _realtimeSubscription = EchosphereRealtimeService().events.listen((event) {
          final ev = event.event.toUpperCase();
          if (ev == 'QUEUE_SYNC_START') {
            // The speaker just started pulling this notice's audio: start the bar from 0
            final dur = event.rawData['duration_seconds'] as int?;
            if (dur != null && dur > 0) {
              currentTotalDuration.value = dur;
            }
            speakerConfirmed.value = true;
            isPlaying.value = true;
            _syncServerElapsed((event.rawData['elapsed_seconds'] as num?)?.toDouble() ?? 0);
            _startPlaybackTimer();
            refreshQueue(silent: true);
          } else if (ev.contains('QUEUE') || ev.contains('ANNOUNCEMENT') || ev.contains('EMERGENCY') || ev.contains('PLAYBACK') || ev.contains('NOTICE')) {
            refreshQueue(silent: true);
          }
        });
      } catch (e) {
        debugPrint('Realtime queue subscription note: $e');
      }
    }

    // Also listen to changes in AnnouncementController to immediately pick up new notices
    if (Get.isRegistered<AnnouncementController>()) {
      final annCtrl = Get.find<AnnouncementController>();
      ever(annCtrl.rxAnnouncements, (_) {
        _syncWithLocalAnnouncements();
      });
    }
  }

  void cancelAllTimers() {
    _playbackTimer?.cancel();
    _pollTimer?.cancel();
    _intermissionTimer?.cancel();
    _realtimeSubscription?.cancel();
  }

  @override
  void onClose() {
    cancelAllTimers();
    super.onClose();
  }

  bool isScheduleActiveNow(Map<String, dynamic> sched) {
    if (sched['is_active'] == false) return false;
    final now = DateTime.now();

    if (sched['end_date'] != null) {
      final endDt = DateTime.tryParse(sched['end_date'].toString());
      if (endDt != null && now.isAfter(endDt.toLocal())) return false;
    }

    final mode = (sched['repeat_mode'] ?? '').toString().toUpperCase();
    final slots = (sched['selected_slots'] as List? ?? []).map((e) => e.toString().toUpperCase()).toList();

    // INTERVAL mode is active continuously across the schedule lifespan
    if (mode == 'INTERVAL' || slots.contains('INTERVAL')) return true;

    final curMinutes = now.hour * 60 + now.minute;

    // Standard break slots in minutes:
    // SHORT_BREAK: 11:00 - 11:15 (660 - 675)
    // LUNCH_BREAK: 13:15 - 14:00 (795 - 840)
    // EVENING_BREAK: 16:30 - 17:00 (990 - 1020)
    // HOSTEL_WINDOW: 19:30 - 20:30 (1170 - 1230)
    if (slots.contains('SHORT_BREAK') && curMinutes >= 660 && curMinutes <= 675) return true;
    if (slots.contains('LUNCH_BREAK') && curMinutes >= 795 && curMinutes <= 840) return true;
    if (slots.contains('EVENING_BREAK') && curMinutes >= 990 && curMinutes <= 1020) return true;
    if (slots.contains('HOSTEL_WINDOW') && curMinutes >= 1170 && curMinutes <= 1230) return true;

    if (slots.contains('CUSTOM_WINDOW')) {
      final startStr = (sched['custom_start_time'] ?? '').toString().trim();
      final endStr = (sched['custom_end_time'] ?? '').toString().trim();
      if (startStr.isNotEmpty) {
        int parseMinutes(String s) {
          final m12 = RegExp(r'^(\d{1,2}):([0-5]\d)\s*([AaPp][Mm])$').firstMatch(s);
          if (m12 != null) {
            var h = int.parse(m12.group(1)!);
            final m = int.parse(m12.group(2)!);
            final mer = m12.group(3)!.toUpperCase();
            if (mer == 'PM' && h != 12) h += 12;
            if (mer == 'AM' && h == 12) h = 0;
            return h * 60 + m;
          }
          final parts = s.split(':');
          if (parts.length >= 2) {
            final h = int.tryParse(parts[0]) ?? 0;
            final m = int.tryParse(parts[1].substring(0, 2)) ?? 0;
            return h * 60 + m;
          }
          return 0;
        }

        final startM = parseMinutes(startStr);
        final endM = endStr.isNotEmpty ? parseMinutes(endStr) : (startM + 30);
        if (curMinutes >= startM && curMinutes <= endM) {
          return true;
        }
      }
    }
    return false;
  }

  bool _isNoticeEmergency(AnnouncementModel a) {
    final p = a.priority.toUpperCase();
    final el = a.emergencyLevel.toUpperCase();
    final cat = a.category.toUpperCase();
    if (p == 'EMERGENCY' || p == 'CRITICAL' || el == 'EMERGENCY' || el == 'CRITICAL' || cat == 'EMERGENCY') {
      return true;
    }
    final text = '${a.title} ${a.description}'.toLowerCase();
    const emergencyKeywords = [
      'earthquake', 'evacuat', 'fire alert', 'siren', 'lockdown',
      'hazard', 'gas leak', 'tsunami', 'tornado', 'active shooter', 'emergency'
    ];
    return emergencyKeywords.any((kw) => text.contains(kw));
  }

  bool _isItemEmergency(Map<String, dynamic> item) {
    final p = (item['priority'] ?? '').toString().toUpperCase();
    final el = (item['emergency_level'] ?? item['emergencyLevel'] ?? '').toString().toUpperCase();
    final cat = (item['category'] ?? '').toString().toUpperCase();
    if (p == 'EMERGENCY' || p == 'CRITICAL' || el == 'EMERGENCY' || el == 'CRITICAL' || cat == 'EMERGENCY') {
      return true;
    }
    final text = '${item['title'] ?? ''} ${item['message'] ?? item['description'] ?? ''}'.toLowerCase();
    const emergencyKeywords = [
      'earthquake', 'evacuat', 'fire alert', 'siren', 'lockdown',
      'hazard', 'gas leak', 'tsunami', 'tornado', 'active shooter', 'emergency'
    ];
    return emergencyKeywords.any((kw) => text.contains(kw));
  }

  /// Returns the maximum repeat broadcasts allowed in a repetition slot based on priority tier:
  /// - Emergency: 999999 (loops continuously for entire break / custom window)
  /// - High: 3 times
  /// - Normal / Medium: 2 times
  /// - Low: 1 time
  int getNoticeMaxRepeats(Map<String, dynamic> item) {
    if (item['max_repeats'] is int && (item['max_repeats'] as int) > 0) {
      return item['max_repeats'] as int;
    }
    if (_isItemEmergency(item)) {
      return 999999;
    }
    final p = (item['priority'] ?? '').toString().toUpperCase();
    final title = (item['title'] ?? '').toString().toLowerCase();
    final desc = (item['description'] ?? item['message'] ?? item['content'] ?? '').toString().toLowerCase();
    final combined = '$title $desc';

    if (p.contains('HIGH') || p.contains('URGENT') ||
        ['exam', 'examination', 'test', 'timetable', 'hall ticket', 'viva', 'semester', 'placement', 'interview', 'deadline', 'fee payment'].any((w) => combined.contains(w))) {
      return 3;
    } else if (p.contains('LOW') ||
        ['lost and found', 'lost & found', 'lost', 'found', 'canteen', 'maintenance', 'bus timing', 'reminder'].any((w) => combined.contains(w))) {
      return 1;
    }
    return 2;
  }

  /// Syncs speaker notices directly from AnnouncementController (test mode only)
  void _syncWithLocalAnnouncements() {
    if (!Get.isRegistered<AnnouncementController>()) return;
    if (!Get.testMode) return; // In live mode, queue is canonical and driven by backend API
    final annCtrl = Get.find<AnnouncementController>();

    // All published announcements marked for speaker broadcast or repeat schedule
    final eligibleNotices = annCtrl.allAnnouncements.where((a) {
      final isApproved = a.status == 'PUBLISHED' || a.status == 'APPROVED' || a.status == 'ACTIVE' || a.status == 'SCHEDULED';
      final isSpeaker = a.deliverSpeaker || a.priority.toUpperCase() == 'EMERGENCY' || a.repeatSchedule != null;
      final isNotAutomated = !a.title.toLowerCase().contains('automated speaker notice') &&
          !a.title.toLowerCase().contains('sample notice');
      final hasActiveRepeat = a.repeatSchedule != null && isScheduleActiveNow(a.repeatSchedule!);
      final isSingleCompleted = dismissedAnnouncementIds.contains(a.id) ||
          completedSinglePlayAnnouncementIds.contains(a.id) ||
          annCtrl.playedSpeakerNoticeIds.contains(a.id);
      if (isSingleCompleted && !hasActiveRepeat) return false;
      return isApproved && isSpeaker && isNotAutomated && (!a.playedOnSpeaker || hasActiveRepeat);
    }).toList();

    // Emergency Override Check: If ANY emergency notice is active (e.g. Earthquake Alert)
    final emergencyNotices = eligibleNotices.where((a) => _isNoticeEmergency(a)).toList();

    if (emergencyNotices.isNotEmpty) {
      // Pause ALL non-emergency notices currently in queue to enforce total lockdown
      for (var q in queueItems) {
        if (!_isItemEmergency(q)) {
          q['status'] = 'Paused';
        }
      }
    }

    final List<AnnouncementModel> finalCandidates = emergencyNotices.isNotEmpty
        ? emergencyNotices
        : eligibleNotices;

    bool changed = false;
    for (var notice in finalCandidates) {
      final hasNoticeRepeat = notice.repeatSchedule != null && isScheduleActiveNow(notice.repeatSchedule!);
      if ((dismissedAnnouncementIds.contains(notice.id) ||
          completedSinglePlayAnnouncementIds.contains(notice.id)) && !hasNoticeRepeat) {
        continue;
      }

      // Check if already in queue by id or by matching title and department
      final matchIdx = queueItems.indexWhere((q) =>
          q['announcement_id'] == notice.id ||
          q['id'] == notice.id ||
          ((q['title'] ?? '').toString().trim().toLowerCase() == notice.title.trim().toLowerCase() &&
           (q['department'] ?? '').toString() == notice.department));

      if (matchIdx != -1) {
        // Already in queue! Reconcile temporary ID if needed and never duplicate
        final existingItem = queueItems[matchIdx];
        if (existingItem['id'] != notice.id || existingItem['announcement_id'] != notice.id) {
          existingItem['id'] = notice.id;
          existingItem['announcement_id'] = notice.id;
          existingItem['audio_url'] = '/static/audio_streams/announcement_${notice.id}.mp3';
          changed = true;
        }
        continue;
      }

      final isEm = notice.priority.toUpperCase() == 'EMERGENCY' ||
          notice.title.toLowerCase().contains('earthquake') ||
          notice.title.toLowerCase().contains('emergency') ||
          notice.title.toLowerCase().contains('evacuat');
      final nodeName = _getNodeName(notice.speakerNodeId);

      final now = DateTime.now();
      final isFutureScheduled = notice.scheduledAt != null && notice.scheduledAt!.isAfter(now);
      final hasActivePlayback = isPlaying.value && queueItems.any((q) => q['status'] == 'Playing');
      final shouldPlayNow = isEm || (!isFutureScheduled && !hasActivePlayback);

      final itemMap = {
        'id': notice.id,
        'announcement_id': notice.id,
        'title': isEm && notice.repeatSchedule != null ? '[EMERGENCY REPEAT] ${notice.title}' : notice.title,
        'description': notice.description,
        'department': notice.department,
        'priority': isEm ? 'EMERGENCY' : notice.priority,
        'category': notice.category,
        'type': 'AI Speech',
        'status': shouldPlayNow ? 'Playing' : 'Queued',
        'queue_position': shouldPlayNow ? 1 : queueItems.length + 1,
        'scheduled_time': notice.scheduledAt?.toIso8601String() ?? notice.createdAt.toIso8601String(),
        'speaker_node_id': notice.speakerNodeId,
        'node_name': nodeName,
        'duration_seconds': notice.durationSeconds,
        'audio_url': '/static/audio_streams/announcement_${notice.id}.mp3',
        'repeat_schedule': notice.repeatSchedule,
        'has_repeat': notice.repeatSchedule != null,
        'repeat_round': 1,
        'played_count': 0,
      };

      if (shouldPlayNow) {
        userPausedOrStopped.value = false;
        queueItems.insert(0, itemMap);
        activeIndex.value = 0;
        currentElapsedSeconds.value = 0;
        isPlaying.value = true;
        _startPlaybackTimer();
      } else {
        queueItems.add(itemMap);
      }
      changed = true;
    }

    if (changed) {
      _updateActiveNoticeMetrics();
      queueItems.refresh();
      if (!Get.testMode && !isPlaying.value && !userPausedOrStopped.value && queueItems.isNotEmpty) {
        togglePlayPause(index: 0);
      }
    }
  }

  String _getNodeName(int? nodeId) {
    if (nodeId == null) return 'All Nodes (College-Wide)';
    final match = speakerNodes.firstWhereOrNull((n) =>
        n['id'] == nodeId ||
        ((nodeId == 10 || nodeId == 13 || nodeId == 14) && ((n['name'] ?? '').toString().contains('ESP32') || (n['mac_address'] ?? '').toString().contains('2A:CD'))) ||
        ((nodeId == 21 || nodeId == 16 || nodeId == 9) && (n['name'] ?? '').toString().contains('Client 2')) ||
        ((nodeId == 15 || nodeId == 8) && (n['name'] ?? '').toString().contains('Client') && !(n['name'] ?? '').toString().contains('Client 2')) ||
        ((nodeId == 14 || nodeId == 12) && (n['name'] ?? '').toString().contains('Wokwi')));
    if (match != null) return match['name'] ?? 'Speaker #$nodeId';
    return 'Speaker Node #$nodeId';
  }

  String getNodeName(int? nodeId) => _getNodeName(nodeId);

  String getNodeStatus(int? nodeId) {
    if (nodeId == null) {
      final anyOnline = speakerNodes.any((n) => (n['status'] ?? '').toString().toUpperCase() == 'ONLINE');
      return anyOnline ? 'ONLINE' : 'OFFLINE';
    }
    final match = speakerNodes.firstWhereOrNull((n) =>
        n['id'] == nodeId ||
        ((nodeId == 10 || nodeId == 13 || nodeId == 14) && ((n['name'] ?? '').toString().contains('ESP32') || (n['mac_address'] ?? '').toString().contains('2A:CD'))) ||
        ((nodeId == 21 || nodeId == 16 || nodeId == 9) && (n['name'] ?? '').toString().contains('Client 2')) ||
        ((nodeId == 15 || nodeId == 8) && (n['name'] ?? '').toString().contains('Client') && !(n['name'] ?? '').toString().contains('Client 2')) ||
        ((nodeId == 14 || nodeId == 12) && (n['name'] ?? '').toString().contains('Wokwi')));
    return (match?['status'] ?? 'OFFLINE').toString().toUpperCase();
  }

  bool isNodeOnline(int? nodeId) {
    return getNodeStatus(nodeId) == 'ONLINE';
  }

  /// Refreshes queue and nodes from both local announcements and remote backend
  Future<void> refreshQueue({bool silent = false}) async {
    if (!silent) isLoading.value = true;
    errorMessage.value = '';

    if (Get.testMode) {
      try {
        _syncWithLocalAnnouncements();
      } finally {
        if (!silent) isLoading.value = false;
      }
      return;
    }

    try {
      // Fetch remote hardware nodes and queue concurrently in parallel
      List<dynamic> remoteNodes = [];
      List<dynamic> rawQueue = [];
      try {
        final results = await Future.wait([
          _apiService.getSpeakerNodes().catchError((e) {
            debugPrint('Remote speaker nodes fetch note: $e');
            return <dynamic>[];
          }),
          _apiService.getSpeakerQueue().catchError((e) {
            debugPrint('Remote speaker queue fetch note: $e');
            return <dynamic>[];
          }),
        ]);
        remoteNodes = results[0];
        rawQueue = results[1];
      } catch (e) {
        debugPrint('Parallel speaker refresh note: $e');
      }
      applyServerSnapshot(nodes: remoteNodes, queue: rawQueue);
    } catch (e) {
      debugPrint('Error in SpeakerQueueController refreshQueue: $e');
      errorMessage.value = e.toString();
    } finally {
      if (!silent) isLoading.value = false;
    }
  }

  /// Applies one backend snapshot (speaker nodes + queue) to the page state.
  /// The backend is the only source of truth for what is queued, playing or held.
  void applyServerSnapshot({required List<dynamic> nodes, required List<dynamic> queue}) {
    List<Map<String, dynamic>> remoteActiveItems = [];
    final fetchedNodes = nodes
        .whereType<Map>()
        .map((n) => Map<String, dynamic>.from(n))
        .toList();
    if (fetchedNodes.isNotEmpty) {
      speakerNodes.assignAll(fetchedNodes);
    } else if (speakerNodes.isEmpty) {
      speakerNodes.assignAll(defaultSpeakerNodes);
    }

    remoteActiveItems = queue
        .whereType<Map>()
        .map((q) => Map<String, dynamic>.from(q))
        // Show exactly what the backend queue holds. (Local "already played" / "dismissed"
        // lists used to hide items here, so a replayed or re-queued notice showed an empty
        // queue while the speaker was playing it.)
        .where((q) {
          return q['status'] != 'Completed' &&
              q['status'] != 'Cancelled' &&
              q['status'] != 'Skipped';
        })
        .toList();

    // 3. Assemble active queue strictly from canonical backend queue
    List<Map<String, dynamic>> combined = [];
    final Set<int> seenAnnouncementIds = {};

    for (var q in remoteActiveItems) {
      final annId = q['announcement_id'] as int? ?? q['id'] as int? ?? 0;
      final targetNodeId = q['speaker_node_id'] as int?;
      final nodeName = q['speaker_node_name'] ?? _getNodeName(targetNodeId);
      final nodeStatus = q['speaker_node_status'] ?? getNodeStatus(targetNodeId);
      seenAnnouncementIds.add(annId);

      final existing = queueItems.firstWhereOrNull((item) => (item['announcement_id'] == annId || item['id'] == annId));
      final backendPlayedCount = q['repeat_schedule'] != null ? (q['repeat_schedule']['total_played_count'] as int? ?? 0) : (q['current_round'] as int? ?? 0);
      final existingPlayedCount = existing?['played_count'] as int? ?? backendPlayedCount;
      final backendRound = q['repeat_round'] as int?;
      final currentRound = backendRound ?? (existing?['repeat_round'] as int? ?? (backendPlayedCount + 1));
      final bool hasRepeatActive = q['has_repeat'] == true ||
          (q['repeat_schedule'] != null &&
           q['repeat_schedule'] is Map &&
           (q['repeat_schedule'] as Map)['is_active'] == true);
      final maxReps = hasRepeatActive ? (q['max_repeats'] as int? ?? getNoticeMaxRepeats(q)) : 1;

      combined.add({
        ...q,
        'node_name': nodeName,
        'node_status': nodeStatus,
        'duration_seconds': q['duration_seconds'] ?? 15,
        'has_repeat': hasRepeatActive,
        'is_repeat': q['is_repeat'] == true || (hasRepeatActive && currentRound > 1),
        'max_repeats': maxReps,
        'played_count': backendPlayedCount > 0 ? backendPlayedCount : existingPlayedCount,
        'repeat_round': currentRound,
        'repeat_mode': q['repeat_mode'] ?? (q['repeat_schedule'] != null ? q['repeat_schedule']['repeat_mode'] : 'BREAK_SLOTS'),
        'interval_minutes': q['interval_minutes'] ?? (q['repeat_schedule'] != null ? q['repeat_schedule']['interval_minutes'] : 0),
        'next_repeat_at': q['next_repeat_at'] ?? q['scheduled_time'],
      });
    }

    // Filter out any legacy dummy/automated notices from combined list
    combined.removeWhere((item) {
      final t = (item['title'] ?? '').toString().toLowerCase();
      return t.contains('automated speaker notice') || t.contains('sample notice');
    });

    if (combined.isEmpty) {
      isPlaying.value = false;
      userPausedOrStopped.value = false;
      _playbackTimer?.cancel();
      activeIndex.value = 0;
      currentElapsedSeconds.value = 0;
    }

    // If previous queue was empty, clear any prior paused flag so incoming notices play automatically
    if (queueItems.isEmpty && combined.isNotEmpty) {
      userPausedOrStopped.value = false;
    }

    // The backend is the only source of truth. A notice is "playing" on the bar only after
    // the speaker confirms it, and a user pause is the backend's 'Held' status.
    final playingIdx = combined.indexWhere((q) => q['status']?.toString().toLowerCase() == 'playing');
    final heldIdx = combined.indexWhere((q) => q['status']?.toString().toLowerCase() == 'held');
    userPausedOrStopped.value = heldIdx != -1 && playingIdx == -1;
    if (playingIdx != -1) {
      activeIndex.value = playingIdx;
      combined[playingIdx]['status'] = 'Playing';
      final dur = combined[playingIdx]['duration_seconds'] as int? ?? 15;
      currentTotalDuration.value = dur > 0 ? dur : 15;
      final confirmed = combined[playingIdx]['speaker_confirmed'] == true;
      speakerConfirmed.value = confirmed;
      _syncServerElapsed(confirmed ? (combined[playingIdx]['speaker_elapsed_seconds'] as num?)?.toDouble() ?? 0 : null);
      if (!isPlaying.value || _playbackTimer == null || !_playbackTimer!.isActive) {
        isPlaying.value = true;
        _startPlaybackTimer();
      }
    } else {
      if (heldIdx != -1) activeIndex.value = heldIdx;
      isPlaying.value = false;
      speakerConfirmed.value = false;
      _playbackTimer?.cancel();
      _syncServerElapsed(null);
    }

    queueItems.assignAll(combined);
    _updateActiveNoticeMetrics();
  }

  void _updateActiveNoticeMetrics() {
    if (queueItems.isEmpty || activeIndex.value < 0 || activeIndex.value >= queueItems.length) {
      currentTotalDuration.value = 15;
      return;
    }
    final item = queueItems[activeIndex.value];
    final dur = item['duration_seconds'] as int? ?? 15;
    currentTotalDuration.value = dur > 0 ? dur : 15;
  }

  String get activeTitle {
    if (queueItems.isEmpty || activeIndex.value < 0 || activeIndex.value >= queueItems.length) {
      return 'No active speaker announcement';
    }
    final item = queueItems[activeIndex.value];
    return (item['title'] ?? 'Untitled Announcement').toString();
  }

  String get activeSubtitle {
    if (queueItems.isEmpty || activeIndex.value < 0 || activeIndex.value >= queueItems.length) {
      return 'PA system standing by';
    }
    final item = queueItems[activeIndex.value];
    final dept = item['department']?.toString() ?? 'College-Wide';
    final node = item['node_name']?.toString() ?? 'All Nodes';
    return '$dept \u2022 $node';
  }

  String get currentElapsedFormatted {
    final mins = (currentElapsedSeconds.value ~/ 60).toString().padLeft(2, '0');
    final secs = (currentElapsedSeconds.value % 60).toString().padLeft(2, '0');
    return '$mins:$secs';
  }

  String get currentTotalFormatted {
    final mins = (currentTotalDuration.value ~/ 60).toString().padLeft(2, '0');
    final secs = (currentTotalDuration.value % 60).toString().padLeft(2, '0');
    return '$mins:$secs';
  }

  double get playbackProgress {
    if (currentTotalDuration.value <= 0) return 0.0;
    return (currentElapsedSeconds.value / currentTotalDuration.value).clamp(0.0, 1.0);
  }

  /// Sends one queue command to the backend (which drives the speaker) and re-reads the
  /// real queue state. Live mode only: the backend is the single scheduler.
  Future<bool> _sendLiveQueueAction(Map<String, dynamic> item, String action) async {
    final annId = item['announcement_id'] as int?;
    if (annId == null || annId <= 0) return false;
    try {
      await _apiService.queueAction(annId, action, target: 'announcement');
      return true;
    } catch (e) {
      errorSnackBar('Speaker command failed: ${e.toString().replaceAll("Exception: ", "")}');
      return false;
    } finally {
      await refreshQueue(silent: true);
    }
  }

  /// Starts or resumes playing the notice at [index] (or active notice)
  Future<void> togglePlayPause({int? index}) async {
    if (queueItems.isEmpty) {
      snackBar('Speaker queue is currently empty.');
      return;
    }

    final targetIdx = index ?? activeIndex.value;
    if (targetIdx < 0 || targetIdx >= queueItems.length) return;

    if (!Get.testMode) {
      final item = queueItems[targetIdx];
      final pausing = (item['status']?.toString().toLowerCase() == 'playing');
      // Pause stops the speaker and holds the queue; play/resume restarts the notice from the beginning
      if (await _sendLiveQueueAction(item, pausing ? 'pause' : 'play')) {
        snackBar(pausing ? 'Speaker playback paused.' : 'Broadcasting: "${item['title'] ?? 'Announcement'}"');
      }
      return;
    }

    if (isPlaying.value && (index == null || index == activeIndex.value)) {
      // Pause
      isPlaying.value = false;
      userPausedOrStopped.value = true;
      _playbackTimer?.cancel();
      queueItems[activeIndex.value]['status'] = 'Paused';
      queueItems.refresh();

      final item = queueItems[activeIndex.value];
      final targetId = item['announcement_id'] as int? ?? item['id'] as int?;
      if (!Get.testMode && targetId != null) {
        _apiService.queueAction(targetId, 'pause').catchError((_) => <String, dynamic>{});
      }
      if (!Get.testMode) {
        try {
          TtsAudioService.instance.pause();
        } catch (_) {}
      }
      snackBar('Speaker playback paused.');
      return;
    }

    // Play/Resume
    activeIndex.value = targetIdx;
    currentElapsedSeconds.value = 0;
    _updateActiveNoticeMetrics();
    userPausedOrStopped.value = false;

    final item = queueItems[activeIndex.value];
    final annId = item['announcement_id'] as int? ?? item['id'] as int?;
    if (annId != null && annId > 0) {
      completedSinglePlayAnnouncementIds.remove(annId);
      dismissedAnnouncementIds.remove(annId);
      if (Get.isRegistered<AnnouncementController>()) {
        Get.find<AnnouncementController>().playedSpeakerNoticeIds.remove(annId);
      }
    }

    // Mark active item as Playing and others as Queued
    for (int i = 0; i < queueItems.length; i++) {
      queueItems[i]['status'] = (i == activeIndex.value) ? 'Playing' : 'Queued';
    }
    queueItems.refresh();

    isPlaying.value = true;
    _startPlaybackTimer();

    final targetId = item['announcement_id'] as int? ?? item['id'] as int?;
    if (!Get.testMode && targetId != null) {
      final queueId = item['id'] as int? ?? targetId;
      _apiService.queueAction(queueId, 'play').catchError((e) {
        debugPrint('[SpeakerQueue] queueAction play initial attempt note: $e, ensuring enqueued first...');
        return _apiService.enqueueAnnouncement(
          announcementId: targetId,
          title: item['title'] as String?,
          content: (item['description'] ?? item['content']) as String?,
        ).then((res) {
          final realQId = res['id'] ?? (res['details'] != null ? res['details']['queue_id'] : null) ?? queueId;
          return _apiService.queueAction(realQId as int, 'play');
        }).catchError((err) {
          debugPrint('[SpeakerQueue] queueAction play fallback note: $err');
          return <String, dynamic>{};
        });
      });
    }

    if (!Get.testMode && enableLocalAudioPreview.value) {
      try {
        final annId = item['announcement_id'] as int? ?? item['id'] as int?;
        if (annId != null && annId > 0) {
          TtsAudioService.instance.playAnnouncement(
            annId,
            title: item['title']?.toString(),
            content: item['description']?.toString(),
            directUrl: item['audio_url']?.toString(),
          );
        }
      } catch (e) {
        debugPrint('[SpeakerQueue] Audio playback note: $e');
      }
    }

    snackBar('Broadcasting: "${item['title'] ?? 'Announcement'}"');
  }

  void _startPlaybackTimer() {
    _playbackTimer?.cancel();
    if (Get.testMode) return;
    _playbackTimer = Timer.periodic(const Duration(milliseconds: 250), (timer) {
      if (!isPlaying.value) {
        timer.cancel();
        return;
      }
      // The bar only moves once the speaker has confirmed it is playing,
      // and always follows the server-reported position.
      final syncedAt = _serverElapsedSyncedAt;
      if (!speakerConfirmed.value || syncedAt == null) {
        currentElapsedSeconds.value = 0;
        return;
      }
      final elapsed = _serverElapsedAtSync + DateTime.now().difference(syncedAt).inMilliseconds / 1000.0;
      currentElapsedSeconds.value = elapsed.floor().clamp(0, currentTotalDuration.value);
    });
  }

  /// Manually or programmatically triggers playback completion (used in tests and skips)
  Future<void> completeCurrentPlayback() async {
    _playbackTimer?.cancel();
    await _onNoticePlaybackCompleted();
  }

  /// Called automatically when the current notice completes its single playback
  Future<void> _onNoticePlaybackCompleted() async {
    _playbackTimer?.cancel();

    if (queueItems.isEmpty || activeIndex.value < 0 || activeIndex.value >= queueItems.length) {
      isPlaying.value = false;
      return;
    }

    final playedItem = queueItems[activeIndex.value];
    final annId = playedItem['announcement_id'] as int? ?? playedItem['id'] as int? ?? 0;
    final playedTitle = (playedItem['title'] ?? 'Announcement').toString();

    final bool isEmergencyNotice = _isItemEmergency(playedItem);
    final bool hasRepeat = playedItem['has_repeat'] == true ||
        (playedItem['repeat_schedule'] != null &&
         playedItem['repeat_schedule'] is Map &&
         (playedItem['repeat_schedule'] as Map)['is_active'] != false);

    bool isSlotActive = true;
    if (playedItem['repeat_schedule'] != null && playedItem['repeat_schedule'] is Map) {
      isSlotActive = isScheduleActiveNow(Map<String, dynamic>.from(playedItem['repeat_schedule']));
    }

    final int maxRepeats = getNoticeMaxRepeats(playedItem);
    int currentPlayedCount = (playedItem['played_count'] as int? ?? 0) + 1;
    playedItem['played_count'] = currentPlayedCount;

    if (!Get.testMode && enableLocalAudioPreview.value) {
      try {
        TtsAudioService.instance.stop();
      } catch (_) {}
    }

    // 1. Emergency Continuous Loop (Emergency repeats throughout the whole break/custom window ONLY if rescheduling was configured)
    if (isEmergencyNotice && hasRepeat && isSlotActive) {
      currentElapsedSeconds.value = 0;
      queueItems[activeIndex.value]['status'] = 'Playing';
      _updateActiveNoticeMetrics();
      queueItems.refresh();
      isPlaying.value = true;
      _startPlaybackTimer();

      // Enforce lockdown: ensure all non-emergency notices in queue remain Paused
      for (int i = 0; i < queueItems.length; i++) {
        if (i != activeIndex.value && !_isItemEmergency(queueItems[i])) {
          queueItems[i]['status'] = 'Paused';
        }
      }
      queueItems.refresh();

      snackBar('Repeating Emergency Broadcast: "$playedTitle"', title: 'Emergency Broadcast Continuous Loop');
      return;
    }

    // 2. Continuous rotation / future slot repeat:
    final bool repeatsRemain = (!isEmergencyNotice && hasRepeat && (maxRepeats <= 0 || currentPlayedCount < maxRepeats));

    // Notify backend that notice playback finished
    final targetId = annId > 0 ? annId : (playedItem['id'] as int? ?? 0);
    if (!Get.testMode && targetId > 0) {
      _apiService.queueAction(targetId, 'complete').then((resp) {
        if (resp['new_status'] == 'Queued' || resp['next_repeat_at'] != null) {
          refreshQueue(silent: true);
        }
      }).catchError((_) {});
    }

    if (repeatsRemain) {
      // Re-queue at the end of queue for continuous rotation or upcoming scheduled repeat
      playedItem['status'] = 'Queued';
      playedItem['repeat_round'] = currentPlayedCount + 1;
      final requeuedItem = Map<String, dynamic>.from(playedItem);
      queueItems.removeAt(activeIndex.value);
      queueItems.add(requeuedItem);
      currentElapsedSeconds.value = 0;

      final roundInfo = maxRepeats > 0 ? '$currentPlayedCount of $maxRepeats' : '$currentPlayedCount';
      snackBar(
        'Broadcasted repeat round $roundInfo for "$playedTitle". Queued for next scheduled repeat.',
        title: 'Repeat Broadcast Progress',
      );
    } else {
      // All repeats completed (or single play notice, or repeat limit reached)
      dismissedAnnouncementIds.add(annId);
      completedSinglePlayAnnouncementIds.add(annId);
      _savePersistedCompletedIds();
      if (annId > 0 && Get.isRegistered<AnnouncementController>()) {
        Get.find<AnnouncementController>().markNoticePlayedOnSpeaker(annId);
      }

      queueItems.removeAt(activeIndex.value);
      // Purge any duplicate records of this notice with no repeat schedule
      queueItems.removeWhere((q) =>
          (q['announcement_id'] == annId ||
           q['id'] == annId ||
           (q['title'] ?? '').toString().trim().toLowerCase() == playedTitle.trim().toLowerCase()) &&
          q['has_repeat'] != true &&
          q['repeat_schedule'] == null);
      currentElapsedSeconds.value = 0;

      final finishMsg = hasRepeat
          ? 'Completed all scheduled repeat rounds for "$playedTitle". Removed from speaker queue.'
          : 'Completed broadcast of "$playedTitle". Removed from speaker queue.';
      snackBar(finishMsg, title: 'Broadcast Finished');
    }

    // 3. Advance to next queued notice or finish (with clean transition to prevent audio overlap)
    if (queueItems.isNotEmpty) {
      // Small clean silence gap between notices so audio never collides or overlaps
      if (!Get.testMode) {
        await Future.delayed(const Duration(milliseconds: 1500));
      }
      if (userPausedOrStopped.value || queueItems.isEmpty) return;
      // Priority 1: Emergency preemption - check if an emergency notice is queued (prioritized first)
      final emergencyIdx = queueItems.indexWhere((q) => _isItemEmergency(q));

      if (emergencyIdx != -1) {
        final emergencyItem = queueItems.removeAt(emergencyIdx);
        queueItems.insert(0, emergencyItem);
        activeIndex.value = 0;
        queueItems[0]['status'] = 'Playing';
        currentElapsedSeconds.value = 0;
        _updateActiveNoticeMetrics();

        // Lockdown: keep all other notices paused while emergency is active
        for (int i = 1; i < queueItems.length; i++) {
          if (!_isItemEmergency(queueItems[i])) {
            queueItems[i]['status'] = 'Paused';
          }
        }
        queueItems.refresh();
        isPlaying.value = true;
        _startPlaybackTimer();

        final nextTargetId = emergencyItem['announcement_id'] as int? ?? emergencyItem['id'] as int?;
        if (!Get.testMode && nextTargetId != null) {
          _apiService.queueAction(nextTargetId, 'play').catchError((_) => <String, dynamic>{});
        }

        if (!Get.testMode && enableLocalAudioPreview.value) {
          try {
            final nextAnnId = emergencyItem['announcement_id'] as int? ?? emergencyItem['id'] as int?;
            if (nextAnnId != null && nextAnnId > 0) {
              TtsAudioService.instance.playAnnouncement(
                nextAnnId,
                title: emergencyItem['title']?.toString(),
                content: emergencyItem['description']?.toString(),
                directUrl: emergencyItem['audio_url']?.toString(),
              );
            }
          } catch (e) {
            debugPrint('[SpeakerQueue] Emergency audio play note: $e');
          }
        }
        return;
      }

      // Priority 2: Advance to next queued notice in round-robin rotation cleanly
      _advanceToNextEligibleNotice();
    } else {
      _playbackTimer?.cancel();
      _intermissionTimer?.cancel();
      isIntermission.value = false;
      activeIndex.value = 0;
      isPlaying.value = false;
      userPausedOrStopped.value = false;
      currentElapsedSeconds.value = 0;
      queueItems.refresh();
      snackBar('All queued speaker notices have completed broadcast.');
    }
  }

  /// Advances to the next eligible queued notice on a First Come First Serve (FCFS) basis,
  /// respecting scheduled times (only playing notices whose scheduled_time <= now).
  void _advanceToNextEligibleNotice() {
    // Purge any completed single-play notices before advancing
    queueItems.removeWhere((q) {
      final annId = q['announcement_id'] as int? ?? q['id'] as int? ?? 0;
      final hasRepeat = q['has_repeat'] == true || q['repeat_schedule'] != null;
      return !hasRepeat &&
          (completedSinglePlayAnnouncementIds.contains(annId) ||
           dismissedAnnouncementIds.contains(annId) ||
           (Get.isRegistered<AnnouncementController>() && Get.find<AnnouncementController>().playedSpeakerNoticeIds.contains(annId)));
    });

    if (queueItems.isEmpty) {
      isPlaying.value = false;
      userPausedOrStopped.value = false;
      return;
    }

    final now = DateTime.now();
    int eligibleIdx = -1;

    // FCFS: iterate in queue order and pick first notice whose scheduled_time has arrived
    for (int i = 0; i < queueItems.length; i++) {
      final q = queueItems[i];
      if (q['status'] == 'Paused' || q['status'] == 'Completed' || q['status'] == 'Cancelled') continue;
      final schedStr = q['scheduled_time']?.toString();
      if (schedStr == null || schedStr.isEmpty) {
        eligibleIdx = i;
        break;
      }
      final sched = DateTime.tryParse(schedStr);
      if (sched == null || sched.isBefore(now.add(const Duration(seconds: 2)))) {
        eligibleIdx = i;
        break;
      }
    }

    if (eligibleIdx != -1) {
      activeIndex.value = eligibleIdx;
      for (int i = 0; i < queueItems.length; i++) {
        queueItems[i]['status'] = (i == activeIndex.value) ? 'Playing' : 'Queued';
      }
      currentElapsedSeconds.value = 0;
      _updateActiveNoticeMetrics();
      queueItems.refresh();
      isPlaying.value = true;
      _startPlaybackTimer();

      final nextItem = queueItems[activeIndex.value];
      final nextTargetId = nextItem['announcement_id'] as int? ?? nextItem['id'] as int?;
      if (!Get.testMode && nextTargetId != null) {
        _apiService.queueAction(nextTargetId, 'play').catchError((_) => <String, dynamic>{});
      }

      if (!Get.testMode && enableLocalAudioPreview.value) {
        try {
          final nextAnnId = nextItem['announcement_id'] as int? ?? nextItem['id'] as int?;
          if (nextAnnId != null && nextAnnId > 0) {
            TtsAudioService.instance.playAnnouncement(
              nextAnnId,
              title: nextItem['title']?.toString(),
              content: nextItem['description']?.toString(),
              directUrl: nextItem['audio_url']?.toString(),
            );
          }
        } catch (e) {
          debugPrint('[SpeakerQueue] Next audio play note: $e');
        }
      }
    } else {
      // Future scheduled notices are waiting for their scheduled time
      isPlaying.value = false;
      for (int i = 0; i < queueItems.length; i++) {
        queueItems[i]['status'] = 'Queued';
      }
      queueItems.refresh();
    }
  }

  /// Skips the current notice, removes it, and advances to the next
  Future<void> skipCurrent() async {
    if (queueItems.isEmpty) return;
    if (!Get.testMode) {
      if (activeIndex.value >= 0 && activeIndex.value < queueItems.length &&
          await _sendLiveQueueAction(queueItems[activeIndex.value], 'skip')) {
        snackBar('Skipped to the next notice.');
      }
      return;
    }
    _playbackTimer?.cancel();
    await _onNoticePlaybackCompleted();
  }

  /// Manually triggers the next scheduled repeat broadcast round immediately
  Future<void> triggerRepeatNow(int queueId) async {
    try {
      isLoading.value = true;
      await _apiService.triggerQueueRepeatNow(queueId);
      snackBar('Next repeat broadcast round initiated!');
      await refreshQueue(silent: false);
    } catch (e) {
      errorSnackBar('Failed to trigger repeat round: ${e.toString().replaceAll("Exception: ", "")}');
    } finally {
      isLoading.value = false;
    }
  }

  /// Stops current playback
  Future<void> stopCurrent() async {
    if (queueItems.isEmpty) return;
    if (!Get.testMode) {
      if (activeIndex.value >= 0 && activeIndex.value < queueItems.length &&
          await _sendLiveQueueAction(queueItems[activeIndex.value], 'stop')) {
        snackBar('Playback stopped.');
      }
      return;
    }
    _playbackTimer?.cancel();
    isPlaying.value = false;
    userPausedOrStopped.value = true;
    currentElapsedSeconds.value = 0;

    if (!Get.testMode) {
      try {
        TtsAudioService.instance.stop();
      } catch (_) {}
    }

    if (activeIndex.value >= 0 && activeIndex.value < queueItems.length) {
      queueItems[activeIndex.value]['status'] = 'Paused';
      final item = queueItems[activeIndex.value];
      final targetId = item['announcement_id'] as int? ?? item['id'] as int?;
      if (!Get.testMode && targetId != null) {
        _apiService.queueAction(targetId, 'stop').catchError((_) => <String, dynamic>{});
      }
    }
    queueItems.refresh();
    snackBar('Playback stopped.');
  }

  /// Manually dismisses/removes a notice from the queue
  Future<void> removeNotice(int index) async {
    if (index < 0 || index >= queueItems.length) return;

    final item = queueItems[index];
    final isCurrent = (index == activeIndex.value);
    final targetId = item['announcement_id'] as int? ?? item['id'] as int?;

    if (!Get.testMode) {
      // Backend stops the speaker, cancels pending plays and ends any repeat schedule
      if (await _sendLiveQueueAction(item, 'remove')) {
        snackBar('Notice removed from speaker queue.');
      }
      return;
    }

    if (targetId != null && targetId > 0) {
      dismissedAnnouncementIds.add(targetId);
      if (Get.isRegistered<AnnouncementController>()) {
        Get.find<AnnouncementController>().markNoticePlayedOnSpeaker(targetId);
      }
      if (!Get.testMode) {
        _apiService.queueAction(targetId, 'remove').catchError((_) => <String, dynamic>{});
      }
    }

    if (isCurrent) {
      _playbackTimer?.cancel();
      isPlaying.value = false;
      currentElapsedSeconds.value = 0;
    }

    queueItems.removeAt(index);
    if (queueItems.isEmpty) {
      userPausedOrStopped.value = false;
      activeIndex.value = 0;
    } else if (index < activeIndex.value) {
      activeIndex.value--;
    } else if (activeIndex.value >= queueItems.length) {
      activeIndex.value = (queueItems.isEmpty ? 0 : queueItems.length - 1);
    }
    _updateActiveNoticeMetrics();
    queueItems.refresh();

    snackBar('Notice removed from speaker queue.');
  }

  /// Explicitly broadcasts an announcement immediately:
  /// 1. Adds it to the speaker queue instantly with 0ms UI lag.
  /// 2. If no notice is currently playing, starts playback immediately and plays voice audio.
  /// 3. If another notice is already broadcasting, enqueues it behind the active notice.
  /// 4. Dispatches backend sync & hardware node notification in background.
  Future<bool> broadcastAnnouncement(
    AnnouncementModel announcement, {
    int? speakerNodeId,
  }) async {
    final targetNodeId = speakerNodeId ?? announcement.speakerNodeId;
    final nodeName = _getNodeName(targetNodeId);

    // 1. Mark in AnnouncementController so local list recognizes it as speaker notice
    completedSinglePlayAnnouncementIds.remove(announcement.id);
    dismissedAnnouncementIds.remove(announcement.id);
    if (Get.isRegistered<AnnouncementController>()) {
      final annCtrl = Get.find<AnnouncementController>();
      annCtrl.playedSpeakerNoticeIds.remove(announcement.id);
      final idx = annCtrl.rxAnnouncements.indexWhere((a) => a.id == announcement.id);
      if (idx != -1) {
        final old = annCtrl.rxAnnouncements[idx];
        annCtrl.rxAnnouncements[idx] = old.copyWith(
          deliverSpeaker: true,
          playedOnSpeaker: false,
        );
        annCtrl.rxAnnouncements.refresh();
      }
    }

    if (!Get.testMode) {
      try {
        final res = await _apiService.enqueueAnnouncement(
          announcementId: announcement.id,
          speakerNodeId: _resolveNodeId(targetNodeId),
          audioType: 'AI Speech',
        );
        await refreshQueue(silent: true);
        final playingNow = res['is_playing'] == true;
        snackBar(
          playingNow
              ? 'Sending "${announcement.title}" to the campus speakers.'
              : 'Added "${announcement.title}" to the speaker queue.',
          title: playingNow ? 'Speaker Broadcast Started' : 'Added to Speaker Queue',
        );
        return true;
      } catch (e) {
        errorSnackBar('Could not queue notice for the speakers: ${e.toString().replaceAll("Exception: ", "")}');
        return false;
      }
    }

    // 2. Check if already in queue or if queue is currently playing
    final existingIdx = queueItems.indexWhere(
      (q) => (q['announcement_id'] == announcement.id || q['id'] == announcement.id) &&
             q['status'] != 'Completed',
    );

    // Check if there is currently an active playback
    final bool hasActivePlayback = isPlaying.value &&
        queueItems.any((q) => q['status'] == 'Playing');

    final bool isEmergency = announcement.priority.toUpperCase() == 'EMERGENCY' ||
        announcement.emergencyLevel.toUpperCase() == 'EMERGENCY';
    final now = DateTime.now();
    final bool isFutureScheduled = announcement.scheduledAt != null && announcement.scheduledAt!.isAfter(now);

    // Emergency always plays immediately; Publish Now plays immediately if queue is idle;
    // Scheduled notices are queued for their scheduled time in FCFS order.
    final bool shouldPlayNow = isEmergency || (!isFutureScheduled && !hasActivePlayback);

    int targetIndex;

    if (existingIdx != -1) {
      targetIndex = existingIdx;
      if (shouldPlayNow) {
        queueItems[existingIdx]['status'] = 'Playing';
      }
    } else {
      final newItem = {
        'id': announcement.id,
        'announcement_id': announcement.id,
        'title': announcement.title,
        'description': announcement.description,
        'department': announcement.department,
        'priority': announcement.priority,
        'category': announcement.category,
        'type': 'AI Speech',
        'status': shouldPlayNow ? 'Playing' : 'Queued',
        'queue_position': shouldPlayNow ? 1 : queueItems.length + 1,
        'scheduled_time': announcement.scheduledAt?.toIso8601String() ?? announcement.createdAt.toIso8601String(),
        'speaker_node_id': targetNodeId,
        'node_name': nodeName,
        'duration_seconds': announcement.durationSeconds > 0 ? announcement.durationSeconds : 15,
        'audio_url': '/static/audio_streams/announcement_${announcement.id}.mp3',
        'repeat_schedule': announcement.repeatSchedule,
        'has_repeat': announcement.repeatSchedule != null,
        'played_count': 0,
        'repeat_round': 1,
      };

      if (isEmergency) {
        queueItems.insert(0, newItem);
        targetIndex = 0;
      } else if (shouldPlayNow) {
        queueItems.insert(0, newItem);
        targetIndex = 0;
      } else {
        // FCFS: append to queue
        queueItems.add(newItem);
        targetIndex = queueItems.length - 1;
      }
    }

    // 3. If playing now, update active notice, start timer and voice speech audio
    if (shouldPlayNow) {
      userPausedOrStopped.value = false;
      activeIndex.value = targetIndex;
      currentElapsedSeconds.value = 0;
      _updateActiveNoticeMetrics();

      for (int i = 0; i < queueItems.length; i++) {
        queueItems[i]['status'] = (i == activeIndex.value) ? 'Playing' : 'Queued';
      }
      queueItems.refresh();

      isPlaying.value = true;
      _startPlaybackTimer();

      if (!Get.testMode && enableLocalAudioPreview.value) {
        try {
          TtsAudioService.instance.playAnnouncement(
            announcement.id,
            title: announcement.title,
            content: announcement.description,
            summary: announcement.aiSummary,
            directUrl: queueItems[activeIndex.value]['audio_url']?.toString(),
          );
        } catch (e) {
          debugPrint('[SpeakerQueue] Audio speech broadcast note: $e');
        }
      }

      snackBar(
        'Now broadcasting "${announcement.title}" on campus speakers.',
        title: 'Speaker Broadcast Started',
      );
    } else {
      queueItems.refresh();
      snackBar(
        'Added "${announcement.title}" to speaker queue (Position #${targetIndex + 1}).',
        title: 'Added to Speaker Queue',
      );
    }

    // 4. Background backend sync (MQTT dispatch and database update) without blocking UI
    if (!Get.testMode) {
      int? resolvedNodeId = targetNodeId;
      final matchNode = speakerNodes.firstWhereOrNull((n) =>
          n['id'] == targetNodeId ||
          ((targetNodeId == 21 || targetNodeId == 16) && (n['name'] ?? '').toString().contains('Client 2')) ||
          (targetNodeId == 15 && (n['name'] ?? '').toString().contains('Client') && !(n['name'] ?? '').toString().contains('Client 2')) ||
          (targetNodeId == 14 && (n['name'] ?? '').toString().contains('Wokwi')));
      if (matchNode != null && matchNode['id'] is int) {
        resolvedNodeId = matchNode['id'] as int;
      }

      unawaited(
        _apiService.enqueueAnnouncement(
          announcementId: announcement.id,
          speakerNodeId: resolvedNodeId,
          audioType: 'AI Speech',
        ).then((res) {
          debugPrint('[SpeakerQueue] Remote enqueue success: $res');
        }, onError: (e) {
          debugPrint('[SpeakerQueue] Remote enqueue note: $e');
        })
      );
    }

    return true;
  }

  int? _resolveNodeId(int? nodeId) {
    final matchNode = speakerNodes.firstWhereOrNull((n) =>
        n['id'] == nodeId ||
        ((nodeId == 21 || nodeId == 16) && (n['name'] ?? '').toString().contains('Client 2')) ||
        (nodeId == 15 && (n['name'] ?? '').toString().contains('Client') && !(n['name'] ?? '').toString().contains('Client 2')) ||
        (nodeId == 14 && (n['name'] ?? '').toString().contains('Wokwi')));
    return (matchNode != null && matchNode['id'] is int) ? matchNode['id'] as int : nodeId;
  }

  /// Explicitly enqueues an announcement into the queue
  Future<void> enqueueNotice({
    required int announcementId,
    String audioType = 'AI Speech',
    int? speakerNodeId,
  }) async {
    completedSinglePlayAnnouncementIds.remove(announcementId);
    dismissedAnnouncementIds.remove(announcementId);
    if (Get.isRegistered<AnnouncementController>()) {
      final annCtrl = Get.find<AnnouncementController>();
      annCtrl.playedSpeakerNoticeIds.remove(announcementId);
      final match = annCtrl.allAnnouncements.firstWhereOrNull((a) => a.id == announcementId);
      if (match != null) {
        await broadcastAnnouncement(match, speakerNodeId: speakerNodeId);
        return;
      }
    }

    int? resolvedNodeId = speakerNodeId;
    final matchNode = speakerNodes.firstWhereOrNull((n) =>
        n['id'] == speakerNodeId ||
        ((speakerNodeId == 21 || speakerNodeId == 16) && (n['name'] ?? '').toString().contains('Client 2')) ||
        (speakerNodeId == 15 && (n['name'] ?? '').toString().contains('Client') && !(n['name'] ?? '').toString().contains('Client 2')) ||
        (speakerNodeId == 14 && (n['name'] ?? '').toString().contains('Wokwi')));
    if (matchNode != null && matchNode['id'] is int) {
      resolvedNodeId = matchNode['id'] as int;
    }

    // Fallback if notice not found in AnnouncementController
    try {
      await _apiService.enqueueAnnouncement(
        announcementId: announcementId,
        audioType: audioType,
        speakerNodeId: resolvedNodeId,
      );
    } catch (e) {
      debugPrint('Enqueue remote notice note: $e');
    }

    await refreshQueue(silent: true);
    snackBar('Notice successfully queued for speaker broadcast!');
  }

  void reorderQueue(int oldIndex, int newIndex) {
    if (oldIndex < 0 || oldIndex >= queueItems.length || newIndex < 0 || newIndex >= queueItems.length) return;
    final item = queueItems.removeAt(oldIndex);
    queueItems.insert(newIndex, item);

    if (activeIndex.value == oldIndex) {
      activeIndex.value = newIndex;
    } else if (activeIndex.value == newIndex) {
      activeIndex.value = oldIndex;
    }

    queueItems.refresh();
    final ids = queueItems.map((q) => q['id'] as int? ?? 0).where((id) => id > 0).toList();
    if (!Get.testMode && ids.isNotEmpty) {
      _apiService.reorderSpeakerQueue(ids).catchError((_) => <String, dynamic>{});
    }
  }

  /// Registers a new physical speaker node
  Future<void> registerNode({
    required String name,
    required String macAddress,
    String? ipAddress,
    required String zone,
    required String department,
  }) async {
    try {
      await _apiService.registerSpeakerNode(
        name: name,
        macAddress: macAddress,
        ipAddress: ipAddress,
        zone: zone,
        department: department,
      );
      snackBar('Speaker Node registered successfully!');
    } catch (e) {
      snackBar('Registration error: ${e.toString()}');
    }
    await refreshQueue(silent: true);
  }

  /// Updates configuration for a speaker node
  Future<void> updateNode(
    int nodeId, {
    String? name,
    String? zone,
    String? department,
    int? volume,
  }) async {
    try {
      await _apiService.updateSpeakerNode(
        nodeId,
        name: name,
        zone: zone,
        department: department,
        volume: volume,
      );
      snackBar('Speaker Node updated successfully!');
    } catch (e) {
      snackBar('Update error: ${e.toString()}');
    }
    await refreshQueue(silent: true);
  }

  /// Deletes a speaker node
  Future<void> deleteNode(int index, int nodeId) async {
    try {
      await _apiService.deleteSpeakerNode(nodeId);
    } catch (e) {
      debugPrint('Delete speaker node error: $e');
    }
    if (index >= 0 && index < speakerNodes.length) {
      speakerNodes.removeAt(index);
    }
    snackBar('Speaker node removed successfully.');
  }

  /// Sends control command to a node
  Future<void> controlNode(int nodeId, String command, String nodeName) async {
    try {
      await _apiService.controlSpeakerNode(nodeId, command: command);
      if (command == 'TEST_SPEAKER') {
        snackBar('Test tone sent to $nodeName');
      } else if (command == 'RESTART') {
        snackBar('Restart signal sent to $nodeName');
      } else {
        snackBar('Command sent to $nodeName');
      }
    } catch (e) {
      snackBar('Command sent: ${e.toString()}');
    }
  }

  /// Sets volume for a speaker node
  Future<void> setNodeVolume(int nodeId, int volume, String nodeName) async {
    try {
      await _apiService.controlSpeakerNode(nodeId, command: 'SET_VOLUME', volume: volume);
      final idx = speakerNodes.indexWhere((n) => n['id'] == nodeId);
      if (idx != -1) {
        speakerNodes[idx]['volume'] = volume;
        speakerNodes.refresh();
      }
      snackBar('Volume for $nodeName set to $volume%');
    } catch (e) {
      snackBar('Volume update: ${e.toString()}');
    }
  }

  /// Explicitly advances the hardware queue to the next announcement
  Future<void> advanceHardwareQueue() async {
    try {
      await _apiService.advanceSpeakerQueue();
      snackBar('Queue advanced to next announcement');
      await refreshQueue();
    } catch (e) {
      snackBar('Advance queue: ${e.toString()}');
    }
  }

  /// Triggers emergency override
  Future<void> triggerEmergency({
    required String title,
    required String message,
  }) async {
    try {
      await _apiService.triggerEmergencyOverride(
        title: title,
        message: message,
      );
      snackBar('EMERGENCY SIREN BROADCASTING LIVE ACROSS ALL NODES');
    } catch (e) {
      snackBar('Emergency broadcast sent: ${e.toString()}');
    }
    await refreshQueue(silent: true);
  }
}

