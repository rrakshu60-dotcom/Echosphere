import 'dart:async';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/services/calendar_sync_service.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/services/echosphere_realtime_service.dart';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';

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

  AnnouncementModel({
    required this.id,
    required this.title,
    required this.description,
    required this.priority,
    required this.emergencyLevel,
    required this.status,
    required this.creatorName,
    this.creatorRole = 'Faculty / Official',
    required this.department,
    this.targetAudience = 'Entire College',
    required this.category,
    required this.createdAt,
    this.scheduledAt,
    this.aiSummary,
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
  });

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
    );
  }
}

class AnnouncementController extends GetxController {
  final RxList<AnnouncementModel> _rawAnnouncements = <AnnouncementModel>[].obs;
  RxList<AnnouncementModel> get rxAnnouncements => _rawAnnouncements;
  final RxString selectedCategory = 'All'.obs;
  final RxString selectedPriority = 'All'.obs;
  final RxString searchQuery = ''.obs;
  final RxBool showTodayOnly = false.obs;
  final RxBool isLoading = false.obs;
  final RxString sortBy = 'Newest First'.obs;
  final RxMap<int, CalendarEventData> calendarEvents = <int, CalendarEventData>{}.obs;
  static int _idCounter = 0;

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

  @override
  void onInit() {
    super.onInit();
    _initRealtimeSync();
    fetchAnnouncements();
    _startPeriodicSync();
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
      debugPrint('⚡ [LiveSync] Event in AnnouncementController: ${event.event} (#${event.announcementId})');
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
    } else if (event.event == 'ANNOUNCEMENT_CREATED') {
      _silentApprovalQueueSync();
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
    isLoading.value = true;
    if (!Get.testMode) {
      try {
        final api = EchosphereApiService();
        final publicData = await api.getAnnouncements();
        final List<AnnouncementModel> fetched = [];
        if (publicData.isNotEmpty) {
          fetched.addAll(publicData.map((e) => AnnouncementModel.fromJson(e as Map<String, dynamic>)));
        }

        // Also fetch approval queue for staff/teachers/approvers
        try {
          final queueData = await api.getApprovalQueue();
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
        } catch (qe) {
          debugPrint('Approval queue fetch log: $qe');
        }

        if (fetched.isNotEmpty) {
          _rawAnnouncements.value = fetched;
          isLoading.value = false;
          update();
          return;
        }
      } catch (e) {
        debugPrint('Live backend announcements fetch notice: $e');
      }
    }

    // Seed/Sample announcements for instant demonstration & offline resilience
    if (_rawAnnouncements.isEmpty) {
      _rawAnnouncements.value = _getSampleAnnouncements();
    }
    isLoading.value = false;
    update();
  }

  void filterTodayOnly() {
    showTodayOnly.value = true;
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
      if (showTodayOnly.value) {
        final isToday = a.createdAt.year == now.year &&
            a.createdAt.month == now.month &&
            a.createdAt.day == now.day;
        if (!isToday) return false;
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

    return _applySort(filtered);
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
    int? speakerNodeId,
    List<String> attachments = const [],
  }) async {
    isLoading.value = true;

    int catId = 1;
    final catLower = category.toLowerCase();
    if (catLower.contains('exam')) catId = 2;
    if (catLower.contains('event')) catId = 3;
    if (catLower.contains('sport')) catId = 4;
    if (catLower.contains('placement')) catId = 5;
    if (catLower.contains('emergency')) catId = 6;

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
      aiSummary: 'Summary: $title',
      attachments: attachments,
      deliverSpeaker: deliverSpeaker,
      speakerNodeId: speakerNodeId,
      speakerStatus: deliverSpeaker ? 'Queued' : null,
      playedOnSpeaker: false,
      durationSeconds: durSecs,
    );

    // 0ms Instant Local Insertion for snappy responsiveness
    _rawAnnouncements.insert(0, newNotice);
    _rawAnnouncements.refresh();
    isLoading.value = false;
    update();

    // Background Async Backend Sync & AI Summarization (non-blocking)
    if (!Get.testMode) {
      Future.microtask(() async {
        try {
          final res = await EchosphereApiService().createAnnouncement(
            title: title,
            description: description,
            categoryId: catId,
            priority: priority,
            emergencyLevel: priority == 'EMERGENCY' ? 'CRITICAL' : 'NORMAL',
            scheduledAt: isScheduleLater && scheduledDateTime != null
                ? scheduledDateTime.toIso8601String()
                : null,
            deliverSpeaker: deliverSpeaker,
            deliverInApp: deliverInApp,
            deliverPush: deliverPush,
            targetAudience: targetAudience,
            speakerNodeId: speakerNodeId,
          );
          final backendId = res['id'];
          if (backendId != null && backendId is int && deliverSpeaker) {
            try {
              await EchosphereApiService().enqueueAnnouncement(
                announcementId: backendId,
                speakerNodeId: speakerNodeId,
              );
            } catch (_) {
              // Already automatically enqueued by backend service
            }
          }
        } catch (e) {
          debugPrint('Async backend create announcement log: $e');
        }

        try {
          final summary = await EchosphereApiService().summarizeContent(description);
          final idx = _rawAnnouncements.indexWhere((a) => a.id == newId);
          if (idx != -1 && summary.isNotEmpty) {
            final old = _rawAnnouncements[idx];
            _rawAnnouncements[idx] = old.copyWith(aiSummary: summary);
            _rawAnnouncements.refresh();
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
    // 0ms Optimistic UI update
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = old.copyWith(
        status: 'PUBLISHED',
        remarks: remarks ?? 'Approved for college-wide publication',
        speakerStatus: old.deliverSpeaker ? 'Queued' : old.speakerStatus,
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
      debugPrint('Approve announcement API error: $e');
      await fetchAnnouncements();
      rethrow;
    }
  }

  /// Marks an announcement as played on the smart speaker queue
  void markNoticePlayedOnSpeaker(int id) {
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
    // 0ms Optimistic UI update
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = old.copyWith(
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
      debugPrint('Reject announcement API error: $e');
      await fetchAnnouncements();
      rethrow;
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
  }) async {
    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = AnnouncementModel(
        id: old.id,
        title: title,
        description: description,
        priority: priority,
        emergencyLevel: priority == 'EMERGENCY' ? 'CRITICAL' : 'NORMAL',
        status: old.status,
        creatorName: old.creatorName,
        department: old.department,
        category: category,
        createdAt: old.createdAt,
        aiSummary: 'AI Summary: $title - Modified notice.',
        remarks: 'Modified by Administrator',
      );
      _rawAnnouncements.refresh();
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

  List<AnnouncementModel> _getSampleAnnouncements() {
    final now = DateTime.now();
    return [
      AnnouncementModel(
        id: 1,
        title: 'Mid-Term Academic Progress Review & Proctor Mentorship Sessions',
        description: 'All B.E. and M.Tech students are required to attend the mandatory mid-term academic counseling sessions scheduled from October 20, 2026 to October 24, 2026 between 10:00 AM and 4:30 PM in their respective Department Faculty Cabins. Faculty proctors will review IA-1 answer scripts, syllabus completion, and attendance registers. Students with attendance below 85% must report along with their local guardians.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. B Kursheed',
        creatorRole: 'Teacher',
        department: 'AIML',
        category: 'Academic',
        createdAt: now.subtract(const Duration(hours: 3)),
        aiSummary: 'Mandatory academic counseling and proctor review from October 20-24, 2026 between 10:00 AM and 4:30 PM in Faculty Cabins; IA-1 and attendance review required.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 2,
        title: 'Final Professional & Open Elective Subject Selection Deadline',
        description: 'The online academic ERP portal is officially active for submitting elective preferences for the upcoming semester. Students from 5th and 7th semesters must submit choices through the student portal before October 25, 2026 at 5:00 PM. Elective seats in AI Architecture and Cloud Computing are allocated strictly on a first-come, first-served basis.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. B Kursheed',
        creatorRole: 'Teacher',
        department: 'AIML',
        category: 'Academic',
        createdAt: now.subtract(const Duration(hours: 5)),
        aiSummary: 'Online ERP portal open for 5th & 7th semester elective course selection until October 25, 2026 at 5:00 PM.',
        attachments: const ['Course_Syllabus_2026.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 3,
        title: 'National Board of Accreditation (NBA) Student Feedback Survey',
        description: 'In compliance with NBA accreditation parameters, the Academic Quality Cell invites all students to participate in the annual Course Outcome (CO) and Program Outcome (PO) survey. Please access the survey link sent to your registered college email and complete the feedback by October 28, 2026 at 6:00 PM.',
        priority: 'LOW',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. B Kursheed',
        creatorRole: 'Teacher',
        department: 'AIML',
        category: 'Academic',
        createdAt: now.subtract(const Duration(hours: 7)),
        aiSummary: 'NBA curriculum outcome feedback survey active for all students via registered email until October 28, 2026 at 6:00 PM.',
        attachments: const ['Fee_Structure_2026.pdf', 'Scholarship_Application.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 4,
        title: 'Final Schedule for Semester End Theory Examinations - Odd Semester 2026',
        description: 'The Controller of Examinations has published the definitive timetable for the upcoming Semester End Theory Examinations commencing November 15, 2026 at 9:30 AM in Examination Block 3. Morning sessions run from 9:30 AM to 12:30 PM and afternoon sessions from 2:00 PM to 5:00 PM. Download your verified digital hall tickets from the student portal.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Controller of Examinations',
        creatorRole: 'HoD',
        department: 'Examinations',
        category: 'Examination',
        createdAt: now.subtract(const Duration(hours: 9)),
        aiSummary: 'Final timetable for Semester End Examinations starting November 15, 2026 at 9:30 AM in Exam Block 3; download digital hall tickets online.',
        attachments: const ['Exam_Timetable_Final.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 5,
        title: 'Physical Hall Ticket Distribution & Malpractice Prevention Rules',
        description: 'Eligible candidates appearing for semester university examinations must collect their physical signed Hall Tickets from their department offices between October 27, 2026 and October 31, 2026 at 4:00 PM after clearing all library and lab dues. Smartwatches, mobile phones, and programmable devices are strictly banned in examination halls.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Controller of Examinations',
        creatorRole: 'HoD',
        department: 'Examinations',
        category: 'Examination',
        createdAt: now.subtract(const Duration(hours: 11)),
        aiSummary: 'Collect signed hall tickets from department offices by October 31, 2026 at 4:00 PM; smartwatches and electronic devices strictly banned.',
        attachments: const ['Exam_Timetable_Final.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 6,
        title: 'Supplementary Examination & Re-evaluation Applications Window',
        description: 'Applications are formally invited for answer script photocopy evaluation and re-valuation for previous semester courses. The online fee payment gateway remains open until November 5, 2026 at 11:59 PM. Late applications will not be processed under any circumstances.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Controller of Examinations',
        creatorRole: 'HoD',
        department: 'Examinations',
        category: 'Examination',
        createdAt: now.subtract(const Duration(hours: 13)),
        aiSummary: 'Re-evaluation and photocopy application window open until November 5, 2026 at 11:59 PM via online exam portal.',
        attachments: const ['Exam_Timetable_Final.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 7,
        title: 'Tier-1 Recruitment Drive: Microsoft Cloud & AI Engineering',
        description: 'The Department of Training and Placement announces on-campus recruitment by Microsoft for Cloud Solutions Architect and AI Development roles. Eligible streams: CSE, AIML, ISE, and ECE with CGPA 8.0 and above. The mandatory online technical assessment will be held on October 24, 2026 at 10:00 AM in the Advanced Computing Lab.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Placement Officer',
        creatorRole: 'Faculty / Official',
        department: 'Placements',
        category: 'Placement',
        createdAt: now.subtract(const Duration(hours: 15)),
        aiSummary: 'Microsoft recruitment drive for Cloud & AI roles; mandatory technical assessment on October 24, 2026 at 10:00 AM in Advanced Computing Lab.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 8,
        title: 'Corporate Mock Interview & ATS Resume Critique Workshop',
        description: 'Senior technical recruiters from top MNCs will conduct 1-on-1 mock interviews and technical portfolio reviews for 6th and 7th semester students on October 22, 2026 at 9:00 AM in the Placement Cell. Students must bring two printed copies of their updated resume in standard format and report in business formal attire.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Placement Officer',
        creatorRole: 'Faculty / Official',
        department: 'Placements',
        category: 'Placement',
        createdAt: now.subtract(const Duration(hours: 17)),
        aiSummary: '1-on-1 technical mock interviews by MNC recruiters on October 22, 2026 at 9:00 AM in Placement Cell; carry 2 resume copies in formal attire.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 9,
        title: 'Summer Technology Internship Drive at Goldman Sachs & Morgan Stanley',
        description: 'Registrations are open for the 8-week Summer Technology Analyst Internship program offering a monthly stipend of ₹75,000 with Pre-Placement Interview (PPI) opportunities. Eligible candidates must apply through the Superset portal before October 26, 2026 at 11:59 PM.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Placement Officer',
        creatorRole: 'Faculty / Official',
        department: 'Placements',
        category: 'Placement',
        createdAt: now.subtract(const Duration(hours: 19)),
        aiSummary: 'Goldman Sachs and Morgan Stanley summer internship applications open on Superset until October 26, 2026 at 11:59 PM with ₹75,000 monthly stipend.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 10,
        title: 'HackEcho 2026: 24-Hour National Collegiate Hackathon',
        description: 'Registrations are live for HackEcho 2026, our flagship national 24-hour hackathon happening on November 7, 2026 at 9:00 AM in the Main Campus Auditorium. Total cash prize pool of ₹2,50,000 across AI/ML, Cyber Defense, and IoT tracks. Free food, mentoring, high-speed WiFi, and overnight accommodation provided for registered teams.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Institution',
        category: 'Event',
        createdAt: now.subtract(const Duration(hours: 21)),
        aiSummary: 'HackEcho 2026 national 24-hour hackathon begins November 7, 2026 at 9:00 AM in Main Auditorium with ₹2.5 Lakhs prize pool.',
        attachments: const ['HackEcho_Rulebook_2026.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 11,
        title: 'Annual College Day Celebrations & Alumni Homecoming \'Samanvay 2026\'',
        description: 'The Annual Institution Day and Alumni Meet \'Samanvay 2026\' will take place on November 21, 2026 at 4:30 PM in the College Quadrangle. The grand evening will feature academic excellence awards, alumni keynotes, and musical performances. All students, faculty, and alumni are cordially invited.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Institution',
        category: 'Event',
        createdAt: now.subtract(const Duration(hours: 23)),
        aiSummary: 'Annual College Day and Alumni Homecoming \'Samanvay 2026\' scheduled for November 21, 2026 at 4:30 PM in College Quadrangle.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 12,
        title: 'Campus Founder Pitchfest: Angel Investors & Startup Seed Grants',
        description: 'The Centre for Innovation and Entrepreneurship (CIE) hosts the annual Campus Founder Pitchfest on October 29, 2026 at 11:00 AM in Seminar Hall 1. Student startup founders can pitch to venture capitalists for seed grants up to ₹5,00,000. Submit your pitch deck before October 26, 2026.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Institution',
        category: 'Event',
        createdAt: now.subtract(const Duration(hours: 25)),
        aiSummary: 'CIE Campus Founder Pitchfest on October 29, 2026 at 11:00 AM in Seminar Hall 1; startup seed funding grants up to ₹5,00,000.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 13,
        title: 'Hands-On Workshop: Fine-Tuning Open-Source LLMs with LoRA & Unsloth',
        description: 'The Department of AIML conducts an intensive 2-day hands-on workshop on fine-tuning Qwen 2.5 and LLaMA 3.1 models on local workstation GPUs. The workshop will be held on October 30, 2026 at 9:30 AM in the High Performance Computing Lab. Hands-on coding kits and cloud GPU compute credits provided to all attendees.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. B Kursheed',
        creatorRole: 'Teacher',
        department: 'AIML',
        category: 'Workshop',
        createdAt: now.subtract(const Duration(hours: 27)),
        aiSummary: '2-day LLM fine-tuning workshop using LoRA and Unsloth starting October 30, 2026 at 9:30 AM in HPC Lab with GPU credits provided.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 14,
        title: 'Practical Embedded Systems & ESP32 IoT Prototyping Workshop',
        description: 'Learn circuit design, sensor integration, FreeRTOS multi-threading, and MQTT cloud telemetry using ESP32 microcontrollers. The hands-on bootcamp takes place on October 31, 2026 at 10:00 AM in Electronics Lab 2. Hardware components and sensor kits provided to registered participant pairs.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. B Kursheed',
        creatorRole: 'Teacher',
        department: 'AIML',
        category: 'Workshop',
        createdAt: now.subtract(const Duration(hours: 29)),
        aiSummary: 'Hands-on ESP32 IoT and FreeRTOS embedded systems workshop on October 31, 2026 at 10:00 AM in Electronics Lab 2 with kits provided.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 15,
        title: 'Full-Stack Development with Flutter 3 & FastAPI Masterclass',
        description: 'An intensive weekend masterclass covering reactive cross-platform mobile UI with Flutter, asynchronous REST APIs with FastAPI, WebSocket real-time streams, and SQLite persistence. Scheduled for November 1, 2026 at 9:00 AM in Seminar Hall 2. Ideal for capstone project teams.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. B Kursheed',
        creatorRole: 'Teacher',
        department: 'AIML',
        category: 'Workshop',
        createdAt: now.subtract(const Duration(hours: 31)),
        aiSummary: 'Full-stack Flutter 3 and FastAPI masterclass on November 1, 2026 at 9:00 AM in Seminar Hall 2 covering WebSockets and API architectures.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 16,
        title: 'Distinguished Lecture on Quantum Computing by IBM Quantum Fellow',
        description: 'The Department of Computer Science welcomes Dr. Richard Thorne, Principal Scientist at IBM Quantum Labs, for a keynote on \'Fault-Tolerant Quantum Algorithms and Practical Qubit Scaling\' on October 23, 2026 at 11:00 AM in Sir M. Visvesvaraya Auditorium. Attendance is open to all engineering disciplines.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'CSE',
        category: 'Seminar',
        createdAt: now.subtract(const Duration(hours: 33)),
        aiSummary: 'IBM Quantum Fellow Dr. Richard Thorne delivering keynote on Fault-Tolerant Quantum Algorithms on October 23, 2026 at 11:00 AM in Visvesvaraya Auditorium.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 17,
        title: 'Technical Seminar on Automotive Cybersecurity in Autonomous Vehicles',
        description: 'Cybersecurity architects from Bosch Automotive Technologies will present real-world attack vectors, CAN-bus security vulnerabilities, and ISO 21434 automotive standards on October 27, 2026 at 2:00 PM in Seminar Hall 1. Pre-registration is mandatory via the departmental portal.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'CSE',
        category: 'Seminar',
        createdAt: now.subtract(const Duration(hours: 35)),
        aiSummary: 'Bosch automotive cybersecurity seminar exploring CAN-bus exploits and countermeasures on October 27, 2026 at 2:00 PM in Seminar Hall 1.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 18,
        title: 'Higher Studies Abroad Seminar: GRE, TOEFL & Ivy League Admissions',
        description: 'International educational advisors from EducationUSA will conduct an interactive guidance session on university shortlisting, statement of purpose (SOP) drafting, research assistantships, and visa protocols on October 28, 2026 at 3:00 PM in the Central Library Conference Hall.',
        priority: 'LOW',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'CSE',
        category: 'Seminar',
        createdAt: now.subtract(const Duration(hours: 37)),
        aiSummary: 'EducationUSA guidance seminar on GRE prep, Ivy League applications, and international scholarships on October 28, 2026 at 3:00 PM in Library Conference Hall.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 19,
        title: 'Institutional Holiday Notification on Account of Maha Shivaratri',
        description: 'As declared in the official state gazette, the college will observe a holiday on October 23, 2026 on account of Maha Shivaratri. Regular academic classes, practical laboratories, and administrative offices will resume on October 26, 2026 at 8:30 AM.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. Principal',
        creatorRole: 'Principal',
        department: 'Institution',
        category: 'Holiday',
        createdAt: now.subtract(const Duration(hours: 39)),
        aiSummary: 'Campus closed on October 23, 2026 for Maha Shivaratri holiday; classes and offices resume on October 26, 2026 at 8:30 AM.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 20,
        title: 'Mid-Term Semester Vacation Schedule & Hostel Mess Timings',
        description: 'The institution will observe a mid-semester recess from November 2, 2026 to November 6, 2026. Student hostels will remain fully operational with revised mess timings: Breakfast 8:00 AM, Lunch 1:00 PM, and Dinner 8:00 PM. Research computing labs remain accessible with ID validation.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. Principal',
        creatorRole: 'Principal',
        department: 'Institution',
        category: 'Holiday',
        createdAt: now.subtract(const Duration(hours: 41)),
        aiSummary: 'Mid-semester vacation scheduled from November 2-6, 2026; student hostels remain open with revised dining hours.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 21,
        title: 'Republic Day National Celebration & Ceremonial Flag Hoisting',
        description: 'The 77th Republic Day celebration will be held on campus on January 26, 2027 at 8:30 AM in the College Quadrangle. The event includes ceremonial flag hoisting by the Principal, NCC cadet march-past, and patriotic musical performances. All staff and students should assemble by 8:15 AM.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. Principal',
        creatorRole: 'Principal',
        department: 'Institution',
        category: 'Holiday',
        createdAt: now.subtract(const Duration(hours: 43)),
        aiSummary: 'Republic Day ceremonial flag hoisting and NCC parade on January 26, 2027 at 8:30 AM in College Quadrangle; assembly at 8:15 AM.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 22,
        title: 'Inter-Branch Football & Volleyball Tournament Match Fixtures',
        description: 'The Department of Physical Education has scheduled the annual Inter-Branch Sports Tournament matches starting October 22, 2026 at 6:30 AM on Sports Ground 1. Football league matches will be played in morning slots and Volleyball matches at 4:30 PM on Court 2. Teams must wear official department jerseys.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Director of Physical Education',
        creatorRole: 'Faculty / Official',
        department: 'Sports',
        category: 'Sports',
        createdAt: now.subtract(const Duration(hours: 45)),
        aiSummary: 'Inter-Branch Football and Volleyball tournaments begin October 22, 2026 at 6:30 AM on Sports Ground 1; match fixtures published.',
        attachments: const ['Tournament_Fixtures_Map.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 23,
        title: 'Varsity Badminton & Table Tennis Selection Trials for State Meet',
        description: 'Open selection trials for the college varsity Badminton and Table Tennis teams will take place on October 24, 2026 at 4:00 PM in the Indoor Sports Complex. Shortlisted players will represent the institution at the upcoming VTU State Championship. Non-marking shoes are mandatory.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Director of Physical Education',
        creatorRole: 'Faculty / Official',
        department: 'Sports',
        category: 'Sports',
        createdAt: now.subtract(const Duration(hours: 47)),
        aiSummary: 'Varsity Badminton and Table Tennis selection trials on October 24, 2026 at 4:00 PM in Indoor Sports Complex; non-marking shoes required.',
        attachments: const ['Tournament_Fixtures_Map.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 24,
        title: 'Refurbished Student Gymnasium Inauguration & Revised Operating Hours',
        description: 'The campus fitness gymnasium has been equipped with new cardiovascular treadmills and Olympic strength stations. Operating hours: Morning slot from 6:00 AM to 8:30 AM and Evening slot from 4:30 PM to 8:00 PM. Certified fitness trainers will be available for orientation starting October 20, 2026.',
        priority: 'LOW',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Director of Physical Education',
        creatorRole: 'Faculty / Official',
        department: 'Sports',
        category: 'Sports',
        createdAt: now.subtract(const Duration(hours: 49)),
        aiSummary: 'Upgraded gymnasium open from October 20, 2026 with slots 6:00-8:30 AM and 4:30-8:00 PM; certified trainers available.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 25,
        title: 'Aura 2026: Battle of the Bands & Acoustic Vocal Auditions',
        description: 'The Cultural Committee invites vocalists, guitarists, drummers, and musical bands for live auditions for the Battle of the Bands stage at Aura 2026. Auditions will be judged by studio producers on October 25, 2026 at 3:00 PM in the Open Air Amphitheatre.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Cultural Coordinator',
        creatorRole: 'Faculty / Official',
        department: 'Cultural',
        category: 'Cultural',
        createdAt: now.subtract(const Duration(hours: 51)),
        aiSummary: 'Battle of the Bands and vocal auditions for Aura 2026 cultural fest on October 25, 2026 at 3:00 PM in Open Air Amphitheatre.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 26,
        title: 'Classical & Contemporary Dance Troupe Selection Trials',
        description: 'Auditions for the university-level classical solo, semi-classical group, and hip-hop dance troupes will be conducted on October 26, 2026 at 4:00 PM in the Cultural Activity Room. Selected dancers will receive formal sponsorship for interstate cultural competitions.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Cultural Coordinator',
        creatorRole: 'Faculty / Official',
        department: 'Cultural',
        category: 'Cultural',
        createdAt: now.subtract(const Duration(hours: 53)),
        aiSummary: 'Dance troupe selection trials for Classical and Western formats on October 26, 2026 at 4:00 PM in Cultural Activity Room.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 27,
        title: 'Intra-College Literary Fest: Parliamentary Debate & Elocution',
        description: 'The Literary Society announces the Annual Debate Championship on October 27, 2026 at 2:30 PM in Seminar Hall 2. Contests include British Parliamentary Debate, Slam Poetry, and Flash Fiction with cash prizes and medals for winners.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Cultural Coordinator',
        creatorRole: 'Faculty / Official',
        department: 'Cultural',
        category: 'Cultural',
        createdAt: now.subtract(const Duration(hours: 55)),
        aiSummary: 'Annual Parliamentary Debate and Literary Championship on October 27, 2026 at 2:30 PM in Seminar Hall 2 with cash awards.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 28,
        title: 'Robotics Club (RoboTech): Autonomous Rover Challenge Orientation',
        description: 'The RoboTech robotics club launches its Autonomous Rover Challenge with an orientation on October 21, 2026 at 4:30 PM in Innovation Lab 1. Participants will receive LiDAR sensor kits, ROS2 codebases, and guidance on computer vision navigation.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Student Affairs',
        category: 'Club Activities',
        createdAt: now.subtract(const Duration(hours: 57)),
        aiSummary: 'RoboTech Autonomous Rover orientation on October 21, 2026 at 4:30 PM in Innovation Lab 1; sensor kits and ROS2 codebases provided.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 29,
        title: 'Google Developer Student Club (GDSC) Core Team Recruitment Drive',
        description: 'GDSC is recruiting student leads in AI/ML, Flutter Mobile, Cloud Engineering, and Event Design. Submit your technical GitHub profiles and portfolio assignments via the GDSC campus portal before October 25, 2026 at 11:59 PM.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Student Affairs',
        category: 'Club Activities',
        createdAt: now.subtract(const Duration(hours: 59)),
        aiSummary: 'GDSC technical and leadership core team recruitment open until October 25, 2026 at 11:59 PM; submit GitHub portfolios online.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 30,
        title: 'Mega Blood Donation & Community Health Checkup Camp',
        description: 'Youth Red Cross, Rotaract, and NSS organize a voluntary Blood Donation and Free Health Camp in collaboration with the Government Hospital on October 28, 2026 at 9:00 AM in the College Auditorium. Donor certificates and healthy refreshments provided.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Student Affairs',
        category: 'Club Activities',
        createdAt: now.subtract(const Duration(hours: 1)),
        aiSummary: 'Voluntary blood donation and health checkup camp on October 28, 2026 at 9:00 AM in College Auditorium with certificates provided.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 31,
        title: 'Campus Cafeteria Nutritional Menu Expansion & Quality Standards',
        description: 'The Central Cafeteria has updated its daily dining menu starting October 20, 2026, introducing fresh juice bars, healthy salad bars, and nutritious millet meals adhering strictly to ISO food safety and hygiene protocols.',
        priority: 'LOW',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Institution',
        category: 'General',
        createdAt: now.subtract(const Duration(hours: 3)),
        aiSummary: 'Central Cafeteria rolls out expanded healthy dining menu with fresh juice and millet lunches adhering to ISO hygiene standards.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 32,
        title: 'Eco-Friendly Electric Shuttle Buggy Service on Campus',
        description: 'Two eco-friendly battery electric shuttle buggies are now operational between the Main Gate, Academic Blocks, Research Labs, and Sports Pavilion from 8:00 AM to 6:00 PM daily. Service is complimentary for all campus students and staff.',
        priority: 'LOW',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Institution',
        category: 'General',
        createdAt: now.subtract(const Duration(hours: 5)),
        aiSummary: 'Complimentary campus electric shuttle buggies running between Main Gate, Academic Blocks, and Sports Pavilion daily from 8:00 AM to 6:00 PM.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 33,
        title: 'Cryptographic Digital Campus ID Card Enabled on Echosphere App',
        description: 'Students and faculty can now access verifiable QR-coded Digital ID cards directly inside the Echosphere mobile app. The digital ID card is officially accepted for Library transactions, Cafeteria payments, and Campus Gate entry starting today.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Institution',
        category: 'General',
        createdAt: now.subtract(const Duration(hours: 7)),
        aiSummary: 'Cryptographic digital ID card activated in Echosphere app for library checkouts, cafeteria payments, and gate verification.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 34,
        title: 'EMERGENCY: Severe Weather & Thunderstorm Safety Protocol',
        description: 'The State Meteorological Department has issued an orange alert for severe localized thunderstorms and heavy winds. All outdoor sports and activities are suspended immediately. Students must remain inside reinforced academic buildings until the storm advisory clears.',
        priority: 'HIGH',
        emergencyLevel: 'EMERGENCY',
        status: 'PUBLISHED',
        creatorName: 'Dr. Principal',
        creatorRole: 'Principal',
        department: 'Institution',
        category: 'Emergency',
        createdAt: now.subtract(const Duration(hours: 9)),
        aiSummary: 'Emergency weather advisory: Orange alert for thunderstorms; outdoor sports suspended immediately and students advised to stay indoors.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 35,
        title: 'EMERGENCY: Campus Power Substation Scheduled Grid Repair',
        description: 'Due to emergency transformer repair by the electricity board, main grid power will be isolated today from 2:00 PM to 4:30 PM. Essential laboratories and data center servers will operate uninterrupted on diesel generator backup power.',
        priority: 'HIGH',
        emergencyLevel: 'EMERGENCY',
        status: 'PUBLISHED',
        creatorName: 'Dr. Principal',
        creatorRole: 'Principal',
        department: 'Institution',
        category: 'Emergency',
        createdAt: now.subtract(const Duration(hours: 11)),
        aiSummary: 'Emergency power substation maintenance today from 2:00-4:30 PM; servers and critical laboratories running on diesel generator backup.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 36,
        title: 'EMERGENCY: Mandatory Campus-Wide Fire Drill & Evacuation Exercise',
        description: 'A mandatory fire safety and emergency evacuation exercise will take place on October 21, 2026 at 11:30 AM across all academic blocks. Upon hearing the siren, walk calmly through fire exits to your block assembly zone. Do not use elevators.',
        priority: 'HIGH',
        emergencyLevel: 'EMERGENCY',
        status: 'PUBLISHED',
        creatorName: 'Dr. Principal',
        creatorRole: 'Principal',
        department: 'Institution',
        category: 'Emergency',
        createdAt: now.subtract(const Duration(hours: 13)),
        aiSummary: 'Mandatory campus fire safety evacuation drill on October 21, 2026 at 11:30 AM; follow fire exits to green assembly zones.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 37,
        title: 'Circular: Mandatory Biometric & Facial Recognition Attendance Protocol',
        description: 'In accordance with institutional guidelines, all faculty, administrative staff, and students must record their daily attendance using biometric or facial scanners at campus entrances. Wearing official ID cards is strictly mandatory on campus premise.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Administration',
        category: 'Circular',
        createdAt: now.subtract(const Duration(hours: 15)),
        aiSummary: 'Circular mandating biometric attendance logging and wearing of photo ID badges on campus premises.',
        attachments: const ['Official_Circular_Gazette.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 38,
        title: 'Circular: Campus Traffic Regulation & Vehicle Sticker Enforcement',
        description: 'All student and staff two-wheelers and four-wheelers must display valid campus security parking stickers. Parking along emergency fire lanes or pedestrian pathways is strictly prohibited and subject to wheel-clamping penalties starting October 22, 2026.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Administration',
        category: 'Circular',
        createdAt: now.subtract(const Duration(hours: 17)),
        aiSummary: 'Circular enforcing parking stickers and zero tolerance for parking in fire lanes or pedestrian walkways from October 22, 2026.',
        attachments: const ['Official_Circular_Gazette.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 39,
        title: 'Circular: Code of Conduct & Classroom Decorum Regulations',
        description: 'Students must observe professional decorum during instructional hours. Mobile phones must be silenced inside classrooms, laboratories, and the central library. Unauthorized video recording during lectures is strictly forbidden.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Administration',
        category: 'Circular',
        createdAt: now.subtract(const Duration(hours: 19)),
        aiSummary: 'Circular outlining classroom decorum rules, mandatory silent mobile devices, and prohibition of unauthorized lecture recordings.',
        attachments: const ['Official_Circular_Gazette.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 40,
        title: 'Semester Tuition & Examination Fee Online Payment Notification',
        description: 'The online ERP payment portal is open for remitting tuition and university examination fees for the upcoming semester. Remit payments via UPI, Net Banking, or Debit Cards without transaction fees before October 25, 2026 at 11:59 PM.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Finance',
        category: 'Fee Payment',
        createdAt: now.subtract(const Duration(hours: 21)),
        aiSummary: 'Online ERP portal open for semester tuition and university exam fee payments without convenience charges until October 25, 2026 at 11:59 PM.',
        attachments: const ['Exam_Timetable_Final.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 41,
        title: 'Government Scholarship (SSP/NSP) Document Verification Window',
        description: 'Students who applied for Post-Matric, Vidyasiri, SSP, or National Scholarship Portal (NSP) schemes must submit original income certificates and bank passbooks to the Accounts Section before October 30, 2026 at 4:00 PM for institutional verification.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Finance',
        category: 'Fee Payment',
        createdAt: now.subtract(const Duration(hours: 23)),
        aiSummary: 'Accounts section verification for SSP and NSP scholarship applicants open until October 30, 2026 at 4:00 PM; submit income certificates.',
        attachments: const ['Fee_Structure_2026.pdf', 'Scholarship_Application.pdf'],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 42,
        title: 'Hostel Accommodation & Campus Bus Transport Pass Renewal Schedule',
        description: 'The Accounts Office reminds hostellers and day-scholars to clear the second installment of hostel fees and renew bus transport passes before October 31, 2026 at 5:00 PM to ensure uninterrupted boarding and transit facilities.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        creatorRole: 'College Admin',
        department: 'Finance',
        category: 'Fee Payment',
        createdAt: now.subtract(const Duration(hours: 25)),
        aiSummary: 'Deadline for second installment of hostel fees and college bus pass renewals on October 31, 2026 at 5:00 PM.',
        attachments: const [],
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 99,
        title: 'Draft Notice: Guest Lecture on Distributed Cloud Systems',
        description: 'Draft proposal for hosting an expert talk by AWS Lead Architect next Friday in Auditorium 2.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PENDING_APPROVAL',
        creatorName: 'Dr. B Kursheed',
        creatorRole: 'Teacher',
        department: 'AIML',
        category: 'Academic',
        createdAt: now.subtract(const Duration(hours: 2)),
        aiSummary: 'Pending HoD approval for guest lecture on Cloud Systems next Friday.',
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
      AnnouncementModel(
        id: 100,
        title: 'Archived: Mid-Term Examination Retest Guidelines & Instructions',
        description: 'Official guidelines for students eligible for the Mid-Term Retests. Submissions must be approved by respective HoDs before the deadline.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'ARCHIVED',
        creatorName: 'Controller of Examinations',
        creatorRole: 'HoD',
        department: 'Examinations',
        category: 'Examination',
        createdAt: now.subtract(const Duration(days: 12)),
        aiSummary: 'Archived circular: Mid-term retest instructions and HoD approval requirements.',
        deliverSpeaker: false,
        deliverInApp: true,
        deliverPush: true,
      ),
    ];
  }
}
