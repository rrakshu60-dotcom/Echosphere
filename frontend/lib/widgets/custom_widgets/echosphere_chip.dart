import 'package:anymex/constants/themes.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

enum BadgeVariant {
  defaultVariant,
  secondary,
  outline,
  destructive,
  muted,
}

enum BadgeSize {
  sm,
  md,
  lg,
}

/// Official Shadcn / Tweakcn Badge Widget
/// Compact, elegant, non-interactive (or tap-responsive) status badge.
class EchoSphereBadge extends StatelessWidget {
  final String label;
  final IconData? icon;
  final BadgeVariant variant;
  final BadgeSize size;
  final VoidCallback? onTap;

  const EchoSphereBadge({
    super.key,
    required this.label,
    this.icon,
    this.variant = BadgeVariant.secondary,
    this.size = BadgeSize.sm,
    this.onTap,
  });

  const EchoSphereBadge.secondary({
    super.key,
    required this.label,
    this.icon,
    this.size = BadgeSize.sm,
    this.onTap,
  }) : variant = BadgeVariant.secondary;

  const EchoSphereBadge.outline({
    super.key,
    required this.label,
    this.icon,
    this.size = BadgeSize.sm,
    this.onTap,
  }) : variant = BadgeVariant.outline;

  const EchoSphereBadge.destructive({
    super.key,
    required this.label,
    this.icon,
    this.size = BadgeSize.sm,
    this.onTap,
  }) : variant = BadgeVariant.destructive;

  const EchoSphereBadge.muted({
    super.key,
    required this.label,
    this.icon,
    this.size = BadgeSize.sm,
    this.onTap,
  }) : variant = BadgeVariant.muted;

  const EchoSphereBadge.defaultBadge({
    super.key,
    required this.label,
    this.icon,
    this.size = BadgeSize.sm,
    this.onTap,
  }) : variant = BadgeVariant.defaultVariant;

  factory EchoSphereBadge.priority({
    Key? key,
    required String priority,
    BadgeSize size = BadgeSize.sm,
    VoidCallback? onTap,
  }) {
    final clean = priority.toUpperCase();
    if (clean == 'EMERGENCY') {
      return EchoSphereBadge.destructive(
        key: key,
        label: priority,
        icon: Icons.warning_amber_rounded,
        size: size,
        onTap: onTap,
      );
    }
    if (clean == 'HIGH') {
      return EchoSphereBadge.secondary(
        key: key,
        label: priority,
        icon: Icons.priority_high_rounded,
        size: size,
        onTap: onTap,
      );
    }
    if (clean == 'NORMAL') {
      return EchoSphereBadge.secondary(
        key: key,
        label: priority,
        size: size,
        onTap: onTap,
      );
    }
    return EchoSphereBadge.outline(
      key: key,
      label: priority,
      size: size,
      onTap: onTap,
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    Color bg;
    Color fg;
    Color border;

    switch (variant) {
      case BadgeVariant.destructive:
        bg = isDark
            ? EchoSpherePalette.darkErrorContainer.withOpacity(0.55)
            : EchoSpherePalette.lightErrorContainer;
        fg = isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive;
        border = isDark
            ? EchoSpherePalette.darkDestructive.withOpacity(0.35)
            : EchoSpherePalette.lightDestructive.withOpacity(0.28);
        break;
      case BadgeVariant.outline:
        bg = Colors.transparent;
        fg = isDark ? EchoSpherePalette.darkTextSecondary : EchoSpherePalette.lightTextSecondary;
        border = isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder;
        break;
      case BadgeVariant.muted:
        bg = isDark ? EchoSpherePalette.darkMuted : EchoSpherePalette.lightMuted;
        fg = isDark ? EchoSpherePalette.darkMutedForeground : EchoSpherePalette.lightMutedForeground;
        border = isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder;
        break;
      case BadgeVariant.defaultVariant:
        bg = isDark ? EchoSpherePalette.darkPrimary : EchoSpherePalette.lightPrimary;
        fg = isDark ? EchoSpherePalette.darkPrimaryForeground : EchoSpherePalette.lightPrimaryForeground;
        border = bg;
        break;
      case BadgeVariant.secondary:
        bg = isDark ? EchoSpherePalette.darkSecondary : EchoSpherePalette.lightSecondary;
        fg = isDark ? EchoSpherePalette.darkSecondaryForeground : EchoSpherePalette.lightSecondaryForeground;
        border = isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder;
        break;
    }

    Widget content = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: border, width: 1.0),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 12, color: fg),
            const SizedBox(width: 4),
          ],
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: GoogleFonts.inter(
                color: fg,
                fontSize: 11,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.22,
              ),
            ),
          ),
        ],
      ),
    );

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: content,
      );
    }
    return content;
  }
}

/// Official Shadcn / Tweakcn Interactive Filter Chip
/// Used for filtering categories, tabs, and toggles without distracting neon glow.
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
    this.showCheck = false,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final selectedBg = isDark
        ? EchoSpherePalette.darkSecondary
        : const Color(0xFFEEF2FF);
    final selectedFg = isDark
        ? EchoSpherePalette.darkSecondaryForeground
        : const Color(0xFF4338CA);
    final selectedBorder = isDark
        ? EchoSpherePalette.darkPrimary
        : const Color(0xFF6366F1);

    final unselectedBg = isDark
        ? EchoSpherePalette.darkSurface
        : EchoSpherePalette.lightSurface;
    final unselectedFg = isDark
        ? EchoSpherePalette.darkTextSecondary
        : EchoSpherePalette.lightTextSecondary;
    final unselectedBorder = isDark
        ? EchoSpherePalette.darkBorder
        : EchoSpherePalette.lightBorder;

    return InkWell(
      onTap: () => onSelected(!isSelected),
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? selectedBg : unselectedBg,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? selectedBorder : unselectedBorder,
            width: isSelected ? 1.2 : 1.0,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: 13,
                color: isSelected ? selectedBorder : unselectedFg,
              ),
              const SizedBox(width: 5),
            ] else if (showCheck && isSelected) ...[
              Icon(
                Icons.check_rounded,
                size: 13,
                color: selectedBorder,
              ),
              const SizedBox(width: 5),
            ],
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.inter(
                  color: isSelected ? selectedFg : unselectedFg,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  fontSize: 12,
                  letterSpacing: -0.24,
                ),
              ),
            ),
          ],
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

  const EchoSphereIconChip({
    super.key,
    required this.icon,
    required this.isSelected,
    required this.onSelected,
    this.showCheck = false,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final selectedBg = isDark ? EchoSpherePalette.darkSecondary : const Color(0xFFEEF2FF);
    final selectedBorder = isDark ? EchoSpherePalette.darkPrimary : const Color(0xFF6366F1);

    final unselectedBg = isDark ? EchoSpherePalette.darkSurface : EchoSpherePalette.lightSurface;
    final unselectedBorder = isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder;

    return InkWell(
      onTap: () => onSelected(!isSelected),
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: isSelected ? selectedBg : unselectedBg,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? selectedBorder : unselectedBorder,
            width: isSelected ? 1.2 : 1.0,
          ),
        ),
        child: icon,
      ),
    );
  }
}
