import 'package:anymex/controllers/notification_controller.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
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
        // Top Bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
          child: Row(
            children: [
              Icon(Icons.notifications_rounded, size: 22, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Notifications',
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
              const SizedBox(width: 6),
              Obx(() => Flexible(
                    child: EchoSphereChip(
                      label: '${controller.unreadCount} Unread',
                      isSelected: true,
                      onSelected: (_) {},
                    ),
                  )),
              const SizedBox(width: 4),
              IconButton(
                tooltip: 'Mark all as read',
                constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
                padding: EdgeInsets.zero,
                icon: Icon(Icons.done_all_rounded, size: 18, color: theme.colorScheme.primary),
                onPressed: () => controller.markAllAsRead(),
              ),
            ],
          ),
        ),
        const Divider(height: 1),

        // Notifications List
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
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

            final list = controller.notifications;
            if (list.isEmpty) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(32.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.notifications_none_rounded,
                        size: 56,
                        color: theme.colorScheme.onSurface.withOpacity(0.2),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No notifications yet',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'You will receive campus alerts, approvals, and system updates here.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 12,
                          color: theme.colorScheme.onSurface.withOpacity(0.4),
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
                final isRead = controller.isRead(id);
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
                      padding: const EdgeInsets.all(16.0),
                      color: isRead ? null : theme.colorScheme.primary.withOpacity(0.06),
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
                          const SizedBox(width: 14),
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
                                          fontWeight: isRead ? FontWeight.w600 : FontWeight.bold,
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
                        ],
                      ),
                    ),
                  ),
                );
              },
            );
          }),
        ),
      ],
    );
  }
}
