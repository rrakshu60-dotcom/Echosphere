import 'package:anymex/services/echosphere_api_service.dart';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';

class AnnouncementModel {
  final int id;
  final String title;
  final String description;
  final String priority; // EMERGENCY, HIGH, NORMAL, LOW
  final String emergencyLevel;
  final String status; // DRAFT, SUBMITTED, APPROVED, REJECTED, PUBLISHED, ARCHIVED
  final String creatorName;
  final String department;
  final String category;
  final DateTime createdAt;
  final String? aiSummary;
  final String? remarks;

  AnnouncementModel({
    required this.id,
    required this.title,
    required this.description,
    required this.priority,
    required this.emergencyLevel,
    required this.status,
    required this.creatorName,
    required this.department,
    required this.category,
    required this.createdAt,
    this.aiSummary,
    this.remarks,
  });

  factory AnnouncementModel.fromJson(Map<String, dynamic> json) {
    final catId = json['category_id'] ?? 1;
    String catName = 'Academics';
    if (catId == 2) catName = 'Examinations';
    if (catId == 3) catName = 'Events';
    if (catId == 4) catName = 'Sports';
    if (catId == 5) catName = 'Placements';
    if (catId == 6) catName = 'Emergency';

    return AnnouncementModel(
      id: json['id'] ?? 0,
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      priority: json['priority'] ?? 'NORMAL',
      emergencyLevel: json['emergency_level'] ?? 'NORMAL',
      status: json['status'] ?? 'PUBLISHED',
      creatorName: json['creator_name'] ?? 'Faculty',
      department: json['department_name'] ?? 'CSE',
      category: json['category_name'] ?? catName,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now()
          : DateTime.now(),
      aiSummary: json['ai_summary'],
      remarks: json['remarks'],
    );
  }
}

class AnnouncementController extends GetxController {
  final RxList<AnnouncementModel> _rawAnnouncements = <AnnouncementModel>[].obs;
  final RxString selectedCategory = 'All'.obs;
  final RxString selectedPriority = 'All'.obs;
  final RxString searchQuery = ''.obs;
  final RxBool showTodayOnly = false.obs;
  final RxBool isLoading = false.obs;

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

  // Active announcements restricted strictly to approved/published notices within the current week (past 7 days)
  List<AnnouncementModel> get announcements {
    final now = DateTime.now();
    return _rawAnnouncements.where((a) {
      final diffDays = now.difference(a.createdAt).inDays;
      final isApproved = a.status == 'PUBLISHED' || a.status == 'APPROVED';
      return diffDays <= 7 && isApproved;
    }).toList();
  }

  Future<void> fetchAnnouncements() async {
    isLoading.value = true;
    try {
      final data = await EchosphereApiService().getAnnouncements();
      if (data.isNotEmpty) {
        _rawAnnouncements.value = data
            .map((e) => AnnouncementModel.fromJson(e as Map<String, dynamic>))
            .toList();
        isLoading.value = false;
        return;
      }
    } catch (e) {
      debugPrint('Live backend announcements fetch notice: $e');
    }

    // Seed/Sample announcements for instant demonstration & offline resilience
    if (_rawAnnouncements.isEmpty) {
      _rawAnnouncements.value = _getSampleAnnouncements();
    }
    isLoading.value = false;
  }

  void filterTodayOnly() {
    showTodayOnly.value = true;
    searchQuery.value = '';
    selectedCategory.value = 'All';
    selectedPriority.value = 'All';
  }

  // Archived notices (older than 1 week / 7 days)
  List<AnnouncementModel> get archivedAnnouncements {
    final now = DateTime.now();
    return _rawAnnouncements.where((a) {
      final diffDays = now.difference(a.createdAt).inDays;
      return diffDays > 7;
    }).toList();
  }

  List<AnnouncementModel> get priorityAnnouncements {
    return announcements
        .where((a) =>
            a.priority == 'EMERGENCY' ||
            a.priority == 'HIGH' ||
            a.emergencyLevel == 'CRITICAL')
        .toList();
  }

  List<AnnouncementModel> get todayAnnouncements {
    final now = DateTime.now();
    return announcements.where((a) {
      return a.createdAt.year == now.year &&
          a.createdAt.month == now.month &&
          a.createdAt.day == now.day;
    }).toList();
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
    return _rawAnnouncements
        .where((a) => a.status == 'SUBMITTED' || a.status == 'DRAFT' || a.status == 'PENDING_APPROVAL')
        .toList();
  }

  List<AnnouncementModel> get mySubmissions {
    return _rawAnnouncements.toList();
  }

  List<AnnouncementModel> get filteredAnnouncements {
    final now = DateTime.now();

    return announcements.where((a) {
      if (showTodayOnly.value) {
        final isToday = a.createdAt.year == now.year &&
            a.createdAt.month == now.month &&
            a.createdAt.day == now.day;
        if (!isToday) return false;
      }

      final selectedCat = selectedCategory.value.toLowerCase();
      final noticeCat = a.category.toLowerCase();

      final matchesCategory = selectedCat == 'all' ||
          noticeCat == selectedCat ||
          noticeCat.replaceAll('s', '') == selectedCat.replaceAll('s', '') ||
          noticeCat.startsWith(selectedCat.replaceAll('s', '')) ||
          selectedCat.startsWith(noticeCat.replaceAll('s', ''));

      final matchesPriority = selectedPriority.value == 'All' ||
          a.priority.toLowerCase() == selectedPriority.value.toLowerCase();

      final query = searchQuery.value.toLowerCase();
      final matchesSearch = query.isEmpty ||
          a.title.toLowerCase().contains(query) ||
          a.description.toLowerCase().contains(query) ||
          a.department.toLowerCase().contains(query);

      return matchesCategory && matchesPriority && matchesSearch;
    }).toList();
  }

  Future<bool> createAnnouncement({
    required String title,
    required String description,
    required String category,
    required String priority,
    required String creatorRole,
    required String creatorName,
    required String department,
  }) async {
    isLoading.value = true;

    int catId = 1;
    if (category == 'Examinations') catId = 2;
    if (category == 'Events') catId = 3;
    if (category == 'Sports') catId = 4;
    if (category == 'Placements') catId = 5;
    if (category == 'Emergency') catId = 6;

    // Roles Teacher/HoD create SUBMITTED or APPROVED based on hierarchy
    final initialStatus = (creatorRole == 'Principal' ||
            creatorRole == 'College Admin' ||
            creatorRole == 'Developer')
        ? 'PUBLISHED'
        : 'SUBMITTED';

    try {
      final res = await EchosphereApiService().createAnnouncement(
        title: title,
        description: description,
        categoryId: catId,
        priority: priority,
        emergencyLevel: priority == 'EMERGENCY' ? 'CRITICAL' : 'NORMAL',
      );
      if (res.isNotEmpty) {
        await fetchAnnouncements();
        isLoading.value = false;
        return true;
      }
    } catch (e) {
      debugPrint('Error creating via API, adding locally: $e');
    }

    final newNotice = AnnouncementModel(
      id: announcements.length + 101,
      title: title,
      description: description,
      priority: priority,
      emergencyLevel: priority == 'EMERGENCY' ? 'CRITICAL' : 'NORMAL',
      status: initialStatus,
      creatorName: creatorName,
      department: department,
      category: category,
      createdAt: DateTime.now(),
      aiSummary: 'AI Summary: $title - Important update for $department department.',
    );

    announcements.insert(0, newNotice);
    isLoading.value = false;
    return true;
  }

  Future<bool> approveAnnouncement(int id, {String? remarks}) async {
    try {
      await EchosphereApiService().approveAnnouncement(id, remarks: remarks);
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
        status: 'PUBLISHED',
        creatorName: old.creatorName,
        department: old.department,
        category: old.category,
        createdAt: old.createdAt,
        aiSummary: old.aiSummary,
        remarks: remarks ?? 'Approved by Administrator',
      );
      _rawAnnouncements.refresh();
    }
    return true;
  }

  Future<bool> rejectAnnouncement(int id, {required String remarks}) async {
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
        createdAt: DateTime.now().subtract(const Duration(hours: 1)),
        aiSummary: 'Campus closed today due to heavy rain. Online classes continue as scheduled.',
      ),
      AnnouncementModel(
        id: 2,
        title: 'End-Semester Lab Examination Timetable (5th & 7th Sem CSE)',
        description:
            'The detailed schedule for the 5th and 7th Semester CSE Practical Examinations has been published. All students must bring their signed lab records and college ID cards.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'CSE HoD',
        department: 'CSE',
        category: 'Examinations',
        createdAt: DateTime.now().subtract(const Duration(hours: 4)),
        aiSummary: 'Lab exam schedule released for 5th & 7th Sem CSE. Mandatory ID & records required.',
      ),
      AnnouncementModel(
        id: 3,
        title: 'Campus Placement Drive: Google & Microsoft Registration Open',
        description:
            'Registration is now open for the upcoming campus recruitment drive. Eligible streams: CSE, ISE, ECE with CGPA 7.5 and above without active backlogs.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Placement Cell',
        department: 'Placements',
        category: 'Placements',
        createdAt: DateTime.now().subtract(const Duration(hours: 12)),
        aiSummary: 'Registration open for Google & Microsoft placement drive for eligible CSE/ISE/ECE students.',
      ),
      AnnouncementModel(
        id: 4,
        title: 'Annual Technical Symposium - HackEcho 2026',
        description:
            'Register your teams for HackEcho 2026, a 24-hour national level hackathon featuring prizes worth ₹1,50,000. Tracks include AI/ML, CyberSecurity, and Web3.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'CSE Teacher',
        department: 'CSE',
        category: 'Events',
        createdAt: DateTime.now().subtract(const Duration(days: 1)),
        aiSummary: 'HackEcho 2026 24hr Hackathon registrations open with prizes worth ₹1.5 Lakhs.',
      ),
      AnnouncementModel(
        id: 5,
        title: 'Draft Notice: Guest Lecture on Distributed Cloud Systems',
        description:
            'Draft proposal for hosting an expert talk by AWS Lead Architect next Friday in Auditorium 2.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'SUBMITTED',
        creatorName: 'CSE Teacher',
        department: 'CSE',
        category: 'Academics',
        createdAt: DateTime.now().subtract(const Duration(hours: 2)),
        aiSummary: 'Pending HoD approval for guest lecture on Cloud Systems next Friday.',
      ),
      AnnouncementModel(
        id: 6,
        title: 'Archived: Mid-Term Examination Retest Guidelines & Instructions',
        description:
            'Official guidelines for students eligible for the Mid-Term Retests. Submissions must be approved by respective HoDs before the deadline.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'ARCHIVED',
        creatorName: 'Academic Controller',
        department: 'Examinations',
        category: 'Examinations',
        createdAt: DateTime.now().subtract(const Duration(days: 12)),
        aiSummary: 'Archived circular: Mid-term retest instructions and HoD approval requirements.',
      ),
      AnnouncementModel(
        id: 7,
        title: 'Archived: Campus Sports Meet Registration & Athletic Trials',
        description:
            'All undergraduate and postgraduate students are invited to register for the annual inter-departmental athletic events.',
        priority: 'NORMAL',
        emergencyLevel: 'NORMAL',
        status: 'ARCHIVED',
        creatorName: 'Physical Education Dept',
        department: 'Sports',
        category: 'Sports',
        createdAt: DateTime.now().subtract(const Duration(days: 22)),
        aiSummary: 'Archived notification: Annual sports meet trial schedules and team registrations.',
      ),
    ];
  }
}
