import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/screens/announcements/announcement_detail_page.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
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

  final List<String> statusFilters = ['All', 'PUBLISHED', 'SCHEDULED', 'SUBMITTED', 'REJECTED'];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final canPop = ModalRoute.of(context)?.canPop ?? false;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 10.0),
              child: Row(
                children: [
                  if (canPop) ...[
                    IconButton(
                      icon: const Icon(Icons.arrow_back_rounded),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    const SizedBox(width: 4),
                  ],
                  const Icon(Icons.auto_fix_high_rounded, size: 22, color: Colors.amber),
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
                          label: '${controller.announcements.length} Total',
                          isSelected: true,
                          onSelected: (_) {},
                        ),
                      )),
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
                final list = controller.announcements.where((a) {
                  final q = searchQuery.toLowerCase();
                  final matchesQuery = q.isEmpty ||
                      a.title.toLowerCase().contains(q) ||
                      a.creatorName.toLowerCase().contains(q) ||
                      a.department.toLowerCase().contains(q);
                  final matchesStatus = selectedStatusFilter == 'All' || a.status == selectedStatusFilter;
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
                        onTap: () => Get.to(() => AnnouncementDetailPage(announcement: item)),
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
                                  EchoSphereChip(label: item.category, isSelected: true, onSelected: (_) {}),
                                  EchoSphereChip(label: item.priority, isSelected: false, onSelected: (_) {}),
                                  _buildStatusBadge(item.status),
                                ],
                              ),
                              const SizedBox(height: 10),
                              Text(
                                item.title,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'By: ${item.creatorName} (${item.department}) • ${DateFormat("MMM dd, yyyy • hh:mm a").format(item.createdAt)}',
                                style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurface.withOpacity(0.65)),
                              ),
                              const Divider(height: 20),

                              // Moderation Buttons Row
                              Wrap(
                                spacing: 8,
                                runSpacing: 6,
                                children: [
                                  EchoSphereButton(
                                    height: 34,
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    onTap: () => _showEditDialog(context, item),
                                    child: const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.edit_rounded, size: 14),
                                        SizedBox(width: 4),
                                        Text('Modify', style: TextStyle(fontSize: 12)),
                                      ],
                                    ),
                                  ),
                                  EchoSphereButton(
                                    height: 34,
                                    color: Colors.blue.withOpacity(0.15),
                                    border: const BorderSide(color: Colors.blue),
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    onTap: () => _showReschedulePicker(context, item),
                                    child: const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.event_rounded, size: 14, color: Colors.blue),
                                        SizedBox(width: 4),
                                        Text('Reschedule', style: TextStyle(fontSize: 12, color: Colors.blue)),
                                      ],
                                    ),
                                  ),
                                  EchoSphereButton(
                                    height: 34,
                                    color: Colors.red.withOpacity(0.15),
                                    border: const BorderSide(color: Colors.red),
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    onTap: () => _showDeleteConfirm(context, item),
                                    child: const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.delete_outline_rounded, size: 14, color: Colors.red),
                                        SizedBox(width: 4),
                                        Text('Delete', style: TextStyle(fontSize: 12, color: Colors.red)),
                                      ],
                                    ),
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
    );
  }

  void _showEditDialog(BuildContext context, AnnouncementModel item) {
    final titleCtrl = TextEditingController(text: item.title);
    final descCtrl = TextEditingController(text: item.description);
    String catVal = item.category;
    String prioVal = item.priority;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) => EchoSphereDialog(
          title: 'Modify Announcement',
          contentWidget: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Title', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(controller: titleCtrl, decoration: const InputDecoration(border: OutlineInputBorder())),
                const SizedBox(height: 12),
                const Text('Description / Content', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(controller: descCtrl, maxLines: 4, decoration: const InputDecoration(border: OutlineInputBorder())),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Category', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                          const SizedBox(height: 4),
                          EchoSphereDropdown(
                            label: 'Category',
                            icon: Icons.category,
                            selectedItem: DropdownItem(value: catVal, text: catVal),
                            items: AnnouncementController.categories
                                .where((c) => c != 'All')
                                .map((c) => DropdownItem(value: c, text: c))
                                .toList(),
                            onChanged: (val) => setDlgState(() => catVal = val.value),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Priority', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                          const SizedBox(height: 4),
                          EchoSphereDropdown(
                            label: 'Priority',
                            icon: Icons.priority_high,
                            selectedItem: DropdownItem(value: prioVal, text: prioVal),
                            items: ['NORMAL', 'HIGH', 'EMERGENCY']
                                .map((p) => DropdownItem(value: p, text: p))
                                .toList(),
                            onChanged: (val) => setDlgState(() => prioVal = val.value),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
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
            );
            snackBar('Announcement updated successfully!');
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

        snackBar('Announcement rescheduled for ${DateFormat("MMM dd, yyyy • hh:mm a").format(newDateTime)}!');
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

  Widget _buildStatusBadge(String status) {
    Color bg = Colors.green;
    if (status == 'SUBMITTED' || status == 'DRAFT') bg = Colors.orange;
    if (status == 'SCHEDULED') bg = Colors.blue;
    if (status == 'REJECTED') bg = Colors.red;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg.withOpacity(0.2),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: bg, width: 1),
      ),
      child: Text(
        status,
        style: TextStyle(
          color: bg,
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
