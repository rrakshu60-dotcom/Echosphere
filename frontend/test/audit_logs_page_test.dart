import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/settings/settings.dart';
import 'package:echosphere/controllers/theme.dart';
import 'package:echosphere/screens/admin/audit_logs_page.dart';
import 'package:echosphere/services/audit_repository.dart';
import 'package:echosphere/utils/audit_export.dart';

Map<String, dynamic> _notice(int id, String title, {bool deleted = false, bool? beforeBroadcast}) => {
      'announcement_id': id,
      'title': title,
      'content': '$title — full text of the notice.',
      'original_title': title,
      'original_content': '$title — full text of the notice.',
      'category': 'Events',
      'priority': 'High',
      'emergency_level': 'Normal',
      'target_audience': 'Entire College',
      'channels': ['In-App Feed', 'Speaker'],
      'status': 'Published',
      'creator_id': 1,
      'creator_name': 'Dev Admin',
      'creator_role': 'Dev Admin',
      'creator_department': 'General',
      'created_at': '2026-10-22T09:00:00Z',
      'scheduled_at': null,
      'published_at': '2026-10-22T09:00:00Z',
      'first_delivered_at': '2026-10-22T09:00:05Z',
      'last_delivered_at': '2026-10-22T09:00:20Z',
      'speaker_play_count': 1,
      'deleted': deleted,
      'deleted_at': deleted ? '2026-10-22T10:00:00Z' : null,
      'deleted_by_name': deleted ? 'College Admin' : null,
      'deleted_by_role': deleted ? 'College Admin' : null,
      'deleted_before_broadcast': beforeBroadcast,
      'audio_deleted_at': deleted ? '2026-10-22T10:00:02Z' : null,
      'partial': false,
    };

class FakeAuditRepository implements AuditRepository {
  final List<Map<String, dynamic>> calls = [];
  final List<int> endedSessions = [];

  @override
  Future<AuditPage> list(AuditTab tab, Map<String, dynamic> params) async {
    calls.add({'tab': tab, ...params});
    switch (tab) {
      case AuditTab.notices:
        final all = [
          _notice(101, 'Library closes early'),
          _notice(102, 'Seminar on robotics', deleted: true, beforeBroadcast: true),
        ];
        final page = (params['page'] as int?) ?? 1;
        if (params['state'] == 'deleted') return AuditPage(items: [all[1]], total: 1, page: 1, pageSize: 50);
        if (page == 2) return AuditPage(items: [_notice(103, 'Third notice')], total: 3, page: 2, pageSize: 2);
        return AuditPage(items: all, total: 3, page: 1, pageSize: 2);
      case AuditTab.signIns:
        return AuditPage(items: [
          {'id': 1, 'at': '2026-10-22T08:00:00Z', 'identifier': 'esdev01', 'user_name': 'Dev Admin', 'role': 'Dev Admin',
           'success': true, 'reason': 'ok', 'ip': '106.51.203.220', 'platform': 'web', 'user_agent': 'Chrome', 'session_id': 19},
          {'id': 2, 'at': '2026-10-22T08:01:00Z', 'identifier': 'My••• (17 chars)', 'user_name': null, 'role': null,
           'success': false, 'reason': 'unknown_user', 'ip': '10.0.0.9', 'platform': 'android', 'user_agent': 'Dart', 'session_id': null},
        ], total: 2, page: 1, pageSize: 50);
      case AuditTab.access:
        return AuditPage(items: [
          {'id': 1, 'at': '2026-10-22T08:02:00Z', 'event': 'launch', 'user_name': 'Dev Admin', 'session_id': 19,
           'platform': 'windows', 'app_version': '1.1.0+2', 'ip': '106.51.203.220', 'user_agent': 'Dart'},
        ], total: 1, page: 1, pageSize: 50);
      case AuditTab.sessions:
        return AuditPage(items: [
          {'id': 19, 'user_id': 1, 'user_name': 'Dev Admin', 'active': true, 'remember_me': true, 'platform': 'web',
           'user_agent': 'Chrome', 'ip': '106.51.203.220', 'last_ip': '106.51.203.220', 'started_at': '2026-10-22T08:00:00Z',
           'last_seen_at': '2026-10-22T08:30:00Z', 'expires_at': '2026-11-21T08:00:00Z', 'ended_at': null, 'end_reason': null},
        ], total: 1, page: 1, pageSize: 50);
      case AuditTab.activity:
        return AuditPage(items: [
          {'id': 5, 'created_at': '2026-10-22T07:00:00Z', 'action': 'END_SESSION', 'entity': 'SESSION', 'entity_id': 4,
           'user_id': 1, 'description': 'Dev Admin signed out session #4.'},
        ], total: 1, page: 1, pageSize: 50);
    }
  }

  @override
  Future<Map<String, dynamic>> noticeRecord(int announcementId) async => {
        'record': _notice(announcementId, 'Seminar on robotics', deleted: true, beforeBroadcast: true),
        'events': [
          {'id': 1, 'at': '2026-10-22T09:00:00Z', 'event': 'CREATED', 'actor_name': 'Dev Admin', 'actor_role': 'Dev Admin', 'detail': 'Created as Published.'},
          {'id': 2, 'at': '2026-10-22T10:00:00Z', 'event': 'DELETED', 'actor_name': 'College Admin', 'actor_role': 'College Admin', 'detail': 'Deleted before its first broadcast.'},
          {'id': 3, 'at': '2026-10-22T10:00:02Z', 'event': 'AUDIO_DELETED', 'actor_name': 'System', 'actor_role': null, 'detail': 'Removed 2 local audio file(s).'},
        ],
      };

  @override
  Future<void> endSession(int sessionId) async => endedSessions.add(sessionId);
}

Future<FakeAuditRepository> _pump(WidgetTester tester, {String role = 'Dev Admin', double width = 320, AuditTab tab = AuditTab.notices}) async {
  tester.view.physicalSize = Size(width, 800);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  Get.find<AuthController>().currentUser.value = EchosphereUser(id: 1, fullName: 'Someone', role: role);
  final repo = FakeAuditRepository();
  await tester.pumpWidget(ChangeNotifierProvider(
    create: (_) => ThemeProvider(),
    child: GetMaterialApp(home: AuditLogsPage(repository: repo, initialTab: tab)),
  ));
  await tester.pump(const Duration(milliseconds: 600));
  return repo;
}

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.put(Settings());
    Get.put(AuthController());
  });
  tearDown(Get.reset);

  testWidgets('only Dev Admin and College Admin can open the audit page', (tester) async {
    final repo = await _pump(tester, role: 'Principal');
    expect(find.textContaining("don't have access"), findsOneWidget);
    expect(repo.calls, isEmpty);
  });

  for (final role in ['Dev Admin', 'College Admin']) {
    testWidgets('$role sees all five log tabs', (tester) async {
      await _pump(tester, role: role);
      for (final tab in ['Notices', 'Sign-ins', 'App Access', 'Sessions', 'Activity']) {
        expect(find.text(tab), findsWidgets);
      }
    });
  }

  for (final width in [320.0, 900.0]) {
    testWidgets('every tab fits without overflow at ${width.toInt()}px', (tester) async {
      for (final tab in AuditTab.values) {
        await _pump(tester, width: width, tab: tab);
        expect(tester.takeException(), isNull, reason: 'overflow on ${tab.name} at ${width}px');
      }
    });
  }

  testWidgets('notices are listed, searchable, filterable and pageable', (tester) async {
    final repo = await _pump(tester, width: 400);
    expect(find.text('Library closes early'), findsOneWidget);
    expect(find.text('Seminar on robotics'), findsOneWidget);
    expect(find.text('Deleted before broadcast'), findsOneWidget);

    await tester.enterText(find.byType(TextField).first, 'robotics');
    await tester.pump(const Duration(milliseconds: 600));
    expect(repo.calls.last['q'], 'robotics');

    await tester.tap(find.text('Deleted').first);
    await tester.pump(const Duration(milliseconds: 300));
    expect(repo.calls.last['state'], 'deleted');
    expect(find.text('Library closes early'), findsNothing);

    await tester.tap(find.text('Deleted').first); // toggle the filter off again
    await tester.pump(const Duration(milliseconds: 300));
    await tester.scrollUntilVisible(find.text('Load more'), 200,
        scrollable: find.descendant(of: find.byType(ListView), matching: find.byType(Scrollable)).first);
    await tester.tap(find.text('Load more'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(repo.calls.last['page'], 2);
    expect(find.text('Third notice'), findsOneWidget);
  });

  testWidgets('a deleted notice with unknown delivery is not claimed as delivered', (tester) async {
    final repo = UnknownDeliveryRepository();
    tester.view.physicalSize = const Size(400, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    Get.find<AuthController>().currentUser.value = EchosphereUser(id: 1, fullName: 'Someone', role: 'Dev Admin');
    await tester.pumpWidget(ChangeNotifierProvider(
      create: (_) => ThemeProvider(),
      child: GetMaterialApp(home: AuditLogsPage(repository: repo)),
    ));
    await tester.pump(const Duration(milliseconds: 600));
    expect(find.text('Old notice'), findsOneWidget);
    expect(find.text('Deleted after delivery'), findsNothing);
    expect(find.text('Deleted before broadcast'), findsNothing);
    expect(find.text('Deleted'), findsWidgets); // the badge (the filter chip also says "Deleted")
    expect(find.text('Partial record'), findsOneWidget);
  });

  testWidgets('sorting asks the backend for the chosen order', (tester) async {
    final repo = await _pump(tester, width: 400);
    await tester.tap(find.byTooltip('Oldest first'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(repo.calls.last['order'], 'asc');
  });

  testWidgets('a notice opens its full record and timeline', (tester) async {
    await _pump(tester, width: 400);
    await tester.tap(find.text('Seminar on robotics'));
    await tester.pumpAndSettle();
    expect(find.text('Seminar on robotics — full text of the notice.'), findsWidgets);
    expect(find.text('Created'), findsOneWidget);
    expect(find.text('Deleted'), findsWidgets);
    expect(find.text('Audio deleted'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('an admin can end an active session after confirming', (tester) async {
    final repo = await _pump(tester, width: 400, tab: AuditTab.sessions);
    await tester.tap(find.text('Sign out device'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sign out'));
    await tester.pumpAndSettle();
    expect(repo.endedSessions, [19]);
  });

  testWidgets('sign-ins show the result and reason in plain words', (tester) async {
    await _pump(tester, width: 400, tab: AuditTab.signIns);
    expect(find.text('Signed in'), findsOneWidget);
    expect(find.text('Unknown ID'), findsOneWidget);
    expect(find.textContaining('106.51.203.220'), findsWidgets);
  });

  test('notice export is a readable text record with the full timeline', () {
    final txt = noticeRecordToText(_notice(102, 'Seminar on robotics', deleted: true, beforeBroadcast: true), [
      {'at': '2026-10-22T09:00:00Z', 'event': 'CREATED', 'actor_name': 'Dev Admin', 'actor_role': 'Dev Admin', 'detail': 'Created as Published.'},
      {'at': '2026-10-22T10:00:00Z', 'event': 'DELETED', 'actor_name': 'College Admin', 'actor_role': 'College Admin', 'detail': 'Deleted before its first broadcast.'},
    ]);
    expect(txt, contains('Notice #102'));
    expect(txt, contains('Seminar on robotics — full text of the notice.'));
    expect(txt, contains('Deleted before broadcast: yes'));
    expect(txt, contains('Created by: Dev Admin (Dev Admin, General)'));
    expect(txt.indexOf('Created'), lessThan(txt.indexOf('Deleted by')));
    expect(txt, contains('College Admin (College Admin): Deleted before its first broadcast.'));
  });

  test('list export writes one readable block per entry', () {
    final txt = auditRowsToText(AuditTab.signIns, [
      {'at': '2026-10-22T08:00:00Z', 'identifier': 'esdev01', 'user_name': 'Dev Admin', 'role': 'Dev Admin',
       'success': true, 'reason': 'ok', 'ip': '106.51.203.220', 'platform': 'web', 'user_agent': 'Chrome', 'session_id': 19},
    ]);
    expect(txt, contains('Sign-ins'));
    expect(txt, contains('esdev01'));
    expect(txt, contains('106.51.203.220'));
    expect(txt, contains('Signed in'));
  });
}


class UnknownDeliveryRepository extends FakeAuditRepository {
  @override
  Future<AuditPage> list(AuditTab tab, Map<String, dynamic> params) async {
    final old = _notice(55, 'Old notice', deleted: true)..['partial'] = true;
    return AuditPage(items: [old], total: 1, page: 1, pageSize: 50);
  }
}
