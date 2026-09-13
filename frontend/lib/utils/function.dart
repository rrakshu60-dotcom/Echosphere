import 'dart:io';

import 'package:anymex/utils/theme_extensions.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

extension StringExtensions on String {
  String get getUrlWithoutDomain {
    final uri = Uri.parse(replaceAll(' ', '%20'));
    String out = uri.path;
    if (uri.query.isNotEmpty) {
      out += '?${uri.query}';
    }
    if (uri.fragment.isNotEmpty) {
      out += '#${uri.fragment}';
    }
    return out;
  }
}

String convertAniListStatus(String? status, {bool isManga = false}) {
  switch (status?.toUpperCase()) {
    case 'CURRENT':
      return isManga ? "CURRENTLY READING" : 'CURRENTLY WATCHING';
    case 'PLANNING':
      return 'PLANNING TO ${isManga ? 'READ' : 'WATCH'}';
    case 'COMPLETED':
      return 'COMPLETED';
    case 'DROPPED':
      return 'DROPPED';
    case 'PAUSED':
      return 'PAUSED';
    case 'REPEATING':
      return isManga ? "REREADING" : 'REWATCHING';
    default:
      return 'ADD TO LIST';
  }
}

Future<void> snackString(
  String? s, {
  String? clipboard,
}) async {
  var context = Get.context;

  if (context != null && s != null && s.isNotEmpty) {
    var theme = context.colors;

    try {
      final snackBar = SnackBar(
        content: GestureDetector(
          onTap: () => ScaffoldMessenger.of(context).hideCurrentSnackBar(),
          child: Text(
            s,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: 'Poppins',
              fontSize: 16.0,
              fontWeight: FontWeight.w600,
              color: theme.onSurface,
            ),
          ),
        ),
        backgroundColor: theme.surface,
        behavior: SnackBarBehavior.floating,
        margin: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom + 32,
          left: 32,
          right: 32,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        duration: const Duration(seconds: 2),
      );
      ScaffoldMessenger.of(context).showSnackBar(snackBar);
    } catch (e, stackTrace) {
      debugPrint('Error showing SnackBar: $e');
      debugPrint(stackTrace.toString());
    }
  } else {
    debugPrint('No valid context or string provided.');
  }
}

class ChapterRecognition {
  static const _numberPattern = r"([0-9]+)(\.[0-9]+)?(\.?[a-z]+)?";

  static final _unwanted =
      RegExp(r"\b(?:v|ver|vol|version|volume|season|s)[^a-z]?[0-9]+");

  static final _unwantedWhiteSpace = RegExp(r"\s(?=extra|special|omake)");

  static dynamic parseChapterNumber(String mangaTitle, String chapterName) {
    var name = chapterName.toLowerCase();

    name = name.replaceAll(mangaTitle.toLowerCase(), "").trim();

    name = name.replaceAll(',', '.').replaceAll('-', '.');

    name = name.replaceAll(_unwantedWhiteSpace, "");

    name = name.replaceAll(_unwanted, "");

    final episodeMatch = RegExp(r"e(\d+)").firstMatch(name);
    if (episodeMatch != null) {
      return int.parse(episodeMatch.group(1)!);
    }

    const numberPat = "*$_numberPattern";
    const ch = r"(?<=ch\.)";
    var match = RegExp("$ch $numberPat").firstMatch(name);
    if (match != null) {
      return _convertToIntIfWhole(_getChapterNumberFromMatch(match));
    }

    match = RegExp(_numberPattern).firstMatch(name);
    if (match != null) {
      return _convertToIntIfWhole(_getChapterNumberFromMatch(match));
    }

    return 0;
  }

  static dynamic _convertToIntIfWhole(double value) {
    return value % 1 == 0 ? value.toInt() : value;
  }

  static double _getChapterNumberFromMatch(Match match) {
    final initial = double.parse(match.group(1)!);
    final subChapterDecimal = match.group(2);
    final subChapterAlpha = match.group(3);
    final addition = _checkForDecimal(subChapterDecimal, subChapterAlpha);
    return initial + addition;
  }

  static double _checkForDecimal(String? decimal, String? alpha) {
    if (decimal != null && decimal.isNotEmpty) {
      return double.parse(decimal);
    }

    if (alpha != null && alpha.isNotEmpty) {
      if (alpha.contains("extra")) {
        return 0.99;
      }
      if (alpha.contains("omake")) {
        return 0.98;
      }
      if (alpha.contains("special")) {
        return 0.97;
      }
      final trimmedAlpha = alpha.replaceFirst('.', '');
      if (trimmedAlpha.length == 1) {
        return _parseAlphaPostFix(trimmedAlpha[0]);
      }
    }

    return 0.0;
  }

  static double _parseAlphaPostFix(String alpha) {
    final number = alpha.codeUnitAt(0) - ('a'.codeUnitAt(0) - 1);
    if (number >= 10) return 0.0;
    return number / 10.0;
  }
}


String calcTime(String timestamp, {String format = "dd-MM-yyyy"}) {
  if (timestamp.trim().isEmpty) return "";

  DateTime? dateTime;
  final cleanTimestamp = timestamp.trim();
  final parsedInt = int.tryParse(cleanTimestamp);

  if (parsedInt != null) {
    if (cleanTimestamp.length == 10) {
      dateTime = DateTime.fromMillisecondsSinceEpoch(parsedInt * 1000);
    } else if (cleanTimestamp.length == 13) {
      dateTime = DateTime.fromMillisecondsSinceEpoch(parsedInt);
    } else if (cleanTimestamp.length == 16) {
      dateTime = DateTime.fromMillisecondsSinceEpoch(parsedInt ~/ 1000);
    } else {
      if (parsedInt > 9999999999) {
        dateTime = DateTime.fromMillisecondsSinceEpoch(parsedInt);
      } else {
        dateTime = DateTime.fromMillisecondsSinceEpoch(parsedInt * 1000);
      }
    }
  } else {
    dateTime = DateTime.tryParse(cleanTimestamp);
  }

  if (dateTime == null) {
    return timestamp;
  }

  final now = DateTime.now();
  final difference = now.difference(dateTime);

  if (difference.inDays <= 14 && difference.inDays >= 0) {
    if (difference.inDays == 0) {
      if (difference.inHours < 1) {
        return "${difference.inMinutes} minutes ago";
      }
      return "${difference.inHours} hours ago";
    }
    return "${difference.inDays} days ago";
  }

  return DateFormat(format).format(dateTime);
}

String dateFormatHour(String timestamp) {
  final dateTime = DateTime.fromMillisecondsSinceEpoch(int.parse(timestamp));
  return DateFormat.Hm().format(dateTime);
}



String formatTimeAgo(int millisecondsSinceEpoch) {
  final now = DateTime.now();
  final date = DateTime.fromMillisecondsSinceEpoch(millisecondsSinceEpoch);

  final difference = now.difference(date);

  if (difference.inSeconds < 60) {
    return "${difference.inSeconds} seconds ago";
  } else if (difference.inMinutes < 60) {
    return "${difference.inMinutes} minutes ago";
  } else if (difference.inHours < 24) {
    return "${difference.inHours} hours ago";
  } else if (difference.inDays < 7) {
    return "${difference.inDays} days ago";
  } else {
    return "${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}";
  }
}

int getResponsiveCrossAxisVal(double screenWidth, {int itemWidth = 150}) {
  if (!screenWidth.isFinite || itemWidth <= 0) {
    return 1;
  }
  final count = (screenWidth / itemWidth).floor();
  return count.clamp(1, 12);
}

Future<bool> isTv() async {
  if (kIsWeb || !Platform.isAndroid) return false;
  DeviceInfoPlugin deviceInfo = DeviceInfoPlugin();
  AndroidDeviceInfo androidInfo = await deviceInfo.androidInfo;
  bool isTV = androidInfo.systemFeatures.contains('android.software.leanback');
  return isTV;
}

Future<void> navigate(dynamic page) async {
  await Navigator.push(Get.context!, MaterialPageRoute(builder: (c) => page()));
}

Future<void> navigateWithAnimation(dynamic page) async {
  await Navigator.push(
    Get.context!,
    PageRouteBuilder(
      pageBuilder: (context, animation, secondaryAnimation) => page(),
      transitionDuration: const Duration(milliseconds: 320),
      reverseTransitionDuration: const Duration(milliseconds: 300),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        final fadeAnim = CurvedAnimation(
          parent: animation,
          curve: Curves.fastOutSlowIn,
        );
        return FadeTransition(
          opacity: fadeAnim,
          child: child,
        );
      },
    ),
  );
}

Future<void> navigateWithSlide(dynamic page) async {
  await Navigator.push(
    Get.context!,
    PageRouteBuilder(
      pageBuilder: (context, animation, secondaryAnimation) => page(),
      transitionDuration: const Duration(milliseconds: 300),
      reverseTransitionDuration: const Duration(milliseconds: 250),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        final offsetAnim = Tween<Offset>(
          begin: const Offset(0, 0.08),
          end: Offset.zero,
        ).animate(CurvedAnimation(
          parent: animation,
          curve: Curves.easeOutCubic,
        ));
        final fadeAnim = CurvedAnimation(
          parent: animation,
          curve: Curves.easeIn,
        );
        return FadeTransition(
          opacity: fadeAnim,
          child: SlideTransition(
            position: offsetAnim,
            child: child,
          ),
        );
      },
    ),
  );
}

extension SizedBoxExt on num {
  SizedBox width() {
    return SizedBox(width: toDouble());
  }

  SizedBox height() {
    return SizedBox(height: toDouble());
  }
}

String getRandomTag({String? addition}) {
  if (addition != null) {
    return '$addition-${DateTime.now().millisecond}';
  }
  return DateTime.now().millisecond.toString();
}
