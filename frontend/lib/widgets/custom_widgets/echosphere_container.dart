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

    final BoxDecoration effectiveDecoration = decoration ??
        BoxDecoration(
          color: color ?? Theme.of(context).colorScheme.surfaceContainerHighest.opaque(0.25),
          borderRadius: effectiveRadius,
          border: border ?? Border.all(
            color: Theme.of(context).colorScheme.primary.opaque(0.18),
            width: 0.8,
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
                        color: Theme.of(context).colorScheme.primary.opaque(0.03),
                        blurRadius: 20,
                        spreadRadius: -4,
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
