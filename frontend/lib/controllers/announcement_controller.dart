import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/services/echosphere_api_service.dart';
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
  final List<String> attachments;
  final bool deliverSpeaker;
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
    this.attachments = const [],
    this.deliverSpeaker = false,
    this.speakerNodeId,
    this.speakerStatus,
    this.playedOnSpeaker = false,
    this.durationSeconds = 15,
  });

  factory AnnouncementModel.fromJson(Map<String, dynamic> json) {
    final catId = json['category_id'] ?? 1;
    String catName = 'Academics';
    if (catId == 2) catName = 'Examinations';
    if (catId == 3) catName = 'Events';
    if (catId == 4) catName = 'Sports';
    if (catId == 5) catName = 'Placements';
    if (catId == 6) catName = 'Emergency';

    final bool delivSpk = json['deliver_speaker'] == true ||
        json['deliverSpeaker'] == true ||
        (json['priority']?.toString().toUpperCase() == 'EMERGENCY');

    return AnnouncementModel(
      id: json['id'] ?? 0,
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      priority: json['priority'] ?? 'NORMAL',
      emergencyLevel: json['emergency_level'] ?? 'NORMAL',
      status: json['status'] ?? 'PUBLISHED',
      creatorName: json['creator_name'] ?? 'Faculty',
      creatorRole: json['creator_role'] ?? json['creator_designation'] ?? json['designation'] ?? json['role'] ?? 'Faculty / Official',
      department: json['department_name'] ?? 'AIML',

      targetAudience: json['target_audience'] ?? 'Entire College',
      category: json['category_name'] ?? catName,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now()
          : DateTime.now(),
      scheduledAt: json['scheduled_at'] != null
          ? DateTime.tryParse(json['scheduled_at'])
          : null,
      aiSummary: json['ai_summary'],
      remarks: json['remarks'],
      attachments: json['attachments'] != null
          ? List<String>.from(json['attachments'])
          : const [],
      deliverSpeaker: delivSpk,
      speakerNodeId: json['speaker_node_id'] ?? json['speakerNodeId'],
      speakerStatus: json['speaker_status'] ?? json['speakerStatus'] ?? (delivSpk ? 'Queued' : null),
      playedOnSpeaker: json['played_on_speaker'] == true || json['playedOnSpeaker'] == true,
      durationSeconds: json['duration_seconds'] ?? json['durationSeconds'] ?? 15,
    );
  }

  AnnouncementModel copyWith({
    int? id,
    String? title,
    String? description,
    String? priority,
    String? emergencyLevel,
    String? status,
    String? creatorName,
    String? department,
    String? targetAudience,
    String? category,
    DateTime? createdAt,
    DateTime? scheduledAt,
    String? aiSummary,
    String? remarks,
    List<String>? attachments,
    bool? deliverSpeaker,
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
      department: department ?? this.department,
      targetAudience: targetAudience ?? this.targetAudience,
      category: category ?? this.category,
      createdAt: createdAt ?? this.createdAt,
      scheduledAt: scheduledAt ?? this.scheduledAt,
      aiSummary: aiSummary ?? this.aiSummary,
      remarks: remarks ?? this.remarks,
      attachments: attachments ?? this.attachments,
      deliverSpeaker: deliverSpeaker ?? this.deliverSpeaker,
      speakerNodeId: speakerNodeId ?? this.speakerNodeId,
      speakerStatus: speakerStatus ?? this.speakerStatus,
      playedOnSpeaker: playedOnSpeaker ?? this.playedOnSpeaker,
      durationSeconds: durationSeconds ?? this.durationSeconds,
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
  static int _idCounter = 0;

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
    'Circular',
    'Emergency',
    'Sports',
    'Cultural',
    'Fee Payment',
    'Holiday',
    'Miscellaneous',
  ];

  @override
  void onInit() {
    super.onInit();
    fetchAnnouncements();
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
      // Semester 1, 2 -> 1st Year
      // Semester 3, 4 -> 2nd Year
      // Semester 5, 6 -> 3rd Year
      // Semester 7, 8 -> 4th Year
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

  final Map<int, String> _statusOverrides = {};

  Future<void> _loadStatusOverrides() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final keys = prefs.getKeys().where((k) => k.startsWith('notice_override_'));
      for (var key in keys) {
        final idStr = key.replaceFirst('notice_override_', '');
        final id = int.tryParse(idStr);
        if (id != null) {
          _statusOverrides[id] = prefs.getString(key) ?? 'PUBLISHED';
        }
      }
    } catch (_) {}
  }

  void _applyStatusOverrides() {
    final list = _rawAnnouncements.toList();
    for (int i = 0; i < list.length; i++) {
      final item = list[i];
      if (_statusOverrides.containsKey(item.id)) {
        final newStatus = _statusOverrides[item.id]!;
        list[i] = AnnouncementModel(
          id: item.id,
          title: item.title,
          description: item.description,
          priority: item.priority,
          emergencyLevel: item.emergencyLevel,
          status: newStatus,
          creatorName: item.creatorName,
          department: item.department,
          targetAudience: item.targetAudience,
          category: item.category,
          createdAt: item.createdAt,
          scheduledAt: item.scheduledAt,
          aiSummary: item.aiSummary,
          remarks: newStatus == 'PUBLISHED'
              ? 'Approved & Published'
              : 'Rejected by Administrator',
        );
      }
    }
    _rawAnnouncements.value = list;
  }

  Future<void> fetchAnnouncements() async {
    isLoading.value = true;
    await _loadStatusOverrides();
    if (!Get.testMode) {
      try {
        final data = await EchosphereApiService().getAnnouncements();
        if (data.isNotEmpty) {
          _rawAnnouncements.value = data
              .map((e) => AnnouncementModel.fromJson(e as Map<String, dynamic>))
              .toList();
          _applyStatusOverrides();
          isLoading.value = false;
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
    _applyStatusOverrides();
    isLoading.value = false;
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
    final filtered = _rawAnnouncements
        .where((a) => a.status == 'SUBMITTED' || a.status == 'DRAFT' || a.status == 'PENDING_APPROVAL')
        .toList();
    return _applySort(filtered);
  }

  List<AnnouncementModel> get mySubmissions {
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
    _statusOverrides[id] = 'PUBLISHED';
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('notice_override_$id', 'PUBLISHED');
    } catch (_) {}

    try {
      await EchosphereApiService().approveAnnouncement(id, remarks: remarks);
    } catch (_) {}

    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = old.copyWith(
        status: 'PUBLISHED',
        remarks: remarks ?? 'Approved by Executive Administrator',
        speakerStatus: old.deliverSpeaker ? 'Queued' : old.speakerStatus,
      );
      _rawAnnouncements.refresh();
      update();
    }
    return true;
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
    _statusOverrides[id] = 'REJECTED';
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('notice_override_$id', 'REJECTED');
    } catch (_) {}

    try {
      await EchosphereApiService().rejectAnnouncement(id, remarks: remarks);
    } catch (_) {}

    final idx = _rawAnnouncements.indexWhere((a) => a.id == id);
    if (idx != -1) {
      final old = _rawAnnouncements[idx];
      _rawAnnouncements[idx] = AnnouncementModel(
        id: old.id,
        title: old.title,
        description: old.description,
        priority: old.priority,
        emergencyLevel: old.emergencyLevel,
        status: 'REJECTED',
        creatorName: old.creatorName,
        department: old.department,
        category: old.category,
        createdAt: old.createdAt,
        aiSummary: old.aiSummary,
        remarks: remarks,
      );
      _rawAnnouncements.refresh();
    }
    return true;
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
        title: 'EMERGENCY: Heavy Rainfall Alert - Campus Closed Today',
        description:
            'Due to severe weather warnings and flooding in the city, all offline classes and lab sessions are suspended for today. Online classes will resume as per schedule.',
        priority: 'EMERGENCY',
        emergencyLevel: 'CRITICAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. Principal',
        department: 'Institution',
        category: 'Emergency',
        createdAt: now.subtract(const Duration(minutes: 30)),
        aiSummary: 'Campus closed today due to heavy rain. Online classes continue as scheduled.',
      ),
      AnnouncementModel(
        id: 2,
        title: 'End-Semester Lab Examination Timetable (5th & 7th Sem AIML)',
        description:
            'The detailed schedule for the 5th and 7th Semester AIML Practical Examinations has been published. All students must bring their signed lab records and college ID cards.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'AIML HoD',
        department: 'AIML',
        category: 'Examination',
        createdAt: now.subtract(const Duration(hours: 2)),
        aiSummary: 'Lab exam schedule released for 5th & 7th Sem AIML. Mandatory ID & records required.',
      ),
      AnnouncementModel(
        id: 3,
        title: 'Campus Placement Drive: Google & Microsoft Registration Open',
        description:
            'Registration is now open for the upcoming campus recruitment drive. Eligible streams: AIML, CSE, ISE, ECE with CGPA 7.5 and above without active backlogs.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Placement Cell',
        department: 'Placements',
        category: 'Placement',
        createdAt: now.subtract(const Duration(hours: 3)),
        aiSummary: 'Registration open for Google & Microsoft placement drive for eligible AIML/CSE/ISE/ECE students.',
      ),
      AnnouncementModel(
        id: 4,
        title: 'Annual Technical Symposium - HackEcho 2026',
        description:
            'Register your teams for HackEcho 2026, a 24-hour national level hackathon featuring prizes worth ₹1,50,000. Tracks include AI/ML, CyberSecurity, and Web3.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. B Kursheed',
        department: 'AIML',
        category: 'Event',
        createdAt: now.subtract(const Duration(hours: 4)),
        aiSummary: 'HackEcho 2026 24hr Hackathon registrations open with prizes worth ₹1.5 Lakhs.',
      ),
      AnnouncementModel(
        id: 5,
        title: 'Guest Lecture on Generative AI & Large Language Models',
        description:
            'Department of AIML is hosting an expert guest lecture on GenAI architecture and LLM fine-tuning by Google Senior AI Research Scientist in Seminar Hall 1.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Dr. B Kursheed',
        department: 'AIML',
        category: 'Academic',
        createdAt: now.subtract(const Duration(hours: 5)),
        aiSummary: 'Expert talk on GenAI & LLMs by Google AI Lead today at 2:00 PM in Seminar Hall 1.',
      ),
      AnnouncementModel(
        id: 6,
        title: 'Circular: Biometric Attendance & Identity Card Compliance',
        description:
            'All faculty, staff, and students are required to complete biometric verification at the main gate. Wearing college ID cards is strictly mandatory on campus premise.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'College Admin',
        department: 'Administration',
        category: 'Circular',
        createdAt: now.subtract(const Duration(hours: 6)),
        aiSummary: 'Mandatory biometric verification and ID card compliance notice for all campus members.',
      ),
      AnnouncementModel(
        id: 7,
        title: 'VTU Inter-College Cricket Tournament Squad Selection Trials',
        description:
            'Selection trials for the college cricket team participating in the upcoming VTU State Level Tournament will take place today at the main sports ground.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Sports Director',
        department: 'Sports',
        category: 'Sports',
        createdAt: now.subtract(const Duration(hours: 7)),
        aiSummary: 'Cricket team selection trials for VTU tournament today at 3:30 PM on main ground.',
      ),
      AnnouncementModel(
        id: 8,
        title: 'Cultural Fest "Aura 2026" Music & Dance Auditions',
        description:
            'Auditions for Western/Classical dance and vocal music performances for the annual cultural extravaganza Aura 2026 will start at 4 PM in the Amphitheatre.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Cultural Committee',
        department: 'Cultural',
        category: 'Cultural',
        createdAt: now.subtract(const Duration(hours: 8)),
        aiSummary: 'Auditions for Aura 2026 fest dance and music performances today at 4:00 PM.',
      ),
      AnnouncementModel(
        id: 9,
        title: 'Notification: Even Semester Tuition Fee Payment Portal Active',
        description:
            'The online payment portal for 2026 Even Semester tuition and examination fee is now live. Students can pay via UPI, NetBanking, or Credit Cards without late fee.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Accounts Office',
        department: 'Finance',
        category: 'Fee Payment',
        createdAt: now.subtract(const Duration(hours: 9)),
        aiSummary: 'Online fee payment portal live for Even Semester tuition and VTU exam fees.',
      ),
      AnnouncementModel(
        id: 10,
        title: 'Institutional Holiday Announcement: General Election Day',
        description:
            'In accordance with state government directives, the institution will remain closed on Friday for polling. Examinations scheduled for that day are postponed.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Principal Office',
        department: 'Administration',
        category: 'Holiday',
        createdAt: now.subtract(const Duration(hours: 10)),
        aiSummary: 'College holiday declared for upcoming Election Friday. Exams rescheduled.',
      ),
      AnnouncementModel(
        id: 11,
        title: 'Miscellaneous: Recovered Laptop Charger & Earbuds at Central Library',
        description:
            'A Dell 65W USB-C charger and a pair of wireless earbuds were found in the 2nd floor library reading room. Owner can collect them from the Chief Librarian office.',
        priority: 'LOW',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Chief Librarian',
        department: 'Library',
        category: 'Miscellaneous',
        createdAt: now.subtract(const Duration(hours: 11)),
        aiSummary: 'Lost items (USB-C charger & earbuds) available at Chief Librarian office.',
      ),
      AnnouncementModel(
        id: 12,
        title: 'Draft Notice: Guest Lecture on Distributed Cloud Systems',
        description:
            'Draft proposal for hosting an expert talk by AWS Lead Architect next Friday in Auditorium 2.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'SUBMITTED',
        creatorName: 'Dr. B Kursheed',
        department: 'AIML',
        category: 'Academic',
        createdAt: now.subtract(const Duration(hours: 2)),
        aiSummary: 'Pending HoD approval for guest lecture on Cloud Systems next Friday.',
      ),
      AnnouncementModel(
        id: 13,
        title: 'Archived: Mid-Term Examination Retest Guidelines & Instructions',
        description:
            'Official guidelines for students eligible for the Mid-Term Retests. Submissions must be approved by respective HoDs before the deadline.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'ARCHIVED',
        creatorName: 'Academic Controller',
        department: 'Examinations',
        category: 'Examination',
        createdAt: now.subtract(const Duration(days: 12)),
        aiSummary: 'Archived circular: Mid-term retest instructions and HoD approval requirements.',
      ),
    ];
  }
}
