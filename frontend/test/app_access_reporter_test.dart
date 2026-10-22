import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:echosphere/services/app_access_reporter.dart';

void main() {
  late List<String> sent;
  late DateTime now;
  late AppAccessReporter reporter;

  setUp(() {
    sent = [];
    now = DateTime(2026, 10, 22, 9, 0);
    reporter = AppAccessReporter(send: (event) async => sent.add(event), clock: () => now);
  });

  test('every launch is reported', () async {
    await reporter.reportLaunch();
    expect(sent, ['launch']);
  });

  test('coming back within 5 minutes is not reported', () async {
    await reporter.reportLaunch();
    reporter.didChangeAppLifecycleState(AppLifecycleState.paused);
    now = now.add(const Duration(minutes: 4, seconds: 59));
    reporter.didChangeAppLifecycleState(AppLifecycleState.resumed);
    await pumpEventQueue();
    expect(sent, ['launch']);
  });

  test('coming back after 5 minutes or more is reported as a resume', () async {
    await reporter.reportLaunch();
    reporter.didChangeAppLifecycleState(AppLifecycleState.hidden);
    now = now.add(const Duration(minutes: 5));
    reporter.didChangeAppLifecycleState(AppLifecycleState.resumed);
    await pumpEventQueue();
    expect(sent, ['launch', 'resume']);
  });

  test('only the time actually away counts', () async {
    await reporter.reportLaunch();
    now = now.add(const Duration(hours: 2)); // in use the whole time
    reporter.didChangeAppLifecycleState(AppLifecycleState.paused);
    now = now.add(const Duration(minutes: 1));
    reporter.didChangeAppLifecycleState(AppLifecycleState.resumed);
    await pumpEventQueue();
    expect(sent, ['launch']);
  });

  test('a failed report never breaks the app', () async {
    final failing = AppAccessReporter(send: (_) async => throw Exception('offline'), clock: () => now);
    await failing.reportLaunch();
  });
}
