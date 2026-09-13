import 'package:anymex/constants/themes.dart';
import 'package:dynamic_color/dynamic_color.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class ThemeProvider extends ChangeNotifier {
  bool isLightMode;
  bool isSystemMode;
  bool isOled;
  late ThemeData _lightTheme;
  late ThemeData _darkTheme;
  late String currentThemeMode;
  Color _seedColor;
  late int selectedVariantIndex;

  List<String> availThemeModes = ["default", "material", "custom"];

  ThemeProvider()
      : _seedColor = EchoSpherePalette.lightPrimary,
        isLightMode = false,
        isSystemMode = false,
        isOled = false,
        selectedVariantIndex = 0,
        currentThemeMode = "default" {
    _determineSeedColor();
    _updateTheme();
  }

  ThemeData get lightTheme => _lightTheme;
  ThemeData get darkTheme => _darkTheme;
  Color get seedColor => _seedColor;

  void _determineSeedColor() {
    if (currentThemeMode == "default") {
      _seedColor = EchoSpherePalette.lightPrimary;
    } else if (currentThemeMode == "material") {
      loadDynamicTheme();
    } else {
      _seedColor = EchoSpherePalette.lightPrimary;
    }
  }

  Future<void> loadDynamicTheme() async {
    currentThemeMode = "material";
    final corePalette = await DynamicColorPlugin.getCorePalette();
    _seedColor = corePalette != null
        ? Color(corePalette.primary.get(40))
        : EchoSpherePalette.lightPrimary;
    _updateTheme();
  }

  void updateSchemeVariant(int index) {
    selectedVariantIndex = index;
    _updateTheme();
  }

  void toggleTheme() {
    isLightMode = !isLightMode;
    isSystemMode = false;
    _updateTheme();
  }

  void setSystemMode() {
    isSystemMode = true;
    notifyListeners();
  }

  void setLightMode() {
    isLightMode = true;
    _updateTheme();
  }

  void setDarkMode() {
    isLightMode = false;
    isSystemMode = false;
    _updateTheme();
  }

  void setDefaultTheme() {
    currentThemeMode = "default";
    _seedColor = EchoSpherePalette.lightPrimary;
    _updateTheme();
  }

  void setCustomSeedColor(int index, {Color? customColor}) {
    currentThemeMode = "custom";
    if (customColor != null) {
      _seedColor = customColor;
    } else {
      _seedColor = EchoSpherePalette.lightPrimary;
    }
    _updateTheme();
  }

  void toggleOled(bool value) {
    isOled = value;
    _updateTheme();
  }

  void syncStatusBar() {
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle(
        systemNavigationBarColor: Colors.transparent,
        systemNavigationBarContrastEnforced: false,
        systemNavigationBarDividerColor: Colors.transparent,
        systemNavigationBarIconBrightness:
            isLightMode ? Brightness.dark : Brightness.light,
        statusBarColor: Colors.transparent,
        statusBarBrightness: isLightMode ? Brightness.dark : Brightness.light,
        statusBarIconBrightness:
            isLightMode ? Brightness.dark : Brightness.light));
  }

  void clearCache() {
    isLightMode = false;
    isSystemMode = false;
    isOled = false;
    selectedVariantIndex = 0;
    currentThemeMode = "default";
    _seedColor = EchoSpherePalette.lightPrimary;

    _updateTheme();
    notifyListeners();
  }

  void _updateTheme() {
    _lightTheme = lightMode;
    _darkTheme = isOled
        ? darkMode.copyWith(
            scaffoldBackgroundColor: Colors.black,
            colorScheme: darkMode.colorScheme.copyWith(
              surface: Colors.black,
              surfaceContainer: Colors.black,
            ),
          )
        : darkMode;

    syncStatusBar();
    notifyListeners();
  }
}
