import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';
import 'package:echosphere/controllers/theme.dart';
import 'package:echosphere/screens/announcements/create_announcement_dialog.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/utils/logger.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';

class CopilotClient {
  static final CopilotClient _instance = CopilotClient._internal();
  factory CopilotClient() => _instance;
  CopilotClient._internal();

  /// Execute an in-app action triggered by CopilotKit / Gemma
  Future<bool> executeAction(Map<String, dynamic> actionPayload) async {
    final actionName = actionPayload['action'] as String?;
    final params = Map<String, dynamic>.from(actionPayload['parameters'] ?? {});

    Logger.i("CopilotClient executing action: $actionName with params: $params");

    final auth = Get.isRegistered<AuthController>() ? Get.find<AuthController>() : null;
    final isStudent = (auth?.currentUser.value?.role ?? 'Student').toLowerCase() == 'student';

    if (isStudent &&
        const {
          'control_speaker_queue',
          'set_speaker_volume',
          'approve_notice',
          'reject_notice',
          'delete_notice',
          'create_announcement_draft',
        }.contains(actionName)) {
      snackBar('Students do not have permission to execute this administrative action.', title: 'Access Restricted');
      return false;
    }

    try {
      switch (actionName) {
        case 'navigate':
          return _handleNavigation(params);

        case 'create_announcement_draft':
          return _handleDraftCreation(params);

        case 'toggle_theme':
          return _handleThemeToggle(params);

        case 'control_speaker_queue':
          return await _handleSpeakerControl(params);

        case 'set_speaker_volume':
          return await _handleSetSpeakerVolume(params);

        case 'approve_notice':
          return await _handleApproveNotice(params);

        case 'reject_notice':
          return await _handleRejectNotice(params);

        case 'delete_notice':
          return await _handleDeleteNotice(params);

        case 'filter_notices':
          return _handleFilterNotices(params);

        default:
          Logger.w("Unknown Copilot action: $actionName");
          return false;
      }
    } catch (e) {
      Logger.e("CopilotClient error executing $actionName: $e");
      return false;
    }
  }

  bool _handleNavigation(Map<String, dynamic> params) {
    final screen = (params['screen'] as String? ?? '').toLowerCase();
    final filterCat = params['filter_category'] as String?;
    final filterDept = params['filter_dept'] as String?;

    if (filterCat != null && filterCat.isNotEmpty) {
      try {
        final annCtrl = Get.find<AnnouncementController>();
        annCtrl.selectedCategory.value = filterCat;
      } catch (_) {}
    }

    if (filterDept != null && filterDept.isNotEmpty) {
      try {
        final annCtrl = Get.find<AnnouncementController>();
        annCtrl.searchQuery.value = filterDept;
      } catch (_) {}
    }

    final auth = Get.isRegistered<AuthController>() ? Get.find<AuthController>() : null;
    final isStudent = (auth?.currentUser.value?.role ?? 'Student').toLowerCase() == 'student';

    switch (screen) {
      case 'speaker_queue':
      case 'speakers':
        if (isStudent) return false;
        Get.toNamed('/speaker-queue');
        return true;

      case 'announcement_management':
      case 'moderation':
        if (isStudent) return false;
        Get.toNamed('/announcement-management');
        return true;

      case 'approval_queue':
      case 'approvals':
        if (isStudent) return false;
        Get.toNamed('/approval-queue');
        return true;

      case 'user_management':
      case 'users':
        if (isStudent) return false;
        Get.toNamed('/user-management');
        return true;

      case 'archive':
      case 'history':
        Get.toNamed('/archive');
        return true;

      case 'notifications':
        Get.toNamed('/notifications');
        return true;

      case 'profile':
      case 'profile_settings':
      case 'security_preferences':
      case 'preferences':
      case 'settings':
      case 'smart_notes':
        Get.toNamed('/profile');
        return true;

      case 'notices':
      case 'home':
      default:
        Get.offAllNamed('/home');
        return true;
    }
  }

  bool _handleDraftCreation(Map<String, dynamic> params) {
    final context = Get.context;
    if (context == null) return false;

    showDialog(
      context: context,
      builder: (_) => CreateAnnouncementDialog(
        initialTitle: params['title'] as String? ?? params['topic'] as String?,
        initialContent: params['content'] as String?,
        initialCategory: params['category'] as String?,
      ),
    );
    return true;
  }

  bool _handleThemeToggle(Map<String, dynamic> params) {
    final context = Get.context;
    if (context == null) return false;

    final mode = (params['mode'] as String? ?? 'toggle').toLowerCase();
    final themeProvider = Provider.of<ThemeProvider>(context, listen: false);

    if (mode == 'dark') {
      if (themeProvider.isLightMode) themeProvider.toggleTheme();
    } else if (mode == 'light') {
      if (!themeProvider.isLightMode) themeProvider.toggleTheme();
    } else {
      themeProvider.toggleTheme();
    }
    return true;
  }

  Future<bool> _handleSpeakerControl(Map<String, dynamic> params) async {
    final action = params['action'] as String?;
    final nodeId = params['node_id'];
    // The queue moves by itself: only commands for a named speaker are allowed (no manual advance)
    if (nodeId is! int || action == null) return false;
    await EchosphereApiService().controlSpeakerNode(nodeId, command: action.toUpperCase());

    Get.snackbar(
      'Speaker Hardware',
      'Dispatched action: $action',
      snackPosition: SnackPosition.BOTTOM,
      duration: const Duration(seconds: 2),
    );
    return true;
  }

  Future<bool> _handleSetSpeakerVolume(Map<String, dynamic> params) async {
    final rawVol = params['volume'];
    final volume = (rawVol is num ? rawVol.toInt() : int.tryParse(rawVol?.toString() ?? '80')) ?? 80;
    final clampedVol = volume.clamp(0, 100);
    final targetNode = params['node_id']?.toString() ?? 'ALL';

    final queueCtrl = Get.isRegistered<SpeakerQueueController>() ? Get.find<SpeakerQueueController>() : null;
    final apiService = EchosphereApiService();

    if (targetNode.toUpperCase() == 'ALL' || targetNode.toLowerCase() == 'campus' || targetNode.toLowerCase() == 'all nodes') {
      final nodes = queueCtrl?.speakerNodes ?? await apiService.getSpeakerNodes();
      for (final n in nodes) {
        final id = n['id'];
        if (id is int) {
          await apiService.setSpeakerNodeVolume(id, clampedVol);
        }
      }
      if (queueCtrl != null) {
        for (final n in queueCtrl.speakerNodes) {
          n['volume'] = clampedVol;
        }
        queueCtrl.speakerNodes.refresh();
      }
      snackBar('All campus speaker nodes set to $clampedVol% volume', title: 'Speaker Hardware');
      return true;
    }

    int? resolvedId = int.tryParse(targetNode);
    String nodeName = targetNode;
    final nodes = queueCtrl?.speakerNodes ?? await apiService.getSpeakerNodes();

    if (resolvedId == null) {
      final match = nodes.firstWhereOrNull((n) {
        final name = (n['name'] ?? '').toString().toLowerCase();
        final zone = (n['zone'] ?? '').toString().toLowerCase();
        final query = targetNode.toLowerCase();
        return name.contains(query) || zone.contains(query);
      });
      if (match != null) {
        resolvedId = match['id'] is int ? match['id'] : int.tryParse(match['id'].toString());
        nodeName = match['name']?.toString() ?? 'Speaker Node #$resolvedId';
      }
    }

    if (resolvedId != null) {
      if (queueCtrl != null) {
        await queueCtrl.setNodeVolume(resolvedId, clampedVol, nodeName);
      } else {
        await apiService.setSpeakerNodeVolume(resolvedId, clampedVol);
        snackBar('Volume for $nodeName set to $clampedVol%', title: 'Speaker Hardware');
      }
      return true;
    }

    if (nodes.isNotEmpty && nodes.first['id'] is int) {
      final firstId = nodes.first['id'] as int;
      await apiService.setSpeakerNodeVolume(firstId, clampedVol);
      snackBar('Volume set to $clampedVol% on ${nodes.first['name'] ?? 'Speaker #$firstId'}', title: 'Speaker Hardware');
      return true;
    }

    snackBar('Could not locate speaker node "$targetNode"', title: 'Speaker Hardware');
    return false;
  }

  Future<bool> _handleApproveNotice(Map<String, dynamic> params) async {
    final rawId = params['announcement_id'] ?? params['notice_id'] ?? params['id'];
    final id = rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '');
    if (id == null) {
      snackBar('Missing announcement ID for approval', title: 'Moderation Error');
      return false;
    }

    final remarks = (params['remarks'] as String?) ?? 'Approved via EchoSphere Copilot';
    final annCtrl = Get.isRegistered<AnnouncementController>() ? Get.find<AnnouncementController>() : null;

    if (annCtrl != null) {
      final success = await annCtrl.approveAnnouncement(id, remarks: remarks);
      if (success) {
        snackBar('Announcement #$id officially approved and queued for broadcast!', title: 'Notice Approved');
        return true;
      }
    } else {
      await EchosphereApiService().approveAnnouncement(id, remarks: remarks);
      snackBar('Announcement #$id officially approved!', title: 'Notice Approved');
      return true;
    }
    return false;
  }

  Future<bool> _handleRejectNotice(Map<String, dynamic> params) async {
    final rawId = params['announcement_id'] ?? params['notice_id'] ?? params['id'];
    final id = rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '');
    if (id == null) {
      snackBar('Missing announcement ID for rejection', title: 'Moderation Error');
      return false;
    }

    final remarks = (params['remarks'] as String?) ?? 'Rejected via EchoSphere Copilot: Does not meet submission guidelines';
    final annCtrl = Get.isRegistered<AnnouncementController>() ? Get.find<AnnouncementController>() : null;

    if (annCtrl != null) {
      final success = await annCtrl.rejectAnnouncement(id, remarks: remarks);
      if (success) {
        snackBar('Announcement #$id has been rejected.', title: 'Notice Rejected');
        return true;
      }
    } else {
      await EchosphereApiService().rejectAnnouncement(id, remarks: remarks);
      snackBar('Announcement #$id has been rejected.', title: 'Notice Rejected');
      return true;
    }
    return false;
  }

  Future<bool> _handleDeleteNotice(Map<String, dynamic> params) async {
    final rawId = params['announcement_id'] ?? params['notice_id'] ?? params['id'];
    final id = rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '');
    if (id == null) {
      snackBar('Missing announcement ID for deletion', title: 'Action Error');
      return false;
    }

    final annCtrl = Get.isRegistered<AnnouncementController>() ? Get.find<AnnouncementController>() : null;
    if (annCtrl != null) {
      final success = await annCtrl.deleteAnnouncement(id);
      if (success) {
        snackBar('Announcement #$id permanently removed from feed.', title: 'Notice Deleted');
        return true;
      }
    } else {
      await EchosphereApiService().deleteAnnouncement(id);
      snackBar('Announcement #$id deleted.', title: 'Notice Deleted');
      return true;
    }
    return false;
  }

  bool _handleFilterNotices(Map<String, dynamic> params) {
    final category = params['category'] as String?;
    final dept = params['department'] as String?;
    final priority = params['priority'] as String?;

    final annCtrl = Get.isRegistered<AnnouncementController>() ? Get.find<AnnouncementController>() : null;
    if (annCtrl != null) {
      if (category != null && category.isNotEmpty) {
        annCtrl.selectedCategory.value = category;
      }
      if (dept != null && dept.isNotEmpty) {
        annCtrl.searchQuery.value = dept;
      }
      if (priority != null && priority.isNotEmpty) {
        annCtrl.selectedPriority.value = priority;
      }
    }

    Get.offAllNamed('/home');
    snackBar('Filtering notices: ${category ?? dept ?? priority ?? 'Applied'}', title: 'Notice Feed Filter');
    return true;
  }
}
