import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:get/get.dart';
import 'package:echosphere/firebase_options.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Ensure Firebase is initialized for background message handler
  try {
    await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  } catch (_) {}
  debugPrint("🔥 [FCM BACKGROUND] Received message: ${message.messageId} - ${message.notification?.title}");
}

class FcmPushService {
  FcmPushService._();
  static final FcmPushService instance = FcmPushService._();

  FirebaseMessaging? _messaging;
  bool _isInitialized = false;
  String? _fcmToken;

  String? get fcmToken => _fcmToken;
  bool get isSupported => kIsWeb || Platform.isAndroid || Platform.isIOS || Platform.isMacOS;

  /// Initializes Firebase and FCM push notification listeners
  Future<void> initialize() async {
    if (_isInitialized) return;
    if (!isSupported) {
      debugPrint("ℹ️ [FCM] Push notifications not natively supported on this desktop platform (Windows/Linux fallback mode).");
      return;
    }

    try {
      // 1. Ensure Firebase Core is initialized
      try {
        await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
      } catch (e) {
        debugPrint("ℹ️ [FCM] Firebase Core already initialized or notes: $e");
      }

      _messaging = FirebaseMessaging.instance;

      // 2. Request user permissions on mobile
      NotificationSettings settings = await _messaging!.requestPermission(
        alert: true,
        announcement: false,
        badge: true,
        carPlay: false,
        criticalAlert: true,
        provisional: false,
        sound: true,
      );

      debugPrint('🔥 [FCM] Notification authorization status: ${settings.authorizationStatus}');

      // 3. Register background handler
      FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

      // 4. Retrieve FCM device registration token
      try {
        _fcmToken = await _messaging!.getToken();
        debugPrint('🔥 [FCM TOKEN] Device Token: $_fcmToken');
      } catch (e) {
        debugPrint('ℹ️ [FCM] Token retrieval note: $e');
      }

      // 5. Subscribe to baseline campus channels
      await _messaging!.subscribeToTopic('all_campus');
      await _messaging!.subscribeToTopic('emergency_broadcasts');
      debugPrint('🔥 [FCM] Subscribed to default topics: all_campus, emergency_broadcasts');

      // 6. Foreground message listener (Shows in-app banner alert)
      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        debugPrint('🔥 [FCM FOREGROUND] Notice arrived: ${message.notification?.title}');
        final title = message.notification?.title ?? message.data['title'] ?? 'Campus Announcement';
        final body = message.notification?.body ?? message.data['body'] ?? 'New notification received';
        snackBar(body, title: title);
      });

      // 7. Background message opened listener (App was in background)
      FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
        debugPrint('🔥 [FCM APP OPENED] User tapped push notification: ${message.data}');
        _navigateToAnnouncementDetail(message.data);
      });

      // 8. Check if app was launched from a terminated state via push notification
      final initialMsg = await _messaging!.getInitialMessage();
      if (initialMsg != null) {
        debugPrint('🔥 [FCM LAUNCH FROM TERMINATED] App opened via push notification: ${initialMsg.data}');
        _navigateToAnnouncementDetail(initialMsg.data);
      }

      _isInitialized = true;
    } catch (e) {
      debugPrint('⚠️ [FCM] Firebase Messaging initialization warning: $e');
    }
  }

  /// Subscribes the authenticated user to their department and role channels
  Future<void> syncUserSubscriptions({String? departmentCode, String? role}) async {
    if (!isSupported || _messaging == null) return;
    try {
      if (departmentCode != null && departmentCode.isNotEmpty && departmentCode.toLowerCase() != 'college-wide') {
        final deptTopic = 'dept_${departmentCode.toLowerCase().trim().replaceAll(' ', '_')}';
        await _messaging!.subscribeToTopic(deptTopic);
        debugPrint('🔥 [FCM] Subscribed to department topic: $deptTopic');
      }
      if (role != null && role.isNotEmpty) {
        final roleTopic = 'role_${role.toLowerCase().trim().replaceAll(' ', '_')}';
        await _messaging!.subscribeToTopic(roleTopic);
        debugPrint('🔥 [FCM] Subscribed to role topic: $roleTopic');
      }
    } catch (e) {
      debugPrint('⚠️ [FCM] Subscription sync warning: $e');
    }
  }

  /// Unsubscribes user from role/department channels on logout
  Future<void> unsubscribeUserSubscriptions({String? departmentCode, String? role}) async {
    if (!isSupported || _messaging == null) return;
    try {
      if (departmentCode != null && departmentCode.isNotEmpty) {
        final deptTopic = 'dept_${departmentCode.toLowerCase().trim().replaceAll(' ', '_')}';
        await _messaging!.unsubscribeFromTopic(deptTopic);
      }
      if (role != null && role.isNotEmpty) {
        final roleTopic = 'role_${role.toLowerCase().trim().replaceAll(' ', '_')}';
        await _messaging!.unsubscribeFromTopic(roleTopic);
      }
    } catch (e) {
      debugPrint('⚠️ [FCM] Unsubscribe warning: $e');
    }
  }

  void _navigateToAnnouncementDetail(Map<String, dynamic> data) {
    final annIdStr = data['announcement_id'];
    if (annIdStr != null) {
      final annId = int.tryParse(annIdStr.toString());
      if (annId != null) {
        Get.toNamed('/announcements/detail', arguments: {'id': annId});
      }
    }
  }
}
