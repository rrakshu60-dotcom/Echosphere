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

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: isSelected ? [glowingShadow(context)] : null,
      ),
      child: FilterChip(
        selected: isSelected,
        onSelected: onSelected,
        avatar: icon != null
            ? Icon(
                icon,
                size: 14,
                color: isSelected
                    ? Colors.white
                    : (isDark ? const Color(0xFFCBD5E1) : const Color(0xFF475569)),
              )
            : null,
        label: Text(label),
        labelStyle: TextStyle(
          color: isSelected
              ? Colors.white
              : (isDark ? const Color(0xFFCBD5E1) : const Color(0xFF475569)),
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
          fontSize: 12,
        ),
        checkmarkColor: isSelected ? Colors.white : Colors.transparent,
        backgroundColor: isDark
            ? const Color(0xFF1E293B)
            : const Color(0xFFF1F5F9),
        selectedColor: theme.colorScheme.primary,
        side: BorderSide(
          color: isSelected
              ? theme.colorScheme.primary
              : (isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0)),
          width: 0.8,
        ),
        showCheckmark: icon == null && showCheck,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
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
    return FilterChip(
      selected: isSelected,
      onSelected: onSelected,
      showCheckmark: showCheck,
      label: icon,
      checkmarkColor: isSelected
          ? context.colors.onPrimary
          : context.colors.onSurfaceVariant,
      labelStyle: TextStyle(
        color: isSelected
            ? context.colors.onPrimary
            : context.colors.onSurfaceVariant,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
      ),
      backgroundColor: context.colors.secondaryContainer,
      selectedColor: context.colors.primary,
      side: BorderSide.none,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
    );
  }
}
