import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:get/get.dart';
import 'package:echosphere/firebase_options.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Ensure Firebase is initialized for background message handler
  try {
    await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  } catch (_) {}
  debugPrint("🔥 [FCM BACKGROUND] Received message: ${message.messageId} - ${message.notification?.title}");
}

/// Public half of the project's web push key pair (Firebase console > Cloud Messaging > Web Push certificates).
const _webPushKey = 'BPuxjXbW_edSA2lZ7gV1wF6unLnI0uQ-chY8qNUufRkOe_XMJm4VZa28LaMlyPtMtAZxx5sRgojtWMdOCkYRkyk';

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
        _fcmToken = await _messaging!.getToken(vapidKey: kIsWeb ? _webPushKey : null);
        debugPrint('🔥 [FCM TOKEN] Device Token: $_fcmToken');
      } catch (e) {
        debugPrint('ℹ️ [FCM] Token retrieval note: $e');
      }

      // 5. Topics are subscribed by the server after sign-in (syncUserSubscriptions): browsers can't subscribe
      //    themselves, and the server decides the topics from the account.

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

  /// After sign-in: registers this device's push token with the server, which subscribes it to the account's
  /// topics (whole campus, emergencies, own department).
  Future<void> syncUserSubscriptions({String? departmentCode, String? role}) async {
    if (!isSupported || _messaging == null) return;
    try {
      _fcmToken ??= await _messaging!.getToken(vapidKey: kIsWeb ? _webPushKey : null);
      final token = _fcmToken;
      if (token == null || token.isEmpty) return;
      await EchosphereApiService().registerPushDevice(token, kIsWeb ? 'web' : Platform.operatingSystem);
    } catch (e) {
      debugPrint('⚠️ [FCM] Push registration warning: $e');
    }
  }

  /// On sign-out: deletes this device's push token, so a signed-out device stops receiving campus pushes.
  Future<void> unsubscribeUserSubscriptions({String? departmentCode, String? role}) async {
    if (!isSupported || _messaging == null) return;
    try {
      await _messaging!.deleteToken();
      _fcmToken = null;
    } catch (e) {
      debugPrint('⚠️ [FCM] Token removal warning: $e');
    }
  }

  void _navigateToAnnouncementDetail(Map<String, dynamic> data) {
    final annIdStr = data['announcement_id'];
    if (annIdStr != null) {
      final annId = int.tryParse(annIdStr.toString());
      if (annId != null) {
        Get.toNamed('/announcement?id=$annId');
      }
    }
  }
}
