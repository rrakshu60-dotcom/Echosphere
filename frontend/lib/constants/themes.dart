import 'package:anymex/widgets/animation/page_transition.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Central Design Token System for EchoSphere
/// Executive institutional palette: Deep Indigo, Tech Cyan, crisp Slate neutrals, and soft tinted priority badges.
class EchoSpherePalette {
  // Brand Core
  static const Color primary = Color(0xFF4F46E5); // Deep Indigo
  static const Color primaryAccent = Color(0xFF6366F1); // Vibrant Indigo
  static const Color secondary = Color(0xFF0EA5E9); // Tech Sky Cyan
  static const Color secondaryAccent = Color(0xFF38BDF8); // Light Cyan
  static const Color tertiary = Color(0xFF8B5CF6); // Soft Lilac Accent

  // Semantic Status Tokens
  static const Color emergency = Color(0xFFEF4444); // Controlled Crimson
  static const Color urgent = Color(0xFFF59E0B); // Warm Amber
  static const Color high = Color(0xFFEAB308); // High Yellow
  static const Color normal = Color(0xFF4F46E5); // Indigo
  static const Color low = Color(0xFF64748B); // Slate Gray
  static const Color success = Color(0xFF10B981); // Emerald

  // Light Mode Surfaces & Neutrals
  static const Color lightScaffold = Color(0xFFF8FAFC);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceContainer = Color(0xFFF1F5F9);
  static const Color lightBorder = Color(0xFFE2E8F0);
  static const Color lightTextPrimary = Color(0xFF0F172A);
  static const Color lightTextSecondary = Color(0xFF475569);
  static const Color lightTextMuted = Color(0xFF94A3B8);

  // Dark Mode Surfaces & Neutrals
  static const Color darkScaffold = Color(0xFF0B1120); // Midnight Slate
  static const Color darkSurface = Color(0xFF131D33);
  static const Color darkSurfaceContainer = Color(0xFF1E293B);
  static const Color darkBorder = Color(0xFF1E293B);
  static const Color darkTextPrimary = Color(0xFFF8FAFC);
  static const Color darkTextSecondary = Color(0xFF94A3B8);
  static const Color darkTextMuted = Color(0xFF64748B);

  /// Returns the semantic accent color for a notice priority.
  static Color getPriorityColor(String priority) {
    switch (priority.toUpperCase()) {
      case 'EMERGENCY':
        return emergency;
      case 'URGENT':
        return urgent;
      case 'HIGH':
        return high;
      case 'LOW':
        return low;
      case 'NORMAL':
      default:
        return normal;
    }
  }

  /// Returns the subtle tinted background color for priority badges.
  static Color getPriorityBgColor(String priority, {required bool isDark}) {
    final baseColor = getPriorityColor(priority);
    return isDark ? baseColor.withValues(alpha: 0.16) : baseColor.withValues(alpha: 0.09);
  }

  /// Returns the subtle outline border color for priority badges.
  static Color getPriorityBorderColor(String priority, {required bool isDark}) {
    final baseColor = getPriorityColor(priority);
    return isDark ? baseColor.withValues(alpha: 0.35) : baseColor.withValues(alpha: 0.25);
  }
}

const Color seedColor = EchoSpherePalette.primary;

ThemeData lightMode = ThemeData(
  useMaterial3: true,
  brightness: Brightness.light,
  scaffoldBackgroundColor: EchoSpherePalette.lightScaffold,
  colorScheme: ColorScheme.fromSeed(
    seedColor: EchoSpherePalette.primary,
    brightness: Brightness.light,
    primary: EchoSpherePalette.primary,
    secondary: EchoSpherePalette.secondary,
    surface: EchoSpherePalette.lightScaffold,
    surfaceContainer: EchoSpherePalette.lightSurface,
    surfaceContainerHighest: EchoSpherePalette.lightSurfaceContainer,
    outline: EchoSpherePalette.lightBorder,
  ),
  pageTransitionsTheme: PageTransitionsTheme(
    builders: {
      for (var platform in TargetPlatform.values)
        if (platform != TargetPlatform.iOS)
          platform: const SharedAxisTransition(),
    },
  ),
  textTheme: GoogleFonts.plusJakartaSansTextTheme(
    const TextTheme(
      bodyLarge: TextStyle(color: EchoSpherePalette.lightTextPrimary, height: 1.4, letterSpacing: 0.15),
      bodyMedium: TextStyle(color: EchoSpherePalette.lightTextSecondary, height: 1.35, letterSpacing: 0.1),
      titleLarge: TextStyle(
          color: EchoSpherePalette.lightTextPrimary, fontWeight: FontWeight.bold, fontSize: 24, letterSpacing: 0.2),
      bodySmall: TextStyle(color: EchoSpherePalette.lightTextMuted, fontSize: 12, height: 1.3),
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: EchoSpherePalette.lightSurfaceContainer,
    hintStyle: const TextStyle(color: EchoSpherePalette.lightTextMuted, fontSize: 13),
    prefixIconColor: EchoSpherePalette.lightTextSecondary,
    suffixIconColor: EchoSpherePalette.lightTextSecondary,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(color: EchoSpherePalette.lightBorder, width: 1),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(color: EchoSpherePalette.lightBorder, width: 1),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(color: EchoSpherePalette.primary, width: 1.5),
    ),
  ),
  buttonTheme: const ButtonThemeData(
    buttonColor: EchoSpherePalette.primary,
    textTheme: ButtonTextTheme.primary,
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      foregroundColor: Colors.white,
      backgroundColor: EchoSpherePalette.primary,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
    ),
  ),
  iconTheme: const IconThemeData(
    color: EchoSpherePalette.lightTextPrimary,
    size: 24,
  ),
  floatingActionButtonTheme: const FloatingActionButtonThemeData(
    backgroundColor: EchoSpherePalette.primary,
    foregroundColor: Colors.white,
  ),
);

ThemeData darkMode = ThemeData(
  useMaterial3: true,
  brightness: Brightness.dark,
  scaffoldBackgroundColor: EchoSpherePalette.darkScaffold,
  colorScheme: ColorScheme.fromSeed(
    seedColor: EchoSpherePalette.primary,
    brightness: Brightness.dark,
    primary: EchoSpherePalette.primaryAccent,
    secondary: EchoSpherePalette.secondary,
    surface: EchoSpherePalette.darkScaffold,
    surfaceContainer: EchoSpherePalette.darkSurface,
    surfaceContainerHighest: EchoSpherePalette.darkSurfaceContainer,
    outline: EchoSpherePalette.darkBorder,
  ),
  textTheme: GoogleFonts.plusJakartaSansTextTheme(
    const TextTheme(
      bodyLarge: TextStyle(color: EchoSpherePalette.darkTextPrimary, height: 1.4, letterSpacing: 0.15),
      bodyMedium: TextStyle(color: EchoSpherePalette.darkTextSecondary, height: 1.35, letterSpacing: 0.1),
      titleLarge: TextStyle(color: EchoSpherePalette.darkTextPrimary, fontWeight: FontWeight.bold, letterSpacing: 0.2),
      bodySmall: TextStyle(color: EchoSpherePalette.darkTextMuted, fontSize: 12, height: 1.3),
    ),
  ),
  pageTransitionsTheme: PageTransitionsTheme(
    builders: {
      for (var platform in TargetPlatform.values)
        if (platform != TargetPlatform.iOS)
          platform: const SharedAxisTransition(),
    },
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: EchoSpherePalette.darkSurface,
    hintStyle: const TextStyle(color: EchoSpherePalette.darkTextMuted, fontSize: 13),
    prefixIconColor: EchoSpherePalette.darkTextSecondary,
    suffixIconColor: EchoSpherePalette.darkTextSecondary,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(color: EchoSpherePalette.darkBorder, width: 1),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(color: EchoSpherePalette.darkBorder, width: 1),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: const BorderSide(color: EchoSpherePalette.primaryAccent, width: 1.5),
    ),
  ),
  buttonTheme: const ButtonThemeData(
    buttonColor: EchoSpherePalette.primaryAccent,
    textTheme: ButtonTextTheme.primary,
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      foregroundColor: Colors.white,
      backgroundColor: EchoSpherePalette.primaryAccent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
    ),
  ),
  iconTheme: const IconThemeData(
    color: Colors.white,
    size: 24,
  ),
  floatingActionButtonTheme: const FloatingActionButtonThemeData(
    backgroundColor: EchoSpherePalette.primaryAccent,
    foregroundColor: Colors.white,
  ),
);
