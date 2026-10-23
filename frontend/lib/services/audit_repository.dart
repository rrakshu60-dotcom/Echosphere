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
    AuditTab.activity: '/audit/activity',
  };

  /// [params]: q, filters, from/to, sort, order, page, page_size (as the backend names them).
  Future<AuditPage> list(AuditTab tab, Map<String, dynamic> params) async {
    final api = EchosphereApiService();
    final query = Map<String, dynamic>.from(params)..removeWhere((_, v) => v == null || v == '');
    return AuditPage.fromJson(Map<String, dynamic>.from(await api.getJson(_paths[tab]!, query: query) as Map));
  }

  Future<Map<String, dynamic>> noticeRecord(int announcementId) async =>
      Map<String, dynamic>.from(await EchosphereApiService().getJson('/audit/notices/$announcementId') as Map);

  Future<void> endSession(int sessionId) => EchosphereApiService().postJson('/audit/sessions/$sessionId/end');
}
