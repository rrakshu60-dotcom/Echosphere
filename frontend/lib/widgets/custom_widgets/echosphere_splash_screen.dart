import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_animated_logo.dart';

/// Splash Screen with Animated EchoSphere ES Logo
class EchoSphereSplashScreen extends StatefulWidget {
  final VoidCallback? onAnimationComplete;

  const EchoSphereSplashScreen({
    super.key,
    this.onAnimationComplete,
  });

  @override
  State<EchoSphereSplashScreen> createState() => _EchoSphereSplashScreenState();
}

class _EchoSphereSplashScreenState extends State<EchoSphereSplashScreen> {
  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.sizeOf(context);
    final logoSize =
        math.min(screenSize.width * 0.45, 210.0).clamp(120.0, 220.0);

    return Scaffold(
      backgroundColor: const Color(0xFF050406),
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.center,
            radius: 0.95,
            colors: [
              Color(0xFF210F3D), // Shadcn dark accent violet glow
              Color(0xFF130924), // Subtle mid violet-obsidian transition
              Color(0xFF050406), // True Shadcn dark obsidian background
            ],
            stops: [0.0, 0.55, 1.0],
          ),
        ),
        child: Center(
          child: SingleChildScrollView(
            physics: const NeverScrollableScrollPhysics(),
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  EchoSphereAnimatedLogo(
                    size: logoSize,
                    autoPlay: true,
                    onAnimationComplete: () {
                      // Seamless transition after fill animation completes
                      Future.delayed(const Duration(milliseconds: 400), () {
                        if (mounted) {
                          widget.onAnimationComplete?.call();
                        }
                      });
                    },
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

