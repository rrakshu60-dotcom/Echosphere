import 'package:echosphere/constants/themes.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';
import 'package:echosphere/services/calendar_sync_service.dart';
import 'package:echosphere/widgets/common/glow.dart';
import 'package:echosphere/widgets/custom_widgets/calendar_sync_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/attachment_viewer_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_button.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_chip.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_container.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/widgets/notice_audio_player_bar.dart';
import 'package:echosphere/services/tts_audio_service.dart';
import 'package:echosphere/utils/navigation_helper.dart';

class AnnouncementDetailPage extends StatefulWidget {
  final AnnouncementModel announcement;

  const AnnouncementDetailPage({super.key, required this.announcement});

  @override
  State<AnnouncementDetailPage> createState() => _AnnouncementDetailPageState();
}

class _AnnouncementDetailPageState extends State<AnnouncementDetailPage> {
  AnnouncementModel get announcement {
    if (Get.isRegistered<AnnouncementController>()) {
      final annCtrl = Get.find<AnnouncementController>();
      final match = annCtrl.allAnnouncements.firstWhereOrNull(
        (a) => a.id == widget.announcement.id ||
               (a.title == widget.announcement.title && a.createdAt == widget.announcement.createdAt),
      );
      if (match != null) return match;
    }
    return widget.announcement;
  }
  String? _aiSummary;
  bool _isSummarizing = false;
  bool _isBroadcasting = false;
  CalendarEventData? _calendarEvent;
  Map<String, dynamic>? _repeatSchedule;
  bool _isLoadingRepeatSchedule = false;
  Map<String, dynamic>? _vipProtocol;
  bool _isLoadingVipProtocol = false;
  bool _isAnalyzingVip = false;
  bool _isTriggeringFanfare = false;

  @override
  void initState() {
    super.initState();
    _aiSummary = widget.announcement.aiSummary;
    _fetchCalendarEvent();
    _fetchRepeatSchedule();
    _fetchVipProtocol();
    // Pre-warm speech synthesis in background for zero-latency instant playback
    TtsAudioService.instance.prewarmAnnouncement(
      widget.announcement.id,
      title: widget.announcement.title,
      content: widget.announcement.description,
      summary: widget.announcement.aiSummary,
    );
    // If notice summary is not yet present, pre-generate with Qwen in background
    if (_aiSummary == null || _aiSummary!.isEmpty) {
      EchosphereApiService().summarizeContent(widget.announcement.description).then((sum) {
        if (mounted && sum.isNotEmpty) {
          setState(() {
            _aiSummary = sum;
          });
          TtsAudioService.instance.prewarmAnnouncement(
            widget.announcement.id,
            title: widget.announcement.title,
            content: widget.announcement.description,
            summary: sum,
          );
        }
      }).catchError((_) {});
    }
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

  Future<void> _fetchRepeatSchedule() async {
    if (widget.announcement.id <= 0) return;
    setState(() => _isLoadingRepeatSchedule = true);
    try {
      final schedule = await EchosphereApiService()
          .getRepeatSchedule(widget.announcement.id)
          .timeout(const Duration(seconds: 4), onTimeout: () => null);
      if (mounted) {
        setState(() {
          _repeatSchedule = schedule;
          _isLoadingRepeatSchedule = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _repeatSchedule = null;
          _isLoadingRepeatSchedule = false;
        });
      }
    } finally {
      if (mounted && _isLoadingRepeatSchedule) {
        setState(() => _isLoadingRepeatSchedule = false);
      }
    }
  }

  Future<void> _fetchVipProtocol() async {
    if (widget.announcement.id <= 0) return;
    setState(() => _isLoadingVipProtocol = true);
    try {
      final protocol = await EchosphereApiService()
          .getVipProtocol(widget.announcement.id)
          .timeout(const Duration(seconds: 4), onTimeout: () => null);
      if (mounted) {
        setState(() {
          _vipProtocol = protocol;
          _isLoadingVipProtocol = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _vipProtocol = null;
          _isLoadingVipProtocol = false;
        });
      }
    } finally {
      if (mounted && _isLoadingVipProtocol) {
        setState(() => _isLoadingVipProtocol = false);
      }
    }
  }

  Future<void> _analyzeVipProtocol() async {
    setState(() => _isAnalyzingVip = true);
    try {
      final protocol = await EchosphereApiService().analyzeVipProtocol(widget.announcement.id);
      if (mounted) {
        setState(() {
          _vipProtocol = protocol;
          _isAnalyzingVip = false;
        });
        snackBar('VIP Protocol analyzed and ceremonial script generated.');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isAnalyzingVip = false);
        errorSnackBar('VIP Analysis: ${e.toString().replaceAll("Exception: ", "")}');
      }
    }
  }

  Future<void> _triggerArrivalFanfare() async {
    setState(() => _isTriggeringFanfare = true);
    try {
      final res = await EchosphereApiService().triggerVipArrival(
        widget.announcement.id,
        targetZone: 'Portico-Auditorium',
        customWelcomeNote: 'Chief Guest has arrived at campus portico.',
      );
      if (mounted) {
        setState(() => _isTriggeringFanfare = false);
        final statusMsg = res['message'] ?? 'Arrival Fanfare broadcast dispatched at priority Position #2.';
        snackBar(statusMsg.toString());
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isTriggeringFanfare = false);
        errorSnackBar('Arrival Fanfare failed: ${e.toString().replaceAll("Exception: ", "")}');
      }
    }
  }

  Future<void> _deleteRepeatSchedule() async {
    try {
      final ok = await EchosphereApiService().deleteRepeatSchedule(widget.announcement.id);
      if (ok && mounted) {
        setState(() => _repeatSchedule = null);
        snackBar('Repeat broadcast schedule removed.');
      }
    } catch (e) {
      errorSnackBar('Failed to remove repeat schedule: $e');
    }
  }

  Future<void> _triggerRepeatSlotCheck() async {
    try {
      final res = await EchosphereApiService().triggerRepeatCheck();
      snackBar('Slot check evaluated: ${res['status'] ?? 'completed'}');
      _fetchRepeatSchedule();
    } catch (e) {
      errorSnackBar('Slot check failed: $e');
    }
  }

  void _showConfigureRepeatScheduleDialog() {
    final selectedSlots = <String>{
      if (_repeatSchedule != null)
        ...((_repeatSchedule!['selected_slots'] as List?)?.map((e) => e.toString()) ?? [])
      else
        'SHORT_BREAK',
    };
    String selectedScope = _repeatSchedule?['target_scope'] ?? 'DEPARTMENT';
    final customStartCtrl = TextEditingController(text: _repeatSchedule?['custom_start_time'] ?? '10:00');
    final customEndCtrl = TextEditingController(text: _repeatSchedule?['custom_end_time'] ?? '11:00');
    bool isSaving = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) {
          return AlertDialog(
            title: const Row(
              children: [
                Icon(Icons.repeat_rounded, size: 20),
                SizedBox(width: 8),
                Text('Configure Repeat Schedule', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ],
            ),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Select Repeat Broadcast Slots:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      FilterChip(
                        label: const Text('Short Break (11:00 AM)', style: TextStyle(fontSize: 11)),
                        selected: selectedSlots.contains('SHORT_BREAK'),
                        onSelected: (val) {
                          setDlgState(() {
                            val ? selectedSlots.add('SHORT_BREAK') : selectedSlots.remove('SHORT_BREAK');
                          });
                        },
                      ),
                      FilterChip(
                        label: const Text('Lunch Break (1:15 PM)', style: TextStyle(fontSize: 11)),
                        selected: selectedSlots.contains('LUNCH_BREAK'),
                        onSelected: (val) {
                          setDlgState(() {
                            val ? selectedSlots.add('LUNCH_BREAK') : selectedSlots.remove('LUNCH_BREAK');
                          });
                        },
                      ),
                      FilterChip(
                        label: const Text('Custom Window', style: TextStyle(fontSize: 11)),
                        selected: selectedSlots.contains('CUSTOM_WINDOW'),
                        onSelected: (val) {
                          setDlgState(() {
                            val ? selectedSlots.add('CUSTOM_WINDOW') : selectedSlots.remove('CUSTOM_WINDOW');
                          });
                        },
                      ),
                    ],
                  ),
                  if (selectedSlots.contains('CUSTOM_WINDOW')) ...[
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: customStartCtrl,
                            decoration: const InputDecoration(labelText: 'Start (HH:MM)', border: OutlineInputBorder()),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextField(
                            controller: customEndCtrl,
                            decoration: const InputDecoration(labelText: 'End (HH:MM)', border: OutlineInputBorder()),
                          ),
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 14),
                  const Text('Target Scope:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String>(
                    value: selectedScope,
                    items: const [
                      DropdownMenuItem(value: 'DEPARTMENT', child: Text('Department Nodes Only', style: TextStyle(fontSize: 12))),
                      DropdownMenuItem(value: 'COLLEGE_WIDE', child: Text('College-Wide All Nodes', style: TextStyle(fontSize: 12))),
                      DropdownMenuItem(value: 'HOSTEL', child: Text('Hostel & Common Areas', style: TextStyle(fontSize: 12))),
                    ],
                    onChanged: (val) {
                      if (val != null) setDlgState(() => selectedScope = val);
                    },
                    decoration: const InputDecoration(border: OutlineInputBorder()),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: isSaving ? null : () => Navigator.pop(ctx),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                onPressed: isSaving
                    ? null
                    : () async {
                        if (selectedSlots.isEmpty) {
                          errorSnackBar('Please select at least one repeat slot.');
                          return;
                        }
                        setDlgState(() => isSaving = true);
                        try {
                          final now = DateTime.now();
                          final data = {
                            'selected_slots': selectedSlots.toList(),
                            'target_scope': selectedScope,
                            'event_datetime': now.add(const Duration(hours: 24)).toIso8601String(),
                            'start_date': now.toIso8601String(),
                            'end_date': now.add(const Duration(hours: 48)).toIso8601String(),
                            'force_enable_speaker': true,
                            if (selectedSlots.contains('CUSTOM_WINDOW')) ...{
                              'custom_start_time': customStartCtrl.text.trim(),
                              'custom_end_time': customEndCtrl.text.trim(),
                            },
                          };
                          final res = await EchosphereApiService().setRepeatSchedule(widget.announcement.id, data);
                          if (ctx.mounted) Navigator.pop(ctx);
                          if (mounted) setState(() => _repeatSchedule = res);
                          snackBar('Repeat broadcast schedule saved.');
                        } catch (e) {
                          setDlgState(() => isSaving = false);
                          errorSnackBar('Save failed: ${e.toString().replaceAll("Exception: ", "")}');
                        }
                      },
                child: isSaving
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Save Schedule'),
              ),
            ],
          );
        },
      ),
    );
  }

  void _showEditVipProtocolDialog() {
    if (_vipProtocol == null) return;
    final nameCtrl = TextEditingController(text: _vipProtocol!['guest_name'] ?? '');
    final titleCtrl = TextEditingController(text: _vipProtocol!['guest_title'] ?? '');
    final venueCtrl = TextEditingController(text: _vipProtocol!['venue'] ?? '');
    final scriptCtrl = TextEditingController(text: _vipProtocol!['spoken_script'] ?? '');
    String voiceProfile = _vipProtocol!['voice_profile'] ?? 'FEMALE_EXECUTIVE';
    bool examSuppression = _vipProtocol!['exam_suppression_active'] == true;
    bool isSaving = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.stars_rounded, size: 20),
              SizedBox(width: 8),
              Text('Edit VIP Protocol & Script', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(labelText: 'Guest Name', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: titleCtrl,
                  decoration: const InputDecoration(labelText: 'Guest Title / Designation', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: venueCtrl,
                  decoration: const InputDecoration(labelText: 'Reception Venue', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: scriptCtrl,
                  maxLines: 4,
                  decoration: const InputDecoration(labelText: 'Spoken Broadcast Script', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  value: voiceProfile,
                  items: const [
                    DropdownMenuItem(value: 'FEMALE_EXECUTIVE', child: Text('Female Executive (Clear / Formal)', style: TextStyle(fontSize: 12))),
                    DropdownMenuItem(value: 'MALE_AUTHORITATIVE', child: Text('Male Authoritative (Formal Announcement)', style: TextStyle(fontSize: 12))),
                  ],
                  onChanged: (val) {
                    if (val != null) setDlgState(() => voiceProfile = val);
                  },
                  decoration: const InputDecoration(labelText: 'Voice Profile', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 10),
                SwitchListTile(
                  title: const Text('Exam Suppression Active', style: TextStyle(fontSize: 12)),
                  subtitle: const Text('Suppress broadcast in quiet / exam rooms', style: TextStyle(fontSize: 10)),
                  value: examSuppression,
                  onChanged: (val) => setDlgState(() => examSuppression = val),
                  contentPadding: EdgeInsets.zero,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: isSaving ? null : () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: isSaving
                  ? null
                  : () async {
                      setDlgState(() => isSaving = true);
                      try {
                        final data = {
                          'guest_name': nameCtrl.text.trim(),
                          'guest_title': titleCtrl.text.trim(),
                          'venue': venueCtrl.text.trim(),
                          'spoken_script': scriptCtrl.text.trim(),
                          'voice_profile': voiceProfile,
                          'exam_suppression_active': examSuppression,
                        };
                        final res = await EchosphereApiService().updateVipProtocol(widget.announcement.id, data);
                        if (ctx.mounted) Navigator.pop(ctx);
                        if (mounted) setState(() => _vipProtocol = res);
                        snackBar('VIP Protocol updated successfully.');
                      } catch (e) {
                        setDlgState(() => isSaving = false);
                        errorSnackBar('Update failed: ${e.toString().replaceAll("Exception: ", "")}');
                      }
                    },
              child: isSaving
                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Save Changes'),
            ),
          ],
        ),
      ),
    );
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
        TtsAudioService.instance.prewarmAnnouncement(
          widget.announcement.id,
          title: widget.announcement.title,
          content: widget.announcement.description,
          summary: summary,
        );
        snackBar('AI Summary generated successfully.');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSummarizing = false);
        snackBar('Failed to generate summary: $e');
      }
    }
  }

  Future<void> _broadcastToSpeakers() async {
    if (_isBroadcasting) return;
    final queueCtrl = Get.isRegistered<SpeakerQueueController>()
        ? Get.find<SpeakerQueueController>()
        : Get.put(SpeakerQueueController());

    debugPrint('[Broadcast] Tapped: broadcasting announcement #${announcement.id} (${announcement.title})...');
    setState(() => _isBroadcasting = true);

    try {
      await queueCtrl.broadcastAnnouncement(announcement);
    } catch (e) {
      debugPrint('[Broadcast] Error: $e');
      snackBar('Failed to broadcast: ${e.toString().replaceAll('Exception: ', '')}');
    } finally {
      if (mounted) {
        setState(() => _isBroadcasting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final announcement = widget.announcement;
    final theme = Theme.of(context);
    final authController = Get.find<AuthController>();
    final announcementController = Get.find<AnnouncementController>();

    final userRole = authController.currentUser.value?.role ?? 'Student';
    final canApprove = (userRole == 'HoD' || userRole == 'College Admin' || userRole == 'Principal' || userRole == 'Dev Admin' || userRole == 'Developer') &&
        (announcement.status == 'SUBMITTED' || announcement.status == 'DRAFT' || announcement.status == 'PENDING_APPROVAL');

    final canDelete = userRole == 'Principal' || userRole == 'Dev Admin' || userRole == 'Developer' || (userRole == 'HoD' && announcement.department == authController.currentUser.value?.department);
    final canBroadcast = (announcement.status == 'APPROVED' || announcement.status == 'PUBLISHED' || announcement.status == 'ACTIVE' || announcement.status == 'SCHEDULED');
    final canArchive = (userRole == 'HoD' || userRole == 'College Admin' || userRole == 'Principal' || userRole == 'Dev Admin' || userRole == 'Developer') &&
        (announcement.status == 'APPROVED' || announcement.status == 'PUBLISHED' || announcement.status == 'ACTIVE');

    return SubPagePopScope(
      fallbackRoute: '/home',
      child: Scaffold(
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
                  const EchoSphereBackButton(fallbackRoute: '/home'),
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
                  IconButton(
                    icon: const Icon(Icons.event_note_rounded, size: 20),
                    tooltip: 'Sync Notice to Calendar',
                    onPressed: () {
                      final event = _calendarEvent ?? CalendarEventData(
                        hasEvent: true,
                        title: announcement.title,
                        startTime: announcement.createdAt.add(const Duration(hours: 1)),
                        endTime: announcement.createdAt.add(const Duration(hours: 2)),
                        description: announcement.description,
                        location: announcement.department,
                        actionRequired: '',
                      );
                      showCalendarSyncSheet(context, event);
                    },
                  ),
                  const SizedBox(width: 6),
                  EchoSphereBadge.priority(
                    priority: announcement.priority,
                    size: BadgeSize.md,
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
                                  EchoSphereBadge.secondary(
                                    label: announcement.category,
                                  ),
                                  EchoSphereBadge.outline(
                                    label: announcement.department,
                                  ),
                                  _buildStatusBadge(context, announcement.status),
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
                                          '${announcement.creatorName} \u2022 Designation: ${announcement.creatorRole}',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 14,
                                            color: theme.colorScheme.primary,
                                          ),
                                        ),
                                        Text(
                                          'Department: ${announcement.department} \u2022 ${DateFormat("MMMM dd, yyyy \u2022 hh:mm a").format(announcement.createdAt)}',
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
                                const Icon(Icons.auto_awesome, color: EchoSpherePalette.lightPrimary, size: 24),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Wrap(
                                        alignment: WrapAlignment.spaceBetween,
                                        crossAxisAlignment: WrapCrossAlignment.center,
                                        spacing: 8,
                                        runSpacing: 4,
                                        children: [
                                          Text(
                                            'AI Summary',
                                            style: TextStyle(
                                              fontSize: 12,
                                              fontWeight: FontWeight.bold,
                                              color: theme.colorScheme.primary,
                                            ),
                                          ),
                                          Wrap(
                                            crossAxisAlignment: WrapCrossAlignment.center,
                                            spacing: 6,
                                            children: [
                                              Obx(() {
                                                final audio = TtsAudioService.instance;
                                                final isPlayingSummary = audio.isAnnouncementPlaying(announcement.id) && audio.readMode.value == 'summary';
                                                return InkWell(
                                                  onTap: () {
                                                    audio.playAnnouncement(
                                                      announcement.id,
                                                      title: announcement.title,
                                                      content: announcement.description,
                                                      summary: _aiSummary,
                                                      forceMode: 'summary',
                                                    );
                                                  },
                                                  borderRadius: BorderRadius.circular(4),
                                                  child: Padding(
                                                    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                                                    child: Row(
                                                      mainAxisSize: MainAxisSize.min,
                                                      children: [
                                                        Icon(
                                                          isPlayingSummary ? Icons.pause_circle_filled_rounded : Icons.volume_up_rounded,
                                                          size: 14,
                                                          color: theme.colorScheme.primary,
                                                        ),
                                                        const SizedBox(width: 3),
                                                        Text(
                                                          isPlayingSummary ? 'Playing' : 'Listen',
                                                          style: TextStyle(
                                                            fontSize: 11,
                                                            fontWeight: FontWeight.bold,
                                                            color: theme.colorScheme.primary,
                                                          ),
                                                        ),
                                                      ],
                                                    ),
                                                  ),
                                                );
                                              }),
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
                                                    color: theme.colorScheme.primary,
                                                  ),
                                                ),
                                              ),
                                              InkWell(
                                                onTap: _isSummarizing ? null : _generateAiSummary,
                                                child: Row(
                                                  mainAxisSize: MainAxisSize.min,
                                                  children: [
                                                    Icon(
                                                      Icons.refresh_rounded,
                                                      size: 13,
                                                      color: theme.colorScheme.primary,
                                                    ),
                                                    const SizedBox(width: 3),
                                                    Text(
                                                      _isSummarizing ? 'Regenerating...' : 'Regenerate',
                                                      style: TextStyle(
                                                        fontSize: 11,
                                                        color: theme.colorScheme.primary,
                                                        fontWeight: FontWeight.w600,
                                                      ),
                                                    ),
                                                  ],
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
                                const Icon(Icons.auto_awesome, color: EchoSpherePalette.lightPrimary, size: 24),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    'Need a fast overview? Generate an AI summary in seconds.',
                                    style: TextStyle(
                                      fontSize: 13,
                                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                ElevatedButton.icon(
                                  onPressed: _isSummarizing ? null : _generateAiSummary,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: theme.colorScheme.primary,
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
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
                          initialVoiceGender: announcement.speakerVoice,
                        ),
                        const SizedBox(height: 16),

                        // AI Calendar Event Card (If dates/deadlines extracted)
                        if (_calendarEvent != null && _calendarEvent!.hasEvent) ...[
                          Container(
                            padding: const EdgeInsets.all(16.0),
                            decoration: BoxDecoration(
                              color: theme.colorScheme.primary.withOpacity(0.08),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: theme.colorScheme.primary.withOpacity(0.28),
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
                                        color: theme.colorScheme.primary.withOpacity(0.16),
                                        shape: BoxShape.circle,
                                      ),
                                      child: Icon(
                                        Icons.event_available_rounded,
                                        color: theme.colorScheme.primary,
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
                                          color: theme.colorScheme.primary,
                                        ),
                                      ),
                                    ),
                                    Text(
                                      DateFormat('MMM d, yyyy').format(_calendarEvent!.startTime),
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                        color: theme.colorScheme.primary,
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
                                    Icon(Icons.schedule_rounded, size: 13, color: theme.colorScheme.primary),
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
                                      Icon(Icons.task_alt_rounded, size: 13, color: theme.colorScheme.primary),
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
                                        backgroundColor: theme.colorScheme.primary,
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
                                        side: BorderSide(color: theme.colorScheme.primary.withOpacity(0.4)),
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
                                    final iconCol = theme.colorScheme.primary;
                                    final lower = file.toLowerCase();
                                    if (lower.endsWith('.pdf')) {
                                      icon = Icons.picture_as_pdf_rounded;
                                    } else if (lower.endsWith('.xls') || lower.endsWith('.xlsx') || lower.endsWith('.csv')) {
                                      icon = Icons.table_chart_rounded;
                                    } else if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg')) {
                                      icon = Icons.image_rounded;
                                    } else if (lower.endsWith('.doc') || lower.endsWith('.docx')) {
                                      icon = Icons.description_rounded;
                                    }
                                    return ConstrainedBox(
                                      constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width - 80),
                                      child: ActionChip(
                                        avatar: Icon(icon, color: iconCol, size: 18),
                                        label: Text(file, maxLines: 1, overflow: TextOverflow.ellipsis),
                                        onPressed: () => AttachmentViewerDialog.show(
                                          context,
                                          filename: file,
                                          notice: announcement,
                                        ),
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

                        // Automated Repeat Broadcast Schedule Section
                        _buildRepeatScheduleCard(theme),
                        const SizedBox(height: 20),

                        // VIP Dignitary Protocol Section
                        _buildVipProtocolCard(theme),
                        const SizedBox(height: 20),

                        // Audit Trail Section
                        EchoSphereContainer(
                          padding: const EdgeInsets.all(20.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(Icons.history_rounded, size: 20, color: theme.colorScheme.primary),
                                  const SizedBox(width: 8),
                                  const Expanded(
                                    child: Text(
                                      'Audit Trail & Delivery Info',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 16),
                              _buildAuditRow(
                                icon: Icons.person_outline_rounded,
                                label: 'Created By',
                                value: '${announcement.creatorName} (${announcement.department})',
                                theme: theme,
                              ),
                              const SizedBox(height: 10),
                              _buildAuditRow(
                                icon: Icons.groups_outlined,
                                label: 'Target Audience',
                                value: 'Entire College & Department',
                                theme: theme,
                              ),
                              const SizedBox(height: 10),
                              _buildAuditRow(
                                icon: Icons.cell_tower_rounded,
                                label: 'Delivery Channels',
                                value: 'In-App Feed, Push Notification',
                                theme: theme,
                              ),
                              const SizedBox(height: 10),
                              _buildAuditRow(
                                icon: Icons.verified_outlined,
                                label: 'Approval Status',
                                value: announcement.status,
                                theme: theme,
                              ),
                              const SizedBox(height: 10),
                              _buildAuditRow(
                                icon: Icons.schedule_rounded,
                                label: 'Timestamp',
                                value: DateFormat('MMM dd, yyyy \u2022 hh:mm:ss a').format(announcement.createdAt),
                                theme: theme,
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
                                  color: _isBroadcasting ? theme.colorScheme.primary.withOpacity(0.08) : theme.colorScheme.primary.withOpacity(0.15),
                                  border: BorderSide(color: theme.colorScheme.primary),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: _isBroadcasting ? null : () => _broadcastToSpeakers(),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      if (_isBroadcasting)
                                        SizedBox(
                                          width: 14,
                                          height: 14,
                                          child: CircularProgressIndicator(strokeWidth: 2, color: theme.colorScheme.primary),
                                        )
                                      else
                                        Icon(Icons.podcasts_rounded, size: 16, color: theme.colorScheme.primary),
                                      const SizedBox(width: 6),
                                      Flexible(
                                        child: Text(
                                          _isBroadcasting ? 'Sending...' : 'Broadcast to Speakers',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(color: theme.colorScheme.primary, fontSize: 12, fontWeight: FontWeight.bold),
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
                                Builder(builder: (ctx) {
                                  final isDark = theme.brightness == Brightness.dark;
                                  final rejectColor = isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive;
                                  return EchoSphereButton(
                                    height: 42,
                                    color: rejectColor.withOpacity(0.12),
                                    border: BorderSide(color: rejectColor.withOpacity(0.35), width: 1.2),
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                    onTap: () => _showRejectDialog(context, announcementController),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.cancel_outlined, size: 16, color: rejectColor),
                                        const SizedBox(width: 6),
                                        Flexible(
                                          child: Text('Reject', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: rejectColor, fontSize: 12, fontWeight: FontWeight.w600)),
                                        ),
                                      ],
                                    ),
                                  );
                                }),
                              ],
                              if (canArchive)
                                EchoSphereButton(
                                  height: 42,
                                  color: theme.colorScheme.primary.withOpacity(0.12),
                                  border: BorderSide(color: theme.colorScheme.primary.withOpacity(0.3)),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showArchiveConfirm(context, announcementController),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.archive_outlined, size: 16, color: theme.colorScheme.primary),
                                      const SizedBox(width: 6),
                                      Flexible(
                                        child: Text('Archive', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: theme.colorScheme.primary, fontSize: 12)),
                                      ),
                                    ],
                                  ),
                                ),
                              if (canDelete) ...[
                                EchoSphereButton(
                                  height: 42,
                                  color: theme.colorScheme.primary.withOpacity(0.12),
                                  border: BorderSide(color: theme.colorScheme.primary.withOpacity(0.3)),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showEditDialog(context, announcementController),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.edit_rounded, size: 16, color: theme.colorScheme.primary),
                                      const SizedBox(width: 6),
                                      const Flexible(
                                        child: Text('Modify', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 12)),
                                      ),
                                    ],
                                  ),
                                ),
                                EchoSphereButton(
                                  height: 42,
                                  color: theme.colorScheme.primary.withOpacity(0.12),
                                  border: BorderSide(color: theme.colorScheme.primary.withOpacity(0.3)),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                  onTap: () => _showReschedulePicker(context, announcementController),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.event_rounded, size: 16, color: theme.colorScheme.primary),
                                      const SizedBox(width: 6),
                                      Flexible(
                                        child: Text('Reschedule', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: theme.colorScheme.primary, fontSize: 12)),
                                      ),
                                    ],
                                  ),
                                ),
                                Builder(builder: (ctx) {
                                  final isDark = theme.brightness == Brightness.dark;
                                  final delColor = isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive;
                                  return EchoSphereButton(
                                    height: 42,
                                    color: delColor.withOpacity(0.12),
                                    border: BorderSide(color: delColor.withOpacity(0.35), width: 1.2),
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                    onTap: () => _showDeleteConfirm(context, announcementController),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.delete_outline_rounded, size: 16, color: delColor),
                                        const SizedBox(width: 6),
                                        Flexible(
                                          child: Text('Delete', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: delColor, fontSize: 12, fontWeight: FontWeight.w600)),
                                        ),
                                      ],
                                    ),
                                  );
                                }),
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
    bool deliverSpeakerVal = announcement.deliverSpeaker;
    String speakerVoiceVal = announcement.speakerVoice;

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
              id: announcement.id,
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

        snackBar('Announcement rescheduled for ${DateFormat("MMM dd, yyyy \u2022 hh:mm a").format(newDateTime)}!');
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

  Widget _buildRepeatScheduleCard(ThemeData theme) {
    final hasSchedule = _repeatSchedule != null;
    final selectedSlots = hasSchedule ? (_repeatSchedule!['selected_slots'] as List? ?? []) : [];
    final logs = hasSchedule ? (_repeatSchedule!['execution_logs'] as List? ?? []) : [];
    final scope = hasSchedule ? (_repeatSchedule!['target_scope'] ?? 'DEPARTMENT') : '';
    final isActive = hasSchedule && (_repeatSchedule!['is_active'] ?? true);

    return EchoSphereContainer(
      padding: const EdgeInsets.all(20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.repeat_rounded, size: 20, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Repeat Notice Broadcast',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                ),
              ),
              if (_isLoadingRepeatSchedule)
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: hasSchedule
                        ? (isActive ? theme.colorScheme.primary.withOpacity(0.12) : theme.colorScheme.onSurface.withOpacity(0.08))
                        : theme.colorScheme.onSurface.withOpacity(0.06),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: hasSchedule
                          ? (isActive ? theme.colorScheme.primary.withOpacity(0.3) : theme.colorScheme.outline.withOpacity(0.2))
                          : theme.colorScheme.outline.withOpacity(0.15),
                    ),
                  ),
                  child: Text(
                    hasSchedule ? (isActive ? 'ACTIVE' : 'INACTIVE') : 'NOT CONFIGURED',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: hasSchedule && isActive ? theme.colorScheme.primary : theme.colorScheme.onSurface.withOpacity(0.6),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          if (hasSchedule) ...[
            Text(
              'Configured to rebroadcast across $scope nodes at campus transition windows.',
              style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurface.withOpacity(0.7)),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: selectedSlots.map<Widget>((s) {
                final label = s.toString().replaceAll('_', ' ');
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primary.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: theme.colorScheme.primary.withOpacity(0.2)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.schedule_rounded, size: 12, color: theme.colorScheme.primary),
                      const SizedBox(width: 4),
                      Text(
                        label,
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: theme.colorScheme.primary),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
            if (logs.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'Recent Execution History (${logs.length} runs):',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: theme.colorScheme.onSurface.withOpacity(0.7)),
              ),
              const SizedBox(height: 6),
              ...logs.take(3).map((l) {
                final slotName = l['slot_name'] ?? 'Broadcast Slot';
                final playedAt = l['played_at']?.toString().split('.').first.replaceAll('T', ' ') ?? '';
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4.0),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle_outline_rounded, size: 12, color: theme.colorScheme.primary),
                      const SizedBox(width: 6),
                      Text(
                        '$slotName \u2022 $playedAt',
                        style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.75)),
                      ),
                    ],
                  ),
                );
              }),
            ],
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                OutlinedButton.icon(
                  onPressed: () => _showConfigureRepeatScheduleDialog(),
                  icon: const Icon(Icons.edit_calendar_rounded, size: 13),
                  label: const Text('Edit Schedule', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    side: BorderSide(color: theme.colorScheme.primary.withOpacity(0.4)),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () => _triggerRepeatSlotCheck(),
                  icon: const Icon(Icons.play_circle_outline_rounded, size: 13),
                  label: const Text('Test Slot Check', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    side: BorderSide(color: theme.colorScheme.primary.withOpacity(0.4)),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
                TextButton.icon(
                  onPressed: () => _deleteRepeatSchedule(),
                  icon: Icon(Icons.delete_outline_rounded, size: 13, color: theme.colorScheme.error),
                  label: Text('Remove Schedule', style: TextStyle(fontSize: 11, color: theme.colorScheme.error)),
                ),
              ],
            ),
          ] else ...[
            Text(
              'No automated repeat broadcast schedule configured for this notice. Configure to periodically rebroadcast during short break, lunch break, or dismissal.',
              style: TextStyle(fontSize: 12, height: 1.5, color: theme.colorScheme.onSurface.withOpacity(0.65)),
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: () => _showConfigureRepeatScheduleDialog(),
              icon: const Icon(Icons.add_alarm_rounded, size: 14),
              label: const Text('Configure Repeat Schedule', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
              style: ElevatedButton.styleFrom(
                backgroundColor: theme.colorScheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                elevation: 0,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildVipProtocolCard(ThemeData theme) {
    final hasVip = _vipProtocol != null;
    final guestName = hasVip ? (_vipProtocol!['guest_name'] ?? '') : '';
    final guestTitle = hasVip ? (_vipProtocol!['guest_title'] ?? '') : '';
    final venue = hasVip ? (_vipProtocol!['venue'] ?? '') : '';
    final spokenScript = hasVip ? (_vipProtocol!['spoken_script'] ?? '') : '';
    final voiceProfile = hasVip ? (_vipProtocol!['voice_profile'] ?? 'FEMALE_EXECUTIVE') : 'FEMALE_EXECUTIVE';
    final examSuppression = hasVip && (_vipProtocol!['exam_suppression_active'] == true);
    final confidenceScore = hasVip ? ((_vipProtocol!['confidence_score'] as num? ?? 0.95) * 100).toInt() : 0;

    return EchoSphereContainer(
      padding: const EdgeInsets.all(20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.stars_rounded, size: 20, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Guest Arrival Broadcast',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                ),
              ),
              if (_isLoadingVipProtocol || _isAnalyzingVip)
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else if (hasVip)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primary.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: theme.colorScheme.primary.withOpacity(0.3)),
                  ),
                  child: Text(
                    '$confidenceScore% MATCH',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          if (hasVip) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withOpacity(0.06),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: theme.colorScheme.primary.withOpacity(0.2)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.person_pin_rounded, size: 16, color: theme.colorScheme.primary),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          '$guestName${guestTitle.isNotEmpty ? ' — $guestTitle' : ''}',
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                  if (venue.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Designated Reception Venue: $venue',
                      style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.7)),
                    ),
                  ],
                  const Divider(height: 16),
                  Text(
                    'Ceremonial Radio Broadcast Script ($voiceProfile):',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: theme.colorScheme.primary),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '"$spokenScript"',
                    style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, height: 1.4),
                  ),
                  if (examSuppression) ...[
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(Icons.volume_off_rounded, size: 12, color: theme.colorScheme.primary),
                        const SizedBox(width: 4),
                        Text(
                          'Exam Zone Suppression Active (Quiet Zone respected)',
                          style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: theme.colorScheme.primary),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                ElevatedButton.icon(
                  onPressed: _isTriggeringFanfare ? null : () => _triggerArrivalFanfare(),
                  icon: _isTriggeringFanfare
                      ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.campaign_rounded, size: 14),
                  label: Text(
                    _isTriggeringFanfare ? 'Broadcasting Fanfare...' : 'Trigger Arrival Fanfare',
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: theme.colorScheme.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    elevation: 0,
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () => _showEditVipProtocolDialog(),
                  icon: const Icon(Icons.edit_note_rounded, size: 14),
                  label: const Text('Edit Protocol Script', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    side: BorderSide(color: theme.colorScheme.primary.withOpacity(0.4)),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ],
            ),
          ] else ...[
            Text(
              'Automated entity extraction and ceremonial fanfare protocol for Chief Guests, resource persons, and visiting dignitaries.',
              style: TextStyle(fontSize: 12, height: 1.5, color: theme.colorScheme.onSurface.withOpacity(0.65)),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _isAnalyzingVip ? null : () => _analyzeVipProtocol(),
              icon: _isAnalyzingVip
                  ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.auto_awesome_rounded, size: 14),
              label: Text(
                _isAnalyzingVip ? 'Analyzing Dignitary Details...' : 'Analyze for VIP Dignitary',
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
              ),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                side: BorderSide(color: theme.colorScheme.primary.withOpacity(0.4)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ],
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

  Widget _buildAuditRow({
    required IconData icon,
    required String label,
    required String value,
    required ThemeData theme,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 1.0),
          child: Icon(icon, size: 15, color: theme.colorScheme.primary.withOpacity(0.85)),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: RichText(
            text: TextSpan(
              style: TextStyle(
                fontSize: 12,
                fontFamily: 'Poppins',
                color: theme.colorScheme.onSurface.withOpacity(0.9),
              ),
              children: [
                TextSpan(
                  text: '$label: ',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: theme.colorScheme.onSurface.withOpacity(0.65),
                  ),
                ),
                TextSpan(
                  text: value,
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
