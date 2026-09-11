import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/services/calendar_sync_service.dart';
import 'package:anymex/widgets/common/glow.dart';
import 'package:anymex/widgets/custom_widgets/calendar_sync_dialog.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:anymex/widgets/notice_audio_player_bar.dart';

class AnnouncementDetailPage extends StatefulWidget {
  final AnnouncementModel announcement;

  const AnnouncementDetailPage({super.key, required this.announcement});

  @override
  State<AnnouncementDetailPage> createState() => _AnnouncementDetailPageState();
}

class _AnnouncementDetailPageState extends State<AnnouncementDetailPage> {
  AnnouncementModel get announcement => widget.announcement;
  String? _aiSummary;
  bool _isSummarizing = false;
  CalendarEventData? _calendarEvent;

  @override
  void initState() {
    super.initState();
    _aiSummary = widget.announcement.aiSummary;
    _fetchCalendarEvent();
  }

  Future<void> _fetchCalendarEvent() async {
    try {
      CalendarEventData? ev;
      if (Get.isRegistered<AnnouncementController>()) {
        ev = await Get.find<AnnouncementController>().getOrFetchCalendarEvent(widget.announcement);
      } else {
        ev = await EchosphereApiService().getAnnouncementCalendarEvent(
          widget.announcement.id,
          title: widget.announcement.title,
          content: widget.announcement.description,
        );
      }
      if (mounted) {
        setState(() {
          _calendarEvent = ev;
        });
      }
    } catch (_) {}
  }

  Future<void> _generateAiSummary() async {
    setState(() => _isSummarizing = true);
    try {
      final summary = await EchosphereApiService().summarizeContent(widget.announcement.description);
      if (mounted) {
        setState(() {
          _aiSummary = summary;
          _isSummarizing = false;
        });
        if (Get.isRegistered<AnnouncementController>()) {
          Get.find<AnnouncementController>().updateAnnouncementSummary(widget.announcement.id, summary);
        }
        snackBar('✨ AI Summary generated!');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSummarizing = false);
        snackBar('Failed to generate summary: $e');
      }
    }
  }

  Future<void> _downloadAttachment(BuildContext context, String filename) async {
    final announcement = widget.announcement;
    if (kIsWeb) {
      snackBar("Downloading $filename");
      return;
    }
    try {
      Directory? dir;
      if (!kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS)) {
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
ISSUED BY: ${announcement.creatorName} (Designation: ${announcement.creatorRole})
DATE: ${DateFormat('MMMM dd, yyyy • hh:mm a').format(announcement.createdAt)}

--------------------------------------------------------------------------------
OFFICIAL NOTICE DETAILS:
--------------------------------------------------------------------------------
${announcement.description}

AI SUMMARY:
${_aiSummary ?? announcement.aiSummary ?? 'N/A'}

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
    final announcement = widget.announcement;
    final theme = Theme.of(context);
    final authController = Get.find<AuthController>();
    final announcementController = Get.find<AnnouncementController>();

    final userRole = authController.currentUser.value?.role ?? 'Student';
    final isStudent = userRole.toLowerCase() == 'student';
    final canApprove = (userRole == 'HoD' || userRole == 'College Admin' || userRole == 'Principal' || userRole == 'Dev Admin' || userRole == 'Developer') &&
        (announcement.status == 'SUBMITTED' || announcement.status == 'DRAFT' || announcement.status == 'PENDING_APPROVAL');

    final canDelete = userRole == 'Principal' || userRole == 'Dev Admin' || userRole == 'Developer' || (userRole == 'HoD' && announcement.department == authController.currentUser.value?.department);
    final canBroadcast = !isStudent && (announcement.status == 'APPROVED' || announcement.status == 'PUBLISHED' || announcement.status == 'ACTIVE' || announcement.status == 'SCHEDULED');
    final canArchive = (userRole == 'HoD' || userRole == 'College Admin' || userRole == 'Principal' || userRole == 'Dev Admin' || userRole == 'Developer') &&
        (announcement.status == 'APPROVED' || announcement.status == 'PUBLISHED' || announcement.status == 'ACTIVE');

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
                padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 16.0),
                child: Center(
                  child: Container(
                    constraints: const BoxConstraints(maxWidth: 800),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Title & Status
                        EchoSphereContainer(
                          padding: const EdgeInsets.all(16.0),
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
                                          '${announcement.creatorName} • Designation: ${announcement.creatorRole}',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 14,
                                            color: theme.colorScheme.primary,
                                          ),
                                        ),
                                        Text(
                                          'Department: ${announcement.department} • ${DateFormat("MMMM dd, yyyy • hh:mm a").format(announcement.createdAt)}',
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
                        const SizedBox(height: 16),

                        // AI Summary Box (With On-Demand AI Summarizer powered by trained model)
                        if (_aiSummary != null && _aiSummary!.isNotEmpty)
                          EchoSphereContainer(
                            padding: const EdgeInsets.all(16.0),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(Icons.auto_awesome, color: Colors.amber, size: 24),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          const Expanded(
                                            child: Text(
                                              'AI Summary',
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                              style: TextStyle(
                                                fontSize: 12,
                                                fontWeight: FontWeight.bold,
                                                color: Colors.amber,
                                              ),
                                            ),
                                          ),
                                          Row(
                                            mainAxisSize: MainAxisSize.min,
                                            children: [
                                              InkWell(
                                                onTap: () {
                                                  Clipboard.setData(ClipboardData(text: _aiSummary!));
                                                  snackBar('Summary copied to clipboard');
                                                },
                                                borderRadius: BorderRadius.circular(4),
                                                child: Padding(
                                                  padding: const EdgeInsets.all(4.0),
                                                  child: Icon(
                                                    Icons.copy_rounded,
                                                    size: 14,
                                                    color: Colors.amber.shade700,
                                                  ),
                                                ),
                                              ),
                                              const SizedBox(width: 8),
                                              InkWell(
                                                onTap: _isSummarizing ? null : _generateAiSummary,
                                                child: Text(
                                                  _isSummarizing ? 'Regenerating...' : 'Regenerate ↻',
                                                  style: TextStyle(
                                                    fontSize: 11,
                                                    color: Colors.amber.shade700,
                                                    fontWeight: FontWeight.w600,
                                                  ),
                                                ),
                                              ),
                                            ],
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 6),
                                       Text(
                                         _aiSummary!,
                                         style: TextStyle(
                                          fontSize: 13,
                                          height: 1.4,
                                          color: theme.colorScheme.onSurface.withOpacity(0.9),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          )
                        else
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
                                        'No AI Summary Yet',
                                        style: TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        'Summarize this notice with AI',
                                        style: TextStyle(
                                          fontSize: 11.5,
                                          color: theme.colorScheme.onSurface.withOpacity(0.65),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 8),
                                ElevatedButton.icon(
                                  onPressed: _isSummarizing ? null : _generateAiSummary,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.amber.shade700,
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                  ),
                                  icon: _isSummarizing
                                      ? const SizedBox(
                                          width: 14,
                                          height: 14,
                                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                        )
                                      : const Icon(Icons.auto_awesome, size: 14),
                                  label: Text(
                                    _isSummarizing ? 'Summarizing...' : 'Summarize',
                                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        const SizedBox(height: 16),

                        // Audio Speech Player
                        NoticeAudioPlayerBar(
                          announcementId: announcement.id,
                          title: announcement.title,
                          content: announcement.description,
                          hasAiSummary: (_aiSummary != null && _aiSummary!.isNotEmpty),
                          aiSummary: _aiSummary,
                        ),
                        const SizedBox(height: 16),

                        // AI Calendar Event Card (If dates/deadlines extracted)
                        if (_calendarEvent != null && _calendarEvent!.hasEvent) ...[
                          Container(
                            padding: const EdgeInsets.all(16.0),
                            decoration: BoxDecoration(
                              color: const Color(0xFF10B981).withOpacity(0.08),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: const Color(0xFF10B981).withOpacity(0.28),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(6),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF10B981).withOpacity(0.16),
                                        shape: BoxShape.circle,
                                      ),
                                      child: const Icon(
                                        Icons.event_available_rounded,
                                        color: Color(0xFF10B981),
                                        size: 16,
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        'Event & Deadline Detected',
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold,
                                          letterSpacing: 0.2,
                                          color: Colors.green.shade800,
                                        ),
                                      ),
                                    ),
                                    Text(
                                      DateFormat('MMM d, yyyy').format(_calendarEvent!.startTime),
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.green.shade800,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 10),
                                Text(
                                  _calendarEvent!.title,
                                  style: const TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Row(
                                  children: [
                                    const Icon(Icons.schedule_rounded, size: 13, color: Color(0xFF10B981)),
                                    const SizedBox(width: 5),
                                    Expanded(
                                      child: Text(
                                        '${DateFormat('EEEE, h:mm a').format(_calendarEvent!.startTime)} (${_calendarEvent!.location})',
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: theme.colorScheme.onSurface.withOpacity(0.75),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                if (_calendarEvent!.actionRequired.isNotEmpty) ...[
                                  const SizedBox(height: 4),
                                  Row(
                                    children: [
                                      const Icon(Icons.task_alt_rounded, size: 13, color: Colors.blue),
                                      const SizedBox(width: 5),
                                      Expanded(
                                        child: Text(
                                          _calendarEvent!.actionRequired,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w500,
                                            color: theme.colorScheme.onSurface.withOpacity(0.85),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                                const SizedBox(height: 12),
                                // 1-Tap Action Row: Responsive Wrap to guarantee zero overflow on 320px
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 6,
                                  children: [
                                    ElevatedButton.icon(
                                      onPressed: () => showCalendarSyncSheet(context, _calendarEvent!),
                                      icon: const Icon(Icons.calendar_month_rounded, size: 14),
                                      label: const Text(
                                        'Add to Calendar',
                                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                                      ),
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: const Color(0xFF10B981),
                                        foregroundColor: Colors.white,
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                        elevation: 0,
                                      ),
                                    ),
                                    OutlinedButton.icon(
                                      onPressed: () async {
                                        final ok = await CalendarSyncService.exportAndShareIcs(_calendarEvent!);
                                        if (context.mounted && ok) {
                                          snackBar('Exported .ics event');
                                        }
                                      },
                                      icon: const Icon(Icons.share_outlined, size: 13),
                                      label: const Text(
                                        'Export .ics',
                                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                                      ),
                                      style: OutlinedButton.styleFrom(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                                        side: BorderSide(color: const Color(0xFF10B981).withOpacity(0.4)),
                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 16),
                        ],

                        // Main Description Content
                        EchoSphereContainer(
                          padding: const EdgeInsets.all(20.0),
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
                              if (announcement.attachments.isNotEmpty)
                                Wrap(
                                  spacing: 10,
                                  runSpacing: 10,
                                  children: announcement.attachments.map((file) {
                                    IconData icon = Icons.insert_drive_file_rounded;
                                    Color iconCol = Colors.blue;
                                    final lower = file.toLowerCase();
                                    if (lower.endsWith('.pdf')) {
                                      icon = Icons.picture_as_pdf_rounded;
                                      iconCol = const Color(0xFFF87171);
                                    } else if (lower.endsWith('.xls') || lower.endsWith('.xlsx') || lower.endsWith('.csv')) {
                                      icon = Icons.table_chart_rounded;
                                      iconCol = const Color(0xFF34D399);
                                    } else if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg')) {
                                      icon = Icons.image_rounded;
                                      iconCol = Colors.amber;
                                    } else if (lower.endsWith('.doc') || lower.endsWith('.docx')) {
                                      icon = Icons.description_rounded;
                                      iconCol = Colors.indigoAccent;
                                    }
                                    return ConstrainedBox(
                                      constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width - 80),
                                      child: ActionChip(
                                        avatar: Icon(icon, color: iconCol, size: 18),
                                        label: Text(file, maxLines: 1, overflow: TextOverflow.ellipsis),
                                        onPressed: () => _downloadAttachment(context, file),
                                      ),
                                    );
                                  }).toList(),
                                )
                              else
                                Text(
                                  'No attachments uploaded with this notice.',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontStyle: FontStyle.italic,
                                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                                  ),
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

                        // Action Buttons (Approve / Reject / Modify / Reschedule / Archive / Delete / Broadcast)
                        if (canApprove || canDelete || canBroadcast || canArchive)
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              if (canBroadcast)
                                EchoSphereButton(
                                  height: 42,
                                  color: Colors.purple.withOpacity(0.15),
                                  border: const BorderSide(color: Colors.purple),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () async {
                                    try {
                                      await EchosphereApiService().enqueueAnnouncement(
                                        announcementId: announcement.id,
                                      );
                                      snackBar('Enqueued "${announcement.title}" to PA speaker queue!');
                                    } catch (e) {
                                      snackBar('Failed to queue: ${e.toString()}');
                                    }
                                  },
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.podcasts_rounded, size: 16, color: Colors.purple),
                                      SizedBox(width: 6),
                                      Flexible(
                                        child: Text(
                                          'Broadcast to Speakers',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(color: Colors.purple, fontSize: 12, fontWeight: FontWeight.bold),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
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
                                      Flexible(
                                        child: Text('Approve', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 12)),
                                      ),
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
                                      Flexible(
                                        child: Text('Reject', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: Colors.red, fontSize: 12)),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                              if (canArchive)
                                EchoSphereButton(
                                  height: 42,
                                  color: Colors.blueGrey.withOpacity(0.15),
                                  border: const BorderSide(color: Colors.blueGrey),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showArchiveConfirm(context, announcementController),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.archive_outlined, size: 16, color: Colors.blueGrey),
                                      SizedBox(width: 6),
                                      Flexible(
                                        child: Text('Archive', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: Colors.blueGrey, fontSize: 12)),
                                      ),
                                    ],
                                  ),
                                ),
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
                                      Flexible(
                                        child: Text('Modify', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 12)),
                                      ),
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
                                      Flexible(
                                        child: Text('Reschedule', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: Colors.blue, fontSize: 12)),
                                      ),
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
                                      Flexible(
                                        child: Text('Delete', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: Colors.red, fontSize: 12)),
                                      ),
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
          autoCloseOnConfirm: false,
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
            ],
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
            if (ctx.mounted) {
              Navigator.of(ctx).pop();
            }
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

  void _showArchiveConfirm(BuildContext context, AnnouncementController controller) {
    final reasonCtrl = TextEditingController(text: 'Archived by administrator');
    showDialog(
      context: context,
      builder: (ctx) => EchoSphereDialog(
        title: 'Archive Announcement?',
        contentWidget: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Archiving will move this announcement to historical archives and remove it from active campus feeds.'),
            const SizedBox(height: 12),
            TextField(
              controller: reasonCtrl,
              decoration: const InputDecoration(
                labelText: 'Archive Reason',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        confirmText: 'Archive',
        onConfirm: () async {
          final success = await controller.archiveAnnouncement(
            announcement.id,
            reason: reasonCtrl.text.trim().isNotEmpty ? reasonCtrl.text.trim() : 'Archived by administrator',
          );
          if (success) {
            snackBar('Announcement moved to archive!');
            Get.back();
          } else {
            errorSnackBar('Failed to archive announcement.');
          }
        },
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    Color bg = Colors.green;
    if (status == 'SUBMITTED' || status == 'DRAFT') bg = Colors.orange;
    if (status == 'SCHEDULED') bg = Colors.blue;
    if (status == 'REJECTED') bg = Colors.red;
    if (status == 'ARCHIVED') bg = Colors.blueGrey;

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
