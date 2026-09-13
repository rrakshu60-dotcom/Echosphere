import 'package:anymex/widgets/animation/page_transition.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Central Design Token System for EchoSphere
/// Official Shadcn Violet Design System (OKLCH color space, 1rem/16px radius, slate/obsidian neutrals)
class EchoSpherePalette {
  // ─── SHADCN VIOLET BRAND CORE ─────────────────────────────────────────────
  // Light Mode: Refined modern violet-indigo (soft on eyes, premium, high contrast)
  static const Color lightPrimary = Color(0xFF5B50D6);
  static const Color lightPrimaryForeground = Color(0xFFFFFFFF);

  // Dark Mode: Soft, elegant modern violet (easy on eyes)
  static const Color darkPrimary = Color(0xFF8B5CF6);
  static const Color darkPrimaryForeground = Color(0xFFFFFFFF);

  // ─── SECONDARY & NEUTRAL BADGE TOKENS ─────────────────────────────────────
  // Light: Clean calm slate neutrals with high-contrast text
  static const Color lightSecondary = Color(0xFFF1F5F9);
  static const Color lightSecondaryForeground = Color(0xFF334155);

  // Dark: Soft harmonious slate-violet
  static const Color darkSecondary = Color(0xFF262235);
  static const Color darkSecondaryForeground = Color(0xFFD6C8F5);

  // ─── MUTED & ACCENT TOKENS ────────────────────────────────────────────────
  // Light Muted: Calm slate surface & legible text
  static const Color lightMuted = Color(0xFFF8FAFC);
  static const Color lightMutedForeground = Color(0xFF64748B);

  // Dark Muted: Soft slate-charcoal
  static const Color darkMuted = Color(0xFF222631);
  static const Color darkMutedForeground = Color(0xFFA1A8B8);

  // Light Accent: Gentle violet-tinted wash
  static const Color lightAccent = Color(0xFFF5F3FF);
  static const Color lightAccentForeground = Color(0xFF5B50D6);

  // Dark Accent
  static const Color darkAccent = Color(0xFF28223D);
  static const Color darkAccentForeground = Color(0xFFA78BFA);

  // ─── HARMONIOUS ACCENT / NOTICE TOKENS (No Harsh Red) ──────────────────────
  // Elegant muted rose/plum tones that seamlessly blend with indigo and purple:
  // Light mode: Sophisticated muted rose-wine #8E3B56 (gentle, high legibility)
  // Dark mode: Soft eye-friendly dusty rose #D47A9A (zero eye strain, warm glow)
  static const Color lightDestructive = Color(0xFF8E3B56);
  static const Color darkDestructive = Color(0xFFD47A9A);
  static const Color destructive = lightDestructive;
  static const Color destructiveForeground = Color(0xFFFFFFFF);
  static const Color lightErrorContainer = Color(0xFFF8EBF0);
  static const Color darkErrorContainer = Color(0xFF331B26);

  // ─── SURFACES & NEUTRALS ──────────────────────────────────────────────────
  // Light Mode Surfaces - Serene, soft off-white & crisp high-legibility slate
  static const Color lightScaffold = Color(0xFFF8F9FA); // Gentle eye-resting canvas
  static const Color lightSurface = Color(0xFFFFFFFF);  // Pure crisp white card
  static const Color lightSurfaceContainer = Color(0xFFF1F5F9); // Clean slate container
  static const Color lightBorder = Color(0xFFE2E8F0);   // Subtle, delicate slate border
  static const Color lightTextPrimary = Color(0xFF0F172A); // Slate 900 - supreme readability
  static const Color lightTextSecondary = Color(0xFF475569); // Slate 600 - minimum 7:1 contrast
  static const Color lightTextMuted = Color(0xFF64748B); // Slate 500 - minimum 4.6:1 contrast

  // Dark Mode Surfaces - Softer charcoal & slate (comfortable and modern, no eye-strain)
  static const Color darkScaffold = Color(0xFF111318); // Soft deep slate-charcoal
  static const Color darkSurface = Color(0xFF181B22);  // Refined dark card surface
  static const Color darkSurfaceContainer = Color(0xFF20242E); // Subtle container
  static const Color darkBorder = Color(0xFF2D323E);   // Softer border
  static const Color darkTextPrimary = Color(0xFFF1F3F9);
  static const Color darkTextSecondary = Color(0xFFA1A8B8);
  static const Color darkTextMuted = Color(0xFF737A8C);

  // ─── CHART TOKENS ─────────────────────────────────────────────────────────
  static const Color chart1 = Color(0xFF5B50D6);
  static const Color chart2 = Color(0xFF0CB8DA);
  static const Color chart3 = Color(0xFF29A366);
  static const Color chart4 = Color(0xFFAF57DB);
  static const Color chart5 = Color(0xFFEB4799);

  // ─── RADIUS TOKENS (Tweakcn Exact Scale) ──────────────────────────────────
  static const double radius = 16.0;      // 1rem (Default --radius)
  static const double radiusSm = 12.0;    // calc(1rem - 4px)
  static const double radiusMd = 14.0;    // calc(1rem - 2px)
  static const double radiusLg = 16.0;    // 1rem
  static const double radiusXl = 20.0;    // calc(1rem + 4px)

  // ─── SHADOW TOKENS ────────────────────────────────────────────────────────
  // Light: Soft natural slate drop shadow (no harsh purple halos)
  static const Color lightShadowColor = Color(0x0A0F172A);
  // Dark: Deep charcoal shadow
  static const Color darkShadowColor = Color(0xFF000000);

  /// Generates the signature multi-layer elevation shadow
  static List<BoxShadow> getElevationShadow({required bool isDark, double level = 1}) {
    if (isDark) {
      return [
        BoxShadow(
          color: Colors.black.withOpacity(0.55),
          offset: const Offset(0, 16),
          blurRadius: 36,
          spreadRadius: -8,
        ),
        BoxShadow(
          color: Colors.black.withOpacity(0.35),
          offset: const Offset(0, 1),
          blurRadius: 2,
          spreadRadius: -1,
        ),
      ];
    } else {
      return [
        BoxShadow(
          color: const Color(0xFF0F172A).withOpacity(0.04),
          offset: const Offset(0, 8),
          blurRadius: 24,
          spreadRadius: -4,
        ),
        BoxShadow(
          color: const Color(0xFF0F172A).withOpacity(0.02),
          offset: const Offset(0, 1),
          blurRadius: 3,
          spreadRadius: 0,
        ),
      ];
    }
  }

  // Aliases for compatibility
  static const Color primary = lightPrimary;
  static const Color primaryAccent = darkPrimary;
  static const Color secondary = lightSecondary;

  /// Returns the unified, non-color-coded background color for notice priority badges.
  /// Eliminates distracting rainbow colors in favor of subtle Shadcn secondary styling.
  static Color getPriorityBgColor(String priority, {required bool isDark}) {
    final p = priority.toUpperCase();
    if (p == 'EMERGENCY') {
      return isDark
          ? darkErrorContainer.withOpacity(0.55)
          : lightErrorContainer;
    }
    return isDark ? darkSecondary : lightSecondary;
  }

  /// Returns the subtle outline border color for priority badges.
  static Color getPriorityBorderColor(String priority, {required bool isDark}) {
    final p = priority.toUpperCase();
    if (p == 'EMERGENCY') {
      return isDark
          ? darkDestructive.withOpacity(0.35)
          : lightDestructive.withOpacity(0.28);
    }
    return isDark ? darkBorder : lightBorder;
  }

  /// Returns the high-legibility foreground color for priority badges.
  static Color getPriorityColor(String priority, {bool isDark = false}) {
    final p = priority.toUpperCase();
    if (p == 'EMERGENCY') {
      return isDark ? darkDestructive : lightDestructive;
    }
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
    primaryContainer: EchoSpherePalette.lightAccent,
    onPrimaryContainer: EchoSpherePalette.lightAccentForeground,
    secondary: EchoSpherePalette.lightSecondary,
    onSecondary: EchoSpherePalette.lightSecondaryForeground,
    secondaryContainer: EchoSpherePalette.lightSecondary,
    onSecondaryContainer: EchoSpherePalette.lightSecondaryForeground,
    error: EchoSpherePalette.lightDestructive,
    onError: Colors.white,
    errorContainer: EchoSpherePalette.lightErrorContainer,
    onErrorContainer: EchoSpherePalette.lightDestructive,
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
  textTheme: GoogleFonts.interTextTheme(
    const TextTheme(
      headlineLarge: TextStyle(color: EchoSpherePalette.lightTextPrimary, fontWeight: FontWeight.w700, fontSize: 32, letterSpacing: -0.64),
      headlineMedium: TextStyle(color: EchoSpherePalette.lightTextPrimary, fontWeight: FontWeight.w700, fontSize: 28, letterSpacing: -0.56),
      headlineSmall: TextStyle(color: EchoSpherePalette.lightTextPrimary, fontWeight: FontWeight.w600, fontSize: 24, letterSpacing: -0.48),
      titleLarge: TextStyle(color: EchoSpherePalette.lightTextPrimary, fontWeight: FontWeight.w600, fontSize: 20, letterSpacing: -0.40),
      titleMedium: TextStyle(color: EchoSpherePalette.lightTextPrimary, fontWeight: FontWeight.w600, fontSize: 16, letterSpacing: -0.32),
      titleSmall: TextStyle(color: EchoSpherePalette.lightTextSecondary, fontWeight: FontWeight.w500, fontSize: 14, letterSpacing: -0.28),
      bodyLarge: TextStyle(color: EchoSpherePalette.lightTextPrimary, height: 1.4, fontSize: 16, letterSpacing: -0.32),
      bodyMedium: TextStyle(color: EchoSpherePalette.lightTextSecondary, height: 1.35, fontSize: 14, letterSpacing: -0.28),
      bodySmall: TextStyle(color: EchoSpherePalette.lightTextMuted, fontSize: 12, height: 1.3, letterSpacing: -0.24),
      labelLarge: TextStyle(color: EchoSpherePalette.lightTextPrimary, fontWeight: FontWeight.w500, fontSize: 14, letterSpacing: -0.28),
      labelMedium: TextStyle(color: EchoSpherePalette.lightTextSecondary, fontSize: 12, letterSpacing: -0.24),
      labelSmall: TextStyle(color: EchoSpherePalette.lightTextMuted, fontSize: 11, letterSpacing: -0.22),
    ),
  ),
  cardTheme: CardThemeData(
    color: EchoSpherePalette.lightSurface,
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      side: const BorderSide(color: EchoSpherePalette.lightBorder, width: 1),
    ),
    margin: EdgeInsets.zero,
  ),
  dialogTheme: DialogThemeData(
    backgroundColor: EchoSpherePalette.lightSurface,
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      side: const BorderSide(color: EchoSpherePalette.lightBorder, width: 1),
    ),
  ),
  snackBarTheme: SnackBarThemeData(
    backgroundColor: EchoSpherePalette.lightTextPrimary,
    contentTextStyle: GoogleFonts.inter(
      color: EchoSpherePalette.lightScaffold,
      fontSize: 14,
      letterSpacing: -0.28,
    ),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radiusSm),
    ),
    behavior: SnackBarBehavior.floating,
  ),
  dividerTheme: const DividerThemeData(
    color: EchoSpherePalette.lightBorder,
    thickness: 1,
    space: 1,
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: EchoSpherePalette.lightSurface,
    hintStyle: const TextStyle(color: EchoSpherePalette.lightTextMuted, fontSize: 13, letterSpacing: -0.26),
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
    primaryContainer: EchoSpherePalette.darkAccent,
    onPrimaryContainer: EchoSpherePalette.darkAccentForeground,
    secondary: EchoSpherePalette.darkSecondary,
    onSecondary: EchoSpherePalette.darkSecondaryForeground,
    secondaryContainer: EchoSpherePalette.darkSecondary,
    onSecondaryContainer: EchoSpherePalette.darkSecondaryForeground,
    error: EchoSpherePalette.darkDestructive,
    onError: Colors.white,
    errorContainer: EchoSpherePalette.darkErrorContainer,
    onErrorContainer: EchoSpherePalette.darkDestructive,
    surface: EchoSpherePalette.darkScaffold,
    onSurface: EchoSpherePalette.darkTextPrimary,
    surfaceContainer: EchoSpherePalette.darkSurface,
    surfaceContainerHighest: EchoSpherePalette.darkSurfaceContainer,
    outline: EchoSpherePalette.darkBorder,
  ),
  textTheme: GoogleFonts.interTextTheme(
    const TextTheme(
      headlineLarge: TextStyle(color: EchoSpherePalette.darkTextPrimary, fontWeight: FontWeight.w700, fontSize: 32, letterSpacing: -0.64),
      headlineMedium: TextStyle(color: EchoSpherePalette.darkTextPrimary, fontWeight: FontWeight.w700, fontSize: 28, letterSpacing: -0.56),
      headlineSmall: TextStyle(color: EchoSpherePalette.darkTextPrimary, fontWeight: FontWeight.w600, fontSize: 24, letterSpacing: -0.48),
      titleLarge: TextStyle(color: EchoSpherePalette.darkTextPrimary, fontWeight: FontWeight.w600, fontSize: 20, letterSpacing: -0.40),
      titleMedium: TextStyle(color: EchoSpherePalette.darkTextPrimary, fontWeight: FontWeight.w600, fontSize: 16, letterSpacing: -0.32),
      titleSmall: TextStyle(color: EchoSpherePalette.darkTextSecondary, fontWeight: FontWeight.w500, fontSize: 14, letterSpacing: -0.28),
      bodyLarge: TextStyle(color: EchoSpherePalette.darkTextPrimary, height: 1.4, fontSize: 16, letterSpacing: -0.32),
      bodyMedium: TextStyle(color: EchoSpherePalette.darkTextSecondary, height: 1.35, fontSize: 14, letterSpacing: -0.28),
      bodySmall: TextStyle(color: EchoSpherePalette.darkTextMuted, fontSize: 12, height: 1.3, letterSpacing: -0.24),
      labelLarge: TextStyle(color: EchoSpherePalette.darkTextPrimary, fontWeight: FontWeight.w500, fontSize: 14, letterSpacing: -0.28),
      labelMedium: TextStyle(color: EchoSpherePalette.darkTextSecondary, fontSize: 12, letterSpacing: -0.24),
      labelSmall: TextStyle(color: EchoSpherePalette.darkTextMuted, fontSize: 11, letterSpacing: -0.22),
    ),
  ),
  cardTheme: CardThemeData(
    color: EchoSpherePalette.darkSurface,
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      side: const BorderSide(color: EchoSpherePalette.darkBorder, width: 1),
    ),
    margin: EdgeInsets.zero,
  ),
  dialogTheme: DialogThemeData(
    backgroundColor: EchoSpherePalette.darkSurface,
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
      side: const BorderSide(color: EchoSpherePalette.darkBorder, width: 1),
    ),
  ),
  snackBarTheme: SnackBarThemeData(
    backgroundColor: EchoSpherePalette.darkSurfaceContainer,
    contentTextStyle: GoogleFonts.inter(
      color: EchoSpherePalette.darkTextPrimary,
      fontSize: 14,
      letterSpacing: -0.28,
    ),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(EchoSpherePalette.radiusSm),
      side: const BorderSide(color: EchoSpherePalette.darkBorder, width: 1),
    ),
    behavior: SnackBarBehavior.floating,
  ),
  dividerTheme: const DividerThemeData(
    color: EchoSpherePalette.darkBorder,
    thickness: 1,
    space: 1,
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
    hintStyle: const TextStyle(color: EchoSpherePalette.darkTextMuted, fontSize: 13, letterSpacing: -0.26),
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
