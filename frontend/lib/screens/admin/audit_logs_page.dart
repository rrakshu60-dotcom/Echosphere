import 'dart:async';

import 'package:echosphere/constants/themes.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/services/audit_repository.dart';
import 'package:echosphere/utils/audit_export.dart';
import 'package:echosphere/utils/navigation_helper.dart';
import 'package:echosphere/utils/text_file_saver.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_button.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_chip.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_container.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_tabbar.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

/// Roles allowed into Audit & Logs (the backend enforces the same).
const auditAdminRoles = {'Dev Admin', 'Developer', 'College Admin', 'Admin'};

bool canOpenAuditLogs(String? role) => auditAdminRoles.contains(role);

/// A filter chip: the backend parameters it sets when switched on.
class _Filter {
  final String label;
  final Map<String, dynamic> params;
  const _Filter(this.label, this.params);
}

class _SortOption {
  final String label;
  final String value;
  const _SortOption(this.label, this.value);
}

const _filters = {
  AuditTab.notices: [
    _Filter('Active', {'state': 'active'}),
    _Filter('Deleted', {'state': 'deleted'}),
    _Filter('Before broadcast', {'deleted_before_broadcast': true}),
    _Filter('Speaker', {'channel': 'Speaker'}),
    _Filter('Push', {'channel': 'Push'}),
    _Filter('In-App', {'channel': 'In-App'}),
    _Filter('High priority', {'priority': 'High'}),
  ],
  AuditTab.signIns: [
    _Filter('Failed only', {'success': false}),
    _Filter('Successful', {'success': true}),
    _Filter('Web', {'platform': 'web'}),
    _Filter('Android', {'platform': 'android'}),
    _Filter('Windows', {'platform': 'windows'}),
  ],
  AuditTab.access: [
    _Filter('App opened', {'event': 'launch'}),
    _Filter('Returned', {'event': 'resume'}),
    _Filter('Renewed', {'event': 'refresh'}),
    _Filter('Not signed in', {'signed_in': false}),
    _Filter('Web', {'platform': 'web'}),
    _Filter('Android', {'platform': 'android'}),
    _Filter('Windows', {'platform': 'windows'}),
  ],
  AuditTab.sessions: [
    _Filter('Active', {'state': 'active'}),
    _Filter('Ended', {'state': 'ended'}),
    _Filter('Web', {'platform': 'web'}),
    _Filter('Android', {'platform': 'android'}),
    _Filter('Windows', {'platform': 'windows'}),
  ],
  AuditTab.activity: [
    _Filter('Signed in', {'action': 'LOGIN'}),
    _Filter('Created', {'action': 'CREATE_ANNOUNCEMENT'}),
    _Filter('Edited', {'action': 'UPDATE_ANNOUNCEMENT'}),
    _Filter('Deleted', {'action': 'DELETE_ANNOUNCEMENT'}),
    _Filter('Approved', {'action': 'APPROVE_ANNOUNCEMENT'}),
    _Filter('Rejected', {'action': 'REJECT_ANNOUNCEMENT'}),
    _Filter('Session ended', {'action': 'END_SESSION'}),
    _Filter('Password reset', {'action': 'FORGOT_PASSWORD'}),
  ],
};

const _sorts = {
  AuditTab.notices: [
    _SortOption('Created', 'created'),
    _SortOption('Scheduled', 'scheduled'),
    _SortOption('Last delivered', 'last_delivered'),
    _SortOption('Deleted', 'deleted'),
    _SortOption('Title', 'title'),
  ],
  AuditTab.signIns: [
    _SortOption('Time', 'at'),
    _SortOption('ID typed', 'identifier'),
    _SortOption('User', 'user_name'),
    _SortOption('IP', 'ip')
  ],
  AuditTab.access: [
    _SortOption('Time', 'at'),
    _SortOption('User', 'user_name'),
    _SortOption('IP', 'ip'),
    _SortOption('Platform', 'platform')
  ],
  AuditTab.sessions: [_SortOption('Last seen', 'last_seen'), _SortOption('Started', 'started'), _SortOption('User', 'user_name')],
  AuditTab.activity: [_SortOption('Time', 'at'), _SortOption('Action', 'action'), _SortOption('Person', 'user_name')],
};

const _searchHints = {
  AuditTab.notices: 'Search notice ID, title, content or creator',
  AuditTab.signIns: 'Search ID typed, user, IP or reason',
  AuditTab.access: 'Search user, IP or app version',
  AuditTab.sessions: 'Search user, sign-in ID or IP',
  AuditTab.activity: 'Search person, notice ID, action or description',
};

class _TabState {
  String query = '';
  final Set<String> active = {};
  String sort;
  String order = 'desc';
  DateTimeRange? range;
  List<Map<String, dynamic>> items = [];
  int total = 0;
  int page = 0;
  bool loading = false;
  String? error;

  _TabState(this.sort);
}

/// Audit & Logs: every notice's permanent record, sign-ins, app access, sessions and the activity trail.
class AuditLogsPage extends StatefulWidget {
  final AuditRepository? repository;
  final AuditTab initialTab;

  const AuditLogsPage({super.key, this.repository, this.initialTab = AuditTab.notices});

  @override
  State<AuditLogsPage> createState() => _AuditLogsPageState();
}

class _AuditLogsPageState extends State<AuditLogsPage> {
  static const _pageSize = 50;

  late final AuditRepository _repo = widget.repository ?? AuditRepository();
  late AuditTab _tab = widget.initialTab;
  final Map<AuditTab, _TabState> _state = {for (final t in AuditTab.values) t: _TabState(_sorts[t]!.first.value)};
  final _search = TextEditingController();
  Timer? _debounce;
  bool _exporting = false;

  bool get _allowed => canOpenAuditLogs(Get.find<AuthController>().currentUser.value?.role);

  @override
  void initState() {
    super.initState();
    if (_allowed) _reload();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  _TabState get _s => _state[_tab]!;

  Map<String, dynamic> _params(AuditTab tab, int page, {int pageSize = _pageSize}) {
    final s = _state[tab]!;
    final params = <String, dynamic>{'sort': s.sort, 'order': s.order, 'page': page, 'page_size': pageSize};
    if (s.query.trim().isNotEmpty) params['q'] = s.query.trim();
    for (final f in _filters[tab]!) {
      if (s.active.contains(f.label)) params.addAll(f.params);
    }
    if (s.range != null) {
      params['from'] = DateTime(s.range!.start.year, s.range!.start.month, s.range!.start.day).toUtc().toIso8601String();
      params['to'] = DateTime(s.range!.end.year, s.range!.end.month, s.range!.end.day, 23, 59, 59).toUtc().toIso8601String();
    }
    return params;
  }

  Future<void> _reload() => _load(page: 1);

  Future<void> _load({required int page}) async {
    final tab = _tab;
    final s = _state[tab]!;
    setState(() {
      s.loading = true;
      s.error = null;
    });
    try {
      final result = await _repo.list(tab, _params(tab, page));
      if (!mounted) return;
      setState(() {
        s.items = page == 1 ? result.items : [...s.items, ...result.items];
        s.total = result.total;
        s.page = page;
      });
    } catch (e) {
      if (mounted) setState(() => s.error = 'Could not load this log. Check the connection and try again.');
    } finally {
      if (mounted) setState(() => s.loading = false);
    }
  }

  void _onSearch(String value) {
    _s.query = value;
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), _reload);
  }

  void _toggleFilter(_Filter f) {
    final s = _s;
    setState(() {
      if (s.active.contains(f.label)) {
        s.active.remove(f.label);
      } else {
        // filters that set the same backend field replace each other
        s.active.removeWhere((label) {
          final other = _filters[_tab]!.firstWhere((x) => x.label == label);
          return other.params.keys.any(f.params.containsKey);
        });
        s.active.add(f.label);
      }
    });
    _reload();
  }

  Future<void> _pickRange() async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2025),
      lastDate: DateTime(now.year + 1, 12, 31),
      initialDateRange: _s.range,
    );
    if (picked == null) return;
    setState(() => _s.range = picked);
    _reload();
  }

  void _switchTab(int index) {
    setState(() => _tab = AuditTab.values[index]);
    _search.text = _s.query;
    if (_s.page == 0) _reload();
  }

  Future<void> _export() async {
    if (_exporting) return;
    setState(() => _exporting = true);
    try {
      final rows = <Map<String, dynamic>>[];
      for (var page = 1; page <= 50; page++) {
        final result = await _repo.list(_tab, _params(_tab, page, pageSize: 200));
        rows.addAll(result.items);
        if (rows.length >= result.total || result.items.isEmpty) break;
      }
      final stamp = DateFormat('yyyy-MM-dd_HHmm').format(DateTime.now());
      final name = 'echosphere_${auditTabTitles[_tab]!.toLowerCase().replaceAll(RegExp(r'[^a-z]+'), '_')}_$stamp.txt';
      final saved = await saveTextFile(name, auditRowsToText(_tab, rows));
      if (saved) snackBar('Exported ${rows.length} entr${rows.length == 1 ? 'y' : 'ies'}.');
    } catch (_) {
      snackBar('Export failed. Try again.');
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  Future<void> _confirmEndSession(Map<String, dynamic> session) async {
    await showDialog(
      context: context,
      builder: (_) => EchoSphereDialog(
        title: 'Sign out device',
        confirmText: 'Sign out',
        message: 'Sign ${session['user_name'] ?? 'this user'} out of ${platformLabel(session['platform'] as String?)} '
            '(session #${session['id']})? They will need to sign in again on that device.',
        onConfirm: () async {
          try {
            await _repo.endSession(session['id'] as int);
            snackBar('Device signed out.');
            _reload();
          } catch (_) {
            snackBar('Could not sign the device out. Try again.');
          }
        },
      ),
    );
  }

  void _openNotice(Map<String, dynamic> notice) {
    Get.to(() => NoticeRecordPage(repository: _repo, announcementId: notice['announcement_id'] as int));
  }

  // ------------------------------------------------------------------ build

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (!_allowed) return _denied(theme);

    return SubPagePopScope(
      fallbackRoute: '/home',
      child: Scaffold(
        body: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                child: Row(
                  children: [
                    const EchoSphereBackButton(fallbackRoute: '/home'),
                    const SizedBox(width: 4),
                    Icon(Icons.policy_rounded, size: 22, color: theme.colorScheme.primary),
                    const SizedBox(width: 8),
                    const Expanded(
                      child: EchoSphereText(
                        text: 'Audit & Logs',
                        size: 16,
                        variant: TextVariant.bold,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Export as .txt',
                      onPressed: _exporting ? null : _export,
                      icon: _exporting
                          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.file_download_outlined, size: 22),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: EchoSphereTabBar(
                  selectTabs: AuditTab.values.map((t) => auditTabTitles[t]!).toList(),
                  icons: const [
                    Icons.campaign_rounded,
                    Icons.login_rounded,
                    Icons.devices_rounded,
                    Icons.key_rounded,
                    Icons.history_rounded,
                  ],
                  selectedIndex: _tab.index,
                  onTabSelected: _switchTab,
                  minTabWidth: 116,
                ),
              ),
              _controls(theme),
              const Divider(height: 1),
              Expanded(child: _list(theme)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _denied(ThemeData theme) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: EchoSphereContainer(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(color: theme.colorScheme.primary.withValues(alpha: 0.12), shape: BoxShape.circle),
                    child: Icon(Icons.gpp_bad_rounded, size: 48, color: theme.colorScheme.primary),
                  ),
                  const SizedBox(height: 16),
                  const EchoSphereText(text: 'Audit & Logs', size: 16, variant: TextVariant.bold, textAlign: TextAlign.center),
                  const SizedBox(height: 8),
                  Text(
                    "You don't have access to the audit logs. Only the Dev Admin and College Admin can open them.",
                    style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurface.withValues(alpha: 0.7)),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 20),
                  EchoSphereButton(
                    onTap: () => Get.offAllNamed('/home'),
                    child: const EchoSphereText(text: 'Return to Dashboard', size: 12, variant: TextVariant.bold),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _controls(ThemeData theme) {
    final s = _s;
    final range =
        s.range == null ? 'Any date' : '${DateFormat('d MMM').format(s.range!.start)} - ${DateFormat('d MMM yyyy').format(s.range!.end)}';
    final sortLabel = _sorts[_tab]!.firstWhere((o) => o.value == s.sort).label;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _search,
            onChanged: _onSearch,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              isDense: true,
              hintText: _searchHints[_tab],
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              for (final f in _filters[_tab]!)
                EchoSphereChip(label: f.label, isSelected: s.active.contains(f.label), onSelected: (_) => _toggleFilter(f)),
              EchoSphereChip(
                label: range,
                icon: Icons.date_range_rounded,
                isSelected: s.range != null,
                onSelected: (_) {
                  if (s.range != null) {
                    setState(() => s.range = null);
                    _reload();
                  } else {
                    _pickRange();
                  }
                },
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: Text(
                  s.loading && s.items.isEmpty ? 'Loading...' : '${s.total} entr${s.total == 1 ? 'y' : 'ies'}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.6)),
                ),
              ),
              if (_sorts[_tab]!.length > 1)
                PopupMenuButton<String>(
                  tooltip: 'Sort by',
                  initialValue: s.sort,
                  onSelected: (v) {
                    setState(() => s.sort = v);
                    _reload();
                  },
                  itemBuilder: (_) => [for (final o in _sorts[_tab]!) PopupMenuItem(value: o.value, child: Text(o.label))],
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.sort_rounded, size: 16, color: theme.colorScheme.primary),
                        const SizedBox(width: 4),
                        Text(sortLabel, style: TextStyle(fontSize: 12, color: theme.colorScheme.primary, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ),
                ),
              IconButton(
                visualDensity: VisualDensity.compact,
                tooltip: s.order == 'desc' ? 'Oldest first' : 'Newest first',
                icon: Icon(s.order == 'desc' ? Icons.arrow_downward_rounded : Icons.arrow_upward_rounded, size: 18),
                onPressed: () {
                  setState(() => s.order = s.order == 'desc' ? 'asc' : 'desc');
                  _reload();
                },
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _list(ThemeData theme) {
    final s = _s;
    if (s.error != null && s.items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(s.error!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 13)),
              const SizedBox(height: 12),
              EchoSphereButton(onTap: _reload, child: const Text('Try again')),
            ],
          ),
        ),
      );
    }
    if (s.loading && s.items.isEmpty) return const Center(child: CircularProgressIndicator());
    if (s.items.isEmpty) {
      return Center(
        child: Text('Nothing matches this search.', style: TextStyle(color: theme.colorScheme.onSurface.withValues(alpha: 0.6))),
      );
    }
    final more = s.items.length < s.total;
    return RefreshIndicator(
      onRefresh: _reload,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(12),
        itemCount: s.items.length + (more ? 1 : 0),
        itemBuilder: (_, i) {
          if (i == s.items.length) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Center(
                child: EchoSphereButton(
                  onTap: s.loading ? () {} : () => _load(page: s.page + 1),
                  child: Text(s.loading ? 'Loading...' : 'Load more'),
                ),
              ),
            );
          }
          final row = s.items[i];
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: switch (_tab) {
              AuditTab.notices => _noticeCard(theme, row),
              AuditTab.signIns => _signInCard(theme, row),
              AuditTab.access => _accessCard(theme, row),
              AuditTab.sessions => _sessionCard(theme, row),
              AuditTab.activity => _activityCard(theme, row),
            },
          );
        },
      ),
    );
  }

  // ------------------------------------------------------------------ cards

  Widget _badge(ThemeData theme, String text, {Color? color}) {
    final c = color ?? theme.colorScheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: c.withValues(alpha: 0.3), width: 0.8),
      ),
      child:
          Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: c)),
    );
  }

  Widget _line(ThemeData theme, String text, {int maxLines = 1}) => Text(
        text,
        maxLines: maxLines,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.65)),
      );

  Widget _card({required Widget child, VoidCallback? onTap}) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: EchoSphereContainer(padding: const EdgeInsets.all(12), child: child),
      );

  Widget _noticeCard(ThemeData theme, Map<String, dynamic> r) {
    final deleted = r['deleted'] == true;
    final danger = theme.brightness == Brightness.dark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive;
    return _card(
      onTap: () => _openNotice(r),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(r['title'] ?? 'Untitled notice',
              maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          _line(theme,
              '#${r['announcement_id']} · ${r['category'] ?? '-'} · ${r['creator_name'] ?? 'Unknown'} (${r['creator_role'] ?? '-'})'),
          _line(theme, 'Created ${auditTime(r['created_at'])}'),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: [
              if (deleted && r['deleted_before_broadcast'] == true)
                _badge(theme, 'Deleted before broadcast', color: danger)
              else if (deleted && r['deleted_before_broadcast'] == false)
                _badge(theme, 'Deleted after delivery', color: danger)
              else if (deleted)
                _badge(theme, 'Deleted', color: danger) // older records: delivery before deletion is unknown
              else
                _badge(theme, r['status'] ?? 'Unknown'),
              for (final ch in (r['channels'] as List? ?? const [])) _badge(theme, '$ch'),
              if ((r['speaker_play_count'] ?? 0) > 0) _badge(theme, 'Played ${r['speaker_play_count']}×'),
              if (r['partial'] == true) _badge(theme, 'Partial record', color: theme.colorScheme.onSurface.withValues(alpha: 0.6)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _signInCard(ThemeData theme, Map<String, dynamic> r) {
    final ok = r['success'] == true;
    final danger = theme.brightness == Brightness.dark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive;
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _badge(theme, signInResultLabel(r), color: ok ? null : danger),
              const SizedBox(width: 8),
              Expanded(child: _line(theme, auditTime(r['at']))),
            ],
          ),
          const SizedBox(height: 6),
          Text(r['user_name'] ?? 'No matching account',
              maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
          _line(theme, 'ID typed: ${r['identifier'] ?? '-'}${r['role'] != null ? ' · ${r['role']}' : ''}'),
          _line(theme, 'IP ${r['ip'] ?? '-'} · ${platformLabel(r['platform'] as String?)}'),
          _line(theme, r['user_agent'] ?? '-'),
        ],
      ),
    );
  }

  Widget _accessCard(ThemeData theme, Map<String, dynamic> r) {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _badge(theme, accessEventLabel(r['event'] as String?)),
              const SizedBox(width: 8),
              Expanded(child: _line(theme, auditTime(r['at']))),
            ],
          ),
          const SizedBox(height: 6),
          Text(r['user_name'] ?? 'Not signed in',
              maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
          _line(theme, '${platformLabel(r['platform'] as String?)} ${r['app_version'] ?? ''} · IP ${r['ip'] ?? '-'}'),
          if (r['session_id'] != null) _line(theme, 'Session #${r['session_id']}'),
        ],
      ),
    );
  }

  Widget _sessionCard(ThemeData theme, Map<String, dynamic> r) {
    final active = r['active'] == true;
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _badge(theme, active ? 'Active' : 'Ended', color: active ? null : theme.colorScheme.onSurface.withValues(alpha: 0.6)),
              const SizedBox(width: 8),
              Expanded(
                child: Text(r['user_name'] ?? 'Unknown user',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
              ),
            ],
          ),
          const SizedBox(height: 6),
          _line(theme,
              'Session #${r['id']} · ${platformLabel(r['platform'] as String?)} · ${r['remember_me'] == true ? 'Remember me' : 'This visit only'}'),
          _line(theme, 'IP ${r['ip'] ?? '-'}${r['last_ip'] != null && r['last_ip'] != r['ip'] ? ' (last ${r['last_ip']})' : ''}'),
          _line(theme, 'Started ${auditTime(r['started_at'])} · last seen ${auditTime(r['last_seen_at'])}'),
          _line(
              theme,
              r['ended_at'] != null
                  ? 'Ended ${auditTime(r['ended_at'])} (${(r['end_reason'] ?? '').toString().replaceAll('_', ' ')})'
                  : 'Expires ${auditTime(r['expires_at'])}'),
          if (active) ...[
            const SizedBox(height: 4),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () => _confirmEndSession(r),
                icon: const Icon(Icons.logout_rounded, size: 16),
                label: const Text('Sign out device'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _activityCard(ThemeData theme, Map<String, dynamic> r) {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Flexible(child: _badge(theme, activityActionLabel(r['action'] as String?))),
              const SizedBox(width: 8),
              Expanded(child: _line(theme, auditTime(r['created_at']))),
            ],
          ),
          const SizedBox(height: 6),
          Text(r['user_name'] ?? 'User #${r['user_id'] ?? '-'}',
              maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
          Text(r['description'] ?? '-', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
          _line(theme, activitySubject(r)),
        ],
      ),
    );
  }
}

/// One notice's permanent record: everything known about it, and its full timeline.
class NoticeRecordPage extends StatefulWidget {
  final AuditRepository repository;
  final int announcementId;

  const NoticeRecordPage({super.key, required this.repository, required this.announcementId});

  @override
  State<NoticeRecordPage> createState() => _NoticeRecordPageState();
}

class _NoticeRecordPageState extends State<NoticeRecordPage> {
  Map<String, dynamic>? _data;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await widget.repository.noticeRecord(widget.announcementId);
      if (mounted) setState(() => _data = data);
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not load this record.');
    }
  }

  List<Map<String, dynamic>> get _events =>
      ((_data?['events'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();

  Future<void> _export() async {
    final record = Map<String, dynamic>.from(_data!['record'] as Map);
    final saved = await saveTextFile('echosphere_notice_${widget.announcementId}.txt', noticeRecordToText(record, _events));
    if (saved) snackBar('Notice record exported.');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(
                children: [
                  const EchoSphereBackButton(fallbackRoute: '/audit-logs'),
                  const SizedBox(width: 4),
                  Expanded(
                    child: EchoSphereText(
                      text: 'Notice #${widget.announcementId}',
                      size: 16,
                      variant: TextVariant.bold,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (_data != null)
                    IconButton(tooltip: 'Export as .txt', onPressed: _export, icon: const Icon(Icons.file_download_outlined, size: 22)),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: _error != null
                  ? Center(child: Text(_error!))
                  : _data == null
                      ? const Center(child: CircularProgressIndicator())
                      : _body(theme, Map<String, dynamic>.from(_data!['record'] as Map)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _field(ThemeData theme, String label, String value) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 112,
              child: Text(label, style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.6))),
            ),
            Expanded(child: Text(value, style: const TextStyle(fontSize: 12))),
          ],
        ),
      );

  Widget _section(String title, List<Widget> children) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: EchoSphereContainer(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
              ...children,
            ],
          ),
        ),
      );

  Widget _body(ThemeData theme, Map<String, dynamic> r) {
    String v(dynamic x) => (x == null || '$x'.isEmpty) ? '-' : '$x';
    final deleted = r['deleted'] == true;
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Text(v(r['title']), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
        if (r['partial'] == true)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('Partial record: rebuilt from the earlier audit trail, so some details are unknown.',
                style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.6))),
          ),
        const SizedBox(height: 12),
        _section('Notice', [
          _field(theme, 'Category', v(r['category'])),
          _field(theme, 'Priority', v(r['priority'])),
          _field(theme, 'Emergency level', v(r['emergency_level'])),
          _field(theme, 'Audience', v(r['target_audience'])),
          _field(theme, 'Delivery', auditChannels(r)),
          _field(theme, 'Status', v(r['status'])),
        ]),
        _section('Content', [
          SelectableText(v(r['content']), style: const TextStyle(fontSize: 13, height: 1.4)),
          if (r['original_content'] != null && r['original_content'] != r['content']) ...[
            const SizedBox(height: 10),
            Text('Original content', style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.6))),
            const SizedBox(height: 4),
            SelectableText(v(r['original_content']), style: const TextStyle(fontSize: 12, height: 1.4)),
          ],
        ]),
        _section('People and times', [
          _field(theme, 'Created by', '${v(r['creator_name'])} (${v(r['creator_role'])}, ${v(r['creator_department'])})'),
          _field(theme, 'Created', auditTime(r['created_at'])),
          _field(theme, 'Scheduled for', auditTime(r['scheduled_at'])),
          _field(theme, 'Published', auditTime(r['published_at'])),
          _field(theme, 'First delivered', auditTime(r['first_delivered_at'])),
          _field(theme, 'Last delivered', auditTime(r['last_delivered_at'])),
          _field(theme, 'Speaker plays', auditPlays(r)),
          if (deleted) ...[
            _field(theme, 'Deleted', auditTime(r['deleted_at'])),
            _field(theme, 'Deleted by', '${v(r['deleted_by_name'])} (${v(r['deleted_by_role'])})'),
            _field(theme, 'Before broadcast',
                r['deleted_before_broadcast'] == true ? 'Yes' : (r['deleted_before_broadcast'] == false ? 'No' : '-')),
            _field(theme, 'Audio deleted', auditTime(r['audio_deleted_at'])),
          ],
        ]),
        _section('Timeline', [
          for (final e in _events)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 3),
                    child: Icon(Icons.circle, size: 8, color: theme.colorScheme.primary),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(auditEventLabel(e['event'] as String?), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        Text(
                          '${auditTime(e['at'])} · ${v(e['actor_name'])}${e['actor_role'] != null ? ' (${e['actor_role']})' : ''}',
                          style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.6)),
                        ),
                        if ((e['detail'] ?? '').toString().isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 2),
                            child: SelectableText('${e['detail']}', style: const TextStyle(fontSize: 12)),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ]),
      ],
    );
  }
}
