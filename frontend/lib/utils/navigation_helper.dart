import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/screens/announcements/announcement_detail_page.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

/// Opens the AnnouncementDetailPage with an explicit named route settings
/// so that Flutter Web registers the page in browser window.history.
/// This enables browser back button and Android back gestures to pop
/// back to the previous screen without reloading the entire site.
void openAnnouncementDetail(BuildContext context, AnnouncementModel announcement) {
  Navigator.of(context).push(
    MaterialPageRoute(
      settings: RouteSettings(
        name: '/announcement?id=${announcement.id}',
        arguments: announcement,
      ),
      builder: (_) => AnnouncementDetailPage(announcement: announcement),
    ),
  );
}

/// Safely pops the current route. If this was the root route or cannot be popped
/// (e.g. opened directly via URL or refreshed on web), navigates smoothly to [fallbackRoute].
void safePop(BuildContext context, {String fallbackRoute = '/home'}) {
  if (Navigator.of(context).canPop()) {
    Navigator.of(context).pop();
  } else {
    Get.offAllNamed(fallbackRoute);
  }
}

/// Standardized PopScope wrapper for sub-pages.
/// Intercepts Android back gesture and browser back events so they pop
/// the Flutter Navigator instead of reloading the web page.
class SubPagePopScope extends StatelessWidget {
  final Widget child;
  final String fallbackRoute;

  const SubPagePopScope({
    super.key,
    required this.child,
    this.fallbackRoute = '/home',
  });

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        safePop(context, fallbackRoute: fallbackRoute);
      },
      child: child,
    );
  }
}

/// A reliable back button for any subpage header/appbar that never breaks
/// regardless of whether canPop is true or false.
class EchoSphereBackButton extends StatelessWidget {
  final Color? color;
  final String fallbackRoute;
  final VoidCallback? onBeforePop;

  const EchoSphereBackButton({
    super.key,
    this.color,
    this.fallbackRoute = '/home',
    this.onBeforePop,
  });

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Icon(Icons.arrow_back_rounded, color: color),
      tooltip: 'Back',
      onPressed: () {
        onBeforePop?.call();
        safePop(context, fallbackRoute: fallbackRoute);
      },
    );
  }
}
