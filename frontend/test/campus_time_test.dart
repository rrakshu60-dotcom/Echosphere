import 'package:flutter_test/flutter_test.dart';
import 'package:echosphere/utils/campus_time.dart';

void main() {
  test('a server time without a zone is UTC', () {
    final t = parseServerTime('2026-10-23T04:00:04.926472')!;
    expect(t.isUtc, isTrue);
    expect(t, DateTime.utc(2026, 10, 23, 4, 0, 4, 926, 472));
    expect(parseServerTime('2026-10-23T04:00:04Z'), DateTime.utc(2026, 10, 23, 4, 0, 4));
    expect(parseServerTime('2026-10-23T09:30:04+05:30'), DateTime.utc(2026, 10, 23, 4, 0, 4));
    expect(parseServerTime(null), isNull);
    expect(parseServerTime('not a date'), isNull);
  });

  test('times are shown in Kolkata time whatever the device zone', () {
    final created = parseServerTime('2026-10-23T04:00:04')!; // 9:30 AM IST
    expect(formatCampusTime(created, 'hh:mm a'), '09:30 AM');
    expect(formatCampusTime(DateTime.utc(2026, 10, 23, 19, 0), 'MMM dd, hh:mm a'), 'Oct 24, 12:30 AM');
  });

  test('a notice created a minute ago is a minute old, not 5 hours', () {
    final now = DateTime.now().toUtc();
    final naive = now.subtract(const Duration(minutes: 1)).toIso8601String().replaceAll('Z', '');
    final age = now.difference(parseServerTime(naive)!);
    expect(age.inMinutes, 1);
  });

  test('today and tomorrow follow the Kolkata calendar', () {
    final now = DateTime.utc(2026, 10, 23, 19, 0); // 00:30 on Oct 24 in Kolkata
    expect(campusDayOffset(DateTime.utc(2026, 10, 23, 20, 0), now: now), 0); // 01:30 Oct 24 IST: today
    expect(campusDayOffset(DateTime.utc(2026, 10, 24, 19, 0), now: now), 1); // 00:30 Oct 25 IST: tomorrow
    expect(campusDayOffset(DateTime.utc(2026, 10, 23, 18, 0), now: now), -1); // 23:30 Oct 23 IST: yesterday
  });
}
