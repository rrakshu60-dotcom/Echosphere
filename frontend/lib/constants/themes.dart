import 'package:anymex/widgets/animation/page_transition.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Central Design Token System for EchoSphere
/// Official Shadcn Violet Design System (OKLCH color space, 1rem/16px radius, slate/obsidian neutrals)
class EchoSpherePalette {
  // ─── SHADCN VIOLET BRAND CORE ─────────────────────────────────────────────
  // Light Mode: oklch(0.4865 0.2423 291.8661) -> #6B26D9 (Royal Violet)
  static const Color lightPrimary = Color(0xFF6B26D9);
  static const Color lightPrimaryForeground = Color(0xFFF8FAFC);

  // Dark Mode: oklch(0.6083 0.2172 297.1153) -> #945AF2 (Electric Violet)
  static const Color darkPrimary = Color(0xFF945AF2);
  static const Color darkPrimaryForeground = Color(0xFF050406);

  // ─── SECONDARY & NEUTRAL BADGE TOKENS ─────────────────────────────────────
  // Light: oklch(0.9486 0.0085 303.5068) & oklch(0.3410 0.1625 292.9477)
  static const Color lightSecondary = Color(0xFFEFEDF3);
  static const Color lightSecondaryForeground = Color(0xFF401782);

  // Dark: oklch(0.2363 0.0582 299.6364) & oklch(0.8266 0.0933 301.9462)
  static const Color darkSecondary = Color(0xFF231736);
  static const Color darkSecondaryForeground = Color(0xFFD1B8F9);

  // ─── MUTED & ACCENT TOKENS ────────────────────────────────────────────────
  // Light Muted: oklch(0.9679 0.0027 264.5424) -> #F3F4F6
  static const Color lightMuted = Color(0xFFF3F4F6);
  static const Color lightMutedForeground = Color(0xFF6B7280);

  // Dark Muted: oklch(0.2217 0.0242 299.7054) -> #1D1825
  static const Color darkMuted = Color(0xFF1D1825);
  static const Color darkMutedForeground = Color(0xFFB0ABBA);

  // Light Accent: oklch(0.9546 0.0227 303.2883) -> #F3EDFD
  static const Color lightAccent = Color(0xFFF3EDFD);
  static const Color lightAccentForeground = Color(0xFF6B26D9);

  // Dark Accent: oklch(0.2255 0.0836 296.7401) -> #210F3D
  static const Color darkAccent = Color(0xFF210F3D);
  static const Color darkAccentForeground = Color(0xFF945AF2);

  // Destructive: Unified deep violet/plum tone (harmonious with purple palette, no red)
  static const Color destructive = Color(0xFF7C1E55);

  // ─── SURFACES & NEUTRALS ──────────────────────────────────────────────────
  // Light Mode Surfaces
  static const Color lightScaffold = Color(0xFFF8FAFC); // oklch(0.9838 0.0035 247.8583)
  static const Color lightSurface = Color(0xFFFFFFFF);  // oklch(1.0000 0 0) - Pure white card
  static const Color lightSurfaceContainer = Color(0xFFF3F4F6); // Muted container
  static const Color lightBorder = Color(0xFFE5E7EB);   // oklch(0.9278 0.0058 264.5314)
  static const Color lightTextPrimary = Color(0xFF030711); // oklch(0.1284 0.0267 261.5937)
  static const Color lightTextSecondary = Color(0xFF4B5563);
  static const Color lightTextMuted = Color(0xFF6B7280);

  // Dark Mode Surfaces
  static const Color darkScaffold = Color(0xFF050406); // oklch(0.1091 0.0091 301.6956) - True obsidian
  static const Color darkSurface = Color(0xFF09080D);  // oklch(0.1376 0.0118 301.0607) - Elevated obsidian card
  static const Color darkSurfaceContainer = Color(0xFF1D1825);
  static const Color darkBorder = Color(0xFF241F2E);   // oklch(0.2505 0.0293 299.5707)
  static const Color darkTextPrimary = Color(0xFFF8FAFC); // oklch(0.9838 0.0035 247.8583)
  static const Color darkTextSecondary = Color(0xFFB0ABBA);
  static const Color darkTextMuted = Color(0xFF7A7584);

  // ─── SHADOW TOKENS ────────────────────────────────────────────────────────
  // Light: hsl(263 70% 50% / 0.08)
  static const Color lightShadowColor = Color(0xFF6E26E5);
  // Dark: hsl(0 0% 0% / 0.60)
  static const Color darkShadowColor = Color(0xFF000000);

  // Standard Shadcn 1rem border radius
  static const double radius = 16.0;

  // Aliases for compatibility
  static const Color primary = lightPrimary;
  static const Color primaryAccent = darkPrimary;
  static const Color secondary = lightSecondary;

  /// Returns the unified, non-color-coded background color for notice priority badges.
  /// Eliminates distracting rainbow colors in favor of subtle Shadcn secondary styling.
  static Color getPriorityBgColor(String priority, {required bool isDark}) {
    return isDark ? darkSecondary : lightSecondary;
  }

  /// Returns the subtle outline border color for priority badges.
  static Color getPriorityBorderColor(String priority, {required bool isDark}) {
    return isDark ? darkBorder : lightBorder;
  }

  /// Returns the high-legibility foreground color for priority badges.
  static Color getPriorityColor(String priority, {bool isDark = false}) {
    return isDark ? darkSecondaryForeground : lightSecondaryForeground;
  }
}

const Color seedColor = EchoSpherePalette.lightPrimary;

ThemeData lightMode = ThemeData(
  useMaterial3: true,
  brightness: Brightness.light,
  scaffoldBackgroundColor: EchoSpherePalette.lightScaffold,
  colorScheme: const ColorScheme(
    brightness: Brightness.light,
    primary: EchoSpherePalette.lightPrimary,
    onPrimary: EchoSpherePalette.lightPrimaryForeground,
    secondary: EchoSpherePalette.lightSecondary,
    onSecondary: EchoSpherePalette.lightSecondaryForeground,
    error: EchoSpherePalette.destructive,
    onError: Colors.white,
    surface: EchoSpherePalette.lightScaffold,
    onSurface: EchoSpherePalette.lightTextPrimary,
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
      bodyLarge: TextStyle(color: EchoSpherePalette.lightTextPrimary, height: 1.4, letterSpacing: -0.2),
      bodyMedium: TextStyle(color: EchoSpherePalette.lightTextSecondary, height: 1.35, letterSpacing: -0.1),
      titleLarge: TextStyle(
          color: EchoSpherePalette.lightTextPrimary, fontWeight: FontWeight.bold, fontSize: 24, letterSpacing: -0.3),
      bodySmall: TextStyle(color: EchoSpherePalette.lightTextMuted, fontSize: 12, height: 1.3),
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: EchoSpherePalette.lightSurface,
    hintStyle: const TextStyle(color: EchoSpherePalette.lightTextMuted, fontSize: 13),
    prefixIconColor: EchoSpherePalette.lightTextSecondary,
    suffixIconColor: EchoSpherePalette.lightTextSecondary,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      borderSide: const BorderSide(color: EchoSpherePalette.lightBorder, width: 1),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      borderSide: const BorderSide(color: EchoSpherePalette.lightBorder, width: 1),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      borderSide: const BorderSide(color: EchoSpherePalette.lightPrimary, width: 1.5),
    ),
  ),
  buttonTheme: const ButtonThemeData(
    buttonColor: EchoSpherePalette.lightPrimary,
    textTheme: ButtonTextTheme.primary,
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      foregroundColor: EchoSpherePalette.lightPrimaryForeground,
      backgroundColor: EchoSpherePalette.lightPrimary,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      ),
    ),
  ),
  iconTheme: const IconThemeData(
    color: EchoSpherePalette.lightTextPrimary,
    size: 24,
  ),
  floatingActionButtonTheme: const FloatingActionButtonThemeData(
    backgroundColor: EchoSpherePalette.lightPrimary,
    foregroundColor: EchoSpherePalette.lightPrimaryForeground,
  ),
);

ThemeData darkMode = ThemeData(
  useMaterial3: true,
  brightness: Brightness.dark,
  scaffoldBackgroundColor: EchoSpherePalette.darkScaffold,
  colorScheme: const ColorScheme(
    brightness: Brightness.dark,
    primary: EchoSpherePalette.darkPrimary,
    onPrimary: EchoSpherePalette.darkPrimaryForeground,
    secondary: EchoSpherePalette.darkSecondary,
    onSecondary: EchoSpherePalette.darkSecondaryForeground,
    error: EchoSpherePalette.destructive,
    onError: Colors.white,
    surface: EchoSpherePalette.darkScaffold,
    onSurface: EchoSpherePalette.darkTextPrimary,
    surfaceContainer: EchoSpherePalette.darkSurface,
    surfaceContainerHighest: EchoSpherePalette.darkSurfaceContainer,
    outline: EchoSpherePalette.darkBorder,
  ),
  textTheme: GoogleFonts.plusJakartaSansTextTheme(
    const TextTheme(
      bodyLarge: TextStyle(color: EchoSpherePalette.darkTextPrimary, height: 1.4, letterSpacing: -0.2),
      bodyMedium: TextStyle(color: EchoSpherePalette.darkTextSecondary, height: 1.35, letterSpacing: -0.1),
      titleLarge: TextStyle(
          color: EchoSpherePalette.darkTextPrimary, fontWeight: FontWeight.bold, letterSpacing: -0.3),
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
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      borderSide: const BorderSide(color: EchoSpherePalette.darkBorder, width: 1),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      borderSide: const BorderSide(color: EchoSpherePalette.darkBorder, width: 1),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      borderSide: const BorderSide(color: EchoSpherePalette.darkPrimary, width: 1.5),
    ),
  ),
  buttonTheme: const ButtonThemeData(
    buttonColor: EchoSpherePalette.darkPrimary,
    textTheme: ButtonTextTheme.primary,
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      foregroundColor: EchoSpherePalette.darkPrimaryForeground,
      backgroundColor: EchoSpherePalette.darkPrimary,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      ),
    ),
  ),
  iconTheme: const IconThemeData(
    color: Colors.white,
    size: 24,
  ),
  floatingActionButtonTheme: const FloatingActionButtonThemeData(
    backgroundColor: EchoSpherePalette.darkPrimary,
    foregroundColor: EchoSpherePalette.darkPrimaryForeground,
  ),
);
