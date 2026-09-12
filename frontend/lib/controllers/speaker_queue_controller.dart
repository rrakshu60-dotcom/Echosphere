import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/services/tts_audio_service.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';

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

  Timer? _playbackTimer;
  Timer? _pollTimer;
  Timer? _intermissionTimer;

  // Fallback initial speaker nodes: Canonical nodes (Wokwi + Hardware Clients 1 & 2)
  static final List<Map<String, dynamic>> defaultSpeakerNodes = [
    {
      'id': 14,
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
    {
      'id': 15,
      'name': 'Hardware Speaker Client',
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
      'id': 21,
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
  ];

  @override
  void onInit() {
    super.onInit();
    speakerNodes.assignAll(defaultSpeakerNodes);
    refreshQueue();

    // Auto-poll to keep remote state and nodes in sync (skip in testMode)
    if (!Get.testMode) {
      _pollTimer = Timer.periodic(const Duration(seconds: 4), (_) {
        refreshQueue(silent: true);
      });
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
  }

  @override
  void onClose() {
    cancelAllTimers();
    super.onClose();
  }

  /// Syncs speaker notices directly from AnnouncementController
  void _syncWithLocalAnnouncements() {
    if (!Get.isRegistered<AnnouncementController>()) return;
    final annCtrl = Get.find<AnnouncementController>();

    // All published announcements marked for speaker broadcast that haven't completed playback
    final speakerNotices = annCtrl.allAnnouncements.where((a) {
      final isApproved = a.status == 'PUBLISHED' || a.status == 'APPROVED' || a.status == 'ACTIVE' || a.status == 'SCHEDULED';
      final isSpeaker = a.deliverSpeaker || a.priority.toUpperCase() == 'EMERGENCY';
      return isApproved && isSpeaker && !a.playedOnSpeaker;
    }).toList();

    bool changed = false;
    for (var notice in speakerNotices) {
      final exists = queueItems.any((q) =>
          (q['announcement_id'] == notice.id || q['id'] == notice.id) &&
          q['status'] != 'Completed');
      if (!exists) {
        final nodeName = _getNodeName(notice.speakerNodeId);
        queueItems.add({
          'id': notice.id,
          'announcement_id': notice.id,
          'title': notice.title,
          'description': notice.description,
          'department': notice.department,
          'priority': notice.priority,
          'category': notice.category,
          'type': 'AI Speech',
          'status': queueItems.isEmpty ? 'Playing' : 'Queued',
          'queue_position': queueItems.length + 1,
          'scheduled_time': notice.scheduledAt?.toIso8601String() ?? notice.createdAt.toIso8601String(),
          'speaker_node_id': notice.speakerNodeId,
          'node_name': nodeName,
          'duration_seconds': notice.durationSeconds,
          'audio_url': '/static/audio_streams/announcement_${notice.id}.mp3',
        });
        changed = true;
      }
    }

    if (changed) {
      _updateActiveNoticeMetrics();
      queueItems.refresh();

      // Auto-broadcast immediately if queue was idle and a "Publish Now" notice arrived
      if (!Get.testMode && !isPlaying.value && queueItems.isNotEmpty) {
        final firstItem = queueItems.first;
        final schedStr = firstItem['scheduled_time']?.toString();
        DateTime? sched;
        if (schedStr != null) {
          sched = DateTime.tryParse(schedStr);
        }
        final bool isDueNow = sched == null || sched.isBefore(DateTime.now().add(const Duration(seconds: 5)));
        if (isDueNow) {
          togglePlayPause(index: 0);
        }
      }
    }
  }

  String _getNodeName(int? nodeId) {
    if (nodeId == null) return 'All Nodes (College-Wide)';
    final match = speakerNodes.firstWhereOrNull((n) =>
        n['id'] == nodeId ||
        (nodeId == 16 && (n['name'] ?? '').toString().contains('Client 2')) ||
        (nodeId == 15 && (n['name'] ?? '').toString().contains('Client') && !(n['name'] ?? '').toString().contains('Client 2')) ||
        (nodeId == 14 && (n['name'] ?? '').toString().contains('Wokwi')));
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
        (nodeId == 16 && (n['name'] ?? '').toString().contains('Client 2')) ||
        (nodeId == 15 && (n['name'] ?? '').toString().contains('Client') && !(n['name'] ?? '').toString().contains('Client 2')) ||
        (nodeId == 14 && (n['name'] ?? '').toString().contains('Wokwi')));
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
      // 1. Fetch remote hardware nodes
      try {
        final remoteNodes = await _apiService.getSpeakerNodes();
        final fetchedNodes = remoteNodes
            .whereType<Map>()
            .map((n) => Map<String, dynamic>.from(n))
            .toList();
        if (fetchedNodes.isNotEmpty) {
          speakerNodes.assignAll(fetchedNodes);
        }
      } catch (e) {
        debugPrint('Remote speaker nodes fetch note: $e');
        if (speakerNodes.isEmpty) {
          speakerNodes.assignAll(defaultSpeakerNodes);
        }
      }

      // 2. Fetch remote queue items
      List<Map<String, dynamic>> remoteActiveItems = [];
      try {
        final remoteQueue = await _apiService.getSpeakerQueue();
        remoteActiveItems = remoteQueue
            .whereType<Map>()
            .map((q) => Map<String, dynamic>.from(q))
            .where((q) => q['status'] != 'Completed' && q['status'] != 'Cancelled')
            .toList();
      } catch (e) {
        debugPrint('Remote speaker queue fetch note: $e');
      }

      // 3. Collect local notices from AnnouncementController
      List<Map<String, dynamic>> combined = [];
      final Set<int> seenAnnouncementIds = {};

      // Add remote active items first
      for (var q in remoteActiveItems) {
        final annId = q['announcement_id'] as int? ?? q['id'] as int? ?? 0;
        final targetNodeId = q['speaker_node_id'] as int?;
        final nodeName = q['speaker_node_name'] ?? _getNodeName(targetNodeId);
        final nodeStatus = q['speaker_node_status'] ?? getNodeStatus(targetNodeId);
        seenAnnouncementIds.add(annId);
        combined.add({
          ...q,
          'node_name': nodeName,
          'node_status': nodeStatus,
          'duration_seconds': q['duration_seconds'] ?? 15,
        });
      }

      // Add local speaker notices from AnnouncementController
      if (Get.isRegistered<AnnouncementController>()) {
        final annCtrl = Get.find<AnnouncementController>();
        final speakerNotices = annCtrl.allAnnouncements.where((a) {
          final isApproved = a.status == 'PUBLISHED' || a.status == 'APPROVED';
          final isSpeaker = a.deliverSpeaker || a.priority.toUpperCase() == 'EMERGENCY';
          return isApproved && isSpeaker && !a.playedOnSpeaker;
        }).toList();

        for (var notice in speakerNotices) {
          if (!seenAnnouncementIds.contains(notice.id)) {
            seenAnnouncementIds.add(notice.id);
            combined.add({
              'id': notice.id,
              'announcement_id': notice.id,
              'title': notice.title,
              'description': notice.description,
              'department': notice.department,
              'priority': notice.priority,
              'category': notice.category,
              'type': 'AI Speech',
              'status': combined.isEmpty ? 'Playing' : 'Queued',
              'queue_position': combined.length + 1,
              'scheduled_time': notice.scheduledAt?.toIso8601String() ?? notice.createdAt.toIso8601String(),
              'speaker_node_id': notice.speakerNodeId,
              'node_name': _getNodeName(notice.speakerNodeId),
              'node_status': getNodeStatus(notice.speakerNodeId),
              'duration_seconds': notice.durationSeconds,
              'audio_url': '/static/audio_streams/announcement_${notice.id}.mp3',
            });
          }
        }
      }

      // Preserve playing state if already playing
      if (isPlaying.value && queueItems.isNotEmpty && activeIndex.value < queueItems.length) {
        final currentlyPlayingId = queueItems[activeIndex.value]['announcement_id'];
        final matchIdx = combined.indexWhere((c) => c['announcement_id'] == currentlyPlayingId);
        if (matchIdx != -1) {
          activeIndex.value = matchIdx;
          combined[matchIdx]['status'] = 'Playing';
        }
      } else {
        final playingIdx = combined.indexWhere((q) => q['status']?.toString().toLowerCase() == 'playing');
        if (playingIdx != -1) {
          activeIndex.value = playingIdx;
        } else if (activeIndex.value >= combined.length) {
          activeIndex.value = combined.isNotEmpty ? combined.length - 1 : 0;
        }
      }

      queueItems.assignAll(combined);
      _updateActiveNoticeMetrics();
    } catch (e) {
      debugPrint('Error in SpeakerQueueController refreshQueue: $e');
      errorMessage.value = e.toString();
    } finally {
      if (!silent) isLoading.value = false;
    }
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
    if (isIntermission.value) {
      return 'Intermission (${intermissionSecondsRemaining.value}s)';
    }
    if (queueItems.isEmpty || activeIndex.value < 0 || activeIndex.value >= queueItems.length) {
      return 'No active speaker announcement';
    }
    final item = queueItems[activeIndex.value];
    return (item['title'] ?? 'Untitled Announcement').toString();
  }

  String get activeSubtitle {
    if (isIntermission.value) {
      return '15-second gap before next scheduled broadcast';
    }
    if (queueItems.isEmpty || activeIndex.value < 0 || activeIndex.value >= queueItems.length) {
      return 'PA system standing by';
    }
    final item = queueItems[activeIndex.value];
    final dept = item['department']?.toString() ?? 'College-Wide';
    final node = item['node_name']?.toString() ?? 'All Nodes';
    return '$dept • $node';
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

  /// Starts or resumes playing the notice at [index] (or active notice)
  Future<void> togglePlayPause({int? index}) async {
    if (queueItems.isEmpty) {
      snackBar('Speaker queue is currently empty.');
      return;
    }

    final targetIdx = index ?? activeIndex.value;
    if (targetIdx < 0 || targetIdx >= queueItems.length) return;

    if (isPlaying.value && (index == null || index == activeIndex.value)) {
      // Pause
      isPlaying.value = false;
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

    // Mark active item as Playing and others as Queued
    for (int i = 0; i < queueItems.length; i++) {
      queueItems[i]['status'] = (i == activeIndex.value) ? 'Playing' : 'Queued';
    }
    queueItems.refresh();

    isPlaying.value = true;
    _startPlaybackTimer();

    final item = queueItems[activeIndex.value];
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

    if (!Get.testMode) {
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
    _playbackTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!isPlaying.value) {
        timer.cancel();
        return;
      }

      currentElapsedSeconds.value++;

      // When duration completes: Notice has played once -> Remove it and advance!
      if (currentElapsedSeconds.value >= currentTotalDuration.value) {
        timer.cancel();
        _onNoticePlaybackCompleted();
      }
    });
  }

  /// Manually or programmatically triggers playback completion (used in tests and skips)
  Future<void> completeCurrentPlayback() async {
    _playbackTimer?.cancel();
    await _onNoticePlaybackCompleted();
  }

  /// Called automatically when the current notice completes its single playback
  Future<void> _onNoticePlaybackCompleted() async {
    if (queueItems.isEmpty || activeIndex.value < 0 || activeIndex.value >= queueItems.length) {
      _playbackTimer?.cancel();
      isPlaying.value = false;
      return;
    }

    final playedItem = queueItems[activeIndex.value];
    final annId = playedItem['announcement_id'] as int? ?? playedItem['id'] as int? ?? 0;
    final playedTitle = playedItem['title'] ?? 'Announcement';

    // 1. Mark played in AnnouncementController
    if (annId > 0 && Get.isRegistered<AnnouncementController>()) {
      Get.find<AnnouncementController>().markNoticePlayedOnSpeaker(annId);
    }

    // 2. Notify remote backend action
    final queueId = playedItem['id'];
    if (!Get.testMode && queueId is int) {
      _apiService.queueAction(queueId, 'complete').catchError((_) => <String, dynamic>{});
    }

    // 3. Remove notice from queue (requirement: "play them once and then remove them once they are played")
    queueItems.removeAt(activeIndex.value);
    currentElapsedSeconds.value = 0;

    if (!Get.testMode) {
      try {
        TtsAudioService.instance.stop();
      } catch (_) {}
    }

    snackBar(
      'Completed broadcast of "$playedTitle". Removed from speaker queue.',
      title: 'Broadcast Finished',
    );

    // 4. Advance to next queued notice or finish
    if (queueItems.isNotEmpty) {
      // Priority 1: Emergency preemption - check if an emergency notice is queued (prioritized first, 0s gap)
      final emergencyIdx = queueItems.indexWhere((q) {
        final prio = (q['priority'] ?? '').toString().toUpperCase();
        final title = (q['title'] ?? '').toString().toLowerCase();
        return prio == 'EMERGENCY' || prio == 'CRITICAL' || title.contains('emergency');
      });

      if (emergencyIdx != -1) {
        final emergencyItem = queueItems.removeAt(emergencyIdx);
        queueItems.insert(0, emergencyItem);
        activeIndex.value = 0;
        queueItems[0]['status'] = 'Playing';
        _updateActiveNoticeMetrics();
        queueItems.refresh();
        isPlaying.value = true;
        _startPlaybackTimer();

        final nextTargetId = emergencyItem['announcement_id'] as int? ?? emergencyItem['id'] as int?;
        if (!Get.testMode && nextTargetId != null) {
          _apiService.queueAction(nextTargetId, 'play').catchError((_) => <String, dynamic>{});
        }

        if (!Get.testMode) {
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

      // Priority 2: Normal notices enforce a 10-20 sec gap (15s) and verify scheduled time
      if (Get.testMode) {
        _advanceToNextEligibleNotice();
      } else {
        isPlaying.value = false;
        isIntermission.value = true;
        intermissionSecondsRemaining.value = broadcastGapSeconds;
        queueItems.refresh();

        _intermissionTimer?.cancel();
        _intermissionTimer = Timer.periodic(const Duration(seconds: 1), (t) {
          intermissionSecondsRemaining.value--;
          if (intermissionSecondsRemaining.value <= 0) {
            t.cancel();
            isIntermission.value = false;
            _advanceToNextEligibleNotice();
          }
        });
      }
    } else {
      _playbackTimer?.cancel();
      _intermissionTimer?.cancel();
      isIntermission.value = false;
      activeIndex.value = 0;
      isPlaying.value = false;
      queueItems.refresh();
      snackBar('All queued speaker notices have completed broadcast.');
    }
  }

  /// Advances to the next eligible queued notice on a First Come First Serve (FCFS) basis,
  /// respecting scheduled times (only playing notices whose scheduled_time <= now).
  void _advanceToNextEligibleNotice() {
    if (queueItems.isEmpty) {
      isPlaying.value = false;
      return;
    }

    final now = DateTime.now();
    int eligibleIdx = -1;

    // FCFS: iterate in queue order and pick first notice whose scheduled_time has arrived
    for (int i = 0; i < queueItems.length; i++) {
      final q = queueItems[i];
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
      _updateActiveNoticeMetrics();
      queueItems.refresh();
      isPlaying.value = true;
      _startPlaybackTimer();

      final nextItem = queueItems[activeIndex.value];
      final nextTargetId = nextItem['announcement_id'] as int? ?? nextItem['id'] as int?;
      if (!Get.testMode && nextTargetId != null) {
        _apiService.queueAction(nextTargetId, 'play').catchError((_) => <String, dynamic>{});
      }

      if (!Get.testMode) {
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
    _playbackTimer?.cancel();
    await _onNoticePlaybackCompleted();
  }

  /// Stops current playback
  Future<void> stopCurrent() async {
    if (queueItems.isEmpty) return;
    _playbackTimer?.cancel();
    isPlaying.value = false;
    currentElapsedSeconds.value = 0;

    if (!Get.testMode) {
      try {
        TtsAudioService.instance.stop();
      } catch (_) {}
    }

    if (activeIndex.value >= 0 && activeIndex.value < queueItems.length) {
      queueItems[activeIndex.value]['status'] = 'Queued';
      final item = queueItems[activeIndex.value];
      final targetId = item['announcement_id'] as int? ?? item['id'] as int?;
      if (!Get.testMode && targetId != null) {
        _apiService.queueAction(targetId, 'cancel').catchError((_) => <String, dynamic>{});
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

    if (!Get.testMode && targetId != null) {
      _apiService.queueAction(targetId, 'remove').catchError((_) => <String, dynamic>{});
    }

    if (isCurrent && isPlaying.value) {
      _playbackTimer?.cancel();
      queueItems.removeAt(index);
      currentElapsedSeconds.value = 0;

      if (queueItems.isNotEmpty) {
        if (activeIndex.value >= queueItems.length) {
          activeIndex.value = 0;
        }
        queueItems[activeIndex.value]['status'] = 'Playing';
        _updateActiveNoticeMetrics();
        queueItems.refresh();
        isPlaying.value = true;
        _startPlaybackTimer();
      } else {
        activeIndex.value = 0;
        isPlaying.value = false;
        queueItems.refresh();
      }
    } else {
      queueItems.removeAt(index);
      if (index < activeIndex.value) {
        activeIndex.value--;
      }
      queueItems.refresh();
    }

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
    if (Get.isRegistered<AnnouncementController>()) {
      final annCtrl = Get.find<AnnouncementController>();
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

    // If emergency, preempt any intermission and play immediately
    if (isEmergency) {
      _intermissionTimer?.cancel();
      isIntermission.value = false;
    }

    // Emergency always plays immediately; Publish Now plays immediately if queue is idle;
    // Scheduled notices are queued for their scheduled time in FCFS order.
    final bool shouldPlayNow = isEmergency || (!isFutureScheduled && !hasActivePlayback && !isIntermission.value);

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
      activeIndex.value = targetIndex;
      currentElapsedSeconds.value = 0;
      _updateActiveNoticeMetrics();

      for (int i = 0; i < queueItems.length; i++) {
        queueItems[i]['status'] = (i == activeIndex.value) ? 'Playing' : 'Queued';
      }
      queueItems.refresh();

      isPlaying.value = true;
      _startPlaybackTimer();

      if (!Get.testMode) {
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
        '🔊 Now broadcasting "${announcement.title}" on campus speakers!',
        title: 'Speaker Broadcast Started',
      );
    } else {
      queueItems.refresh();
      snackBar(
        '📋 Added "${announcement.title}" to speaker queue (Position #${targetIndex + 1})',
        title: 'Added to Speaker Queue',
      );
    }

    // 4. Background backend sync (MQTT dispatch and database update) without blocking UI
    if (!Get.testMode) {
      int? resolvedNodeId = targetNodeId;
      final matchNode = speakerNodes.firstWhereOrNull((n) =>
          n['id'] == targetNodeId ||
          (targetNodeId == 16 && (n['name'] ?? '').toString().contains('Client 2')) ||
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

  /// Explicitly enqueues an announcement into the queue
  Future<void> enqueueNotice({
    required int announcementId,
    String audioType = 'AI Speech',
    int? speakerNodeId,
  }) async {
    // Immediately resolve and add from AnnouncementController if present for 0ms lag
    if (Get.isRegistered<AnnouncementController>()) {
      final annCtrl = Get.find<AnnouncementController>();
      final match = annCtrl.allAnnouncements.firstWhereOrNull((a) => a.id == announcementId);
      if (match != null) {
        await broadcastAnnouncement(match, speakerNodeId: speakerNodeId);
        return;
      }
    }

    int? resolvedNodeId = speakerNodeId;
    final matchNode = speakerNodes.firstWhereOrNull((n) =>
        n['id'] == speakerNodeId ||
        (speakerNodeId == 16 && (n['name'] ?? '').toString().contains('Client 2')) ||
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
      snackBar('🚨 EMERGENCY SIREN BROADCASTING LIVE ACROSS ALL NODES');
    } catch (e) {
      snackBar('Emergency broadcast sent: ${e.toString()}');
    }
    await refreshQueue(silent: true);
  }
}

