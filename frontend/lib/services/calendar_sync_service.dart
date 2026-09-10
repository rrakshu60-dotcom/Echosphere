import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

class CalendarEventData {
  final bool hasEvent;
  final String title;
  final DateTime startTime;
  final DateTime endTime;
  final String location;
  final String description;
  final String actionRequired;
  final int alertHoursBefore;
  final String extractionSource;

  CalendarEventData({
    required this.hasEvent,
    required this.title,
    required this.startTime,
    required this.endTime,
    required this.location,
    required this.description,
    required this.actionRequired,
    this.alertHoursBefore = 24,
    this.extractionSource = 'heuristic',
  });

  factory CalendarEventData.fromJson(Map<String, dynamic> json) {
    DateTime parseDt(dynamic val, DateTime fallback) {
      if (val == null) return fallback;
      try {
        return DateTime.parse(val.toString());
      } catch (_) {
        return fallback;
      }
    }

    final now = DateTime.now();
    final defaultStart = now.add(const Duration(days: 1));
    final defaultEnd = defaultStart.add(const Duration(hours: 1));

    return CalendarEventData(
      hasEvent: json['has_event'] == true,
      title: json['title']?.toString() ?? 'Campus Event / Deadline',
      startTime: parseDt(json['start_time'], defaultStart),
      endTime: parseDt(json['end_time'], defaultEnd),
      location: json['location']?.toString() ?? 'College Campus',
      description: json['description']?.toString() ?? '',
      actionRequired: json['action_required']?.toString() ?? 'Check notice details',
      alertHoursBefore: json['alert_hours_before'] is int ? json['alert_hours_before'] as int : 24,
      extractionSource: json['extraction_source']?.toString() ?? 'ai',
    );
  }

  Map<String, dynamic> toJson() => {
        'has_event': hasEvent,
        'title': title,
        'start_time': startTime.toIso8601String(),
        'end_time': endTime.toIso8601String(),
        'location': location,
        'description': description,
        'action_required': actionRequired,
        'alert_hours_before': alertHoursBefore,
        'extraction_source': extractionSource,
      };

  /// Builds RFC 5545 formatted UTC timestamp (e.g. 20261024T170000Z)
  static String formatRfcTimestamp(DateTime dt) {
    final utc = dt.toUtc();
    return DateFormat("yyyyMMdd'T'HHmmss'Z'").format(utc);
  }

  /// Generates deep-link URL for Google Calendar
  String toGoogleCalendarUrl() {
    final startStr = formatRfcTimestamp(startTime);
    final endStr = formatRfcTimestamp(endTime);
    final detailsStr = actionRequired.isNotEmpty
        ? '$description\n\n📌 Required Action: $actionRequired'
        : description;

    final params = {
      'action': 'TEMPLATE',
      'text': title,
      'dates': '$startStr/$endStr',
      'details': detailsStr,
      'location': location,
    };

    final uri = Uri.https('calendar.google.com', '/calendar/render', params);
    return uri.toString();
  }

  /// Generates standard RFC 5545 .ics iCalendar file content
  String generateIcsContent() {
    final startStr = formatRfcTimestamp(startTime);
    final endStr = formatRfcTimestamp(endTime);
    final stampStr = formatRfcTimestamp(DateTime.now());
    final uid = 'echosphere-${startTime.millisecondsSinceEpoch}-${title.hashCode.abs()}@campus';

    final detailsClean = description.replaceAll('\n', '\\n').replaceAll(',', '\\,');
    final titleClean = title.replaceAll('\n', ' ').replaceAll(',', '\\,');
    final locClean = location.replaceAll('\n', ' ').replaceAll(',', '\\,');

    return [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//EchoSphere//Campus AI Calendar//EN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'BEGIN:VEVENT',
      'UID:$uid',
      'DTSTAMP:$stampStr',
      'DTSTART:$startStr',
      'DTEND:$endStr',
      'SUMMARY:$titleClean',
      'DESCRIPTION:$detailsClean',
      'LOCATION:$locClean',
      'BEGIN:VALARM',
      'ACTION:DISPLAY',
      'DESCRIPTION:Reminder: $titleClean',
      'TRIGGER:-PT${alertHoursBefore}H',
      'END:VALARM',
      'END:VEVENT',
      'END:VCALENDAR',
    ].join('\r\n');
  }
}

class CalendarSyncService {
  /// Opens Google Calendar app or web with pre-filled event
  static Future<bool> launchGoogleCalendar(CalendarEventData event) async {
    try {
      final url = event.toGoogleCalendarUrl();
      final uri = Uri.parse(url);
      return await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (e) {
      debugPrint('[CalendarSyncService] Error launching Google Calendar: $e');
      return false;
    }
  }

  /// Exports an .ics file and shares it via the native device share sheet
  static Future<bool> exportAndShareIcs(CalendarEventData event) async {
    try {
      final icsContent = event.generateIcsContent();
      final tempDir = await getTemporaryDirectory();
      final safeName = event.title
          .replaceAll(RegExp(r'[^a-zA-Z0-9_\-]'), '_')
          .toLowerCase();
      final file = File('${tempDir.path}/${safeName}_event.ics');
      await file.writeAsString(icsContent);

      await Share.shareXFiles(
        [XFile(file.path, mimeType: 'text/calendar')],
        text: '📅 ${event.title} - EchoSphere Calendar Event',
        subject: event.title,
      );
      return true;
    } catch (e) {
      debugPrint('[CalendarSyncService] Error exporting .ics file: $e');
      return false;
    }
  }

  /// Client-side resilient fallback parser when offline
  static CalendarEventData extractEventClientSide(String title, String content) {
    final combined = '$title\n$content';
    final now = DateTime.now();

    // 1. Location
    String location = 'College Campus';
    final venueMatch = RegExp(
      r'\b(?:in|at|to)\s+(the\s+)?([A-Za-z0-9\s\-]+?(?:Auditorium|Seminar Hall|Room\s*\d+|Lab\s*\d+|Placement Cell|Library|Ground|Campus))\b',
      caseSensitive: false,
    ).firstMatch(combined);

    if (venueMatch != null) {
      location = venueMatch.group(2)?.trim() ?? 'College Campus';
    } else {
      final directVenue = RegExp(
        r'\b((?:Room|Hall|Lab|Auditorium|Cabin|Block)\s*#?[A-Za-z0-9\-]+|Central Auditorium|Seminar Hall|Placement Cell)\b',
        caseSensitive: false,
      ).firstMatch(combined);
      if (directVenue != null) {
        location = directVenue.group(1)?.trim() ?? 'College Campus';
      }
    }

    // 2. Action & Fee
    String action = 'Check notice instructions';
    final feeMatch = RegExp(r'(?:₹|Rs\.?|INR)\s*([0-9,]+)', caseSensitive: false).firstMatch(combined);
    final feeStr = feeMatch != null ? 'Fee: ₹${feeMatch.group(1)}' : '';

    final actionMatch = RegExp(
      r'\b(submit[^\.\n,;]+|register[^\.\n,;]+|pay[^\.\n,;]+|attend[^\.\n,;]+|report to[^\.\n,;]+)\b',
      caseSensitive: false,
    ).firstMatch(combined);

    if (actionMatch != null) {
      action = actionMatch.group(1)?.trim() ?? '';
      if (feeStr.isNotEmpty && !action.contains(feeStr)) {
        action = '$action ($feeStr)';
      }
    } else if (feeStr.isNotEmpty) {
      action = feeStr;
    }

    // 3. Time
    int hour = 10;
    int minute = 0;
    final timeMatch = RegExp(r'\b(1[0-2]|0?[1-9])(?::([0-5][0-9]))?\s*(AM|PM|am|pm)\b').firstMatch(combined);
    if (timeMatch != null) {
      int h = int.parse(timeMatch.group(1)!);
      int m = timeMatch.group(2) != null ? int.parse(timeMatch.group(2)!) : 0;
      final ampm = timeMatch.group(3)!.toUpperCase();
      if (ampm == 'PM' && h < 12) h += 12;
      if (ampm == 'AM' && h == 12) h = 0;
      hour = h;
      minute = m;
    } else {
      final time24 = RegExp(r'\b([01]?[0-9]|2[0-3]):([0-5][0-9])\b').firstMatch(combined);
      if (time24 != null) {
        hour = int.parse(time24.group(1)!);
        minute = int.parse(time24.group(2)!);
      } else if (RegExp(r'\b(deadline|submit|submission)\b', caseSensitive: false).hasMatch(combined)) {
        hour = 17;
        minute = 0;
      }
    }

    // 4. Date
    DateTime? eventDate;
    final monthMap = {
      'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
      'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
      'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
      'nov': 11, 'november': 11, 'dec': 12, 'december': 12,
    };

    final mA = RegExp(
      r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?\b',
      caseSensitive: false,
    ).firstMatch(combined);

    final mB = RegExp(
      r'\b(\d{1,2})(?:st|nd|rd|th)?(?:\s+of)?\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)(?:\s*,?\s*(\d{4}))?\b',
      caseSensitive: false,
    ).firstMatch(combined);

    final mC = RegExp(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b').firstMatch(combined);
    final mD = RegExp(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b').firstMatch(combined);

    if (mA != null) {
      final mName = mA.group(1)!.toLowerCase();
      final month = monthMap[mName] ?? 1;
      final day = int.parse(mA.group(2)!);
      final year = mA.group(3) != null ? int.parse(mA.group(3)!) : now.year;
      try {
        eventDate = DateTime(year, month, day);
      } catch (_) {}
    } else if (mB != null) {
      final day = int.parse(mB.group(1)!);
      final mName = mB.group(2)!.toLowerCase();
      final month = monthMap[mName] ?? 1;
      final year = mB.group(3) != null ? int.parse(mB.group(3)!) : now.year;
      try {
        eventDate = DateTime(year, month, day);
      } catch (_) {}
    } else if (mC != null) {
      final year = int.parse(mC.group(1)!);
      final month = int.parse(mC.group(2)!);
      final day = int.parse(mC.group(3)!);
      try {
        eventDate = DateTime(year, month, day);
      } catch (_) {}
    } else if (mD != null) {
      final day = int.parse(mD.group(1)!);
      final month = int.parse(mD.group(2)!);
      final year = int.parse(mD.group(3)!);
      try {
        eventDate = DateTime(year, month, day);
      } catch (_) {}
    }

    if (eventDate == null) {
      if (RegExp(r'\btomorrow\b', caseSensitive: false).hasMatch(combined)) {
        eventDate = now.add(const Duration(days: 1));
      } else if (RegExp(r'\bnext week\b', caseSensitive: false).hasMatch(combined)) {
        eventDate = now.add(const Duration(days: 7));
      }
    }

    if (eventDate == null) {
      return CalendarEventData(
        hasEvent: false,
        title: title,
        startTime: now,
        endTime: now,
        location: location,
        description: content,
        actionRequired: action,
        extractionSource: 'client_fallback',
      );
    }

    final start = DateTime(eventDate.year, eventDate.month, eventDate.day, hour, minute);
    final end = start.add(const Duration(hours: 1));

    String eventTitle = title.trim();
    if (eventTitle.length > 60) {
      eventTitle = '${eventTitle.substring(0, 57)}...';
    }

    return CalendarEventData(
      hasEvent: true,
      title: eventTitle,
      startTime: start,
      endTime: end,
      location: location,
      description: content.length > 300 ? content.substring(0, 300).trim() : content.trim(),
      actionRequired: action,
      alertHoursBefore: 24,
      extractionSource: 'client_fallback',
    );
  }
}
