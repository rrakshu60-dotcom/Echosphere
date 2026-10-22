import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/services/session_manager.dart';

Map<String, dynamic> _loginResponse({String access = 'access-1', String refresh = 'refresh-1', int sid = 41}) => {
      'access_token': access,
      'refresh_token': refresh,
      'session_id': sid,
      'user_id': 7,
      'full_name': 'Test Teacher',
      'role': 'Teacher',
    };

const _user = {'id': 7, 'full_name': 'Test Teacher', 'role': 'Teacher'};

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('a remembered sign-in is saved and comes back after a restart', () async {
    final first = SessionManager(refresher: (_) async => throw UnimplementedError());
    await first.start(_loginResponse(), rememberMe: true, user: _user);
    expect(first.accessToken, 'access-1');
    expect(first.sessionId, 41);

    final afterRestart = SessionManager(refresher: (_) async => throw UnimplementedError());
    final user = await afterRestart.restore();
    expect(user, _user);
    expect(afterRestart.refreshToken, 'refresh-1');
    expect(afterRestart.rememberMe, isTrue);
  });

  test('without remember me nothing is written to the device', () async {
    final sessions = SessionManager(refresher: (_) async => throw UnimplementedError());
    await sessions.start(_loginResponse(), rememberMe: false, user: _user);
    expect(sessions.accessToken, 'access-1');

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getKeys(), isEmpty);
    expect(await SessionManager(refresher: (_) async => {}).restore(), isNull);
  });

  test('an old saved login without a refresh key is discarded', () async {
    SharedPreferences.setMockInitialValues({
      'auth_session': jsonEncode({'remember_me': true, 'token': 'old-30-day-token', 'user': _user}),
    });
    final sessions = SessionManager(refresher: (_) async => {});
    expect(await sessions.restore(), isNull);
    expect(sessions.accessToken, isNull);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.containsKey('auth_session'), isFalse);
  });

  test('refresh swaps in the new token and key and saves them', () async {
    String? sentKey;
    final sessions = SessionManager(refresher: (key) async {
      sentKey = key;
      return _loginResponse(access: 'access-2', refresh: 'refresh-2');
    });
    await sessions.start(_loginResponse(), rememberMe: true, user: _user);

    expect(await sessions.refresh(), isTrue);
    expect(sentKey, 'refresh-1');
    expect(sessions.accessToken, 'access-2');
    expect(sessions.refreshToken, 'refresh-2');

    final restored = SessionManager(refresher: (_) async => {});
    await restored.restore();
    expect(restored.refreshToken, 'refresh-2');
  });

  test('simultaneous refreshes share one call, so the key is not spent twice', () async {
    var calls = 0;
    final gate = Completer<Map<String, dynamic>>();
    final sessions = SessionManager(refresher: (_) {
      calls++;
      return gate.future;
    });
    await sessions.start(_loginResponse(), rememberMe: false, user: _user);

    final a = sessions.refresh();
    final b = sessions.refresh();
    final c = sessions.refresh();
    gate.complete(_loginResponse(access: 'access-2', refresh: 'refresh-2'));
    expect(await Future.wait([a, b, c]), [true, true, true]);
    expect(calls, 1);
  });

  test('when the backend says the session ended, it is cleared and the user is signed out', () async {
    var signedOut = 0;
    final sessions = SessionManager(refresher: (_) async => throw const SessionEndedException());
    sessions.onSignedOut = () => signedOut++;
    await sessions.start(_loginResponse(), rememberMe: true, user: _user);

    expect(await sessions.refresh(), isFalse);
    expect(signedOut, 1);
    expect(sessions.accessToken, isNull);
    expect(await SessionManager(refresher: (_) async => {}).restore(), isNull);
  });

  test('a network failure does not sign anyone out', () async {
    var signedOut = 0;
    final sessions = SessionManager(refresher: (_) async => throw Exception('no connection'));
    sessions.onSignedOut = () => signedOut++;
    await sessions.start(_loginResponse(), rememberMe: true, user: _user);

    expect(await sessions.refresh(), isFalse);
    expect(signedOut, 0);
    expect(sessions.refreshToken, 'refresh-1');
  });
}
