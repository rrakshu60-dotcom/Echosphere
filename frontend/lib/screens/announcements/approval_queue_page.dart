import 'package:echosphere/constants/themes.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/utils/navigation_helper.dart';

import 'package:echosphere/widgets/custom_widgets/echosphere_button.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_chip.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_container.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/custom_widgets/notice_sort_button.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
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
  bool isBatchSelectMode = false;
  final Set<int> selectedItemIds = <int>{};
  bool isBatchProcessing = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Get.find<AnnouncementController>().fetchAnnouncements();
    });
  }

  Future<void> _handleBatchApprove(AnnouncementController controller) async {
    final ids = selectedItemIds.toList();
    if (ids.isEmpty) return;
    setState(() => isBatchProcessing = true);
    int successCount = 0;
    for (final id in ids) {
      final ok = await controller.approveAnnouncement(id, remarks: 'Batch approved by Administrator');
      if (ok) successCount++;
    }
    setState(() {
      isBatchProcessing = false;
      isBatchSelectMode = false;
      selectedItemIds.clear();
    });
    snackBar('$successCount notice(s) approved and published to campus feed.');
  }

  void _showBatchRejectDialog(BuildContext context, AnnouncementController controller) {
    final remarksController = TextEditingController();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final rejectColor = isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: rejectColor.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.cancel_rounded, color: rejectColor, size: 24),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Reject ${selectedItemIds.length} Notices',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Please provide a reason for rejecting the ${selectedItemIds.length} selected announcements:',
              style: const TextStyle(fontSize: 13, height: 1.4),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: remarksController,
              autofocus: true,
              maxLines: 2,
              decoration: InputDecoration(
                labelText: 'Rejection Reason (Required)',
                hintText: 'e.g. Incomplete information or duplicate notice',
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
              backgroundColor: rejectColor,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            onPressed: () async {
              final remarks = remarksController.text.trim();
              if (remarks.isEmpty) {
                errorSnackBar('Please enter a rejection reason.');
                return;
              }
              Navigator.pop(ctx);
              setState(() => isBatchProcessing = true);
              final ids = selectedItemIds.toList();
              int successCount = 0;
              for (final id in ids) {
                final ok = await controller.rejectAnnouncement(id, remarks: remarks);
                if (ok) successCount++;
              }
              setState(() {
                isBatchProcessing = false;
                isBatchSelectMode = false;
                selectedItemIds.clear();
              });
              snackBar('$successCount notice(s) rejected.');
            },
            child: const Text('Reject Selected'),
          ),
        ],
      ),
    );
  }

  void _showApproveModal(BuildContext context, AnnouncementModel item, AnnouncementController controller) {
    final remarksController = TextEditingController(text: 'Approved for college-wide publication');
    final approveColor = Theme.of(context).colorScheme.primary;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: approveColor.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.check_circle_rounded, color: approveColor, size: 24),
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
        content: SingleChildScrollView(
          child: Column(
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
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: approveColor,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final rejectColor = isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: rejectColor.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.cancel_rounded, color: rejectColor, size: 24),
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
        content: SingleChildScrollView(
          child: Column(
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
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: rejectColor,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      if (canPop) ...[
                        const EchoSphereBackButton(fallbackRoute: '/home'),
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
                        ),
                      ),
                    ],
                  ),


                  const SizedBox(height: 6),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        const NoticeSortButton(compact: true),
                        const SizedBox(width: 8),
                        Obx(() => EchoSphereChip(
                              label: isTeacher
                                  ? '${controller.mySubmissions.length} Submissions'
                                  : '${controller.pendingApprovals.length} Pending',
                              isSelected: true,
                              onSelected: (_) {},
                            )),
                      ],
                    ),
                  ),
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
            Icon(Icons.gpp_bad_rounded, size: 56, color: theme.colorScheme.primary.withOpacity(0.8)),
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

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // TEACHER STATUS TRACKER VIEW
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  onSelected: (val) => setState(() => selectedFilter = status),
                  selectedColor: theme.colorScheme.primary.withOpacity(0.18),
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
              return RefreshIndicator(
                onRefresh: () => controller.fetchAnnouncements(),
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: SizedBox(
                    height: MediaQuery.of(context).size.height * 0.6,
                    child: Center(
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
                            const SizedBox(height: 14),
                            EchoSphereButton(
                              height: 36,
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                              onTap: () => controller.fetchAnnouncements(),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.refresh_rounded, size: 16),
                                  SizedBox(width: 6),
                                  Text('Refresh Status', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              );
            }

            return RefreshIndicator(
              onRefresh: () => controller.fetchAnnouncements(),
              child: ListView.builder(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(14.0),
                itemCount: submissions.length,
                itemBuilder: (context, index) {
                  final item = submissions[index];
                  final isApproved = item.status == 'PUBLISHED' || item.status == 'APPROVED';
                  final isRejected = item.status == 'REJECTED';

                  Color statusColor = theme.colorScheme.primary;
                  IconData statusIcon = Icons.hourglass_top_rounded;
                  String statusLabel = 'PENDING APPROVAL';

                  if (isApproved) {
                    statusIcon = Icons.verified_rounded;
                    statusLabel = 'APPROVED & PUBLISHED';
                  } else if (isRejected) {
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
                              EchoSphereBadge.secondary(label: item.category),
                              EchoSphereBadge.outline(label: item.department),
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
                                onTap: () => openAnnouncementDetail(context, item),
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
              ),
            );
          }),
        ),
      ],
    );
  }

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // APPROVER QUEUE VIEW (HoD, Admin, Principal, DevAdmin)
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  Widget _buildApproverQueueView(ThemeData theme, AnnouncementController controller) {
    final isDark = theme.brightness == Brightness.dark;
    return Obx(() {
      final pending = controller.pendingApprovals;
      if (pending.isEmpty) {
        return RefreshIndicator(
          onRefresh: () => controller.fetchAnnouncements(),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            child: SizedBox(
              height: MediaQuery.of(context).size.height * 0.65,
              child: Center(
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
                      const SizedBox(height: 16),
                      EchoSphereButton(
                        height: 36,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        onTap: () => controller.fetchAnnouncements(),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.refresh_rounded, size: 16),
                            SizedBox(width: 6),
                            Text('Refresh Queue', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      }

      return Column(
        children: [
          // Batch Mode Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 8.0),
            decoration: BoxDecoration(
              color: isDark ? EchoSpherePalette.darkSurface : EchoSpherePalette.lightSurface,
              border: Border(
                bottom: BorderSide(
                  color: isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder,
                ),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                if (isBatchSelectMode) ...[
                  Row(
                    children: [
                      Checkbox(
                        value: selectedItemIds.length == pending.length && pending.isNotEmpty,
                        tristate: selectedItemIds.isNotEmpty && selectedItemIds.length < pending.length,
                        activeColor: theme.colorScheme.primary,
                        onChanged: (val) {
                          setState(() {
                            if (selectedItemIds.length == pending.length) {
                              selectedItemIds.clear();
                            } else {
                              selectedItemIds.addAll(pending.map((e) => e.id));
                            }
                          });
                        },
                      ),
                      Text(
                        '${selectedItemIds.length} of ${pending.length} Selected',
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  TextButton.icon(
                    icon: const Icon(Icons.close_rounded, size: 16),
                    label: const Text('Exit Batch', style: TextStyle(fontSize: 12)),
                    onPressed: () {
                      setState(() {
                        isBatchSelectMode = false;
                        selectedItemIds.clear();
                      });
                    },
                  ),
                ] else ...[
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary.withValues(alpha: 0.12),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(Icons.pending_actions_rounded, size: 16, color: theme.colorScheme.primary),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Pending Submissions (${pending.length})',
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  OutlinedButton.icon(
                    icon: const Icon(Icons.checklist_rounded, size: 16),
                    label: const Text('Batch Actions', style: TextStyle(fontSize: 12)),
                    style: OutlinedButton.styleFrom(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    ),
                    onPressed: () {
                      setState(() {
                        isBatchSelectMode = true;
                        selectedItemIds.clear();
                      });
                    },
                  ),
                ],
              ],
            ),
          ),

          // Queue List
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => controller.fetchAnnouncements(),
              child: ListView.builder(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(14.0),
                itemCount: pending.length,
                itemBuilder: (context, index) {
                  final item = pending[index];
                  final isSelected = selectedItemIds.contains(item.id);

                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12.0),
                    child: InkWell(
                      onTap: isBatchSelectMode
                          ? () {
                              setState(() {
                                if (isSelected) {
                                  selectedItemIds.remove(item.id);
                                } else {
                                  selectedItemIds.add(item.id);
                                }
                              });
                            }
                          : null,
                      borderRadius: BorderRadius.circular(16),
                      child: EchoSphereContainer(
                        padding: const EdgeInsets.all(14.0),
                        border: isBatchSelectMode && isSelected
                            ? Border.all(color: theme.colorScheme.primary, width: 1.8)
                            : null,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (isBatchSelectMode) ...[
                                  Checkbox(
                                    value: isSelected,
                                    activeColor: theme.colorScheme.primary,
                                    onChanged: (val) {
                                      setState(() {
                                        if (val == true) {
                                          selectedItemIds.add(item.id);
                                        } else {
                                          selectedItemIds.remove(item.id);
                                        }
                                      });
                                    },
                                  ),
                                  const SizedBox(width: 4),
                                ],
                                Expanded(
                                  child: Wrap(
                                    spacing: 8,
                                    runSpacing: 6,
                                    crossAxisAlignment: WrapCrossAlignment.center,
                                    alignment: WrapAlignment.spaceBetween,
                                    children: [
                                      EchoSphereBadge.secondary(label: item.category),
                                      EchoSphereBadge.outline(label: item.department),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: theme.colorScheme.secondary.withOpacity(0.12),
                                          borderRadius: BorderRadius.circular(16),
                                        ),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(Icons.groups_rounded, size: 12, color: theme.colorScheme.secondary),
                                            const SizedBox(width: 4),
                                            Text(
                                              item.targetAudience,
                                              style: TextStyle(
                                                fontSize: 10,
                                                fontWeight: FontWeight.w600,
                                                color: theme.colorScheme.secondary,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: theme.colorScheme.secondary,
                                          borderRadius: BorderRadius.circular(16),
                                          border: Border.all(color: theme.colorScheme.outline),
                                        ),
                                        child: Text(
                                          item.priority,
                                          style: TextStyle(
                                            fontSize: 10,
                                            fontWeight: FontWeight.bold,
                                            color: theme.colorScheme.onSecondary,
                                          ),
                                        ),
                                      ),
                                      Text(
                                        DateFormat('MMM dd, hh:mm a').format(item.createdAt),
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w500,
                                          color: theme.colorScheme.onSurface.withOpacity(0.5),
                                        ),
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
                            if (item.aiSummary != null && item.aiSummary!.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: theme.colorScheme.primary.withOpacity(0.06),
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(color: theme.colorScheme.primary.withOpacity(0.2)),
                                ),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Icon(Icons.auto_awesome, size: 14, color: theme.colorScheme.primary),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        item.aiSummary!,
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: theme.colorScheme.onSurface.withOpacity(0.85),
                                          fontStyle: FontStyle.italic,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                            const SizedBox(height: 10),
                            Text(
                              'Submitted by: ${item.creatorName} (${item.creatorRole}) â€¢ ${item.department}',
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
                                  radius: 16,
                                  color: theme.colorScheme.primary.withOpacity(0.14),
                                  border: BorderSide(color: theme.colorScheme.primary, width: 1.2),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showApproveModal(context, item, controller),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.check_circle_rounded, size: 16, color: theme.colorScheme.primary),
                                      const SizedBox(width: 6),
                                      Text('Approve', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: theme.colorScheme.primary)),
                                    ],
                                  ),
                                ),
                                EchoSphereButton(
                                  height: 36,
                                  radius: 16,
                                  color: isDark ? EchoSpherePalette.darkDestructive.withOpacity(0.12) : EchoSpherePalette.lightDestructive.withOpacity(0.08),
                                  border: BorderSide(color: (isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive).withOpacity(0.35), width: 1.2),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showRejectModal(context, item, controller),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.cancel_rounded, size: 16, color: isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive),
                                      const SizedBox(width: 6),
                                      Text('Reject', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive)),
                                    ],
                                  ),
                                ),
                                EchoSphereButton(
                                  height: 36,
                                  radius: 16,
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => openAnnouncementDetail(context, item),
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
                    ),
                  );
                },
              ),
            ),
          ),

          // Floating Batch Actions Bottom Bar
          if (isBatchSelectMode && selectedItemIds.isNotEmpty)
            Container(
              margin: const EdgeInsets.all(12),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: isDark ? EchoSpherePalette.darkSurface : EchoSpherePalette.lightSurface,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: theme.colorScheme.primary.withValues(alpha: 0.35)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.15),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${selectedItemIds.length} Selected',
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Parallel bulk moderation',
                          style: TextStyle(
                            fontSize: 11,
                            color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (isBatchProcessing)
                    const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  else ...[
                    OutlinedButton(
                      onPressed: () => _showBatchRejectDialog(context, controller),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive,
                        side: BorderSide(
                          color: (isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive).withValues(alpha: 0.5),
                        ),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                      child: const Text('Reject All', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                    ),
                    const SizedBox(width: 8),
                    EchoSphereButton(
                      height: 38,
                      radius: 12,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      onTap: () => _handleBatchApprove(controller),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.check_circle_rounded, size: 16, color: Colors.white),
                          SizedBox(width: 6),
                          Text(
                            'Approve All',
                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
        ],
      );
    });
  }
}
