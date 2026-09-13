import 'package:anymex/constants/themes.dart';
import 'package:anymex/controllers/settings/methods.dart';
import 'package:anymex/controllers/settings/settings.dart';
import 'package:flutter/material.dart';
import 'package:anymex/utils/theme_extensions.dart';
import 'package:get/get.dart';

class EchoSphereChip extends StatelessWidget {
  final String label;
  final IconData? icon;
  final bool isSelected;
  final Function(bool e) onSelected;
  final bool showCheck;

  const EchoSphereChip({
    super.key,
    required this.label,
    this.icon,
    required this.isSelected,
    required this.onSelected,
    this.showCheck = true,
  });

  BoxShadow glowingShadow(BuildContext context) {
    if (!Get.isRegistered<Settings>()) {
      return BoxShadow(
        color: context.colors.primary.opaque(
            Theme.of(context).brightness == Brightness.dark ? 0.08 : 0.15),
        blurRadius: 16.0,
        spreadRadius: -2.0,
        offset: const Offset(0, 2),
      );
    }
    final controller = Get.find<Settings>();
    if (controller.glowMultiplier.value == 0.0) {
      return const BoxShadow(color: Colors.transparent);
    } else {
      return BoxShadow(
        color: context.colors.primary.opaque(
            Theme.of(context).brightness == Brightness.dark ? 0.08 : 0.15),
        blurRadius: 16.0.multiplyBlur(),
        spreadRadius:
            -2.0.multiplyGlow(),
        offset: const Offset(0, 2),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final unselectedFg = isDark
        ? EchoSpherePalette.darkSecondaryForeground
        : EchoSpherePalette.lightSecondaryForeground;
    final unselectedBg = isDark
        ? EchoSpherePalette.darkSecondary
        : EchoSpherePalette.lightSecondary;
    final unselectedBorder = isDark
        ? EchoSpherePalette.darkBorder
        : EchoSpherePalette.lightBorder;

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        boxShadow: isSelected ? [glowingShadow(context)] : null,
      ),
      child: FilterChip(
        selected: isSelected,
        onSelected: onSelected,
        avatar: icon != null
            ? Icon(
                icon,
                size: 14,
                color: isSelected ? Colors.white : unselectedFg,
              )
            : null,
        label: Text(label),
        labelStyle: TextStyle(
          color: isSelected ? Colors.white : unselectedFg,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
          fontSize: 12,
        ),
        checkmarkColor: isSelected ? Colors.white : Colors.transparent,
        backgroundColor: unselectedBg,
        selectedColor: theme.colorScheme.primary,
        side: BorderSide(
          color: isSelected ? theme.colorScheme.primary : unselectedBorder,
          width: 1.0,
        ),
        showCheckmark: icon == null && showCheck,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
      ),
    );
  }
}

class EchoSphereIconChip extends StatelessWidget {
  final Widget icon;
  final bool isSelected;
  final Function(bool e) onSelected;
  final bool showCheck;

  const EchoSphereIconChip(
      {super.key,
      required this.icon,
      required this.isSelected,
      required this.onSelected,
      this.showCheck = true});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return FilterChip(
      selected: isSelected,
      onSelected: onSelected,
      showCheckmark: showCheck,
      label: icon,
      checkmarkColor: isSelected
          ? context.colors.onPrimary
          : (isDark ? EchoSpherePalette.darkSecondaryForeground : EchoSpherePalette.lightSecondaryForeground),
      labelStyle: TextStyle(
        color: isSelected
            ? context.colors.onPrimary
            : (isDark ? EchoSpherePalette.darkSecondaryForeground : EchoSpherePalette.lightSecondaryForeground),
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
      ),
      backgroundColor: isDark ? EchoSpherePalette.darkSecondary : EchoSpherePalette.lightSecondary,
      selectedColor: context.colors.primary,
      side: BorderSide(
        color: isSelected
            ? context.colors.primary
            : (isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder),
        width: 1.0,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
      ),
    );
  }
}
