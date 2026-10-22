import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Thrown by a refresher when the backend says the session is over (HTTP 401).
class SessionEndedException implements Exception {
  const SessionEndedException();
}

/// Holds the signed-in session: a short-lived access token plus a refresh key that the backend
/// replaces on every refresh. Saved on the device only when "Remember me" was ticked.
///
/// Refreshes are shared: while one is running, every caller waits for it, because the backend
/// accepts each refresh key only once.
class SessionManager {
  static const _storageKey = 'auth_session_v2';
  static const _legacyStorageKey = 'auth_session';

  /// Sends the refresh key to the backend and returns its token response.
  /// Throws [SessionEndedException] when the backend refuses the key.
  final Future<Map<String, dynamic>> Function(String refreshKey) refresher;

  /// Called once when the backend ends the session (expired, signed out elsewhere, disabled).
  VoidCallback? onSignedOut;

  String? _accessToken;
  String? _refreshToken;
  int? _sessionId;
  bool _rememberMe = false;
  Map<String, dynamic>? _user;
  Future<bool>? _refreshing;

  SessionManager({required this.refresher});

  String? get accessToken => _accessToken;
  String? get refreshToken => _refreshToken;
  int? get sessionId => _sessionId;
  bool get rememberMe => _rememberMe;
  bool get isActive => _refreshToken != null;

  /// Starts a session from the backend's sign-in response.
  Future<void> start(Map<String, dynamic> tokenResponse, {required bool rememberMe, required Map<String, dynamic> user}) async {
    _rememberMe = rememberMe;
    _user = user;
    _apply(tokenResponse);
    await _persist();
  }

  /// Loads a remembered session saved by an earlier run. Returns the saved user, or null.
  Future<Map<String, dynamic>?> restore() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      // Logins saved before sessions existed carry a 30-day token and no refresh key: drop them.
      await prefs.remove(_legacyStorageKey);
      final raw = prefs.getString(_storageKey);
      if (raw == null) return null;
      final data = jsonDecode(raw) as Map<String, dynamic>;
      if (data['refresh_token'] == null || data['user'] == null) return null;
      _accessToken = data['access_token'] as String?;
      _refreshToken = data['refresh_token'] as String;
      _sessionId = data['session_id'] as int?;
      _rememberMe = true;
      _user = Map<String, dynamic>.from(data['user'] as Map);
      return _user;
    } catch (e) {
      debugPrint('Saved session could not be read: $e');
      return null;
    }
  }

  /// Gets a new access token with the refresh key. Returns false if it could not;
  /// signs out only when the backend says the session has ended, never on a network error.
  Future<bool> refresh() {
    final running = _refreshing;
    if (running != null) return running;
    final next = _refreshOnce();
    _refreshing = next;
    return next.whenComplete(() => _refreshing = null);
  }

  Future<bool> _refreshOnce() async {
    final key = _refreshToken;
    if (key == null) return false;
    try {
      _apply(await refresher(key));
      await _persist();
      return true;
    } on SessionEndedException {
      await clear();
      onSignedOut?.call();
      return false;
    } catch (e) {
      debugPrint('Session refresh failed (kept signed in): $e');
      return false;
    }
  }

  /// Forgets the session on this device.
  Future<void> clear() async {
    _accessToken = null;
    _refreshToken = null;
    _sessionId = null;
    _rememberMe = false;
    _user = null;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_storageKey);
      await prefs.remove(_legacyStorageKey);
    } catch (_) {}
  }

  void _apply(Map<String, dynamic> res) {
    _accessToken = res['access_token'] as String?;
    _refreshToken = res['refresh_token'] as String?;
    _sessionId = (res['session_id'] as num?)?.toInt() ?? _sessionId;
  }

  Future<void> _persist() async {
    if (!_rememberMe) return;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(
        _storageKey,
        jsonEncode({
          'access_token': _accessToken,
          'refresh_token': _refreshToken,
          'session_id': _sessionId,
          'user': _user,
        }),
      );
    } catch (e) {
      debugPrint('Session could not be saved: $e');
    }
  }
}
