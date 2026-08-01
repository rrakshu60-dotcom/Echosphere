import 'package:anymex/widgets/animation/page_transition.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

const Color seedColor = Color(0xFF7C3AED);

ThemeData lightMode = ThemeData(
  useMaterial3: true,
  brightness: Brightness.light,
  scaffoldBackgroundColor: const Color(0xFFF8FAFC),
  colorScheme: ColorScheme.fromSeed(
    seedColor: seedColor,
    brightness: Brightness.light,
    surface: const Color(0xFFF8FAFC),
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
      bodyLarge: TextStyle(color: Color(0xFF0F172A), height: 1.4, letterSpacing: 0.15),
      bodyMedium: TextStyle(color: Color(0xFF334155), height: 1.35, letterSpacing: 0.1),
      titleLarge: TextStyle(
          color: Color(0xFF0F172A), fontWeight: FontWeight.bold, fontSize: 24, letterSpacing: 0.2),
      bodySmall: TextStyle(color: Color(0xFF64748B), fontSize: 12, height: 1.3),
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: Colors.grey.shade100,
    hintStyle: TextStyle(color: Colors.grey.shade500),
    prefixIconColor: Colors.grey.shade700,
    suffixIconColor: Colors.grey.shade700,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: BorderSide.none,
    ),
  ),
  buttonTheme: const ButtonThemeData(
    buttonColor: seedColor,
    textTheme: ButtonTextTheme.primary,
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      foregroundColor: Colors.white,
      backgroundColor: seedColor,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
    ),
  ),
  iconTheme: const IconThemeData(
    color: Color(0xFF0F172A),
    size: 24,
  ),
  floatingActionButtonTheme: const FloatingActionButtonThemeData(
    backgroundColor: seedColor,
    foregroundColor: Colors.white,
  ),
);

ThemeData darkMode = ThemeData(
  useMaterial3: true,
  brightness: Brightness.dark,
  scaffoldBackgroundColor: const Color(0xFF0A0D18),
  colorScheme: ColorScheme.fromSeed(
    seedColor: seedColor,
    brightness: Brightness.dark,
    surface: const Color(0xFF0A0D18),
  ),
  textTheme: GoogleFonts.plusJakartaSansTextTheme(
    const TextTheme(
      bodyLarge: TextStyle(color: Color(0xFFF1F5F9), height: 1.4, letterSpacing: 0.15),
      bodyMedium: TextStyle(color: Color(0xFFCBD5E1), height: 1.35, letterSpacing: 0.1),
      titleLarge: TextStyle(color: Color(0xFFF8FAFC), fontWeight: FontWeight.bold, letterSpacing: 0.2),
      bodySmall: TextStyle(color: Color(0xFF94A3B8), fontSize: 12, height: 1.3),
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
    fillColor: const Color(0xFF161B2E),
    hintStyle: const TextStyle(color: Color(0xFF64748B)),
    prefixIconColor: const Color(0xFF94A3B8),
    suffixIconColor: const Color(0xFF94A3B8),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: BorderSide.none,
    ),
  ),
  buttonTheme: const ButtonThemeData(
    buttonColor: seedColor,
    textTheme: ButtonTextTheme.primary,
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      foregroundColor: Colors.white,
      backgroundColor: seedColor,
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
    backgroundColor: seedColor,
    foregroundColor: Colors.white,
  ),
);
