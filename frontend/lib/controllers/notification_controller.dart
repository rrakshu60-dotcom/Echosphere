import 'dart:convert';
import 'dart:io';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/screens/announcements/announcement_detail_page.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/utils/campus_time.dart';

class NotificationController extends GetxController {
  final RxSet<int> readIds = <int>{}.obs;
  final RxList<Map<String, dynamic>> liveNotifications = <Map<String, dynamic>>[].obs;
  final RxBool isLoading = false.obs;
  final RxBool showOnlyUnread = true.obs;
  final RxString historySearchQuery = ''.obs;
  final RxString historyTypeFilter = 'All'.obs;

  @override
  void onInit() {
    super.onInit();
    _loadReadStateFromDisk();
    fetchBackendNotifications();
  }

  Future<void> fetchBackendNotifications() async {
    try {
      final res = await EchosphereApiService().getNotifications();
      if (res.isNotEmpty) {
        final annCtrl = Get.isRegistered<AnnouncementController>()
            ? Get.find<AnnouncementController>()
            : Get.put(AnnouncementController());

        final mapped = res.map((n) {
          final annId = n['announcement_id'] as int?;
          AnnouncementModel? matchedAnn;
          if (annId != null) {
            final idx = annCtrl.announcements.indexWhere((a) => a.id == annId);
            if (idx != -1) matchedAnn = annCtrl.announcements[idx];
          }

          final priority = (n['priority'] ?? 'NORMAL').toString().toUpperCase();
          final typeStr = priority == 'EMERGENCY'
              ? 'EMERGENCY'
              : ((n['category'] ?? '').toString().toLowerCase().contains('placement')
                  ? 'PLACEMENT'
                  : 'APPROVAL');

          final isReadVal = n['is_read'] == true;
          final notifId = n['id'] as int;
          // The server keeps read / unread, so it wins over this device's copy
          if (isReadVal) {
            readIds.add(notifId);
          } else {
            readIds.remove(notifId);
          }

          return {
            'id': notifId,
            'announcement_id': annId,
            'title': n['title'] ?? (matchedAnn?.title ?? 'Campus Announcement'),
            'message': n['message'] ?? (matchedAnn?.description ?? ''),
            'type': typeStr,
            'time': n['created_at'] != null
                ? parseServerTime(n['created_at']) ?? DateTime.now()
                : DateTime.now(),
            'announcement': matchedAnn,
          };
        }).toList();

        liveNotifications.assignAll(mapped);
        update();
      }
    } catch (e) {
      debugPrint('Live notification fetch fallback: $e');
    }
  }

  // Derive notifications from live database records if available, with resilient local fallback
  List<Map<String, dynamic>> get allNotifications {
    if (liveNotifications.isNotEmpty) {
      return liveNotifications;
    }

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

  Future<void> _loadReadStateFromDisk() async {
    try {
      if (kIsWeb) {
        final prefs = await SharedPreferences.getInstance();
        final list = prefs.getStringList('read_notification_ids') ?? [];
        readIds.assignAll(list.map((e) => int.parse(e)).toSet());
        return;
      }
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/notifications_read_state.json');
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
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('read_notification_ids', readIds.map((e) => e.toString()).toList());
      if (!kIsWeb) {
        final dir = await getApplicationDocumentsDirectory();
        final file = File('${dir.path}/notifications_read_state.json');
        await file.writeAsString(jsonEncode(readIds.toList()));
      }
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

      // Background async backend sync
      EchosphereApiService().markNotificationRead(id).catchError((_) {});
    }
  }

  void markAsUnread(int id) {
    if (readIds.contains(id)) {
      readIds.remove(id);
      readIds.refresh();
      _saveReadStateToDisk();
      update();
      EchosphereApiService().markNotificationUnread(id).catchError((_) {});
    }
  }

  void markAllAsRead() {
    for (var n in allNotifications) {
      readIds.add(n['id'] as int);
    }
    readIds.refresh();
    _saveReadStateToDisk();
    update();

    // Background async backend sync
    EchosphereApiService().markAllNotificationsRead().catchError((_) {});
  }

  /// Clears History: deletes the read alerts on the server and removes them here (it used to mark
  /// everything unread instead). Returns false if the server could not be reached.
  Future<bool> clearAllHistory() async {
    try {
      await EchosphereApiService().clearReadNotifications();
    } catch (_) {
      return false;
    }
    liveNotifications.removeWhere((n) => readIds.contains(n['id']));
    readIds.clear();
    readIds.refresh();
    _saveReadStateToDisk();
    update();
    return true;
  }

  void toggleFilter(bool onlyUnread) {
    showOnlyUnread.value = onlyUnread;
  }

  void openNotificationDetail(Map<String, dynamic> notification) {
    final id = notification['id'] as int;
    markAsRead(id);

    final announcement = notification['announcement'] as AnnouncementModel?;
    if (announcement != null) {
      Get.key.currentState?.push(
        MaterialPageRoute(builder: (_) => AnnouncementDetailPage(announcement: announcement)),
      );
    }
  }
}
