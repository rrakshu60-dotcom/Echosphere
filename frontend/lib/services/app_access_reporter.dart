import 'package:flutter/widgets.dart';

/// Reports app opens for the admin's App Access log: every launch, and every return to the app
/// after at least [awayThreshold] in the background. Reporting never interrupts the app.
class AppAccessReporter with WidgetsBindingObserver {
  static const awayThreshold = Duration(minutes: 5);

  /// Sends one event ("launch" or "resume") to the backend.
  final Future<void> Function(String event) send;
  final DateTime Function() clock;

  DateTime? _wentAwayAt;

  AppAccessReporter({required this.send, DateTime Function()? clock}) : clock = clock ?? DateTime.now;

  Future<void> reportLaunch() => _report('launch');

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.paused:
      case AppLifecycleState.hidden:
      case AppLifecycleState.detached:
        _wentAwayAt ??= clock();
      case AppLifecycleState.resumed:
        final away = _wentAwayAt;
        _wentAwayAt = null;
        if (away != null && clock().difference(away) >= awayThreshold) {
          _report('resume');
        }
      case AppLifecycleState.inactive:
        break;
    }
  }

  Future<void> _report(String event) async {
    try {
      await send(event);
    } catch (e) {
      debugPrint('App access report skipped: $e');
    }
  }
}
