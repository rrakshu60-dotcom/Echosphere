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
        : (borderRadius ?? BorderRadius.circular(20.multiplyRadius()));

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final defaultBgColor = isDark
        ? const Color(0xFF131D33).withValues(alpha: 0.85)
        : Colors.white.withValues(alpha: 0.92);
    final defaultBorderColor = isDark
        ? const Color(0xFF1E293B)
        : const Color(0xFFE2E8F0);

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
                            ? Colors.black.withValues(alpha: 0.25)
                            : const Color(0xFF4F46E5).withValues(alpha: 0.04),
                        blurRadius: 16,
                        offset: const Offset(0, 4),
                        spreadRadius: -2,
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
