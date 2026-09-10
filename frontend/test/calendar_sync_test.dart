import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/controllers/settings/settings.dart';
import 'package:anymex/screens/home/home_dashboard_widgets.dart';
import 'package:anymex/services/calendar_sync_service.dart';
import 'package:anymex/widgets/custom_widgets/calendar_sync_dialog.dart';

Widget createTestApp(Widget home) {
  return ChangeNotifierProvider(
    create: (_) => ThemeProvider(),
    child: GetMaterialApp(
      home: Scaffold(body: home),
    ),
  );
}

void main() {
  setUp(() {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.put(Settings());
    Get.put(AnnouncementController());
  });

  tearDown(() {
    Get.reset();
  });

  group('CalendarSyncService Data & Formats', () {
    test('Google Calendar URL generation produces RFC 5545 compliant parameters', () {
      final start = DateTime.utc(2026, 10, 24, 17, 0, 0);
      final end = DateTime.utc(2026, 10, 24, 18, 0, 0);

      final event = CalendarEventData(
        hasEvent: true,
        title: 'Exam Form Submission',
        startTime: start,
        endTime: end,
        location: 'Room 302',
        description: 'Submit exam forms with ₹500 fee.',
        actionRequired: 'Submit form and pay ₹500',
      );

      final url = event.toGoogleCalendarUrl();
      expect(url, contains('calendar.google.com/calendar/render'));
      expect(url, contains('action=TEMPLATE'));
      expect(url, contains('20261024T170000Z%2F20261024T180000Z'));
      expect(url, contains('Exam+Form+Submission'));
      expect(url, contains('Room+302'));
    });

    test('generateIcsContent produces RFC 5545 iCalendar format', () {
      final start = DateTime.utc(2026, 11, 15, 9, 30, 0);
      final end = DateTime.utc(2026, 11, 15, 10, 30, 0);

      final event = CalendarEventData(
        hasEvent: true,
        title: 'Sports Day 2026',
        startTime: start,
        endTime: end,
        location: 'Football Ground',
        description: 'Annual Sports Day events.',
        actionRequired: 'Attend opening ceremony',
      );

      final ics = event.generateIcsContent();
      expect(ics, contains('BEGIN:VCALENDAR'));
      expect(ics, contains('VERSION:2.0'));
      expect(ics, contains('BEGIN:VEVENT'));
      expect(ics, contains('SUMMARY:Sports Day 2026'));
      expect(ics, contains('LOCATION:Football Ground'));
      expect(ics, contains('DTSTART:20261115T093000Z'));
      expect(ics, contains('DTEND:20261115T103000Z'));
      expect(ics, contains('END:VEVENT'));
      expect(ics, contains('END:VCALENDAR'));
    });

    test('extractEventClientSide extracts dates, times, venues, and fees offline', () {
      final parsed = CalendarSyncService.extractEventClientSide(
        'Fee Payment Deadline',
        'Submit exam fee by Oct 24th, 5 PM to Room 302 with ₹500 fee.',
      );

      expect(parsed.hasEvent, isTrue);
      expect(parsed.startTime.month, equals(10));
      expect(parsed.startTime.day, equals(24));
      expect(parsed.startTime.hour, equals(17));
      expect(parsed.location.toLowerCase(), contains('302'));
      expect(parsed.actionRequired, contains('₹500'));
    });
  });

  group('Calendar UI & Zero Overflow Guarantee', () {
    testWidgets('CalendarSyncSheet renders correctly on 320px compact mobile screen with zero overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 700);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final event = CalendarEventData(
        hasEvent: true,
        title: 'VTU Exam Registration Deadline',
        startTime: DateTime(2026, 10, 24, 17, 0),
        endTime: DateTime(2026, 10, 24, 18, 0),
        location: 'Admin Block Room 302',
        description: 'Submit exam registration and pay ₹500 fee.',
        actionRequired: 'Pay fee and submit forms to office',
      );

      await tester.pumpWidget(createTestApp(
        CalendarSyncSheet(event: event),
      ));
      await tester.pumpAndSettle();

      // Verify all elements render
      expect(find.text('Add to Calendar'), findsOneWidget);
      expect(find.text('VTU Exam Registration Deadline'), findsOneWidget);
      expect(find.text('Admin Block Room 302'), findsOneWidget);
      expect(find.text('Add to Google Calendar (1-Tap)'), findsOneWidget);
      expect(find.text('Device Calendar / Export (.ics)'), findsOneWidget);
      expect(find.text('Copy Details'), findsOneWidget);

      // Verify NO overflow exceptions occurred
      expect(tester.takeException(), isNull);
    });

    testWidgets('AnnouncementFeedCard renders Add to Calendar button on 320px screen with zero overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 700);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final notice = AnnouncementModel(
        id: 305,
        title: 'Campus Placement Drive 2026',
        description: 'T&P Cell announces placement drive on Nov 14, 2026 at 10:00 AM in the Central Auditorium.',
        priority: 'HIGH',
        emergencyLevel: 'NORMAL',
        status: 'PUBLISHED',
        creatorName: 'Placement Officer',
        department: 'T&P Cell',
        category: 'Placement',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(createTestApp(
        SingleChildScrollView(
          child: AnnouncementFeedCard(
            notice: notice,
            index: 0,
          ),
        ),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Campus Placement Drive 2026'), findsOneWidget);
      expect(find.text('Add to Calendar'), findsOneWidget);
      expect(find.text('AI Summarize'), findsOneWidget);
      expect(find.text('Listen'), findsOneWidget);
      expect(find.text('Read Details →'), findsOneWidget);

      // Verify NO layout overflow occurred
      expect(tester.takeException(), isNull);
    });
  });
}
