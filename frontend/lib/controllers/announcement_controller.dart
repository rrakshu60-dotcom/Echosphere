import 'dart:async';
import 'dart:convert';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/services/calendar_sync_service.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/services/echosphere_realtime_service.dart';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AnnouncementModel {
  final int id;
  final String title;
  final String description;
  final String priority; // EMERGENCY, HIGH, NORMAL, LOW
  final String emergencyLevel;
  final String status; // DRAFT, SUBMITTED, APPROVED, REJECTED, PUBLISHED, ARCHIVED, SCHEDULED
  final String creatorName;
  final String creatorRole;
  final String department;
  final String targetAudience;
  final String category;
  final DateTime createdAt;
  final DateTime? scheduledAt;
  final String? aiSummary;
  final String? remarks;
  final String? approverName;
  final DateTime? approvedAt;
  final List<String> attachments;
  final bool deliverSpeaker;
  final bool deliverInApp;
  final bool deliverPush;
  final int? speakerNodeId;
  final String? speakerStatus;
  final bool playedOnSpeaker;
  final int durationSeconds;
  final String speakerVoice; // 'female' | 'male'
  final Map<String, dynamic>? repeatSchedule;

  static String sanitizeText(String input) {
    if (input.isEmpty) return input;
    return input
        .replaceAll('\u00E2\u20AC\u00A2', '\u2022') // bullet -> •
        .replaceAll('\u00E2\u201A\u00B9', '\u20B9') // rupee -> ₹
        .replaceAll('\u00C2\u00B7', '\u2022')         // middle dot -> •
        .replaceAll('\u00C2', '')                     // stray A
        .replaceAll('\u00E2\u20AC\u201D', '\u2014') // em-dash -> —
        .replaceAll('\u00E2\u20AC\u2013', '\u2013') // en-dash -> –
        .replaceAll('\u00E2\u2020\u2019', '\u2192') // right arrow -> →
        .replaceAll('\u00E2\u20AC\u00A6', '...')     // ellipsis -> ...
        .replaceAll('\u00E2\u20AC\u02DC', "'")       // single quote
        .replaceAll('\u00E2\u20AC\u2122', "'")       // single quote
        .replaceAll('\u00E2\u20AC\u0153', '"')       // double quote
        .replaceAll('\u00E2\u20AC\u009D', '"');      // double quote
  }

  AnnouncementModel({
    required this.id,
    required String title,
    required String description,
    required this.priority,
    required this.emergencyLevel,
    required this.status,
    required String creatorName,
    String creatorRole = 'Faculty / Official',
    required String department,
    String targetAudience = 'Entire College',
    required this.category,
    required this.createdAt,
    this.scheduledAt,
    String? aiSummary,
    this.remarks,
    this.approverName,
    this.approvedAt,
    this.attachments = const [],
    this.deliverSpeaker = false,
    this.deliverInApp = true,
    this.deliverPush = true,
    this.speakerNodeId,
    this.speakerStatus,
    this.playedOnSpeaker = false,
    this.durationSeconds = 15,
    this.speakerVoice = 'female',
    this.repeatSchedule,
  })  : title = sanitizeText(title),
        description = sanitizeText(description),
        creatorName = sanitizeText(creatorName),
        creatorRole = sanitizeText(creatorRole),
        department = sanitizeText(department),
        targetAudience = sanitizeText(targetAudience),
        aiSummary = aiSummary != null ? sanitizeText(aiSummary) : null;

  AnnouncementModel copyWith({
    int? id,
    String? title,
    String? description,
    String? priority,
    String? emergencyLevel,
    String? status,
    String? creatorName,
    String? creatorRole,
    String? department,
    String? targetAudience,
    String? category,
    DateTime? createdAt,
    DateTime? scheduledAt,
    String? aiSummary,
    String? remarks,
    String? approverName,
    DateTime? approvedAt,
    List<String>? attachments,
    bool? deliverSpeaker,
    bool? deliverInApp,
    bool? deliverPush,
    int? speakerNodeId,
    String? speakerStatus,
    bool? playedOnSpeaker,
    int? durationSeconds,
    String? speakerVoice,
    Map<String, dynamic>? repeatSchedule,
  }) {
    return AnnouncementModel(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      priority: priority ?? this.priority,
      emergencyLevel: emergencyLevel ?? this.emergencyLevel,
      status: status ?? this.status,
      creatorName: creatorName ?? this.creatorName,
      creatorRole: creatorRole ?? this.creatorRole,
      department: department ?? this.department,
      targetAudience: targetAudience ?? this.targetAudience,
      category: category ?? this.category,
      createdAt: createdAt ?? this.createdAt,
      scheduledAt: scheduledAt ?? this.scheduledAt,
      aiSummary: aiSummary ?? this.aiSummary,
      remarks: remarks ?? this.remarks,
      approverName: approverName ?? this.approverName,
      approvedAt: approvedAt ?? this.approvedAt,
      attachments: attachments ?? this.attachments,
      deliverSpeaker: deliverSpeaker ?? this.deliverSpeaker,
      deliverInApp: deliverInApp ?? this.deliverInApp,
      deliverPush: deliverPush ?? this.deliverPush,
      speakerNodeId: speakerNodeId ?? this.speakerNodeId,
      speakerStatus: speakerStatus ?? this.speakerStatus,
      playedOnSpeaker: playedOnSpeaker ?? this.playedOnSpeaker,
      durationSeconds: durationSeconds ?? this.durationSeconds,
      speakerVoice: speakerVoice ?? this.speakerVoice,
      repeatSchedule: repeatSchedule ?? this.repeatSchedule,
    );
  }

  static String _normalizeStatus(dynamic raw) {
    if (raw == null) return 'PUBLISHED';
    final s = raw.toString().trim().toUpperCase().replaceAll(' ', '_');
    if (s == 'PENDING_APPROVAL' || s == 'PENDING' || s == 'SUBMITTED' || s == 'DRAFT') {
      return 'PENDING_APPROVAL';
    }
    if (s == 'PUBLISHED' || s == 'APPROVED') {
      return 'PUBLISHED';
    }
    if (s == 'REJECTED') {
      return 'REJECTED';
    }
    if (s == 'ARCHIVED') {
      return 'ARCHIVED';
    }
    if (s == 'SCHEDULED') {
      return 'SCHEDULED';
    }
    return s;
  }

  factory AnnouncementModel.fromJson(Map<String, dynamic> json) {
    final catId = json['category_id'] ?? 1;
    String catName = 'Academic';
    if (catId == 2) catName = 'Examination';
    if (catId == 3) catName = 'Placement';
    if (catId == 4) catName = 'Event';
    if (catId == 5) catName = 'Workshop';
    if (catId == 6) catName = 'Seminar';
    if (catId == 7) catName = 'Holiday';
    if (catId == 8) catName = 'Sports';
    if (catId == 9) catName = 'Cultural';
    if (catId == 10) catName = 'Club Activities';
    if (catId == 11) catName = 'General';
    if (catId == 12) catName = 'Emergency';
    if (catId == 13) catName = 'Circular';
    if (catId == 14) catName = 'Fee Payment';

    final bool delivSpk = json['deliver_speaker'] == true || json['deliverSpeaker'] == true;
    final bool delivInApp = json['deliver_in_app'] != null
        ? json['deliver_in_app'] == true
        : (json['deliverInApp'] != null ? json['deliverInApp'] == true : true);
    final bool delivPush = json['deliver_push'] != null
        ? json['deliver_push'] == true
        : (json['deliverPush'] != null ? json['deliverPush'] == true : true);

    return AnnouncementModel(
      id: json['id'] ?? 0,
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      priority: (json['priority'] ?? 'NORMAL').toString().toUpperCase(),
      emergencyLevel: (json['emergency_level'] ?? 'NORMAL').toString().toUpperCase(),
      status: _normalizeStatus(json['status']),
      creatorName: json['creator_name'] ?? 'Faculty',
      creatorRole: json['creator_role'] ?? json['creator_designation'] ?? json['designation'] ?? json['role'] ?? 'Faculty / Official',
      department: json['department_name'] ?? json['department'] ?? 'AIML',
      targetAudience: json['target_audience'] ?? 'Entire College',
      category: json['category_name'] ?? catName,
      createdAt: json['created_at'] != null
          ? (DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now())
          : DateTime.now(),
      scheduledAt: json['scheduled_at'] != null
          ? DateTime.tryParse(json['scheduled_at'].toString())
          : null,
      aiSummary: json['ai_summary'],
      remarks: json['remarks'],
      approverName: json['approver_name'],
      approvedAt: json['approved_at'] != null
          ? DateTime.tryParse(json['approved_at'].toString())
          : null,
      attachments: json['attachments'] != null
          ? List<String>.from(json['attachments'])
          : const [],
      deliverSpeaker: delivSpk,
      deliverInApp: delivInApp,
      deliverPush: delivPush,
      speakerNodeId: json['speaker_node_id'] ?? json['speakerNodeId'],
      speakerStatus: json['speaker_status'] ?? json['speakerStatus'] ?? (delivSpk ? 'Queued' : null),
      playedOnSpeaker: json['played_on_speaker'] == true || json['playedOnSpeaker'] == true,
      durationSeconds: json['duration_seconds'] ?? json['durationSeconds'] ?? 15,
      speakerVoice: (json['speaker_voice'] ?? json['speakerVoice'] ?? 'female').toString().toLowerCase() == 'male' ? 'male' : 'female',
      repeatSchedule: json['repeat_schedule'] != null && json['repeat_schedule'] is Map
          ? Map<String, dynamic>.from(json['repeat_schedule'] as Map)
          : (json['repeatSchedule'] != null && json['repeatSchedule'] is Map
              ? Map<String, dynamic>.from(json['repeatSchedule'] as Map)
              : null),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'priority': priority,
      'emergency_level': emergencyLevel,
      'status': status,
      'creator_name': creatorName,
      'creator_role': creatorRole,
      'department_name': department,
      'target_audience': targetAudience,
      'category_name': category,
      'created_at': createdAt.toIso8601String(),
      'scheduled_at': scheduledAt?.toIso8601String(),
      'ai_summary': aiSummary,
      'remarks': remarks,
      'approver_name': approverName,
      'approved_at': approvedAt?.toIso8601String(),
      'attachments': attachments,
      'deliver_speaker': deliverSpeaker,
      'deliver_in_app': deliverInApp,
      'deliver_push': deliverPush,
      'speaker_node_id': speakerNodeId,
      'speaker_status': speakerStatus,
      'played_on_speaker': playedOnSpeaker,
      'duration_seconds': durationSeconds,
      'speaker_voice': speakerVoice,
      'repeat_schedule': repeatSchedule,
    };
  }
}

class AnnouncementController extends GetxController {
  final RxList<AnnouncementModel> _rawAnnouncements = <AnnouncementModel>[].obs;
  RxList<AnnouncementModel> get rxAnnouncements => _rawAnnouncements;
  final RxString selectedCategory = 'All'.obs;
  final RxString selectedPriority = 'All'.obs;
  final RxString searchQuery = ''.obs;
  final RxBool showTodayOnly = false.obs;
  final RxBool showForYouOnly = false.obs;
  final RxBool showBookmarkedOnly = false.obs;
  final RxSet<int> bookmarkedNoticeIds = <int>{}.obs;
  final RxBool isLoading = false.obs;
  final RxString sortBy = 'Newest First'.obs;
  final RxMap<int, CalendarEventData> calendarEvents = <int, CalendarEventData>{}.obs;
  final RxMap<int, Map<String, dynamic>> relevanceScores = <int, Map<String, dynamic>>{}.obs;
  static int _idCounter = 0;
  int? lastCreatedAnnouncementId;

  bool isBookmarked(int id) => bookmarkedNoticeIds.contains(id);

  Future<void> toggleBookmark(int id) async {
    if (bookmarkedNoticeIds.contains(id)) {
      bookmarkedNoticeIds.remove(id);
    } else {
      bookmarkedNoticeIds.add(id);
    }
    bookmarkedNoticeIds.refresh();
    update();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList(
        'echosphere_bookmarked_ids',
        bookmarkedNoticeIds.map((e) => e.toString()).toList(),
      );
    } catch (_) {}
  }

  Map<String, dynamic> getRelevanceFor(AnnouncementModel notice) {
    if (relevanceScores.containsKey(notice.id)) {
      return relevanceScores[notice.id]!;
    }

    EchosphereUser? user;
    if (Get.isRegistered<AuthController>()) {
      user = Get.find<AuthController>().currentUser.value;
    }

    final userProfile = {
      'role': user?.role ?? 'Student',
      'department': user?.department ?? 'AIML',
      'semester': user?.semester ?? 5,
      'usn': user?.usn,
    };

    final noticeData = {
      'id': notice.id,
      'title': notice.title,
      'description': notice.description,
      'department': notice.department,
      'target_audience': notice.targetAudience,
      'category': notice.category,
      'priority': notice.priority,
      'emergency_level': notice.emergencyLevel,
      'created_at': notice.createdAt.toIso8601String(),
    };

    final scores = EchosphereApiService().calculateRelevanceFallback(userProfile, [noticeData]);
    final res = scores.isNotEmpty
        ? scores.first
        : {
            'announcement_id': notice.id,
            'score': 0.5,
            'is_highly_relevant': false,
            'reasons': <String>[],
          };

    relevanceScores[notice.id] = res;
    return res;
  }

  Future<void> updateAllRelevanceScores() async {
    if (!Get.isRegistered<AuthController>()) return;
    final user = Get.find<AuthController>().currentUser.value;
    final userProfile = {
      'role': user?.role ?? 'Student',
      'department': user?.department ?? 'AIML',
      'semester': user?.semester ?? 5,
      'usn': user?.usn,
    };

    final noticesData = _rawAnnouncements.map((n) => {
      'id': n.id,
      'title': n.title,
      'description': n.description,
      'department': n.department,
      'target_audience': n.targetAudience,
      'category': n.category,
      'priority': n.priority,
      'emergency_level': n.emergencyLevel,
      'created_at': n.createdAt.toIso8601String(),
    }).toList();

    try {
      final scores = Get.testMode
          ? EchosphereApiService().calculateRelevanceFallback(userProfile, noticesData)
          : await EchosphereApiService().getNoticeRelevanceScores(
              userProfile: userProfile,
              announcements: noticesData,
            );
      for (var s in scores) {
        final id = s['announcement_id'] as int? ?? 0;
        if (id > 0) {
          relevanceScores[id] = s;
        }
      }
      relevanceScores.refresh();
      update();
    } catch (_) {}
  }

  void toggleForYouOnly() {
    showForYouOnly.value = !showForYouOnly.value;
    if (showForYouOnly.value) {
      showTodayOnly.value = false;
      selectedCategory.value = 'All';
    }
  }

  Future<CalendarEventData?> getOrFetchCalendarEvent(AnnouncementModel notice) async {
    if (calendarEvents.containsKey(notice.id)) {
      return calendarEvents[notice.id];
    }
    final ev = await EchosphereApiService().getAnnouncementCalendarEvent(
      notice.id,
      title: notice.title,
      content: notice.description,
    );
    if (ev != null) {
      calendarEvents[notice.id] = ev;
    }
    return ev;
  }

  static const List<String> sortOptions = [
    'Newest First',
    'Most Relevant',
    'Oldest First',
    'Highest Priority',
    'Lowest Priority',
    'Title (A-Z)',
    'Title (Z-A)',
  ];

  static const List<String> categories = [
    'All',
    'Academic',
    'Examination',
    'Placement',
    'Event',
    'Workshop',
    'Seminar',
    'Holiday',
    'Sports',
    'Cultural',
    'Club Activities',
    'Circular',
    'Emergency',
    'Fee Payment',
    'General',
  ];

  StreamSubscription<EchosphereRealtimeEvent>? _realtimeSubscription;
  Timer? _periodicSyncTimer;

  final Set<int> _persistedApprovedIds = <int>{};
  final Set<int> _persistedRejectedIds = <int>{};
  final Set<int> playedSpeakerNoticeIds = <int>{};

  Future<void> _loadPersistedPlayedSpeakerNotices() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final list = prefs.getStringList('echosphere_played_speaker_notice_ids') ?? [];
      playedSpeakerNoticeIds.addAll(list.map((e) => int.tryParse(e)).whereType<int>());
    } catch (_) {}
  }

  Future<void> _savePersistedPlayedSpeakerNotices() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList(
        'echosphere_played_speaker_notice_ids',
        playedSpeakerNoticeIds.map((e) => e.toString()).toList(),
      );
    } catch (_) {}
  }

  Future<void> _loadPersistedApprovalStatus() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final approvedList = prefs.getStringList('echosphere_approved_notice_ids') ?? [];
      final rejectedList = prefs.getStringList('echosphere_rejected_notice_ids') ?? [];
      _persistedApprovedIds.clear();
      _persistedApprovedIds.addAll(approvedList.map((e) => int.tryParse(e)).whereType<int>());
      _persistedRejectedIds.clear();
      _persistedRejectedIds.addAll(rejectedList.map((e) => int.tryParse(e)).whereType<int>());
    } catch (_) {}
  }

  Future<void> _recordApprovedNoticeId(int id) async {
    _persistedApprovedIds.add(id);
    _persistedRejectedIds.remove(id);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList(
        'echosphere_approved_notice_ids',
        _persistedApprovedIds.map((e) => e.toString()).toList(),
      );
    } catch (_) {}
  }

  Future<void> _recordRejectedNoticeId(int id) async {
    _persistedRejectedIds.add(id);
    _persistedApprovedIds.remove(id);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList(
        'echosphere_rejected_notice_ids',
        _persistedRejectedIds.map((e) => e.toString()).toList(),
      );
    } catch (_) {}
  }

  Future<void> _loadPersistentCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cachedJson = prefs.getString('echosphere_cached_announcements');
      if (cachedJson != null && cachedJson.isNotEmpty) {
        final decoded = jsonDecode(cachedJson);
        if (decoded is List && decoded.isNotEmpty) {
          final cachedList = decoded
              .map((e) => AnnouncementModel.fromJson(e as Map<String, dynamic>))
              .toList();
          // Filter out any legacy sample / placeholder announcements
          cachedList.removeWhere((a) =>
              a.title.contains('Proctor Mentorship') ||
              a.title.contains('Open Elective') ||
              a.title.contains('NBA') ||
              a.title.contains('Mock Interview') ||
              a.title.contains('Welcome to EchoSphere') ||
              a.title.toLowerCase().contains('automated speaker notice') ||
              a.title.toLowerCase().contains('sample notice'));
          if (cachedList.isNotEmpty) {
            _rawAnnouncements.value = cachedList;
            _rawAnnouncements.refresh();
            update();
          } else {
            prefs.remove('echosphere_cached_announcements');
          }
        }
      }
      final savedBookmarks = prefs.getStringList('echosphere_bookmarked_ids');
      if (savedBookmarks != null && savedBookmarks.isNotEmpty) {
        bookmarkedNoticeIds.clear();
        bookmarkedNoticeIds.addAll(savedBookmarks.map((e) => int.tryParse(e)).whereType<int>());
      }
    } catch (_) {}
  }

  Future<void> _savePersistentCache(List<AnnouncementModel> list) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final encoded = jsonEncode(list.take(40).map((e) => e.toJson()).toList());
      await prefs.setString('echosphere_cached_announcements', encoded);
    } catch (_) {}
  }

  /// Clears persisted approval/rejection IDs so fresh server state is used on next login.
  Future<void> clearPersistedApprovalCache() async {
    _persistedApprovedIds.clear();
    _persistedRejectedIds.clear();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('echosphere_approved_notice_ids');
      await prefs.remove('echosphere_rejected_notice_ids');
      await prefs.remove('echosphere_cached_announcements');
    } catch (_) {}
  }

  @override
  void onInit() {
    super.onInit();
    _loadPersistedPlayedSpeakerNotices();
    _loadPersistedApprovalStatus();
    _loadPersistentCache();
    if (!Get.testMode) {
      _initRealtimeSync();
      fetchAnnouncements();
      _startPeriodicSync();
    }
  }

  @override
  void onClose() {
    _realtimeSubscription?.cancel();
    _periodicSyncTimer?.cancel();
    super.onClose();
  }

  void _initRealtimeSync() {
    final realtimeService = EchosphereRealtimeService();
    realtimeService.initialize();
    _realtimeSubscription?.cancel();
    _realtimeSubscription = realtimeService.events.listen((event) {
      debugPrint('[LiveSync] Event in AnnouncementController: ${event.event} (#${event.announcementId})');
      _handleLiveEvent(event);
    });
  }

  void _startPeriodicSync() {
    _periodicSyncTimer?.cancel();
    _periodicSyncTimer = Timer.periodic(const Duration(seconds: 7), (_) {
      _silentApprovalQueueSync();
    });
  }

  void _handleLiveEvent(EchosphereRealtimeEvent event) {
    if (event.announcementId == null) return;
    final id = event.announcementId!;

    if (event.event == 'ANNOUNCEMENT_APPROVED') {
      final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
      if (idx != -1) {
        final old = _rawAnnouncements[idx];
        _rawAnnouncements[idx] = old.copyWith(
          status: 'PUBLISHED',
          remarks: event.remarks ?? 'Approved for college-wide publication',
          approverName: event.approverName ?? 'HoD / Administrator',
          approvedAt: DateTime.now(),
        );
        _rawAnnouncements.refresh();
        update();
      } else {
        _silentApprovalQueueSync();
      }
    } else if (event.event == 'ANNOUNCEMENT_REJECTED') {
      final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
      if (idx != -1) {
        final old = _rawAnnouncements[idx];
        _rawAnnouncements[idx] = old.copyWith(
          status: 'REJECTED',
          remarks: event.remarks ?? 'Rejected by Approver',
          approverName: event.approverName ?? 'HoD / Administrator',
          approvedAt: DateTime.now(),
        );
        _rawAnnouncements.refresh();
        update();
      } else {
        _silentApprovalQueueSync();
      }
    } else if (event.event == 'ANNOUNCEMENT_CREATED' || event.event == 'ANNOUNCEMENT_PUBLISHED') {
      fetchAnnouncements();
    } else if (event.event == 'ANNOUNCEMENT_DELETED') {
      _rawAnnouncements.removeWhere((a) => a.id == id);
      _rawAnnouncements.refresh();
      update();
    }
  }

  Future<void> _silentApprovalQueueSync() async {
    try {
      final api = EchosphereApiService();
      final queueData = await api.getApprovalQueue();
      if (queueData.isNotEmpty) {
        bool changed = false;
        final currentList = _rawAnnouncements.toList();
        for (var item in queueData) {
          final model = AnnouncementModel.fromJson(item as Map<String, dynamic>);
          final idx = currentList.indexWhere((a) => a.id == model.id);
          if (idx != -1) {
            if (currentList[idx].status != model.status ||
                currentList[idx].remarks != model.remarks) {
              currentList[idx] = model;
              changed = true;
            }
          } else {
            currentList.insert(0, model);
            changed = true;
          }
        }
        if (changed) {
          _rawAnnouncements.value = currentList;
          _rawAnnouncements.refresh();
          update();
        }
      }
    } catch (_) {}
  }

  int _priorityRank(String priority, String emergencyLevel) {
    final p = priority.toUpperCase();
    final e = emergencyLevel.toUpperCase();
    if (p == 'EMERGENCY' || e == 'CRITICAL') return 4;
    if (p == 'HIGH' || p == 'URGENT') return 3;
    if (p == 'NORMAL') return 2;
    return 1;
  }

  List<AnnouncementModel> _applySort(List<AnnouncementModel> list) {
    final sorted = List<AnnouncementModel>.from(list);
    switch (sortBy.value) {
      case 'Oldest First':
        sorted.sort((a, b) => a.createdAt.compareTo(b.createdAt));
        break;
      case 'Highest Priority':
        sorted.sort((a, b) {
          final rankA = _priorityRank(a.priority, a.emergencyLevel);
          final rankB = _priorityRank(b.priority, b.emergencyLevel);
          if (rankA != rankB) return rankB.compareTo(rankA);
          return b.createdAt.compareTo(a.createdAt);
        });
        break;
      case 'Lowest Priority':
        sorted.sort((a, b) {
          final rankA = _priorityRank(a.priority, a.emergencyLevel);
          final rankB = _priorityRank(b.priority, b.emergencyLevel);
          if (rankA != rankB) return rankA.compareTo(rankB);
          return b.createdAt.compareTo(a.createdAt);
        });
        break;
      case 'Title (A-Z)':
        sorted.sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
        break;
      case 'Title (Z-A)':
        sorted.sort((a, b) => b.title.toLowerCase().compareTo(a.title.toLowerCase()));
        break;
      case 'Most Relevant':
        sorted.sort((a, b) {
          final scoreA = (getRelevanceFor(a)['score'] as num?)?.toDouble() ?? 0.0;
          final scoreB = (getRelevanceFor(b)['score'] as num?)?.toDouble() ?? 0.0;
          if (scoreA != scoreB) return scoreB.compareTo(scoreA);
          return b.createdAt.compareTo(a.createdAt);
        });
        break;
      case 'Newest First':
      default:
        sorted.sort((a, b) => b.createdAt.compareTo(a.createdAt));
        break;
    }
    return sorted;
  }

  // Active announcements restricted strictly to approved/published notices within the current week (past 7 days)
  List<AnnouncementModel> get announcements {
    final now = DateTime.now();
    final authController = Get.find<AuthController>();
    final user = authController.currentUser.value;
    final role = user?.role ?? 'Student';
    final userDept = (user?.department ?? 'AIML').trim().toLowerCase();
    final semester = user?.semester ?? 5;

    final filtered = _rawAnnouncements.where((a) {
      final diffDays = now.difference(a.createdAt).inDays;

      final isScheduledDue = a.status == 'SCHEDULED' &&
          a.scheduledAt != null &&
          !a.scheduledAt!.isAfter(now);

      final isApproved = a.status == 'PUBLISHED' ||
          a.status == 'APPROVED' ||
          isScheduledDue;

      if (diffDays > 7 || !isApproved) return false;

      // Staff/Faculty roles (Teacher, HoD, Principal, College Admin, Dev Admin)
      // MUST see ALL notices (including student-targeted notices)!
      if (role != 'Student') return true;

      // Student Role Audience Filter
      final target = a.targetAudience.trim().toLowerCase();

      // 1. Entire College or Faculty & Staff
      if (target.contains('entire') || target.contains('all')) return true;

      // 2. Department Specific (e.g. 'AIML Department', 'CSE Department')
      if (target.contains('department') || target.contains('dept')) {
        if (!target.contains(userDept)) return false;
      }

      // 3. Year Specific Calculation from Semester (Each year has 2 semesters: Sems 1-8)
      int studentYear = 1;
      if (semester >= 1 && semester <= 2) {
        studentYear = 1;
      } else if (semester >= 3 && semester <= 4) {
        studentYear = 2;
      } else if (semester >= 5 && semester <= 6) {
        studentYear = 3;
      } else if (semester >= 7 && semester <= 8) {
        studentYear = 4;
      }

      if (target.contains('1st year') || target.contains('1st-year')) {
        return studentYear == 1;
      }
      if (target.contains('2nd year') || target.contains('2nd-year')) {
        return studentYear == 2;
      }
      if (target.contains('3rd year') || target.contains('3rd-year')) {
        return studentYear == 3;
      }
      if (target.contains('4th year') || target.contains('4th-year')) {
        return studentYear == 4;
      }

      return true;
    }).toList();

    if (filtered.isEmpty && _rawAnnouncements.isNotEmpty) {
      final published = _rawAnnouncements
          .where((a) => a.status == 'PUBLISHED' || a.status == 'APPROVED')
          .toList();
      if (published.isNotEmpty) {
        return _applySort(published);
      }
      return _applySort(_rawAnnouncements.toList());
    }

    return _applySort(filtered);
  }

  // Scheduled announcements awaiting future broadcast
  List<AnnouncementModel> get scheduledAnnouncements {
    final now = DateTime.now();
    final filtered = _rawAnnouncements.where((a) {
      return a.status == 'SCHEDULED' &&
          a.scheduledAt != null &&
          a.scheduledAt!.isAfter(now);
    }).toList();
    return _applySort(filtered);
  }

  Future<void> fetchAnnouncements() async {
    if (_rawAnnouncements.isEmpty) {
      isLoading.value = true;
    }
    if (!Get.testMode) {
      try {
        final api = EchosphereApiService();
        // Fetch public notices and approval queue concurrently in parallel
        final results = await Future.wait([
          api.getAnnouncements().catchError((err) {
            debugPrint('Public announcements fetch notice: $err');
            return <dynamic>[];
          }),
          api.getApprovalQueue().catchError((err) {
            debugPrint('Approval queue fetch notice: $err');
            return <dynamic>[];
          }),
        ]);
        final publicData = results[0];
        final queueData = results[1];

        final List<AnnouncementModel> fetched = [];
        if (publicData.isNotEmpty) {
          fetched.addAll(publicData.map((e) => AnnouncementModel.fromJson(e as Map<String, dynamic>)));
        }

        if (queueData.isNotEmpty) {
          for (var item in queueData) {
            final model = AnnouncementModel.fromJson(item as Map<String, dynamic>);
            final existingIdx = fetched.indexWhere((a) => a.id == model.id);
            if (existingIdx != -1) {
              fetched[existingIdx] = model;
            } else {
              fetched.insert(0, model);
            }
          }
        }

        if (fetched.isNotEmpty) {
          // Dynamic database notices: preserve all announcements by unique database ID
          final Map<int, AnnouncementModel> mergedById = {};
          for (final a in fetched) {
            final wasPlayed = playedSpeakerNoticeIds.contains(a.id) ||
                (_rawAnnouncements.firstWhereOrNull((old) => old.id == a.id)?.playedOnSpeaker ?? false);
            if (wasPlayed) {
              playedSpeakerNoticeIds.add(a.id);
              mergedById[a.id] = a.copyWith(
                playedOnSpeaker: true,
                speakerStatus: 'Completed',
              );
            } else {
              mergedById[a.id] = a;
            }
          }
          _rawAnnouncements.value = mergedById.values.toList();
          _savePersistentCache(_rawAnnouncements.toList());
          isLoading.value = false;
          update();
          // Update relevance scores asynchronously in background without blocking UI
          updateAllRelevanceScores();
          return;
        } else {
          // If server successfully returned 0 notices, clean up stale local cache
          _rawAnnouncements.value = [];
          _savePersistentCache([]);
          try {
            final prefs = await SharedPreferences.getInstance();
            await prefs.remove('echosphere_cached_announcements');
          } catch (_) {}
          isLoading.value = false;
          update();
          return;
        }
      } catch (e) {
        debugPrint('Live backend announcements fetch notice: $e');
      }
    }

    // Finalize loading state without rigid placeholder announcements
    isLoading.value = false;
    update();
    updateAllRelevanceScores();
  }

  void filterTodayOnly() {
    showTodayOnly.value = true;
    showForYouOnly.value = false;
    searchQuery.value = '';
    selectedCategory.value = 'All';
    selectedPriority.value = 'All';
  }

  // Archived notices (explicitly archived or older than 1 week / 7 days)
  List<AnnouncementModel> get archivedAnnouncements {
    final now = DateTime.now();
    final filtered = _rawAnnouncements.where((a) {
      if (a.status == 'ARCHIVED') return true;
      final diffDays = now.difference(a.createdAt).inDays;
      return diffDays > 7;
    }).toList();
    return _applySort(filtered);
  }

  List<AnnouncementModel> get priorityAnnouncements {
    final filtered = announcements
        .where((a) =>
            a.priority == 'EMERGENCY' ||
            a.priority == 'HIGH' ||
            a.emergencyLevel == 'CRITICAL')
        .toList();
    return _applySort(filtered);
  }

  List<AnnouncementModel> get todayAnnouncements {
    final now = DateTime.now();
    final filtered = announcements.where((a) {
      return a.createdAt.year == now.year &&
          a.createdAt.month == now.month &&
          a.createdAt.day == now.day;
    }).toList();
    return _applySort(filtered);
  }

  int get emergencyCount {
    return announcements
        .where((a) =>
            a.priority == 'EMERGENCY' ||
            a.priority == 'URGENT' ||
            a.emergencyLevel == 'CRITICAL')
        .length;
  }

  List<AnnouncementModel> get pendingApprovals {
    final authController = Get.find<AuthController>();
    final user = authController.currentUser.value;
    final userRole = user?.role ?? 'Student';
    final userDept = (user?.department ?? '').trim().toLowerCase();

    final filtered = _rawAnnouncements.where((a) {
      if (_persistedApprovedIds.contains(a.id) || _persistedRejectedIds.contains(a.id)) {
        return false;
      }
      final isPending = a.status == 'PENDING_APPROVAL' ||
          a.status == 'SUBMITTED' ||
          a.status == 'DRAFT';
      if (!isPending) return false;

      // HoD can only review notices from their own department
      if (userRole == 'HoD' && userDept.isNotEmpty) {
        final noticeDept = a.department.trim().toLowerCase();
        if (noticeDept != userDept && !noticeDept.contains(userDept) && !userDept.contains(noticeDept)) {
          return false;
        }
      }
      return true;
    }).toList();
    return _applySort(filtered);
  }

  List<AnnouncementModel> get mySubmissions {
    final authController = Get.find<AuthController>();
    final user = authController.currentUser.value;
    final userName = (user?.fullName ?? '').trim().toLowerCase();
    final userRole = user?.role ?? 'Teacher';

    if (userRole == 'Teacher' && userName.isNotEmpty) {
      final mine = _rawAnnouncements.where((a) {
        final creator = a.creatorName.trim().toLowerCase();
        return creator.contains(userName) || userName.contains(creator) || a.creatorRole == 'Teacher';
      }).toList();
      return _applySort(mine.isNotEmpty ? mine : _rawAnnouncements.toList());
    }

    return _applySort(_rawAnnouncements.toList());
  }

  List<AnnouncementModel> get allAnnouncements {
    return _applySort(_rawAnnouncements.toList());
  }

  void setAnnouncements(List<AnnouncementModel> list) {
    _rawAnnouncements.assignAll(list);
    _rawAnnouncements.refresh();
    update();
  }

  List<AnnouncementModel> get filteredAnnouncements {
    final now = DateTime.now();

    final filtered = announcements.where((a) {
      if (showForYouOnly.value) {
        final rel = getRelevanceFor(a);
        final score = (rel['score'] as num?)?.toDouble() ?? 0.0;
        final isHighlyRel = rel['is_highly_relevant'] == true;
        if (!isHighlyRel && score < 0.60) return false;
      }

      if (showTodayOnly.value) {
        final isToday = a.createdAt.year == now.year &&
            a.createdAt.month == now.month &&
            a.createdAt.day == now.day;
        if (!isToday) return false;
      }

      if (showBookmarkedOnly.value) {
        if (!bookmarkedNoticeIds.contains(a.id)) return false;
      }

      final selectedCat = selectedCategory.value.trim().toLowerCase();
      final noticeCat = a.category.trim().toLowerCase();

      final sCatBase = selectedCat.endsWith('s') && selectedCat.length > 4
          ? selectedCat.substring(0, selectedCat.length - 1)
          : selectedCat;
      final nCatBase = noticeCat.endsWith('s') && noticeCat.length > 4
          ? noticeCat.substring(0, noticeCat.length - 1)
          : noticeCat;

      final matchesCategory = selectedCat == 'all' ||
          selectedCat == noticeCat ||
          sCatBase == nCatBase ||
          nCatBase.startsWith(sCatBase) ||
          sCatBase.startsWith(nCatBase);

      final matchesPriority = selectedPriority.value == 'All' ||
          a.priority.toLowerCase() == selectedPriority.value.toLowerCase();

      final query = searchQuery.value.trim().toLowerCase();
      final matchesSearch = query.isEmpty ||
          a.title.toLowerCase().contains(query) ||
          a.description.toLowerCase().contains(query) ||
          a.department.toLowerCase().contains(query) ||
          a.category.toLowerCase().contains(query);

      return matchesCategory && matchesPriority && matchesSearch;
    }).toList();

    final sorted = _applySort(filtered);
    if (showForYouOnly.value && sortBy.value == 'Newest First') {
      sorted.sort((a, b) {
        final scoreA = (getRelevanceFor(a)['score'] as num?)?.toDouble() ?? 0.0;
        final scoreB = (getRelevanceFor(b)['score'] as num?)?.toDouble() ?? 0.0;
        if (scoreA != scoreB) return scoreB.compareTo(scoreA);
        return b.createdAt.compareTo(a.createdAt);
      });
    }
    return sorted;
  }

  Future<bool> createAnnouncement({
    required String title,
    required String description,
    required String category,
    required String priority,
    required String creatorRole,
    required String creatorName,
    required String department,
    String targetAudience = 'Entire College',
    bool isScheduleLater = false,
    DateTime? scheduledDateTime,
    bool deliverSpeaker = false,
    bool deliverInApp = true,
    bool deliverPush = true,
    String speakerVoice = 'female',
    int? speakerNodeId,
    List<String> attachments = const [],
    Map<String, dynamic>? repeatSchedule,
  }) async {
    isLoading.value = true;

    int catId = 12; // Default to 'General' (ID 12)
    final catLower = category.toLowerCase();
    if (catLower.contains('emerg')) {
      catId = 1;
    } else if (catLower.contains('acad')) {
      catId = 2;
    } else if (catLower.contains('exam')) {
      catId = 3;
    } else if (catLower.contains('place')) {
      catId = 4;
    } else if (catLower.contains('event')) {
      catId = 5;
    } else if (catLower.contains('work')) {
      catId = 6;
    } else if (catLower.contains('sem')) {
      catId = 7;
    } else if (catLower.contains('holi')) {
      catId = 8;
    } else if (catLower.contains('sport')) {
      catId = 9;
    } else if (catLower.contains('cult')) {
      catId = 10;
    } else if (catLower.contains('club')) {
      catId = 11;
    } else if (catLower.contains('circ')) {
      catId = 13;
    } else if (catLower.contains('fee')) {
      catId = 14;
    }

    // RBAC Approval Matrix: Evaluate approval requirements first!
    bool requiresApproval = false;
    if (creatorRole == 'Teacher') {
      // Teachers MANDATORILY require approval for ALL notices (whether immediate or scheduled)
      requiresApproval = true;
    } else if (creatorRole == 'HoD') {
      // HoD can auto-approve department notices for their own department.
      // BUT institution-wide ('Entire College') or cross-department notices require Principal/College Admin approval!
      final target = targetAudience.trim().toLowerCase();
      final userDept = department.trim().toLowerCase();
      final isOwnDeptOnly = target.contains(userDept) && !target.contains('entire') && !target.contains('all');

      if (!isOwnDeptOnly) {
        requiresApproval = true;
      }
    }

    String initialStatus;
    if (requiresApproval) {
      initialStatus = 'SUBMITTED';
    } else if (isScheduleLater) {
      initialStatus = 'SCHEDULED';
    } else {
      initialStatus = 'PUBLISHED';
    }

    final newId = (DateTime.now().millisecondsSinceEpoch + (++_idCounter)) % 1000000;
    final words = ('$title $description').split(' ').length;
    final durSecs = (words / 2.5).round().clamp(10, 60);

    final effectiveDeliverSpeaker = deliverSpeaker || repeatSchedule != null;
    final newNotice = AnnouncementModel(
      id: newId,
      title: title,
      description: description,
      priority: priority,
      emergencyLevel: priority == 'EMERGENCY' ? 'CRITICAL' : 'NORMAL',
      status: initialStatus,
      creatorName: creatorName,
      department: department,
      targetAudience: targetAudience,
      category: category,
      createdAt: DateTime.now(),
      scheduledAt: isScheduleLater ? scheduledDateTime : null,
      aiSummary: description.trim().isNotEmpty
          ? (description.split(RegExp(r'(?<=[.!?])\s+')).first.trim())
          : title,
      attachments: attachments,
      deliverSpeaker: effectiveDeliverSpeaker,
      speakerNodeId: speakerNodeId,
      speakerStatus: effectiveDeliverSpeaker ? 'Queued' : null,
      playedOnSpeaker: false,
      durationSeconds: durSecs,
      speakerVoice: speakerVoice,
      repeatSchedule: repeatSchedule,
    );

    // 0ms Instant Local Insertion for snappy responsiveness
    _rawAnnouncements.insert(0, newNotice);
    _rawAnnouncements.refresh();
    isLoading.value = false;
    update();

    // Synchronously ensure backend creation and get official backend ID
    if (!Get.testMode) {
      int? backendId;
      try {
        final res = await EchosphereApiService().createAnnouncement(
          title: title,
          description: description,
          categoryId: catId,
          priority: priority == 'EMERGENCY' ? 'High' : priority,
          emergencyLevel: priority == 'EMERGENCY' ? 'Emergency' : 'Normal',
          scheduledAt: isScheduleLater && scheduledDateTime != null
              ? scheduledDateTime.toIso8601String()
              : null,
          deliverSpeaker: effectiveDeliverSpeaker,
          deliverInApp: deliverInApp,
          deliverPush: deliverPush,
          speakerVoice: speakerVoice,
          targetAudience: targetAudience,
          speakerNodeId: speakerNodeId,
        );
        final rawBackendId = res['id'];
        backendId = rawBackendId is int ? rawBackendId : int.tryParse(rawBackendId?.toString() ?? '');
        lastCreatedAnnouncementId = backendId;
        if (backendId != null) {
          final idx = _rawAnnouncements.indexWhere((a) => a.id == newId);
          if (idx != -1) {
            final old = _rawAnnouncements[idx];
            final backendSummary = res['ai_summary'] as String?;
            _rawAnnouncements[idx] = old.copyWith(
              id: backendId,
              repeatSchedule: repeatSchedule,
              aiSummary: (backendSummary != null && backendSummary.trim().isNotEmpty)
                  ? backendSummary.trim()
                  : old.aiSummary,
            );
            _rawAnnouncements.refresh();
            update();
          }

          try {
            if (Get.isRegistered<dynamic>(tag: null)) {
              // Reconcile temporary ID in speaker queue controller if active
              final speakerCtrl = Get.isRegistered<dynamic>() ? Get.find<dynamic>() : null;
              if (speakerCtrl != null && speakerCtrl.runtimeType.toString() == 'SpeakerQueueController') {
                (speakerCtrl as dynamic).replaceTemporaryId(newId, backendId);
              }
            }
          } catch (_) {}

          if (repeatSchedule != null) {
            try {
              final schedRes = await EchosphereApiService().setRepeatSchedule(backendId, repeatSchedule);
              debugPrint('Repeat schedule successfully saved on backend for announcement #$backendId: $schedRes');
            } catch (re) {
              debugPrint('Error attaching repeat schedule to announcement #$backendId: $re');
            }
          }
        }
      } catch (e) {
        debugPrint('Backend create announcement error: $e');
      }

      // Background AI Summarization (non-blocking)
      Future.microtask(() async {
        try {
          final summary = await EchosphereApiService().summarizeContent(description);
          final idx = _rawAnnouncements.indexWhere((a) => a.id == newId || (backendId != null && a.id == backendId));
          if (idx != -1 && summary.isNotEmpty) {
            final cleanSummary = summary.toLowerCase().startsWith('summary:')
                ? summary.substring(8).trim()
                : summary.trim();
            final old = _rawAnnouncements[idx];
            _rawAnnouncements[idx] = old.copyWith(aiSummary: cleanSummary);
            _rawAnnouncements.refresh();
            update();
          }
        } catch (_) {}
      });
    }

    return true;
  }

  void updateAnnouncementSummary(int id, String summary) {
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1 && summary.isNotEmpty) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = old.copyWith(aiSummary: summary);
      _rawAnnouncements.refresh();
      update();
    }
  }

  Future<String?> generateSummaryForAnnouncement(int id) async {
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx == -1) return null;
    final notice = _rawAnnouncements[idx];
    if (notice.aiSummary != null && notice.aiSummary!.isNotEmpty) {
      return notice.aiSummary;
    }
    try {
      final summary = await EchosphereApiService().summarizeContent(notice.description);
      if (summary.isNotEmpty) {
        updateAnnouncementSummary(id, summary);
        return summary;
      }
    } catch (e) {
      debugPrint('Error generating AI summary for notice $id: $e');
    }
    return null;
  }

  Future<bool> archiveAnnouncement(int id, {String? reason}) async {
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = AnnouncementModel(
        id: old.id,
        title: old.title,
        description: old.description,
        priority: old.priority,
        emergencyLevel: old.emergencyLevel,
        status: 'ARCHIVED',
        creatorName: old.creatorName,
        department: old.department,
        targetAudience: old.targetAudience,
        category: old.category,
        createdAt: old.createdAt,
        scheduledAt: old.scheduledAt,
        aiSummary: old.aiSummary,
        remarks: old.remarks,
        attachments: old.attachments,
      );
      _rawAnnouncements.refresh();
      update();
    }

    try {
      await EchosphereApiService().archiveAnnouncement(id, reason: reason);
      return true;
    } catch (e) {
      debugPrint('Archive announcement API error: $e');
      return true;
    }
  }

  Future<bool> approveAnnouncement(int id, {String? remarks}) async {
    await _recordApprovedNoticeId(id);

    // 0ms Optimistic UI update -- save original for rollback
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    AnnouncementModel? originalSnapshot;
    if (idx != -1) {
      originalSnapshot = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = originalSnapshot.copyWith(
        status: 'PUBLISHED',
        remarks: remarks ?? 'Approved for college-wide publication',
        speakerStatus: originalSnapshot.deliverSpeaker ? 'Queued' : originalSnapshot.speakerStatus,
        approvedAt: DateTime.now(),
      );
      _rawAnnouncements.refresh();
      update();
    }

    try {
      await EchosphereApiService().approveAnnouncement(id, remarks: remarks);
      await fetchAnnouncements();
      return true;
    } catch (e) {
      debugPrint('Approve announcement API failed: $e');
      // Rollback optimistic update on API failure
      if (originalSnapshot != null && idx != -1 && idx < _rawAnnouncements.length) {
        _rawAnnouncements[idx] = originalSnapshot;
        _rawAnnouncements.refresh();
        update();
      }
      // Remove from local persisted cache since server didn't accept it
      _persistedApprovedIds.remove(id);
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setStringList(
          'echosphere_approved_notice_ids',
          _persistedApprovedIds.map((e) => e.toString()).toList(),
        );
      } catch (_) {}
      await fetchAnnouncements();
      return false;
    }
  }

  /// Marks an announcement as played on the smart speaker queue
  void markNoticePlayedOnSpeaker(int id) {
    playedSpeakerNoticeIds.add(id);
    _savePersistedPlayedSpeakerNotices();
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = old.copyWith(
        playedOnSpeaker: true,
        speakerStatus: 'Completed',
      );
      _rawAnnouncements.refresh();
      update();
    }
  }

  /// Checks whether a scheduled announcement can be modified.
  /// Rule: Cannot edit or reschedule a notice within 5 minutes of broadcast time IF:
  /// 1. Created by a Teacher (requires approval).
  /// 2. Created by an HoD for an institution-wide ('Entire College') or cross-department notice.
  /// Note: Cancellation is ALWAYS allowed regardless of time!
  bool canModifyNotice(AnnouncementModel notice, {String? userRole}) {
    if (notice.status != 'SCHEDULED' || notice.scheduledAt == null) {
      return true;
    }

    final role = userRole ?? 'Teacher';
    final target = notice.targetAudience.trim().toLowerCase();
    final dept = notice.department.trim().toLowerCase();
    final isTeacher = role == 'Teacher';
    final isHodCrossDept = role == 'HoD' && (!target.contains(dept) || target.contains('entire') || target.contains('all'));

    // The 5-minute modification lockout applies ONLY to Teacher or HoD cross-dept approval notices
    if (!isTeacher && !isHodCrossDept) {
      return true;
    }

    final now = DateTime.now();
    final diffMinutes = notice.scheduledAt!.difference(now).inMinutes;
    return diffMinutes >= 5;
  }

  Future<bool> rejectAnnouncement(int id, {required String remarks}) async {
    await _recordRejectedNoticeId(id);

    // 0ms Optimistic UI update -- save original for rollback
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    AnnouncementModel? originalSnapshot;
    if (idx != -1) {
      originalSnapshot = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = originalSnapshot.copyWith(
        status: 'REJECTED',
        remarks: remarks,
        approvedAt: DateTime.now(),
      );
      _rawAnnouncements.refresh();
      update();
    }

    try {
      await EchosphereApiService().rejectAnnouncement(id, remarks: remarks);
      await fetchAnnouncements();
      return true;
    } catch (e) {
      debugPrint('Reject announcement API failed: $e');
      // Rollback optimistic update on API failure
      if (originalSnapshot != null && idx != -1 && idx < _rawAnnouncements.length) {
        _rawAnnouncements[idx] = originalSnapshot;
        _rawAnnouncements.refresh();
        update();
      }
      // Remove from local persisted cache since server didn't accept it
      _persistedRejectedIds.remove(id);
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setStringList(
          'echosphere_rejected_notice_ids',
          _persistedRejectedIds.map((e) => e.toString()).toList(),
        );
      } catch (_) {}
      await fetchAnnouncements();
      return false;
    }
  }

  Future<bool> deleteAnnouncement(int id) async {
    try {
      await EchosphereApiService().deleteAnnouncement(id);
    } catch (_) {}

    _rawAnnouncements.removeWhere((a) => a.id == id);
    return true;
  }

  Future<bool> updateAnnouncement({
    required int id,
    required String title,
    required String description,
    required String category,
    required String priority,
    bool? deliverSpeaker,
    String? speakerVoice,
    int? speakerNodeId,
  }) async {
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = old.copyWith(
        title: title,
        description: description,
        priority: priority,
        emergencyLevel: priority == 'EMERGENCY' ? 'CRITICAL' : 'NORMAL',
        category: category,
        aiSummary: 'AI Summary: $title - Modified notice.',
        remarks: 'Modified by Administrator',
        deliverSpeaker: deliverSpeaker ?? old.deliverSpeaker,
        speakerVoice: speakerVoice ?? old.speakerVoice,
        speakerNodeId: speakerNodeId ?? old.speakerNodeId,
      );
      _rawAnnouncements.refresh();
      update();
    }

    if (!Get.testMode) {
      Future.microtask(() async {
        try {
          int catId = 1;
          final catLower = category.toLowerCase();
          if (catLower.contains('exam')) catId = 2;
          if (catLower.contains('event')) catId = 3;
          if (catLower.contains('sport')) catId = 4;
          if (catLower.contains('placement')) catId = 5;
          if (catLower.contains('emergency')) catId = 6;

          await EchosphereApiService().updateAnnouncement(
            id,
            title: title,
            description: description,
            categoryId: catId,
            priority: priority,
            emergencyLevel: priority == 'EMERGENCY' ? 'CRITICAL' : 'NORMAL',
            deliverSpeaker: deliverSpeaker,
            speakerVoice: speakerVoice,
            speakerNodeId: speakerNodeId,
          );
        } catch (e) {
          debugPrint('Async backend update announcement log: $e');
        }
      });
    }

    return true;
  }

  Future<bool> rescheduleAnnouncement({
    required int id,
    required DateTime newScheduledTime,
  }) async {
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = AnnouncementModel(
        id: old.id,
        title: old.title,
        description: old.description,
        priority: old.priority,
        emergencyLevel: old.emergencyLevel,
        status: 'SCHEDULED',
        creatorName: old.creatorName,
        department: old.department,
        category: old.category,
        createdAt: newScheduledTime,
        aiSummary: old.aiSummary,
        remarks: 'Rescheduled for ${newScheduledTime.toString().substring(0, 16)}',
      );
      _rawAnnouncements.refresh();
    }
    return true;
  }

}
