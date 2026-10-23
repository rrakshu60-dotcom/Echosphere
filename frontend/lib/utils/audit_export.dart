import 'package:echosphere/services/audit_repository.dart';
import 'package:echosphere/utils/campus_time.dart';

/// Plain-language names for notice timeline events.
String auditEventLabel(String? event) {
  const labels = {
    'CREATED': 'Created',
    'EDITED': 'Edited',
    'SETTINGS_CHANGED': 'Settings changed',
    'APPROVED': 'Approved',
    'REJECTED': 'Rejected',
    'PUBLISHED': 'Published',
    'SCHEDULED': 'Scheduled',
    'ARCHIVED': 'Archived',
    'STATUS_CHANGED': 'Status changed',
    'IN_APP_ALERTS': 'In-app alerts sent',
    'PUSH_SENT': 'Push notification',
    'SPEAKER_STARTED': 'Speaker started',
    'SPEAKER_FINISHED': 'Speaker finished',
    'SPEAKER_STOPPED': 'Speaker stopped',
    'DELETED': 'Deleted',
    'AUDIO_DELETED': 'Audio deleted',
    'RECORD_STARTED': 'Record started',
  };
  return labels[event] ?? (event ?? 'Event');
}

/// Plain-language result of a sign-in attempt.
String signInResultLabel(Map<String, dynamic> row) {
  if (row['success'] == true) return 'Signed in';
  const reasons = {
    'unknown_user': 'Unknown ID',
    'wrong_password': 'Wrong password',
    'disabled': 'Account disabled',
    'employee_id_mismatch': 'Employee ID mismatch',
  };
  return reasons[row['reason']] ?? 'Failed';
}

/// Plain words for an activity-trail action ("DELETE_ANNOUNCEMENT" -> "Notice deleted").
String activityActionLabel(String? action) {
  const labels = {
    'LOGIN': 'Signed in',
    'CREATE_ANNOUNCEMENT': 'Notice created',
    'UPDATE_ANNOUNCEMENT': 'Notice edited',
    'DELETE_ANNOUNCEMENT': 'Notice deleted',
    'APPROVE_ANNOUNCEMENT': 'Notice approved',
    'REJECT_ANNOUNCEMENT': 'Notice rejected',
    'END_SESSION': 'Session ended',
    'FORGOT_PASSWORD': 'Password reset requested',
  };
  if (action == null) return '-';
  final known = labels[action];
  if (known != null) return known;
  final words = action.toLowerCase().replaceAll('_', ' ');
  return words.isEmpty ? '-' : words[0].toUpperCase() + words.substring(1);
}

/// What an activity entry is about ("ANNOUNCEMENT" #7 -> "Notice #7").
String activitySubject(Map<String, dynamic> r) {
  const names = {'ANNOUNCEMENT': 'Notice', 'USER': 'User', 'SESSION': 'Session'};
  final entity = '${r['entity'] ?? ''}';
  final name = names[entity] ?? (entity.isEmpty ? 'Item' : entity[0] + entity.substring(1).toLowerCase());
  return '$name #${r['entity_id'] ?? '-'}';
}

String accessEventLabel(String? event) =>
    const {'launch': 'App opened', 'resume': 'Returned to app', 'refresh': 'Session renewed'}[event] ?? (event ?? '');

String platformLabel(String? platform) =>
    const {'web': 'Web', 'android': 'Android', 'ios': 'iOS', 'windows': 'Windows', 'macos': 'macOS', 'linux': 'Linux', 'test': 'Test'}[platform] ??
    (platform ?? 'Unknown');

/// "22 Oct 2026, 14:30:05" in Kolkata time; "-" when missing.
String auditTime(dynamic iso) {
  if (iso == null || '$iso'.isEmpty) return '-';
  final parsed = parseServerTime(iso);
  if (parsed == null) return '$iso';
  return formatCampusTime(parsed, 'd MMM yyyy, HH:mm:ss');
}

String _v(dynamic value) => (value == null || '$value'.isEmpty) ? '-' : '$value';

String _yesNo(dynamic value) => value == null ? '-' : (value == true ? 'yes' : 'no');

/// Delivery channels, or "-" when none are known.
String auditChannels(Map<String, dynamic> r) {
  final channels = (r['channels'] as List?) ?? const [];
  return channels.isEmpty ? '-' : channels.join(', ');
}

/// Speaker plays; unknown ("-") on partial records, whose deliveries were never recorded.
String auditPlays(Map<String, dynamic> r) => r['partial'] == true ? '-' : _v(r['speaker_play_count']);

/// One notice's full record and timeline as readable text.
String noticeRecordToText(Map<String, dynamic> r, List<Map<String, dynamic>> events) {
  final b = StringBuffer()
    ..writeln('EchoSphere notice record')
    ..writeln('=' * 60)
    ..writeln('Notice #${r['announcement_id']}${r['partial'] == true ? '  (partial record)' : ''}')
    ..writeln('Title: ${_v(r['title'])}');
  if (r['original_title'] != null && r['original_title'] != r['title']) b.writeln('Original title: ${r['original_title']}');
  b
    ..writeln('Category: ${_v(r['category'])}   Priority: ${_v(r['priority'])}   Emergency level: ${_v(r['emergency_level'])}')
    ..writeln('Audience: ${_v(r['target_audience'])}')
    ..writeln('Delivery: ${auditChannels(r)}')
    ..writeln('Status: ${_v(r['status'])}')
    ..writeln('Created by: ${_v(r['creator_name'])} (${_v(r['creator_role'])}, ${_v(r['creator_department'])})')
    ..writeln('Created: ${auditTime(r['created_at'])}')
    ..writeln('Scheduled for: ${auditTime(r['scheduled_at'])}')
    ..writeln('Published: ${auditTime(r['published_at'])}')
    ..writeln('First delivered: ${auditTime(r['first_delivered_at'])}')
    ..writeln('Last delivered: ${auditTime(r['last_delivered_at'])}')
    ..writeln('Speaker plays: ${auditPlays(r)}');
  if (r['deleted'] == true) {
    b
      ..writeln('Deleted: ${auditTime(r['deleted_at'])}')
      ..writeln('Deleted by: ${_v(r['deleted_by_name'])} (${_v(r['deleted_by_role'])})')
      ..writeln('Deleted before broadcast: ${_yesNo(r['deleted_before_broadcast'])}')
      ..writeln('Audio deleted: ${auditTime(r['audio_deleted_at'])}');
  }
  b
    ..writeln()
    ..writeln('Content:')
    ..writeln(_v(r['content']));
  if (r['original_content'] != null && r['original_content'] != r['content']) {
    b
      ..writeln()
      ..writeln('Original content:')
      ..writeln(r['original_content']);
  }
  b
    ..writeln()
    ..writeln('Timeline:');
  for (final e in events) {
    final who = e['actor_role'] != null ? '${_v(e['actor_name'])} (${e['actor_role']})' : _v(e['actor_name']);
    b.writeln('${auditTime(e['at'])}  ${auditEventLabel(e['event'] as String?)} - $who: ${_v(e['detail'])}');
  }
  return b.toString();
}

const auditTabTitles = {
  AuditTab.notices: 'Notices',
  AuditTab.signIns: 'Sign-ins',
  AuditTab.access: 'App Access',
  AuditTab.sessions: 'Sessions',
  AuditTab.activity: 'Activity',
};

/// A list of log entries (the current search) as readable text, one block per entry.
String auditRowsToText(AuditTab tab, List<Map<String, dynamic>> rows) {
  final b = StringBuffer()
    ..writeln('EchoSphere ${auditTabTitles[tab]} log - exported ${auditTime(DateTime.now().toUtc().toIso8601String())}')
    ..writeln('${rows.length} entr${rows.length == 1 ? 'y' : 'ies'}')
    ..writeln('=' * 60);
  for (final r in rows) {
    switch (tab) {
      case AuditTab.notices:
        b.writeln('Notice #${r['announcement_id']}: ${_v(r['title'])}');
        b.writeln('  Created ${auditTime(r['created_at'])} by ${_v(r['creator_name'])} (${_v(r['creator_role'])})');
        b.writeln('  ${_v(r['status'])} | ${auditChannels(r)} | speaker plays ${auditPlays(r)}');
        if (r['deleted'] == true) {
          b.writeln('  Deleted ${auditTime(r['deleted_at'])} by ${_v(r['deleted_by_name'])}'
              '${r['deleted_before_broadcast'] == true ? ' (before broadcast)' : ''}');
        }
      case AuditTab.signIns:
        b.writeln('${auditTime(r['at'])}  ${signInResultLabel(r)}  ID typed: ${_v(r['identifier'])}');
        b.writeln('  User: ${_v(r['user_name'])} (${_v(r['role'])})  IP: ${_v(r['ip'])}  ${platformLabel(r['platform'] as String?)}');
        b.writeln('  Device: ${_v(r['user_agent'])}');
      case AuditTab.access:
        b.writeln('${auditTime(r['at'])}  ${accessEventLabel(r['event'] as String?)}  ${r['user_name'] ?? 'Not signed in'}');
        b.writeln('  ${platformLabel(r['platform'] as String?)} ${_v(r['app_version'])}  IP: ${_v(r['ip'])}');
      case AuditTab.sessions:
        b.writeln('Session #${r['id']}: ${_v(r['user_name'])}  ${r['active'] == true ? 'ACTIVE' : 'ended'}');
        b.writeln('  ${platformLabel(r['platform'] as String?)}  IP: ${_v(r['ip'])} (last ${_v(r['last_ip'])})  remember me: ${_yesNo(r['remember_me'])}');
        b.writeln('  Started ${auditTime(r['started_at'])}  last seen ${auditTime(r['last_seen_at'])}  '
            '${r['ended_at'] != null ? 'ended ${auditTime(r['ended_at'])} (${_v(r['end_reason'])})' : 'expires ${auditTime(r['expires_at'])}'}');
      case AuditTab.activity:
        b.writeln('${auditTime(r['created_at'])}  ${activityActionLabel(r['action'] as String?)}  ${activitySubject(r)}  '
            'by ${r['user_name'] ?? 'user #${_v(r['user_id'])}'}');
        b.writeln('  ${_v(r['description'])}');
    }
    b.writeln('-' * 60);
  }
  return b.toString();
}
