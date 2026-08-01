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

  @override
  void onInit() {
    super.onInit();
    _loadReadStateFromDisk();
  }

  // Derive notifications strictly from real active app announcements (zero dummy data)
  List<Map<String, dynamic>> get notifications {
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
    return notifications.where((n) => !isRead(n['id'] as int)).length;
  }

  void markAsRead(int id) {
    if (!readIds.contains(id)) {
      readIds.add(id);
      _saveReadStateToDisk();
    }
  }

  void markAllAsRead() {
    for (var n in notifications) {
      readIds.add(n['id'] as int);
    }
    _saveReadStateToDisk();
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
