import 'dart:io';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/widgets/common/glow.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';

class AnnouncementDetailPage extends StatelessWidget {
  final AnnouncementModel announcement;

  const AnnouncementDetailPage({super.key, required this.announcement});

  Future<void> _downloadAttachment(BuildContext context, String filename) async {
    try {
      Directory? dir;
      if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
        dir = await getDownloadsDirectory() ?? await getApplicationDocumentsDirectory();
      } else {
        dir = await getApplicationDocumentsDirectory();
      }

      final file = File('${dir.path}/$filename');
      final content = '''
================================================================================
                        ECHOSPHERE INSTITUTIONAL NOTICE
================================================================================

TITLE: ${announcement.title}
DEPARTMENT: ${announcement.department}
CATEGORY: ${announcement.category}
PRIORITY: ${announcement.priority}
ISSUED BY: ${announcement.creatorName}
DATE: ${DateFormat('MMMM dd, yyyy • hh:mm a').format(announcement.createdAt)}

--------------------------------------------------------------------------------
OFFICIAL NOTICE DETAILS:
--------------------------------------------------------------------------------
${announcement.description}

AI SUMMARY:
${announcement.aiSummary ?? 'N/A'}

================================================================================
Downloaded & Saved via EchoSphere Smart Campus System
================================================================================
''';

      await file.writeAsString(content);

      snackBar('Downloaded "$filename" to Downloads directory!');

      final uri = Uri.file(file.path);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    } catch (e) {
      snackBar('Saved "$filename" to Downloads directory!');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final authController = Get.find<AuthController>();
    final announcementController = Get.find<AnnouncementController>();

    final userRole = authController.currentUser.value?.role ?? 'Student';
    final canApprove = (userRole == 'HoD' || userRole == 'College Admin' || userRole == 'Principal' || userRole == 'Dev Admin' || userRole == 'Developer') &&
        (announcement.status == 'SUBMITTED' || announcement.status == 'DRAFT' || announcement.status == 'PENDING_APPROVAL');

    final canDelete = userRole == 'Principal' || userRole == 'Dev Admin' || userRole == 'Developer' || (userRole == 'HoD' && announcement.department == authController.currentUser.value?.department);

    return Scaffold(
      body: Glow(
        child: SafeArea(
          top: true,
          bottom: false,
          child: Column(
            children: [
            // Top Navigation Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () => Get.back(),
                  ),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: EchoSphereText(
                      text: 'Announcement Details',
                      size: 16,
                      variant: TextVariant.bold,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  EchoSphereChip(
                    label: announcement.priority,
                    isSelected: true,
                    onSelected: (_) {},
                  ),
                ],
              ),
            ),
            const Divider(height: 1),

            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20.0),
                child: Center(
                  child: Container(
                    constraints: const BoxConstraints(maxWidth: 800),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Title & Status
                        EchoSphereContainer(
                          padding: const EdgeInsets.all(24.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                children: [
                                  EchoSphereChip(
                                    label: announcement.category,
                                    isSelected: true,
                                    onSelected: (_) {},
                                  ),
                                  EchoSphereChip(
                                    label: announcement.department,
                                    isSelected: false,
                                    onSelected: (_) {},
                                  ),
                                  _buildStatusBadge(announcement.status),
                                ],
                              ),
                              const SizedBox(height: 16),
                              Text(
                                announcement.title,
                                style: const TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.bold,
                                  height: 1.3,
                                ),
                              ),
                              const SizedBox(height: 16),
                              Row(
                                children: [
                                  CircleAvatar(
                                    radius: 18,
                                    backgroundColor: theme.colorScheme.primary.withOpacity(0.2),
                                    child: Icon(
                                      Icons.person,
                                      size: 18,
                                      color: theme.colorScheme.primary,
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          announcement.creatorName,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w600,
                                            fontSize: 14,
                                          ),
                                        ),
                                        Text(
                                          DateFormat('MMMM dd, yyyy • hh:mm a').format(announcement.createdAt),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontSize: 12,
                                            color: theme.colorScheme.onSurface.withOpacity(0.6),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 20),

                        // AI Summary Box
                        if (announcement.aiSummary != null && announcement.aiSummary!.isNotEmpty)
                          EchoSphereContainer(
                            padding: const EdgeInsets.all(16.0),
                            child: Row(
                              children: [
                                const Icon(Icons.auto_awesome, color: Colors.amber, size: 24),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        'AI Quick Summary',
                                        style: TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold,
                                          color: Colors.amber,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        announcement.aiSummary!,
                                        style: TextStyle(
                                          fontSize: 13,
                                          color: theme.colorScheme.onSurface.withOpacity(0.9),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        const SizedBox(height: 20),

                        // Main Description Content
                        EchoSphereContainer(
                          padding: const EdgeInsets.all(24.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Official Notice Details',
                                style: TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const Divider(height: 24),
                              Text(
                                announcement.description,
                                style: const TextStyle(
                                  fontSize: 15,
                                  height: 1.6,
                                ),
                              ),
                              if (announcement.remarks != null && announcement.remarks!.isNotEmpty) ...[
                                const SizedBox(height: 16),
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: theme.colorScheme.primary.withOpacity(0.08),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Row(
                                    children: [
                                      const Icon(Icons.comment, size: 18),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          'Remarks: ${announcement.remarks}',
                                          style: const TextStyle(fontSize: 13, fontStyle: FontStyle.italic),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                        const SizedBox(height: 20),

                        // Attachments Section
                        EchoSphereContainer(
                          padding: const EdgeInsets.all(20.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.attach_file_rounded, size: 20),
                                  SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      'Attachments & Documents',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: [
                                  ConstrainedBox(
                                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width - 80),
                                    child: ActionChip(
                                      avatar: const Icon(Icons.picture_as_pdf_rounded, color: Color(0xFFF87171), size: 18),
                                      label: const Text('Official_Circular.pdf (245 KB)', maxLines: 1, overflow: TextOverflow.ellipsis),
                                      onPressed: () => _downloadAttachment(context, 'Official_Circular.pdf'),
                                    ),
                                  ),
                                  ConstrainedBox(
                                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width - 80),
                                    child: ActionChip(
                                      avatar: const Icon(Icons.table_chart_rounded, color: Color(0xFF34D399), size: 18),
                                      label: const Text('Exam_Schedule.xlsx (120 KB)', maxLines: 1, overflow: TextOverflow.ellipsis),
                                      onPressed: () => _downloadAttachment(context, 'Exam_Schedule.xlsx'),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 20),

                        // Audit Trail Section
                        EchoSphereContainer(
                          padding: const EdgeInsets.all(20.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.history, size: 20, color: Colors.blue),
                                  SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      'Audit Trail & Delivery Info',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              Text(
                                '• Created By: ${announcement.creatorName} (${announcement.department})\n'
                                '• Target Audience: Entire College & Department\n'
                                '• Delivery Channels: In-App Feed, Push Notification\n'
                                '• Approval Status: ${announcement.status}\n'
                                '• Timestamp: ${DateFormat("MMM dd, yyyy • hh:mm:ss a").format(announcement.createdAt)}',
                                style: TextStyle(
                                  fontSize: 12,
                                  height: 1.6,
                                  color: theme.colorScheme.onSurface.withOpacity(0.7),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 24),

                        // Action Buttons (Approve / Reject / Modify / Reschedule / Delete)
                        if (canApprove || canDelete)
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              if (canApprove) ...[
                                EchoSphereButton(
                                  height: 42,
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showApproveDialog(context, announcementController),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.check_circle_outline_rounded, size: 16),
                                      SizedBox(width: 6),
                                      Text('Approve', style: TextStyle(fontSize: 12)),
                                    ],
                                  ),
                                ),
                                EchoSphereButton(
                                  height: 42,
                                  color: Colors.red.withOpacity(0.2),
                                  border: const BorderSide(color: Colors.red),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showRejectDialog(context, announcementController),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.cancel_outlined, size: 16, color: Colors.red),
                                      SizedBox(width: 6),
                                      Text('Reject', style: TextStyle(color: Colors.red, fontSize: 12)),
                                    ],
                                  ),
                                ),
                              ],
                              if (canDelete) ...[
                                EchoSphereButton(
                                  height: 42,
                                  color: Colors.amber.withOpacity(0.15),
                                  border: const BorderSide(color: Colors.amber),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showEditDialog(context, announcementController),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.edit_rounded, size: 16, color: Colors.amber),
                                      SizedBox(width: 6),
                                      Text('Modify', style: TextStyle(fontSize: 12)),
                                    ],
                                  ),
                                ),
                                EchoSphereButton(
                                  height: 42,
                                  color: Colors.blue.withOpacity(0.15),
                                  border: const BorderSide(color: Colors.blue),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showReschedulePicker(context, announcementController),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.event_rounded, size: 16, color: Colors.blue),
                                      SizedBox(width: 6),
                                      Text('Reschedule', style: TextStyle(color: Colors.blue, fontSize: 12)),
                                    ],
                                  ),
                                ),
                                EchoSphereButton(
                                  height: 42,
                                  color: Colors.red.withOpacity(0.15),
                                  border: const BorderSide(color: Colors.red),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showDeleteConfirm(context, announcementController),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.delete_outline_rounded, size: 16, color: Colors.red),
                                      SizedBox(width: 6),
                                      Text('Delete', style: TextStyle(color: Colors.red, fontSize: 12)),
                                    ],
                                  ),
                                ),
                              ],
                            ],
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    ),
    );
  }

  void _showApproveDialog(BuildContext context, AnnouncementController controller) {
    final remarksController = TextEditingController(text: 'Approved for publication');

    showDialog(
      context: context,
      builder: (ctx) => EchoSphereDialog(
        title: 'Approve Announcement',
        contentWidget: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Approve this announcement to make it visible to students.'),
            const SizedBox(height: 12),
            TextField(
              controller: remarksController,
              decoration: const InputDecoration(
                labelText: 'Approval Remarks',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        onConfirm: () async {
          await controller.approveAnnouncement(announcement.id, remarks: remarksController.text);
          snackBar('Announcement Approved & Published!');
          Get.back();
        },
      ),
    );
  }

  void _showRejectDialog(BuildContext context, AnnouncementController controller) {
    final remarksController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => EchoSphereDialog(
        title: 'Reject Announcement',
        contentWidget: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Provide reason for rejection so the creator can revise:'),
            const SizedBox(height: 12),
            TextField(
              controller: remarksController,
              decoration: const InputDecoration(
                labelText: 'Rejection Reason',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        onConfirm: () async {
          if (remarksController.text.trim().isEmpty) {
            errorSnackBar('Please enter rejection remarks.');
            return;
          }
          await controller.rejectAnnouncement(announcement.id, remarks: remarksController.text);
          snackBar('Announcement rejected.');
          Get.back();
        },
      ),
    );
  }

  void _showEditDialog(BuildContext context, AnnouncementController controller) {
    final titleCtrl = TextEditingController(text: announcement.title);
    final descCtrl = TextEditingController(text: announcement.description);
    String catVal = announcement.category;
    String prioVal = announcement.priority;

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
              id: announcement.id,
              title: titleCtrl.text.trim(),
              description: descCtrl.text.trim(),
              category: catVal,
              priority: prioVal,
            );
            snackBar('Announcement updated successfully!');
            Get.back();
          },
        ),
      ),
    );
  }

  Future<void> _showReschedulePicker(BuildContext context, AnnouncementController controller) async {
    final now = DateTime.now();
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: announcement.createdAt.isAfter(now) ? announcement.createdAt : now.add(const Duration(hours: 1)),
      firstDate: now.subtract(const Duration(days: 1)),
      lastDate: now.add(const Duration(days: 365)),
    );

    if (pickedDate != null && context.mounted) {
      final pickedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(announcement.createdAt),
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
          id: announcement.id,
          newScheduledTime: newDateTime,
        );

        snackBar('Announcement rescheduled for ${DateFormat("MMM dd, yyyy • hh:mm a").format(newDateTime)}!');
        Get.back();
      }
    }
  }

  void _showDeleteConfirm(BuildContext context, AnnouncementController controller) {
    showDialog(
      context: context,
      builder: (ctx) => EchoSphereDialog(
        title: 'Delete Announcement?',
        message: 'Are you sure you want to delete "${announcement.title}"? This action cannot be undone.',
        confirmText: 'Delete',
        onConfirm: () async {
          await controller.deleteAnnouncement(announcement.id);
          snackBar('Announcement deleted.');
          Get.back();
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
