import 'package:echosphere/services/echosphere_api_service.dart';

/// The five logs on the Audit & Logs page.
enum AuditTab { notices, signIns, access, sessions, activity }

/// One page of log entries as the backend returns it.
class AuditPage {
  final List<Map<String, dynamic>> items;
  final int total;
  final int page;
  final int pageSize;

  const AuditPage({required this.items, required this.total, required this.page, required this.pageSize});

  factory AuditPage.fromJson(Map<String, dynamic> json) => AuditPage(
        items: (json['items'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList(),
        total: (json['total'] as num).toInt(),
        page: (json['page'] as num).toInt(),
        pageSize: (json['page_size'] as num).toInt(),
      );
}

/// Backend access for the Audit & Logs page (Dev Admin and College Admin only; the backend enforces it).
class AuditRepository {
  static const _paths = {
    AuditTab.notices: '/audit/notices',
    AuditTab.signIns: '/audit/sign-ins',
    AuditTab.access: '/audit/access',
    AuditTab.sessions: '/audit/sessions',
  };

  /// [params]: q, filters, from/to, sort, order, page, page_size (as the backend names them).
  Future<AuditPage> list(AuditTab tab, Map<String, dynamic> params) async {
    final api = EchosphereApiService();
    if (tab == AuditTab.activity) return _activity(params);
    final query = Map<String, dynamic>.from(params)..removeWhere((_, v) => v == null || v == '');
    return AuditPage.fromJson(Map<String, dynamic>.from(await api.getJson(_paths[tab]!, query: query) as Map));
  }

  Future<Map<String, dynamic>> noticeRecord(int announcementId) async =>
      Map<String, dynamic>.from(await EchosphereApiService().getJson('/audit/notices/$announcementId') as Map);

  Future<void> endSession(int sessionId) => EchosphereApiService().postJson('/audit/sessions/$sessionId/end');

  /// The general activity trail has no server-side paging: search, sort and page it here.
  Future<AuditPage> _activity(Map<String, dynamic> params) async {
    final raw = await EchosphereApiService().getJson('/audit-logs/') as List;
    var rows = raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final q = (params['q'] as String? ?? '').trim().toLowerCase();
    if (q.isNotEmpty) {
      rows = rows
          .where((r) => [r['action'], r['entity'], r['entity_id'], r['user_id'], r['description']]
              .any((v) => '$v'.toLowerCase().contains(q)))
          .toList();
    }
    rows.sort((a, b) => '${a['created_at']}'.compareTo('${b['created_at']}'));
    if (params['order'] != 'asc') rows = rows.reversed.toList();
    final page = (params['page'] as int?) ?? 1;
    final size = (params['page_size'] as int?) ?? 50;
    final start = (page - 1) * size;
    return AuditPage(
      items: start >= rows.length ? [] : rows.sublist(start, (start + size).clamp(0, rows.length)),
      total: rows.length,
      page: page,
      pageSize: size,
    );
  }
}
