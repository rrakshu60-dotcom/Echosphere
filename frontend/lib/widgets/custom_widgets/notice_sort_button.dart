import 'package:anymex/controllers/announcement_controller.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class NoticeSortButton extends StatelessWidget {
  final bool compact;

  const NoticeSortButton({
    super.key,
    this.compact = false,
  });

  IconData _getSortIcon(String currentSort) {
    switch (currentSort) {
      case 'Oldest First':
        return Icons.history_rounded;
      case 'Highest Priority':
        return Icons.keyboard_double_arrow_up_rounded;
      case 'Lowest Priority':
        return Icons.keyboard_double_arrow_down_rounded;
      case 'Title (A-Z)':
        return Icons.sort_by_alpha_rounded;
      case 'Title (Z-A)':
        return Icons.sort_by_alpha_rounded;
      case 'Newest First':
      default:
        return Icons.schedule_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<AnnouncementController>();
    final theme = Theme.of(context);

    return Obx(() {
      final current = controller.sortBy.value;
      final icon = _getSortIcon(current);

      return PopupMenuButton<String>(
        onSelected: (val) {
          controller.sortBy.value = val;
        },
        tooltip: 'Sort Notices',
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        color: theme.colorScheme.surface,
        elevation: 6,
        itemBuilder: (ctx) => AnnouncementController.sortOptions.map((opt) {
          final isSelected = opt == current;
          return PopupMenuItem<String>(
            value: opt,
            child: Row(
              children: [
                Icon(
                  _getSortIcon(opt),
                  size: 18,
                  color: isSelected
                      ? theme.colorScheme.primary
                      : theme.colorScheme.onSurface.withOpacity(0.7),
                ),
                const SizedBox(width: 10),
                Text(
                  opt,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    color: isSelected
                        ? theme.colorScheme.primary
                        : theme.colorScheme.onSurface,
                  ),
                ),
                if (isSelected) ...[
                  const Spacer(),
                  Icon(Icons.check_rounded, size: 16, color: theme.colorScheme.primary),
                ],
              ],
            ),
          );
        }).toList(),
        child: Container(
          padding: EdgeInsets.symmetric(
            horizontal: compact ? 8 : 10,
            vertical: compact ? 4 : 5,
          ),
          decoration: BoxDecoration(
            color: theme.colorScheme.primary.withOpacity(0.12),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: theme.colorScheme.primary.withOpacity(0.3),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: compact ? 14 : 15,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: 4),
              Text(
                compact ? current.split(' ').first : current,
                style: TextStyle(
                  fontSize: compact ? 11 : 12,
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(width: 2),
              Icon(
                Icons.arrow_drop_down_rounded,
                size: compact ? 14 : 16,
                color: theme.colorScheme.primary,
              ),
            ],
          ),
        ),
      );
    });
  }
}
