import 'dart:async';
import 'dart:io';
import 'dart:ui';

import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/echosphere_ai_controller.dart';
import 'package:anymex/controllers/settings/settings.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/controllers/ui/greeting.dart';
import 'package:anymex/screens/auth/login_screen.dart';
import 'package:anymex/screens/home_page.dart';
import 'package:anymex/utils/external_font_loader.dart';
import 'package:anymex/utils/logger.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_splash_screen.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_titlebar.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:window_manager/window_manager.dart';

WebViewEnvironment? webViewEnvironment;

class MyHttpoverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(context) {
    return super.createHttpClient(context)
      ..badCertificateCallback = (cert, String host, int port) => true;
  }
}

class MyCustomScrollBehavior extends MaterialScrollBehavior {
  @override
  Set<PointerDeviceKind> get dragDevices => {
        PointerDeviceKind.touch,
        PointerDeviceKind.mouse,
        PointerDeviceKind.trackpad,
        PointerDeviceKind.stylus
      };
}

Future<void> safeCall(FutureOr<void> Function() function,
    {String? errorMessage}) async {
  try {
    await function();
  } catch (e) {
    if (errorMessage != null) {
      Logger.e("$errorMessage: $e");
    } else {
      debugPrint("Error: $e");
    }
  }
}

void main(List<String> args) async {
  runZonedGuarded(() async {
    WidgetsFlutterBinding.ensureInitialized();

    await safeCall(() async {
      await Supabase.initialize(
        url: 'https://wvugkkwykdnyzcmaoxgj.supabase.co',
        anonKey: 'sb_publishable_0h1jDPae3piItxkSaJEuqA_aUWgFuDe',
      );
    }, errorMessage: 'Failed to initialize Supabase');

    await safeCall(() async {
      if (!kIsWeb && !Platform.isLinux) {
        if (Platform.isWindows || Platform.isMacOS) {
          webViewEnvironment = await WebViewEnvironment.create();
        }
        await InAppWebViewController.setWebContentsDebuggingEnabled(
          !const bool.fromEnvironment('dart.vm.product'),
        );
      }
    }, errorMessage: 'Failed to initialize WebViewEnvironment');

    await safeCall(() => ExternalFontLoader.loadAllFonts(),
        errorMessage: 'Failed to load external fonts');

    await Logger.init();

    if (!kIsWeb) {
      HttpOverrides.global = MyHttpoverrides();
    }

    _initializeGetxController();

    await safeCall(() async {
      if (!kIsWeb && !Platform.isAndroid && !Platform.isIOS) {
        await windowManager.ensureInitialized();
        await EchoSphereTitleBar.initialize();
      } else if (!kIsWeb) {
        SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
        SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
            systemNavigationBarDividerColor: Colors.transparent,
            systemNavigationBarContrastEnforced: false,
            systemNavigationBarColor: Colors.transparent,
            systemNavigationBarIconBrightness: Brightness.dark,
            statusBarColor: Colors.transparent,
            statusBarBrightness: Brightness.dark));
      }
    }, errorMessage: 'Failed to initialize window manager or system UI');

    FlutterError.onError = (FlutterErrorDetails details) async {
      FlutterError.presentError(details);
      Logger.e("FLUTTER ERROR: ${details.exceptionAsString()}");
      Logger.e("STACK: ${details.stack}");
    };

    PlatformDispatcher.instance.onError = (error, stack) {
      Logger.e("PLATFORM ERROR: $error");
      Logger.e("STACK: $stack");
      return true;
    };

    runApp(
      ChangeNotifierProvider(
        create: (context) => ThemeProvider(),
        child: const MainApp(),
      ),
    );
  }, (error, stackTrace) async {
    Logger.e("CRASH: $error");
    Logger.e("STACK: $stackTrace");
  }, zoneSpecification: ZoneSpecification(
    print: (Zone self, ZoneDelegate parent, Zone zone, String line) {
      if (Logger.isInitialized) {
        Logger.i(line);
      } else {
        parent.print(zone, line);
      }
    },
  ));
}

void _initializeGetxController() async {
  await safeCall(() {
    Get.put(Settings());
    Get.put(AuthController(), permanent: true);
    Get.put(AnnouncementController(), permanent: true);
    Get.put(EchosphereAiController(), permanent: true);
    Get.put(GreetingController());
  }, errorMessage: 'Failed to register GetX controllers');
}

class MainApp extends StatefulWidget {
  const MainApp({super.key});

  @override
  State<MainApp> createState() => _MainAppState();
}

class _MainAppState extends State<MainApp> {
  bool _showMainApp = false;
  bool _isFullScreen = false;

  late FocusNode focusNode;

  KeyEventResult _handleKeyEvent(FocusNode node, KeyEvent event) {
    if (event is KeyDownEvent &&
        event.logicalKey == LogicalKeyboardKey.escape) {
      if (_isFullScreen) {
        EchoSphereTitleBar.setFullScreen(false);
      } else {
        BuildContext escapeContext = Get.context!;
        if (Navigator.of(escapeContext).canPop()) {
          Navigator.pop(escapeContext);
        }
      }
      return KeyEventResult.handled;
    } else if (event is KeyDownEvent &&
        event.logicalKey == LogicalKeyboardKey.f11) {
      EchoSphereTitleBar.toggleFullScreen();
      return KeyEventResult.handled;
    } else if (event is KeyDownEvent &&
        event.logicalKey == LogicalKeyboardKey.enter) {
      final isAltPressed = HardwareKeyboard.instance.logicalKeysPressed
              .contains(LogicalKeyboardKey.altLeft) ||
          HardwareKeyboard.instance.logicalKeysPressed
              .contains(LogicalKeyboardKey.altRight);
      if (isAltPressed) {
        EchoSphereTitleBar.toggleFullScreen();
        return KeyEventResult.handled;
      }
    }
    return KeyEventResult.ignored;
  }

  @override
  void initState() {
    super.initState();

    EchoSphereTitleBar.isFullScreen.addListener(
        () => _isFullScreen = EchoSphereTitleBar.isFullScreen.value);

    focusNode = FocusNode(canRequestFocus: false, skipTraversal: true);

    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        setState(() {
          _showMainApp = true;
        });
      }
    });
  }

  @override
  void dispose() {
    Logger.dispose();
    focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Provider.of<ThemeProvider>(context);

    return Focus(
      focusNode: focusNode,
      onKeyEvent: _handleKeyEvent,
      child: GetMaterialApp(
        scrollBehavior: MyCustomScrollBehavior(),
        debugShowCheckedModeBanner: false,
        title: "EchoSphere",
        theme: theme.lightTheme,
        darkTheme: theme.darkTheme,
        themeMode: theme.isSystemMode
            ? ThemeMode.system
            : theme.isLightMode
                ? ThemeMode.light
                : ThemeMode.dark,
        home: _showMainApp
            ? Obx(() {
                final authController = Get.find<AuthController>();
                return authController.isLoggedIn.value
                    ? const HomePage()
                    : const LoginScreen();
              })
            : const EchoSphereSplashScreen(),
        builder: (context, child) {
          if (PlatformDispatcher.instance.views.length > 1) {
            return child!;
          }
          final isDesktop = !kIsWeb && Platform.isWindows;

          if (isDesktop) {
            return Column(
              children: [
                EchoSphereTitleBar.titleBar(),
                Expanded(child: RepaintBoundary(child: child!)),
              ],
            );
          }

          return child!;
        },
        enableLog: true,
        logWriterCallback: (text, {isError = false}) async {
          Logger.d(text);
        },
      ),
    );
  }
}
