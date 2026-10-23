import 'package:intl/intl.dart';

/// EchoSphere runs on Kolkata time (UTC+5:30, no daylight saving) for everyone, whatever the device's time zone.
const campusUtcOffset = Duration(hours: 5, minutes: 30);

final _zoneSuffix = RegExp(r'(Z|[+-]\d{2}:?\d{2})$', caseSensitive: false);

/// A time from the server as an exact moment (UTC). The server stores UTC and often leaves the zone out,
/// so a date-time without one is UTC, not device-local time.
DateTime? parseServerTime(dynamic value) {
  if (value == null) return null;
  if (value is DateTime) return value.toUtc();
  final text = value.toString().trim();
  if (text.isEmpty || text == 'null') return null;
  final hasTime = text.contains('T') || text.contains(':');
  final parsed = DateTime.tryParse(hasTime && !_zoneSuffix.hasMatch(text) ? '${text}Z' : text);
  return parsed?.toUtc();
}

/// Kolkata's wall-clock reading of a moment (a UTC DateTime holding Kolkata's date and time fields).
DateTime toCampusTime(DateTime moment) => moment.toUtc().add(campusUtcOffset);

/// A moment formatted in Kolkata time, e.g. formatCampusTime(t, 'MMM dd, hh:mm a').
String formatCampusTime(DateTime moment, String pattern) => DateFormat(pattern).format(toCampusTime(moment));

/// Calendar days from today to [moment] on the Kolkata calendar (0 today, 1 tomorrow, -1 yesterday).
int campusDayOffset(DateTime moment, {DateTime? now}) {
  final a = toCampusTime(now ?? DateTime.now());
  final b = toCampusTime(moment);
  return DateTime.utc(b.year, b.month, b.day).difference(DateTime.utc(a.year, a.month, a.day)).inDays;
}
