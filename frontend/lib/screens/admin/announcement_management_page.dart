import 'package:echosphere/constants/themes.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_button.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_chip.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:echosphere/utils/navigation_helper.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

class AnnouncementManagementPage extends StatefulWidget {
  const AnnouncementManagementPage({super.key});

  @override
  State<AnnouncementManagementPage> createState() => _AnnouncementManagementPageState();
}

class _AnnouncementManagementPageState extends State<AnnouncementManagementPage> {
  final controller = Get.find<AnnouncementController>();
  final authController = Get.find<AuthController>();
  final searchController = TextEditingController();

  String selectedStatusFilter = 'All';
  String searchQuery = '';

  final List<String> statusFilters = ['All', 'PUBLISHED', 'SCHEDULED', 'SUBMITTED', 'REJECTED', 'ARCHIVED'];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SubPagePopScope(
      fallbackRoute: '/home',
      child: Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 10.0),
              child: Row(
                children: [
                  const EchoSphereBackButton(fallbackRoute: '/home'),
                  const SizedBox(width: 4),
                  const Icon(Icons.auto_fix_high_rounded, size: 22, color: EchoSpherePalette.lightPrimary),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: EchoSphereText(
                      text: 'Notice Management & Moderation',
                      size: 16,
                      variant: TextVariant.bold,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Obx(() => Flexible(
                        child: EchoSphereChip(
                          label: '${controller.allAnnouncements.length} Total',
                          isSelected: true,
                          onSelected: (_) {},
                        ),
                      )),
                  const SizedBox(width: 4),
                  IconButton(
                    icon: const Icon(Icons.history_rounded, size: 22),
                    tooltip: 'Audit Trail',
                    onPressed: () => _showAuditTrailDialog(context),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),

            // Search and Status Filters
            Padding(
              padding: const EdgeInsets.all(12.0),
              child: Column(
                children: [
                  TextField(
                    controller: searchController,
                    onChanged: (val) => setState(() => searchQuery = val),
                    decoration: InputDecoration(
                      hintText: 'Search by title, creator, or department...',
                      prefixIcon: Icon(Icons.search_rounded, color: theme.colorScheme.primary),
                      suffixIcon: searchQuery.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear_rounded),
                              onPressed: () {
                                searchController.clear();
                                setState(() => searchQuery = '');
                              },
                            )
                          : null,
                      filled: true,
                      fillColor: theme.colorScheme.primary.withOpacity(0.12),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: theme.colorScheme.primary.withOpacity(0.25), width: 1),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: theme.colorScheme.primary.withOpacity(0.25), width: 1),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide(color: theme.colorScheme.primary, width: 1.5),
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    ),
                  ),
                  const SizedBox(height: 10),

                  // Filter Chips Row
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: statusFilters.map((st) {
                        final isSel = selectedStatusFilter == st;
                        return Padding(
                          padding: const EdgeInsets.only(right: 6.0),
                          child: EchoSphereChip(
                            label: st,
                            isSelected: isSel,
                            onSelected: (_) => setState(() => selectedStatusFilter = st),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
            ),

            // Notice List
            Expanded(
              child: Obx(() {
                final list = controller.allAnnouncements.where((a) {
                  final q = searchQuery.toLowerCase();
                  final matchesQuery = q.isEmpty ||
                      a.title.toLowerCase().contains(q) ||
                      a.creatorName.toLowerCase().contains(q) ||
                      a.department.toLowerCase().contains(q);
                  final matchesStatus = selectedStatusFilter == 'All' ||
                      a.status.toUpperCase() == selectedStatusFilter.toUpperCase();
                  return matchesQuery && matchesStatus;
                }).toList();

                if (list.isEmpty) {
                  return const Center(
                    child: Text('No announcements found matching filter.', style: TextStyle(color: Colors.grey)),
                  );
                }

                return ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  itemCount: list.length,
                  itemBuilder: (ctx, i) {
                    final item = list[i];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      child: InkWell(
                        onTap: () => openAnnouncementDetail(context, item),
                        borderRadius: BorderRadius.circular(14),
                        child: Padding(
                          padding: const EdgeInsets.all(14.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                children: [
                                  EchoSphereBadge.secondary(label: item.category),
                                  EchoSphereBadge.priority(priority: item.priority),
                                  _buildStatusBadge(context, item.status),
                                ],
                              ),
                              const SizedBox(height: 10),
                              Text(
                                item.title,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'By: ${item.creatorName} (${item.department}) \u2022 ${DateFormat("MMM dd, yyyy \u2022 hh:mm a").format(item.createdAt)}',
                                style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurface.withOpacity(0.65)),
                              ),
                              const Divider(height: 20),

                              // Moderation Buttons Row
                              Wrap(
                                spacing: 8,
                                runSpacing: 6,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                children: [
                                  EchoSphereButton(
                                    height: 32,
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    onTap: () => _showEditDialog(context, item),
                                    child: const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.edit_rounded, size: 13),
                                        SizedBox(width: 4),
                                        Text('Modify', style: TextStyle(fontSize: 12)),
                                      ],
                                    ),
                                  ),
                                  EchoSphereButton(
                                    height: 32,
                                    color: theme.colorScheme.primary.withOpacity(0.08),
                                    border: BorderSide(color: theme.colorScheme.primary.withOpacity(0.25)),
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    onTap: () => _showReschedulePicker(context, item),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.event_rounded, size: 13, color: theme.colorScheme.primary),
                                        const SizedBox(width: 4),
                                        Text('Reschedule', style: TextStyle(fontSize: 12, color: theme.colorScheme.primary)),
                                      ],
                                    ),
                                  ),
                                  IconButton(
                                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                                    padding: const EdgeInsets.all(6),
                                    icon: Icon(
                                      Icons.delete_outline_rounded,
                                      size: 18,
                                      color: theme.colorScheme.onSurface.withOpacity(0.5),
                                    ),
                                    tooltip: 'Delete Notice',
                                    onPressed: () => _showDeleteConfirm(context, item),
                                  ),
                                ],
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
        ),
      ),
    ),
    );
  }

  void _showEditDialog(BuildContext context, AnnouncementModel item) {
    final titleCtrl = TextEditingController(text: item.title);
    final descCtrl = TextEditingController(text: item.description);
    String catVal = item.category;
    String prioVal = item.priority;
    bool deliverSpeakerVal = item.deliverSpeaker;
    String speakerVoiceVal = item.speakerVoice;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) => EchoSphereDialog(
          title: 'Modify Announcement',
          autoCloseOnConfirm: false,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
          contentWidget: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Title', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              TextField(
                controller: titleCtrl,
                decoration: const InputDecoration(
                  hintText: 'Announcement title...',
                  border: OutlineInputBorder(),
                  contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
              ),
              const SizedBox(height: 12),
              const Text('Description / Content', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              TextField(
                controller: descCtrl,
                maxLines: 4,
                decoration: const InputDecoration(
                  hintText: 'Announcement content...',
                  border: OutlineInputBorder(),
                  contentPadding: EdgeInsets.all(12),
                ),
              ),
              const SizedBox(height: 12),
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth >= 450;
                  final categoryField = Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Category', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                      const SizedBox(height: 4),
                      EchoSphereDropdown(
                        label: 'Category',
                        icon: Icons.category_rounded,
                        selectedItem: DropdownItem(value: catVal, text: catVal),
                        items: AnnouncementController.categories
                            .where((c) => c != 'All')
                            .map((c) => DropdownItem(value: c, text: c))
                            .toList(),
                        onChanged: (val) => setDlgState(() => catVal = val.value),
                      ),
                    ],
                  );

                  final priorityField = Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Priority', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                      const SizedBox(height: 4),
                      EchoSphereDropdown(
                        label: 'Priority',
                        icon: Icons.priority_high_rounded,
                        selectedItem: DropdownItem(value: prioVal, text: prioVal),
                        items: ['NORMAL', 'HIGH', 'EMERGENCY']
                            .map((p) => DropdownItem(value: p, text: p))
                            .toList(),
                        onChanged: (val) => setDlgState(() => prioVal = val.value),
                      ),
                    ],
                  );

                  if (isWide) {
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: categoryField),
                        const SizedBox(width: 10),
                        Expanded(child: priorityField),
                      ],
                    );
                  }

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      categoryField,
                      const SizedBox(height: 12),
                      priorityField,
                    ],
                  );
                },
              ),
              const SizedBox(height: 14),
              const Text('Delivery Channels', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilterChip(
                    avatar: const Icon(Icons.volume_up_rounded, size: 14),
                    label: const Text('Speaker Notice', style: TextStyle(fontSize: 12)),
                    selected: deliverSpeakerVal,
                    onSelected: (val) => setDlgState(() => deliverSpeakerVal = val),
                  ),
                ],
              ),
              if (deliverSpeakerVal) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primary.withOpacity(0.06),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Theme.of(context).colorScheme.primary.withOpacity(0.25)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.record_voice_over_rounded, size: 16, color: Theme.of(context).colorScheme.primary),
                          const SizedBox(width: 6),
                          const Expanded(
                            child: Text(
                              'Speaker Voice',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 6,
                        children: [
                          ChoiceChip(
                            avatar: const Icon(Icons.female_rounded, size: 14),
                            label: const Text('Female Voice', style: TextStyle(fontSize: 11)),
                            selected: speakerVoiceVal == 'female',
                            onSelected: (val) {
                              if (val) setDlgState(() => speakerVoiceVal = 'female');
                            },
                          ),
                          ChoiceChip(
                            avatar: const Icon(Icons.male_rounded, size: 14),
                            label: const Text('Male Voice', style: TextStyle(fontSize: 11)),
                            selected: speakerVoiceVal == 'male',
                            onSelected: (val) {
                              if (val) setDlgState(() => speakerVoiceVal = 'male');
                            },
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
          onConfirm: () async {
            if (titleCtrl.text.trim().isEmpty || descCtrl.text.trim().isEmpty) {
              errorSnackBar('Title and description cannot be empty.');
              return;
            }
            await controller.updateAnnouncement(
              id: item.id,
              title: titleCtrl.text.trim(),
              description: descCtrl.text.trim(),
              category: catVal,
              priority: prioVal,
              deliverSpeaker: deliverSpeakerVal,
              speakerVoice: speakerVoiceVal,
            );
            snackBar('Announcement updated successfully!');
            if (ctx.mounted) {
              Navigator.of(ctx).pop();
            }
            setState(() {});
          },
        ),
      ),
    );
  }

  Future<void> _showReschedulePicker(BuildContext context, AnnouncementModel item) async {
    final now = DateTime.now();
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: item.createdAt.isAfter(now) ? item.createdAt : now.add(const Duration(hours: 1)),
      firstDate: now.subtract(const Duration(days: 1)),
      lastDate: now.add(const Duration(days: 365)),
    );

    if (pickedDate != null && context.mounted) {
      final pickedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(item.createdAt),
      );

      if (pickedTime != null) {
        final newDateTime = DateTime(
          pickedDate.year,
          pickedDate.month,
          pickedDate.day,
          pickedTime.hour,
          pickedTime.minute,
        );

        await controller.rescheduleAnnouncement(
          id: item.id,
          newScheduledTime: newDateTime,
        );

        snackBar('Announcement rescheduled for ${DateFormat("MMM dd, yyyy \u2022 hh:mm a").format(newDateTime)}!');
        setState(() {});
      }
    }
  }

  void _showDeleteConfirm(BuildContext context, AnnouncementModel item) {
    showDialog(
      context: context,
      builder: (ctx) => EchoSphereDialog(
        title: 'Delete Announcement?',
        message: 'Are you sure you want to delete "${item.title}"? This action cannot be undone.',
        confirmText: 'Delete',
        onConfirm: () async {
          await controller.deleteAnnouncement(item.id);
          snackBar('Announcement deleted.');
          setState(() {});
        },
      ),
    );
  }

  Widget _buildStatusBadge(BuildContext context, String status) {
    if (status == 'REJECTED') {
      return EchoSphereBadge.destructive(label: status);
    }
    if (status == 'ARCHIVED') {
      return EchoSphereBadge.muted(label: status);
    }
    if (status == 'SUBMITTED' || status == 'DRAFT') {
      return EchoSphereBadge.secondary(label: status);
    }
    return EchoSphereBadge.defaultBadge(label: status);
  }

  void _showAuditTrailDialog(BuildContext context) {
    List<dynamic>? logs;
    bool isLoading = true;
    bool noticeOnly = true;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) {
          final theme = Theme.of(context);

          if (logs == null && isLoading) {
            EchosphereApiService().getAuditLogs().then((res) {
              if (ctx.mounted) {
                setDlgState(() {
                  logs = res;
                  isLoading = false;
                });
              }
            }).catchError((_) {
              if (ctx.mounted) {
                setDlgState(() {
                  logs = [];
                  isLoading = false;
                });
              }
            });
          }

          final allLogs = logs ?? [];
          final filteredLogs = noticeOnly
              ? allLogs.where((l) {
                  final entity = l['entity']?.toString().toUpperCase() ?? '';
                  final action = l['action']?.toString().toUpperCase() ?? '';
                  final desc = l['description']?.toString().toUpperCase() ?? '';
                  return entity.contains('ANNOUNCEMENT') ||
                      entity.contains('NOTICE') ||
                      action.contains('ANNOUNCEMENT') ||
                      desc.contains('ANNOUNCEMENT') ||
                      desc.contains('NOTICE');
                }).toList()
              : allLogs;

          final isSmall = MediaQuery.of(ctx).size.width < 580;
          final dialogWidth = isSmall ? MediaQuery.of(ctx).size.width * 0.92 : 560.0;

          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                Icon(Icons.history_rounded, color: theme.colorScheme.primary, size: 22),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'Notice Moderation Audit Trail',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh_rounded, size: 20),
                  onPressed: () {
                    setDlgState(() {
                      logs = null;
                      isLoading = true;
                    });
                  },
                ),
              ],
            ),
            content: SizedBox(
              width: dialogWidth,
              height: 440,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      FilterChip(
                        label: const Text('Notice Events', style: TextStyle(fontSize: 11)),
                        selected: noticeOnly,
                        onSelected: (val) => setDlgState(() => noticeOnly = true),
                      ),
                      const SizedBox(width: 8),
                      FilterChip(
                        label: const Text('All System Events', style: TextStyle(fontSize: 11)),
                        selected: !noticeOnly,
                        onSelected: (val) => setDlgState(() => noticeOnly = false),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  const Divider(height: 1),
                  const SizedBox(height: 8),
                  Expanded(
                    child: isLoading
                        ? const Center(child: CircularProgressIndicator())
                        : filteredLogs.isEmpty
                            ? Center(
                                child: Text(
                                  noticeOnly ? 'No notice moderation logs recorded yet.' : 'No audit logs found.',
                                  style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: theme.colorScheme.onSurface.withOpacity(0.6)),
                                ),
                              )
                            : ListView.separated(
                                itemCount: filteredLogs.length,
                                separatorBuilder: (_, __) => const Divider(height: 12),
                                itemBuilder: (context, idx) {
                                  final log = filteredLogs[idx];
                                  final action = log['action']?.toString() ?? 'ACTION';
                                  final desc = log['description']?.toString() ?? '';
                                  final createdAt = log['created_at']?.toString().split('.').first.replaceAll('T', ' ') ?? '';
                                  final userId = log['user_id']?.toString() ?? '';

                                  return Padding(
                                    padding: const EdgeInsets.symmetric(vertical: 4.0),
                                    child: Row(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: theme.colorScheme.primary.withOpacity(0.12),
                                            borderRadius: BorderRadius.circular(6),
                                            border: Border.all(color: theme.colorScheme.primary.withOpacity(0.3)),
                                          ),
                                          child: Text(
                                            action,
                                            style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: theme.colorScheme.primary),
                                          ),
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                desc.isNotEmpty ? desc : action,
                                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                                              ),
                                              const SizedBox(height: 2),
                                              Text(
                                                'Actor: ${userId.isNotEmpty ? "User #$userId" : "System"} \u2022 $createdAt',
                                                style: TextStyle(fontSize: 10, color: theme.colorScheme.onSurface.withOpacity(0.6)),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Close'),
              ),
            ],
          );
        },
      ),
    );
  }
}
