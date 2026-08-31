import 'package:anymex/controllers/notification_controller.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:shimmer/shimmer.dart';

class NotificationsPage extends StatelessWidget {
  const NotificationsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final controller = Get.isRegistered<NotificationController>()
        ? Get.find<NotificationController>()
        : Get.put(NotificationController());

    return Column(
      children: [
        // Top Bar Header
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.notifications_active_rounded, size: 22, color: theme.colorScheme.primary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Campus Alerts & History',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: 'Poppins-Bold',
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                  ),
                  Obx(() {
                    if (controller.showOnlyUnread.value) {
                      return IconButton(
                        tooltip: 'Mark all as read',
                        constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
                        padding: EdgeInsets.zero,
                        icon: Icon(Icons.done_all_rounded, size: 20, color: theme.colorScheme.primary),
                        onPressed: () {
                          controller.markAllAsRead();
                          snackBar('All alerts marked as read and moved to History');
                        },
                      );
                    } else {
                      return IconButton(
                        tooltip: 'Clear Alerts History',
                        constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
                        padding: EdgeInsets.zero,
                        icon: const Icon(Icons.delete_sweep_rounded, size: 20, color: Colors.redAccent),
                        onPressed: () {
                          _showClearHistoryDialog(context, controller);
                        },
                      );
                    }
                  }),
                ],
              ),
              const SizedBox(height: 6),
              Obx(() => SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        EchoSphereChip(
                          label: 'Unread (${controller.unreadCount})',
                          isSelected: controller.showOnlyUnread.value,
                          onSelected: (_) => controller.toggleFilter(true),
                        ),
                        const SizedBox(width: 8),
                        EchoSphereChip(
                          label: 'Alerts History (${controller.historyCount})',
                          isSelected: !controller.showOnlyUnread.value,
                          onSelected: (_) => controller.toggleFilter(false),
                        ),
                      ],
                    ),
                  )),
            ],
          ),
        ),
        const Divider(height: 1),

        // Main Content Switcher (Active Unread vs Alerts History)
        Expanded(
          child: Obx(() {
            if (controller.showOnlyUnread.value) {
              return _buildUnreadAlertsList(context, theme, controller);
            } else {
              return _buildAlertsHistoryView(context, theme, controller);
            }
          }),
        ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Active Unread Alerts List
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildUnreadAlertsList(
      BuildContext context, ThemeData theme, NotificationController controller) {
    if (controller.isLoading.value) {
      return _buildShimmerLoading(theme);
    }

    final list = controller.unreadNotifications;
    if (list.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.check_circle_outline_rounded,
                size: 56,
                color: theme.colorScheme.primary.withOpacity(0.4),
              ),
              const SizedBox(height: 16),
              Text(
                'All Caught Up!',
                style: TextStyle(
                  fontFamily: 'Poppins-Bold',
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'No pending unread alerts. Read notifications automatically move to Alerts History.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 12,
                  color: theme.colorScheme.onSurface.withOpacity(0.5),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () => controller.toggleFilter(false),
                icon: const Icon(Icons.history_rounded, size: 16),
                label: const Text('View Alerts History'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: theme.colorScheme.primary.withOpacity(0.12),
                  foregroundColor: theme.colorScheme.primary,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16.0),
      itemCount: list.length,
      itemBuilder: (ctx, i) {
        final n = list[i];
        final id = n['id'] as int;
        final type = n['type'] as String;

        IconData iconData = Icons.notifications_rounded;
        Color iconColor = theme.colorScheme.primary;
        if (type == 'EMERGENCY') {
          iconData = Icons.warning_amber_rounded;
          iconColor = const Color(0xFFF87171);
        } else if (type == 'APPROVAL') {
          iconData = Icons.check_circle_outline_rounded;
          iconColor = const Color(0xFF34D399);
        }

        return Padding(
          padding: const EdgeInsets.only(bottom: 10.0),
          child: InkWell(
            onTap: () => controller.openNotificationDetail(n),
            borderRadius: BorderRadius.circular(16),
            child: EchoSphereContainer(
              padding: const EdgeInsets.all(14.0),
              color: theme.colorScheme.primary.withOpacity(0.06),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: iconColor.withOpacity(0.15),
                    ),
                    child: Icon(iconData, color: iconColor, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                n['title'],
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                ),
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              DateFormat('hh:mm a').format(n['time']),
                              style: TextStyle(
                                fontSize: 11,
                                color: theme.colorScheme.onSurface.withOpacity(0.5),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          n['message'],
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 13,
                            color: theme.colorScheme.onSurface.withOpacity(0.8),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton(
                    icon: Icon(
                      Icons.check_circle_outline_rounded,
                      size: 20,
                      color: theme.colorScheme.primary,
                    ),
                    tooltip: 'Mark read & move to history',
                    onPressed: () {
                      controller.markAsRead(id);
                      snackBar('Moved alert to History');
                    },
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Dedicated Alerts History View
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildAlertsHistoryView(
      BuildContext context, ThemeData theme, NotificationController controller) {
    final historyList = controller.filteredHistory;

    return Column(
      children: [
        // Search & Category Filters Toolbar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
          child: Column(
            children: [
              // Search Input
              TextField(
                onChanged: (val) => controller.historySearchQuery.value = val,
                decoration: InputDecoration(
                  hintText: 'Search alerts history...',
                  hintStyle: TextStyle(fontSize: 13, color: theme.colorScheme.onSurface.withOpacity(0.5)),
                  prefixIcon: const Icon(Icons.search_rounded, size: 18),
                  suffixIcon: controller.historySearchQuery.value.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear_rounded, size: 18),
                          onPressed: () => controller.historySearchQuery.value = '',
                        )
                      : null,
                  isDense: true,
                  contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                  filled: true,
                  fillColor: theme.colorScheme.surface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: theme.colorScheme.outline.withOpacity(0.3)),
                  ),
                ),
              ),
              const SizedBox(height: 8),

              // Filter Chips
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    'All',
                    'EMERGENCY',
                    'APPROVAL',
                    'PLACEMENT',
                  ].map((type) {
                    final isSel = controller.historyTypeFilter.value == type;
                    return Padding(
                      padding: const EdgeInsets.only(right: 6.0),
                      child: ChoiceChip(
                        label: Text(
                          type == 'EMERGENCY'
                              ? 'Emergency'
                              : (type == 'APPROVAL'
                                  ? 'Approvals'
                                  : (type == 'PLACEMENT' ? 'Placements' : 'All Types')),
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: isSel ? FontWeight.bold : FontWeight.normal,
                            color: isSel ? theme.colorScheme.primary : theme.colorScheme.onSurface,
                          ),
                        ),
                        selected: isSel,
                        onSelected: (val) {
                          if (val) controller.historyTypeFilter.value = type;
                        },
                        selectedColor: theme.colorScheme.primary.withOpacity(0.15),
                        backgroundColor: theme.colorScheme.surface,
                        visualDensity: VisualDensity.compact,
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],
          ),
        ),

        // History List
        Expanded(
          child: historyList.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(32.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.history_toggle_off_rounded,
                          size: 56,
                          color: theme.colorScheme.onSurface.withOpacity(0.2),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'No Alerts in History',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: theme.colorScheme.onSurface.withOpacity(0.6),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Read alerts automatically archive into this history log for permanent reference.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 12,
                            color: theme.colorScheme.onSurface.withOpacity(0.4),
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 6.0),
                  itemCount: historyList.length,
                  itemBuilder: (ctx, i) {
                    final n = historyList[i];
                    final id = n['id'] as int;
                    final type = n['type'] as String;

                    IconData iconData = Icons.history_rounded;
                    Color iconColor = theme.colorScheme.primary;
                    if (type == 'EMERGENCY') {
                      iconData = Icons.warning_amber_rounded;
                      iconColor = const Color(0xFFF87171);
                    } else if (type == 'APPROVAL') {
                      iconData = Icons.check_circle_outline_rounded;
                      iconColor = const Color(0xFF34D399);
                    }

                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10.0),
                      child: InkWell(
                        onTap: () => controller.openNotificationDetail(n),
                        borderRadius: BorderRadius.circular(16),
                        child: EchoSphereContainer(
                          padding: const EdgeInsets.all(14.0),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: iconColor.withOpacity(0.1),
                                ),
                                child: Icon(iconData, color: iconColor.withOpacity(0.7), size: 20),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            n['title'],
                                            maxLines: 2,
                                            overflow: TextOverflow.ellipsis,
                                            style: TextStyle(
                                              fontWeight: FontWeight.w600,
                                              fontSize: 14,
                                              color: theme.colorScheme.onSurface.withOpacity(0.9),
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        Text(
                                          DateFormat('MMM dd, hh:mm a').format(n['time']),
                                          style: TextStyle(
                                            fontSize: 10,
                                            color: theme.colorScheme.onSurface.withOpacity(0.4),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      n['message'],
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: theme.colorScheme.onSurface.withOpacity(0.6),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 6),
                              IconButton(
                                icon: Icon(
                                  Icons.mark_email_unread_rounded,
                                  size: 18,
                                  color: theme.colorScheme.primary.withOpacity(0.7),
                                ),
                                tooltip: 'Restore to Unread Queue',
                                onPressed: () {
                                  controller.markAsUnread(id);
                                  snackBar('Alert restored to Unread Queue');
                                },
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildShimmerLoading(ThemeData theme) {
    final isDark = theme.brightness == Brightness.dark;
    final baseColor = isDark ? Colors.grey.shade800 : Colors.grey.shade300;
    final highlightColor = isDark ? Colors.grey.shade700 : Colors.grey.shade100;
    final cardColor = isDark ? Colors.grey.shade900 : Colors.white;

    return Shimmer.fromColors(
      baseColor: baseColor,
      highlightColor: highlightColor,
      child: ListView.builder(
        padding: const EdgeInsets.all(16.0),
        itemCount: 4,
        itemBuilder: (_, __) => Padding(
          padding: const EdgeInsets.only(bottom: 10.0),
          child: Container(
            height: 80,
            decoration: BoxDecoration(
              color: cardColor,
              borderRadius: BorderRadius.circular(16),
            ),
          ),
        ),
      ),
    );
  }

  void _showClearHistoryDialog(BuildContext context, NotificationController controller) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.delete_sweep_rounded, color: Colors.redAccent),
            SizedBox(width: 8),
            Text('Clear Alerts History?'),
          ],
        ),
        content: const Text(
          'This will clear all archived read alerts from your device history. Unread alerts will remain intact.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () {
              controller.clearAllHistory();
              Navigator.of(ctx).pop();
              snackBar('Alerts History cleared successfully');
            },
            child: const Text('Clear All', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }
}
