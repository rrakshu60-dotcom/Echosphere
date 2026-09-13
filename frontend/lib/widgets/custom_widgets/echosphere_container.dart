import 'package:anymex/constants/themes.dart';
import 'package:anymex/controllers/settings/methods.dart';
import 'package:anymex/controllers/settings/settings.dart';
import 'package:flutter/material.dart';
import 'package:anymex/utils/theme_extensions.dart';
import 'package:get/get.dart';

class EchoSphereContainer extends StatelessWidget {
  final Widget? child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final Color? color;
  final BoxDecoration? decoration;
  final double? height;
  final double? width;
  final AlignmentGeometry? alignment;
  final BorderRadiusGeometry? borderRadius;
  final double? radius;
  final BoxBorder? border;
  final BoxShadow? shadow;
  final Clip clipBehavior;
  final bool enableGlow;

  const EchoSphereContainer({
    super.key,
    this.child,
    this.padding,
    this.margin,
    this.color,
    this.decoration,
    this.height,
    this.width,
    this.alignment,
    this.borderRadius,
    this.radius,
    this.border,
    this.shadow,
    this.clipBehavior = Clip.none,
    this.enableGlow = false,
  });

  @override
  Widget build(BuildContext context) {
    if (Get.isRegistered<Settings>()) {
      return Obx(() {
        final _ = Get.find<Settings>().glowMultiplier.value;
        return _buildContainer(context);
      });
    }
    return _buildContainer(context);
  }

  Widget _buildContainer(BuildContext context) {
    final BorderRadiusGeometry effectiveRadius = radius != null
        ? BorderRadius.circular(radius!.multiplyRadius())
        : (borderRadius ?? BorderRadius.circular(16.multiplyRadius()));

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final defaultBgColor = isDark
        ? EchoSpherePalette.darkSurface
        : EchoSpherePalette.lightSurface;
    final defaultBorderColor = isDark
        ? EchoSpherePalette.darkBorder
        : EchoSpherePalette.lightBorder;

    final BoxDecoration effectiveDecoration = decoration ??
        BoxDecoration(
          color: color ?? defaultBgColor,
          borderRadius: effectiveRadius,
          border: border ?? Border.all(
            color: defaultBorderColor,
            width: 1.0,
          ),
          boxShadow: enableGlow
              ? [
                  BoxShadow(
                    color: Theme.of(context)
                        .colorScheme
                        .primary
                        .opaque(.08.multiplyGlow(), iReallyMeanIt: true),
                    offset: const Offset(0, 4),
                    blurRadius: 30.multiplyBlur(),
                    spreadRadius: 2.multiplyGlow(),
                  )
                ]
              : shadow != null
                  ? [shadow!]
                  : [
                      BoxShadow(
                        color: isDark
                            ? Colors.black.withValues(alpha: 0.55)
                            : const Color(0xFF0F172A).withValues(alpha: 0.04),
                        blurRadius: isDark ? 36 : 20,
                        offset: Offset(0, isDark ? 16 : 4),
                        spreadRadius: isDark ? -8 : -2,
                      ),
                      if (!isDark)
                        BoxShadow(
                          color: const Color(0xFF0F172A).withValues(alpha: 0.02),
                          blurRadius: 4,
                          offset: const Offset(0, 1),
                          spreadRadius: 0,
                        ),
                    ],
        );

    return ClipRRect(
      borderRadius: effectiveRadius,
      clipBehavior: clipBehavior,
      child: Container(
        height: height,
        width: width,
        alignment: alignment,
        margin: margin,
        padding: padding,
        decoration: effectiveDecoration,
        child: child,
      ),
    );
  }
}
