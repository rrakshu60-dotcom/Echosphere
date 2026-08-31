import 'dart:convert';
import 'dart:io';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/screens/announcements/announcement_detail_page.dart';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:path_provider/path_provider.dart';

class NotificationController extends GetxController {
  final RxSet<int> readIds = <int>{}.obs;
  final RxBool isLoading = false.obs;
  final RxBool showOnlyUnread = true.obs;
  final RxString historySearchQuery = ''.obs;
  final RxString historyTypeFilter = 'All'.obs;

  @override
  void onInit() {
    super.onInit();
    _loadReadStateFromDisk();
  }

  // Derive notifications strictly from real active app announcements (zero dummy data)
  List<Map<String, dynamic>> get allNotifications {
    final annCtrl = Get.isRegistered<AnnouncementController>()
        ? Get.find<AnnouncementController>()
        : Get.put(AnnouncementController());

    return annCtrl.announcements.map((a) {
      final typeStr = a.priority == 'EMERGENCY'
          ? 'EMERGENCY'
          : (a.category.toLowerCase().contains('placement')
              ? 'PLACEMENT'
              : 'APPROVAL');

      return {
        'id': a.id,
        'title': a.title,
        'message': a.aiSummary ?? a.description,
        'type': typeStr,
        'time': a.createdAt,
        'announcement': a,
      };
    }).toList();
  }

  List<Map<String, dynamic>> get unreadNotifications {
    return allNotifications.where((n) => !isRead(n['id'] as int)).toList();
  }

  List<Map<String, dynamic>> get readHistory {
    return allNotifications.where((n) => isRead(n['id'] as int)).toList();
  }

  List<Map<String, dynamic>> get filteredHistory {
    final query = historySearchQuery.value.trim().toLowerCase();
    final typeFilter = historyTypeFilter.value;

    return readHistory.where((n) {
      final matchesType = typeFilter == 'All' || n['type'] == typeFilter;
      final matchesSearch = query.isEmpty ||
          (n['title'] as String).toLowerCase().contains(query) ||
          (n['message'] as String).toLowerCase().contains(query);
      return matchesType && matchesSearch;
    }).toList();
  }

  List<Map<String, dynamic>> get notifications {
    if (showOnlyUnread.value) {
      return unreadNotifications;
    }
    return allNotifications;
  }

  Future<File> _getStorageFile() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/notifications_read_state.json');
  }

  Future<void> _loadReadStateFromDisk() async {
    try {
      final file = await _getStorageFile();
      if (await file.exists()) {
        final content = await file.readAsString();
        final List<dynamic> list = jsonDecode(content);
        readIds.assignAll(list.map((e) => (e as num).toInt()).toSet());
      }
    } catch (e) {
      debugPrint('Failed to load read notifications state from disk: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> _saveReadStateToDisk() async {
    try {
      final file = await _getStorageFile();
      await file.writeAsString(jsonEncode(readIds.toList()));
    } catch (e) {
      debugPrint('Failed to save read notifications state to disk: $e');
    }
  }

  bool isRead(int id) {
    return readIds.contains(id);
  }

  int get unreadCount {
    return unreadNotifications.length;
  }

  int get historyCount {
    return readHistory.length;
  }

  void markAsRead(int id) {
    if (!readIds.contains(id)) {
      readIds.add(id);
      readIds.refresh();
      _saveReadStateToDisk();
      update();
    }
  }

  void markAsUnread(int id) {
    if (readIds.contains(id)) {
      readIds.remove(id);
      readIds.refresh();
      _saveReadStateToDisk();
      update();
    }
  }

  void markAllAsRead() {
    for (var n in allNotifications) {
      readIds.add(n['id'] as int);
    }
    readIds.refresh();
    _saveReadStateToDisk();
    update();
  }

  void clearAllHistory() {
    readIds.clear();
    readIds.refresh();
    _saveReadStateToDisk();
    update();
  }

  void toggleFilter(bool onlyUnread) {
    showOnlyUnread.value = onlyUnread;
  }

  void openNotificationDetail(Map<String, dynamic> notification) {
    final id = notification['id'] as int;
    markAsRead(id);

    final announcement = notification['announcement'] as AnnouncementModel?;
    if (announcement != null) {
      Get.to(() => AnnouncementDetailPage(announcement: announcement));
    }
  }
}
