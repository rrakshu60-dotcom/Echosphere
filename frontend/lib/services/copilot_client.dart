import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/screens/announcements/create_announcement_dialog.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/utils/logger.dart';
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

    switch (screen) {
      case 'speaker_queue':
      case 'speakers':
        Get.toNamed('/speaker-queue');
        return true;

      case 'announcement_management':
      case 'moderation':
        Get.toNamed('/announcement-management');
        return true;

      case 'approval_queue':
      case 'approvals':
        Get.toNamed('/approval-queue');
        return true;

      case 'user_management':
      case 'users':
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
    final action = params['action'] as String? ?? 'advance';
    final nodeId = params['node_id'];

    if (nodeId is int) {
      await EchosphereApiService().controlSpeakerNode(nodeId, command: action.toUpperCase());
    } else {
      await EchosphereApiService().advanceSpeakerQueue();
    }

    Get.snackbar(
      'Speaker Hardware',
      'Dispatched action: $action',
      snackPosition: SnackPosition.BOTTOM,
      duration: const Duration(seconds: 2),
    );
    return true;
  }
}
