import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/screens/announcements/announcement_detail_page.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

class ApprovalQueuePage extends StatefulWidget {
  const ApprovalQueuePage({super.key});

  @override
  State<ApprovalQueuePage> createState() => _ApprovalQueuePageState();
}

class _ApprovalQueuePageState extends State<ApprovalQueuePage> {
  String selectedFilter = 'All';

  void _showApproveModal(BuildContext context, AnnouncementModel item, AnnouncementController controller) {
    final remarksController = TextEditingController(text: 'Approved for college-wide publication');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.green.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.check_circle_rounded, color: Colors.green, size: 24),
            ),
            const SizedBox(width: 10),
            const Expanded(
              child: Text(
                'Approve Announcement',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Are you sure you want to approve "${item.title}"? This will publish the notice to the institutional feed immediately.',
              style: const TextStyle(fontSize: 13, height: 1.4),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: remarksController,
              decoration: InputDecoration(
                labelText: 'Approval Remarks / Notes',
                hintText: 'e.g. Approved by HoD',
                prefixIcon: const Icon(Icons.rate_review_outlined, size: 20),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: () async {
              Navigator.pop(ctx);
              await controller.approveAnnouncement(item.id, remarks: remarksController.text.trim());
              snackBar(
                'Notice "#${item.id}" approved & published to campus feed!',
                title: 'Announcement Approved',
              );
            },
            child: const Text('Approve & Publish'),
          ),
        ],
      ),
    );
  }

  void _showRejectModal(BuildContext context, AnnouncementModel item, AnnouncementController controller) {
    final remarksController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.red.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.cancel_rounded, color: Colors.red, size: 24),
            ),
            const SizedBox(width: 10),
            const Expanded(
              child: Text(
                'Reject Announcement',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Please provide a mandatory reason for rejecting "${item.title}" so the author can revise it:',
              style: const TextStyle(fontSize: 13, height: 1.4),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: remarksController,
              autofocus: true,
              maxLines: 2,
              decoration: InputDecoration(
                labelText: 'Rejection Reason (Required)',
                hintText: 'e.g. Schedule conflicts with exam timetable',
                prefixIcon: const Icon(Icons.feedback_outlined, size: 20),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: () async {
              final remarks = remarksController.text.trim();
              if (remarks.isEmpty) {
                errorSnackBar('Please enter a rejection reason.');
                return;
              }
              Navigator.pop(ctx);
              await controller.rejectAnnouncement(item.id, remarks: remarks);
              snackBar(
                'Notice "#${item.id}" has been rejected.',
                title: 'Announcement Rejected',
              );
            },
            child: const Text('Confirm Rejection'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final controller = Get.find<AnnouncementController>();
    final authController = Get.find<AuthController>();

    final userRole = authController.currentUser.value?.role ?? 'Student';
    final isApproverRole = userRole == 'HoD' ||
        userRole == 'College Admin' ||
        userRole == 'Principal' ||
        userRole == 'Dev Admin' ||
        userRole == 'Developer';
    final isTeacher = userRole == 'Teacher';

    final canPop = ModalRoute.of(context)?.canPop ?? false;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar Header
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
                  Icon(
                    isTeacher ? Icons.track_changes_rounded : Icons.fact_check_rounded,
                    size: 22,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: EchoSphereText(
                      text: isTeacher ? 'My Notice Status' : 'Approval Queue',
                      size: 16,
                      variant: TextVariant.bold,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Obx(() => Flexible(
                        child: EchoSphereChip(
                          label: isTeacher
                              ? '${controller.mySubmissions.length} Submissions'
                              : '${controller.pendingApprovals.length} Pending',
                          isSelected: true,
                          onSelected: (_) {},
                        ),
                      )),
                ],
              ),
            ),
            const Divider(height: 1),

            // Content Router based on Role
            Expanded(
              child: isTeacher
                  ? _buildTeacherStatusView(theme, controller)
                  : isApproverRole
                      ? _buildApproverQueueView(theme, controller)
                      : _buildAccessRestrictedView(theme),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAccessRestrictedView(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.gpp_bad_rounded, size: 56, color: Colors.orange.withOpacity(0.8)),
            const SizedBox(height: 14),
            const Text(
              'Access Restricted',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'The Approval Queue is reserved for HoD, College Admin, Principal & Dev Admin roles.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: theme.colorScheme.onSurface.withOpacity(0.6)),
            ),
          ],
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────────────
  // TEACHER STATUS TRACKER VIEW
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildTeacherStatusView(ThemeData theme, AnnouncementController controller) {
    return Column(
      children: [
        // Category Filter Chips for Submissions
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(
            children: ['All', 'Pending', 'Approved', 'Rejected'].map((status) {
              final isSel = selectedFilter == status;
              return Padding(
                padding: const EdgeInsets.only(right: 8.0),
                child: ChoiceChip(
                  label: Text(status, style: TextStyle(fontSize: 12, fontWeight: isSel ? FontWeight.bold : FontWeight.normal)),
                  selected: isSel,
                  onSelected: (val) => setState(() => selectedFilter = status),
                  selectedColor: theme.colorScheme.primary.withOpacity(0.2),
                ),
              );
            }).toList(),
          ),
        ),
        const Divider(height: 1),

        Expanded(
          child: Obx(() {
            final allSubmissions = controller.mySubmissions;
            final submissions = allSubmissions.where((s) {
              if (selectedFilter == 'Pending') {
                return s.status == 'SUBMITTED' || s.status == 'DRAFT' || s.status == 'PENDING_APPROVAL';
              }
              if (selectedFilter == 'Approved') {
                return s.status == 'PUBLISHED' || s.status == 'APPROVED';
              }
              if (selectedFilter == 'Rejected') {
                return s.status == 'REJECTED';
              }
              return true;
            }).toList();

            if (submissions.isEmpty) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.assignment_outlined, size: 56, color: theme.colorScheme.primary.withOpacity(0.4)),
                      const SizedBox(height: 14),
                      const Text(
                        'No Submissions Found',
                        style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'No notice submissions match your selected filter.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 13, color: theme.colorScheme.onSurface.withOpacity(0.6)),
                      ),
                    ],
                  ),
                ),
              );
            }

            return ListView.builder(
              padding: const EdgeInsets.all(14.0),
              itemCount: submissions.length,
              itemBuilder: (context, index) {
                final item = submissions[index];
                final isApproved = item.status == 'PUBLISHED' || item.status == 'APPROVED';
                final isRejected = item.status == 'REJECTED';

                Color statusColor = Colors.orange;
                IconData statusIcon = Icons.hourglass_top_rounded;
                String statusLabel = 'PENDING APPROVAL';

                if (isApproved) {
                  statusColor = Colors.green;
                  statusIcon = Icons.verified_rounded;
                  statusLabel = 'APPROVED & PUBLISHED';
                } else if (isRejected) {
                  statusColor = Colors.red;
                  statusIcon = Icons.cancel_rounded;
                  statusLabel = 'REJECTED';
                }

                return Padding(
                  padding: const EdgeInsets.only(bottom: 12.0),
                  child: EchoSphereContainer(
                    padding: const EdgeInsets.all(14.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Wrap(
                          spacing: 8,
                          runSpacing: 6,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          alignment: WrapAlignment.spaceBetween,
                          children: [
                            EchoSphereChip(label: item.category, isSelected: true, onSelected: (_) {}),
                            EchoSphereChip(label: item.department, isSelected: false, onSelected: (_) {}),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: statusColor.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: statusColor, width: 1),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(statusIcon, size: 13, color: statusColor),
                                  const SizedBox(width: 4),
                                  Text(
                                    statusLabel,
                                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: statusColor),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          item.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          item.description,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 13, color: theme.colorScheme.onSurface.withOpacity(0.75)),
                        ),
                        if (item.remarks != null && item.remarks!.isNotEmpty) ...[
                          const SizedBox(height: 10),
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: statusColor.withOpacity(0.08),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: statusColor.withOpacity(0.3)),
                            ),
                            child: Row(
                              children: [
                                Icon(Icons.comment_bank_outlined, size: 16, color: statusColor),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'Approver Remarks: ${item.remarks}',
                                    style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: statusColor),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                        const SizedBox(height: 12),
                        const Divider(height: 1),
                        const SizedBox(height: 10),

                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'Submitted: ${DateFormat("MMM dd, hh:mm a").format(item.createdAt)}',
                              style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.5)),
                            ),
                            EchoSphereButton(
                              height: 32,
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              onTap: () => Get.to(() => AnnouncementDetailPage(announcement: item)),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text('Details', style: TextStyle(fontSize: 11)),
                                  SizedBox(width: 4),
                                  Icon(Icons.arrow_forward_rounded, size: 12),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
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

  // ──────────────────────────────────────────────────────────────────────────
  // APPROVER QUEUE VIEW (HoD, Admin, Principal, DevAdmin)
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildApproverQueueView(ThemeData theme, AnnouncementController controller) {
    return Obx(() {
      final pending = controller.pendingApprovals;
      if (pending.isEmpty) {
        return Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.verified_rounded, size: 56, color: theme.colorScheme.primary.withOpacity(0.4)),
                const SizedBox(height: 14),
                Text(
                  'No Pending Approvals',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: theme.colorScheme.onSurface),
                ),
                const SizedBox(height: 6),
                Text(
                  'All submitted announcements have been reviewed and processed.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 13, color: theme.colorScheme.onSurface.withOpacity(0.6)),
                ),
              ],
            ),
          ),
        );
      }

      return ListView.builder(
        padding: const EdgeInsets.all(14.0),
        itemCount: pending.length,
        itemBuilder: (context, index) {
          final item = pending[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: 12.0),
            child: EchoSphereContainer(
              padding: const EdgeInsets.all(14.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    alignment: WrapAlignment.spaceBetween,
                    children: [
                      EchoSphereChip(label: item.category, isSelected: true, onSelected: (_) {}),
                      EchoSphereChip(label: item.department, isSelected: false, onSelected: (_) {}),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: (item.priority == 'EMERGENCY' || item.priority == 'HIGH')
                              ? Colors.red.withOpacity(0.15)
                              : Colors.blue.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          item.priority,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            color: (item.priority == 'EMERGENCY' || item.priority == 'HIGH') ? Colors.red : Colors.blue,
                          ),
                        ),
                      ),
                      Text(
                        DateFormat('MMM dd, hh:mm a').format(item.createdAt),
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: theme.colorScheme.onSurface.withOpacity(0.5)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    item.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    item.description,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 13, color: theme.colorScheme.onSurface.withOpacity(0.75)),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Submitted by: ${item.creatorName} (${item.department})',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: theme.colorScheme.onSurface.withOpacity(0.7)),
                  ),
                  const SizedBox(height: 12),
                  const Divider(height: 1),
                  const SizedBox(height: 10),

                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    alignment: WrapAlignment.end,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      EchoSphereButton(
                        height: 36,
                        color: Colors.green.withOpacity(0.18),
                        border: const BorderSide(color: Colors.green, width: 1.2),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        onTap: () => _showApproveModal(context, item, controller),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.check_circle_rounded, size: 16, color: Colors.green),
                            SizedBox(width: 4),
                            Text('Approve', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.green)),
                          ],
                        ),
                      ),
                      EchoSphereButton(
                        height: 36,
                        color: Colors.red.withOpacity(0.18),
                        border: const BorderSide(color: Colors.red, width: 1.2),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        onTap: () => _showRejectModal(context, item, controller),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.cancel_rounded, size: 16, color: Colors.red),
                            SizedBox(width: 4),
                            Text('Reject', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.red)),
                          ],
                        ),
                      ),
                      EchoSphereButton(
                        height: 36,
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        onTap: () => Get.to(() => AnnouncementDetailPage(announcement: item)),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text('Review', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                            SizedBox(width: 4),
                            Icon(Icons.arrow_forward_rounded, size: 14),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      );
    });
  }
}
