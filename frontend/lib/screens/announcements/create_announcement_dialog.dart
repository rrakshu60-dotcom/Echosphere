import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/echosphere_ai_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_chip.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:echosphere/widgets/custom_widgets/voice_dictation_sheet.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:echosphere/utils/campus_time.dart';

class CreateAnnouncementDialog extends StatefulWidget {
  final String? initialTitle;
  final String? initialContent;
  final String? initialCategory;

  const CreateAnnouncementDialog({
    super.key,
    this.initialTitle,
    this.initialContent,
    this.initialCategory,
  });

  @override
  State<CreateAnnouncementDialog> createState() => _CreateAnnouncementDialogState();
}

class _CreateAnnouncementDialogState extends State<CreateAnnouncementDialog> {
  final titleController = TextEditingController();
  final descController = TextEditingController();

  String aiDetectedCategory = 'Academic';
  String aiDetectedPriority = 'NORMAL';
  String selectedAudience = 'Entire College';

  bool deliverInApp = true;
  bool deliverPush = true;
  bool deliverSpeaker = false;
  String speakerVoice = 'female';
  int? selectedSpeakerNodeId;
  List<Map<String, dynamic>> availableSpeakerNodes = [];

  bool isScheduleLater = false;
  DateTime scheduledDateTime = DateTime.now().add(const Duration(hours: 1));

  static const List<Map<String, dynamic>> _breakWindows = [
    {
      'key': 'SHORT_BREAK',
      'title': 'Short Break',
      'time': '11:00 AM – 11:15 AM',
      'duration': '15 mins',
      'icon': Icons.coffee_rounded,
    },
    {
      'key': 'LUNCH_BREAK',
      'title': 'Lunch Break',
      'time': '1:15 PM – 2:00 PM',
      'duration': '45 mins',
      'icon': Icons.restaurant_rounded,
    },
    {
      'key': 'EVENING_BREAK',
      'title': 'Evening Break',
      'time': '4:30 PM – 5:30 PM',
      'duration': '1 hour',
      'icon': Icons.wb_twilight_rounded,
    },
    {
      'key': 'HOSTEL_WINDOW',
      'title': 'Hostel Window',
      'time': '7:30 PM – 9:00 PM',
      'duration': '1 hr 30 mins',
      'icon': Icons.night_shelter_rounded,
    },
  ];

  bool enableRepeatSchedule = false;
  bool repeatPlayOnPublish = true;
  final Set<String> repeatSlots = {'SHORT_BREAK'};
  final repeatStartCtrl = TextEditingController(text: '10:00');
  final repeatEndCtrl = TextEditingController(text: '11:00');


  bool isAiDrafting = false;

  String? aiValidationWarning;
  String? aiSpamWarning;
  String? aiDuplicateWarning;
  Map<String, dynamic>? activeConflictReport;
  Map<String, dynamic>? activeAudienceWarning;
  bool isCheckingConflict = false;
  bool _isResolvingConflict = false;

  List<PlatformFile> attachedFiles = [];

  Future<void> _loadSpeakerNodes() async {
    try {
      final nodes = await EchosphereApiService().getSpeakerNodes();
      if (mounted) {
        setState(() {
          final fetched = nodes.whereType<Map>().map((n) => Map<String, dynamic>.from(n)).toList();
          if (fetched.isNotEmpty) {
            availableSpeakerNodes = fetched;
          } else if (availableSpeakerNodes.isEmpty) {
            availableSpeakerNodes = List<Map<String, dynamic>>.from(SpeakerQueueController.defaultSpeakerNodes);
          }
        });
      }
    } catch (_) {
      if (mounted && availableSpeakerNodes.isEmpty) {
        setState(() {
          availableSpeakerNodes = List<Map<String, dynamic>>.from(SpeakerQueueController.defaultSpeakerNodes);
        });
      }
    }
  }

  String _normalizeRepeatTime(String raw) {
    var s = raw.trim();
    final m12 = RegExp(r'^(\d{1,2}):([0-5]\d)\s*([AaPp][Mm])$').firstMatch(s);
    if (m12 != null) {
      var h = int.parse(m12.group(1)!);
      final m = int.parse(m12.group(2)!);
      final mer = m12.group(3)!.toUpperCase();
      if (h >= 1 && h <= 12) {
        if (mer == 'PM' && h != 12) h += 12;
        if (mer == 'AM' && h == 12) h = 0;
        return '${h.toString().padLeft(2, '0')}:${m.toString().padLeft(2, '0')}';
      }
    }
    if (RegExp(r'^\d:[0-5]\d$').hasMatch(s)) {
      return '0$s';
    }
    return s;
  }

  String _format12Hour(String hhmm) {
    final norm = _normalizeRepeatTime(hhmm);
    final parts = norm.split(':');
    if (parts.length != 2) return hhmm;
    final h = int.tryParse(parts[0]);
    final m = int.tryParse(parts[1]);
    if (h == null || m == null) return hhmm;
    final mer = h >= 12 ? 'PM' : 'AM';
    final h12 = h == 0 ? 12 : (h > 12 ? h - 12 : h);
    return '$h12:${m.toString().padLeft(2, '0')} $mer';
  }

  Map<String, dynamic> _calculateCustomWindowDuration(String startRaw, String endRaw) {
    final startNorm = _normalizeRepeatTime(startRaw);
    final endNorm = _normalizeRepeatTime(endRaw);
    final timeRegex = RegExp(r'^([01]\d|2[0-3]):[0-5]\d$');
    if (!timeRegex.hasMatch(startNorm) || !timeRegex.hasMatch(endNorm)) {
      return {'isValid': false, 'message': 'Please enter valid times (e.g. 10:00 AM or 10:00)'};
    }

    final sp = startNorm.split(':').map(int.parse).toList();
    final ep = endNorm.split(':').map(int.parse).toList();
    int startMins = sp[0] * 60 + sp[1];
    int endMins = ep[0] * 60 + ep[1];

    if (endMins <= startMins) {
      return {'isValid': false, 'message': 'End time must be later than start time'};
    }

    final diff = endMins - startMins;
    final hrs = diff ~/ 60;
    final mins = diff % 60;

    String durationStr;
    if (hrs > 0 && mins > 0) {
      durationStr = '$hrs hr $mins mins';
    } else if (hrs > 0) {
      durationStr = '$hrs hr${hrs > 1 ? "s" : ""}';
    } else {
      durationStr = '$mins mins';
    }

    final displayRange = '${_format12Hour(startNorm)} – ${_format12Hour(endNorm)}';
    return {
      'isValid': true,
      'duration': durationStr,
      'totalMinutes': diff,
      'displayRange': displayRange,
      'message': 'Repeat Window: $displayRange ($durationStr)',
    };
  }

  Future<void> _pickRepeatTime({required bool isStart}) async {
    final currentStr = _normalizeRepeatTime(isStart ? repeatStartCtrl.text : repeatEndCtrl.text);
    TimeOfDay initial = const TimeOfDay(hour: 10, minute: 0);
    try {
      final parts = currentStr.split(':');
      if (parts.length == 2) {
        initial = TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
      }
    } catch (_) {}

    final picked = await showTimePicker(
      context: context,
      initialTime: initial,
      helpText: isStart ? 'Select Repeat Start Time' : 'Select Repeat End Time',
    );
    if (picked != null) {
      final hh = picked.hour.toString().padLeft(2, '0');
      final mm = picked.minute.toString().padLeft(2, '0');
      final timeStr = '$hh:$mm';
      setState(() {
        if (isStart) {
          repeatStartCtrl.text = timeStr;
          final curEnd = _normalizeRepeatTime(repeatEndCtrl.text);
          if (curEnd.isEmpty || curEnd.compareTo(timeStr) <= 0) {
            final endHour = (picked.hour + 1) % 24;
            repeatEndCtrl.text = '${endHour.toString().padLeft(2, '0')}:$mm';
          }
        } else {
          repeatEndCtrl.text = timeStr;
        }
      });
    }
  }

  Future<void> _pickAttachmentFiles() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        allowMultiple: true,
        type: FileType.custom,
        allowedExtensions: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'txt', 'png', 'jpg', 'jpeg', 'webp'],
        withData: true, // the files are uploaded when the notice is published
      );

      if (result != null && result.files.isNotEmpty) {
        setState(() {
          for (final f in result.files) {
            if (!attachedFiles.any((existing) => existing.name == f.name)) {
              attachedFiles.add(f);
            }
          }
        });
        snackBar('Attached ${result.files.length} file(s)');
      }
    } catch (e) {
      snackBar('File picker error or cancelled.');
    }
  }

  final List<String> audiences = [
    'Entire College',
    'AIML Department',
    'AIDS Department',
    'ISE Department',
    'CSE Department',
    'ECE Department',
    'EEE Department',
    'Mechanical Department',
    'Civil Department',
    '1st Year Students',
    '2nd Year Students',
    '3rd Year Students',
    '4th Year Students',
    'Faculty Members',
  ];

  @override
  void initState() {
    super.initState();
    if (widget.initialTitle != null && widget.initialTitle!.isNotEmpty) {
      titleController.text = widget.initialTitle!;
    }
    if (widget.initialContent != null && widget.initialContent!.isNotEmpty) {
      descController.text = widget.initialContent!;
    }
    if (widget.initialCategory != null && widget.initialCategory!.isNotEmpty) {
      aiDetectedCategory = widget.initialCategory!;
    }
    titleController.addListener(_autoDetectAndValidate);
    descController.addListener(_autoDetectAndValidate);
    availableSpeakerNodes = List<Map<String, dynamic>>.from(SpeakerQueueController.defaultSpeakerNodes);
    _loadSpeakerNodes();
  }

  Future<void> _generateDraftWithAi() async {
    final topic = titleController.text.trim().isNotEmpty
        ? titleController.text.trim()
        : descController.text.trim();
    if (topic.isEmpty) {
      errorSnackBar('Please enter a brief topic or title first (e.g. "Annual Hackathon 2026").');
      return;
    }

    setState(() => isAiDrafting = true);

    try {
      final res = await EchosphereApiService().generateAiDraft(
        topic,
        category: aiDetectedCategory,
        targetRole: 'STUDENT',
      );
      if (mounted) {
        setState(() {
          if (res['title'] != null && res['title'].toString().isNotEmpty) {
            titleController.text = res['title'];
          }
          if (res['content'] != null && res['content'].toString().isNotEmpty) {
            descController.text = res['content'];
          }
          if (res['suggested_category'] != null) {
            aiDetectedCategory = res['suggested_category'];
          }
          if (res['suggested_priority'] != null) {
            aiDetectedPriority = res['suggested_priority'];
          }
        });
        snackBar('AI drafted an official institutional announcement from your topic.', title: 'AI Announcement Drafter');
      }
    } catch (e) {
      errorSnackBar('Failed to generate draft: $e');
    } finally {
      if (mounted) setState(() => isAiDrafting = false);
    }
  }

  Future<void> _startVoiceDictation() async {
    final result = await VoiceDictationSheet.show(context);
    if (result != null && mounted) {
      setState(() {
        if (result['title'] != null && result['title'].toString().isNotEmpty) {
          titleController.text = result['title'].toString();
        }
        if (result['content'] != null && result['content'].toString().isNotEmpty) {
          descController.text = result['content'].toString();
        }
        if (result['suggested_category'] != null) {
          aiDetectedCategory = result['suggested_category'].toString();
        }
        if (result['suggested_priority'] != null) {
          aiDetectedPriority = result['suggested_priority'].toString();
        }
        if (result['suggested_audience'] != null) {
          final aud = result['suggested_audience'].toString();
          if (audiences.contains(aud)) {
            selectedAudience = aud;
          }
        }
      });
      snackBar('Voice note transformed into official institutional circular!', title: 'Voice Notice Dictation');
    }
  }

  @override
  void dispose() {
    titleController.removeListener(_autoDetectAndValidate);
    descController.removeListener(_autoDetectAndValidate);
    titleController.dispose();
    descController.dispose();
    repeatStartCtrl.dispose();
    repeatEndCtrl.dispose();
    super.dispose();
  }

  void _autoDetectAndValidate() {
    if (_isResolvingConflict) return;
    final title = titleController.text.trim();
    final desc = descController.text.trim();

    if (title.isEmpty && desc.isEmpty) return;

    final authController = Get.find<AuthController>();
    final user = authController.currentUser.value;
    final role = user?.role ?? 'Teacher';

    final aiController = Get.find<EchosphereAiController>();
    final rec = aiController.recommendPriorityAndCategory(title, desc, userRole: role);

    setState(() {
      aiDetectedPriority = rec['priority'] ?? 'NORMAL';
      aiDetectedCategory = rec['category'] ?? 'Academic';
    });

    // Debounced content validation checks
    if (desc.length > 15) {
      _runAiValidation(title, desc);
    }
  }

  Future<void> _runAiValidation(String title, String desc) async {
    Map<String, dynamic> valRes = {};
    Map<String, dynamic> spamRes = {};
    Map<String, dynamic> dupRes = {};
    Map<String, dynamic> conflictRes = {};
    Map<String, dynamic> audienceRes = {};

    try {
      valRes = await EchosphereApiService().validateContent(desc, title: title);
    } catch (_) {}

    try {
      spamRes = await EchosphereApiService().checkSpam(desc);
    } catch (_) {}

    try {
      dupRes = await EchosphereApiService().checkDuplicate(title, desc);
    } catch (_) {}

    try {
      conflictRes = await EchosphereApiService().checkScheduleConflict(
        title: title,
        content: desc,
        scheduledAt: isScheduleLater ? scheduledDateTime : null,
        category: aiDetectedCategory,
      );
    } catch (_) {}

    try {
      audienceRes = await EchosphereApiService().checkAudienceMismatch(
        title: title,
        content: desc,
        selectedAudience: selectedAudience,
      );
    } catch (_) {}

    if (mounted) {
      setState(() {
        aiValidationWarning = valRes['is_valid'] == true ? null : valRes['suggestion'];
        aiSpamWarning = spamRes['is_spam'] == true ? spamRes['reason'] : null;
        aiDuplicateWarning = dupRes['is_duplicate'] == true ? dupRes['reason'] : null;
        activeConflictReport = conflictRes['has_conflict'] == true ? conflictRes : null;
        activeAudienceWarning = audienceRes['has_mismatch'] == true ? audienceRes : null;
      });
    }
  }

  Future<void> _selectScheduleDateTime() async {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final maxPickerDate = today.add(const Duration(days: 2));
    final maxDate = now.add(const Duration(days: 2));
    final initial = scheduledDateTime.isAfter(maxDate) ? now.add(const Duration(hours: 1)) : scheduledDateTime;

    final pickedDate = await showDatePicker(
      context: context,
      initialDate: initial.isBefore(today) ? today : (initial.isAfter(maxPickerDate) ? maxPickerDate : initial),
      firstDate: today,
      lastDate: maxPickerDate, // Hard-enforced 2 days max limit in GUI
      selectableDayPredicate: (DateTime day) {
        final dayOnly = DateTime(day.year, day.month, day.day);
        return !dayOnly.isBefore(today) && !dayOnly.isAfter(maxPickerDate);
      },
    );

    if (pickedDate != null && mounted) {
      final pickedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(scheduledDateTime),
      );

      if (pickedTime != null) {
        final chosen = DateTime(
          pickedDate.year,
          pickedDate.month,
          pickedDate.day,
          pickedTime.hour,
          pickedTime.minute,
        );

        if (chosen.isBefore(now.add(const Duration(minutes: 5)))) {
          errorSnackBar('Scheduling Policy: Scheduled broadcast time must be at least 5 minutes in the future.');
          return;
        }

        if (chosen.isAfter(maxDate)) {
          errorSnackBar('Scheduling Policy: Announcements cannot be scheduled more than 2 days in advance.');
          return;
        }

        setState(() {
          scheduledDateTime = chosen;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authController = Get.find<AuthController>();
    final annController = Get.find<AnnouncementController>();
    final user = authController.currentUser.value;
    final theme = Theme.of(context);
    final isStudent = user == null || user.role.toLowerCase() == 'student';

    if (isStudent) {
      return EchoSphereDialog(
        title: 'Access Restricted',
        showCancelButton: false,
        confirmText: 'Dismiss',
        onConfirm: () => Navigator.of(context).pop(),
        contentWidget: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.gpp_bad_rounded, color: theme.colorScheme.primary, size: 40),
              const SizedBox(height: 12),
              const Text(
                "I don't have the authority to author or publish announcements directly from this account. If you have an announcement proposal, please coordinate with your faculty advisor or department office.",
                style: TextStyle(fontSize: 12),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    final textLength = descController.text.trim().length;

    return EchoSphereDialog(
      title: 'Create & Schedule Announcement',
      contentWidget: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // AI Fast Intake Studio (Voice Dictation)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              margin: const EdgeInsets.only(bottom: 14),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    theme.colorScheme.primary.withOpacity(0.12),
                    theme.colorScheme.primary.withOpacity(0.06),
                  ],
                ),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: theme.colorScheme.primary.withOpacity(0.25),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Flexible(
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.auto_awesome, size: 14, color: theme.colorScheme.primary),
                            const SizedBox(width: 6),
                            Flexible(
                              child: Text(
                                'AI Fast Intake Studio',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: theme.colorScheme.primary),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      ElevatedButton.icon(
                        key: const Key('voice_dictate_button'),
                        onPressed: _startVoiceDictation,
                        icon: const Icon(Icons.mic_rounded, size: 14),
                        label: const Text('Voice Dictate', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: theme.colorScheme.primary,
                          foregroundColor: Colors.white,
                          visualDensity: VisualDensity.compact,
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 8,
              runSpacing: 4,
              children: [
                const Text('Announcement Title', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                ActionChip(
                  avatar: Icon(Icons.auto_awesome, size: 14, color: theme.colorScheme.primary),
                  label: isAiDrafting
                      ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('AI Auto-Draft', style: TextStyle(fontSize: 11)),
                  onPressed: isAiDrafting ? null : _generateDraftWithAi,
                ),
              ],
            ),
            const SizedBox(height: 6),
            TextField(
              controller: titleController,
              decoration: const InputDecoration(
                hintText: 'e.g. Mid Semester Examination Timetable',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),

            // Description Header with AI Tools
            Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 8,
              runSpacing: 6,
              children: [
                const Text('Announcement Content', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              ],
            ),
            const SizedBox(height: 6),
            TextField(
              controller: descController,
              maxLines: 4,
              decoration: InputDecoration(
                hintText: textLength < 80
                    ? 'Enter notice (short notes < 80 chars can be expanded with AI)...'
                    : 'Enter complete announcement content...',
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),

            // AI Schedule Conflict Alert Card
            if (activeConflictReport != null && activeConflictReport!['has_conflict'] == true) ...[
              _buildScheduleConflictCard(theme),
            ],

            // AI Audience Pre-Flight Warning Card
            if (activeAudienceWarning != null && activeAudienceWarning!['has_mismatch'] == true) ...[
              _buildAudienceWarningCard(theme),
            ],

            // AI Warnings (Validation / Spam / Duplicate)
            if (aiValidationWarning != null || aiSpamWarning != null || aiDuplicateWarning != null) ...[
              Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: theme.colorScheme.primary.withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.warning_amber_rounded, size: 16, color: theme.colorScheme.primary),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text('AI Content Assistance Warnings',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: theme.colorScheme.primary)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    if (aiValidationWarning != null)
                      Text('\u2022 $aiValidationWarning', style: const TextStyle(fontSize: 11)),
                    if (aiSpamWarning != null)
                      Text('\u2022 Spam Alert: $aiSpamWarning', style: TextStyle(fontSize: 11, color: theme.colorScheme.primary)),
                    if (aiDuplicateWarning != null)
                      Text('\u2022 Duplicate Alert: $aiDuplicateWarning', style: TextStyle(fontSize: 11, color: theme.colorScheme.primary)),
                  ],
                ),
              ),
            ],

            // AI Auto-Detected Category & Priority Banner
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: theme.colorScheme.primary.withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  Icon(Icons.auto_awesome, size: 18, color: theme.colorScheme.primary),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'AI Auto-Classification',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: theme.colorScheme.primary),
                        ),
                        const SizedBox(height: 4),
                        Wrap(
                          spacing: 8,
                          runSpacing: 4,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            Text(
                              'Category:',
                              style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.7)),
                            ),
                            EchoSphereBadge.secondary(label: aiDetectedCategory),
                            Text(
                              'Priority:',
                              style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.7)),
                            ),
                            PopupMenuButton<String>(
                              tooltip: 'Change Priority Level',
                              initialValue: aiDetectedPriority,
                              onSelected: (val) {
                                setState(() {
                                  aiDetectedPriority = val;
                                });
                              },
                              itemBuilder: (ctx) => [
                                const PopupMenuItem(value: 'HIGH', child: Text('HIGH (Repeats 3x)')),
                                const PopupMenuItem(value: 'NORMAL', child: Text('NORMAL / MEDIUM (Repeats 2x)')),
                                const PopupMenuItem(value: 'LOW', child: Text('LOW (Repeats 1x)')),
                                if (user.role.toUpperCase() == 'HOD' || user.role.toUpperCase() == 'COLLEGE ADMIN' || user.role.toUpperCase() == 'PRINCIPAL' || user.role.toUpperCase().contains('ADMIN'))
                                  const PopupMenuItem(value: 'EMERGENCY', child: Text('EMERGENCY (Continuous Loop)')),
                              ],
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  EchoSphereBadge.priority(priority: aiDetectedPriority),
                                  const SizedBox(width: 4),
                                  Icon(Icons.arrow_drop_down_rounded, size: 16, color: theme.colorScheme.primary),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Attachments Upload Section
            const Text('Attachments (Documents & Images)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                OutlinedButton.icon(
                  onPressed: _pickAttachmentFiles,
                  icon: const Icon(Icons.attach_file_rounded, size: 16),
                  label: const Text('+ Attach Documents / Images', style: TextStyle(fontSize: 12)),
                ),
                ...attachedFiles.map((file) {
                  final ext = (file.extension ?? 'doc').toLowerCase();
                  final isPdf = ext == 'pdf';
                  final isExcel = ext == 'xlsx' || ext == 'xls' || ext == 'csv';
                  final isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'heic', 'tiff', 'ico'].contains(ext);

                  final iconData = isImage
                      ? Icons.image_rounded
                      : isPdf
                          ? Icons.picture_as_pdf_rounded
                          : isExcel
                              ? Icons.table_chart_rounded
                              : Icons.description_rounded;

                  final iconColor = theme.colorScheme.primary;

                  final sizeKb = (file.size / 1024).toStringAsFixed(0);

                  return InputChip(
                    avatar: Icon(
                      iconData,
                      color: iconColor,
                      size: 16,
                    ),
                    label: Text(
                      '${file.name} ($sizeKb KB)',
                      style: const TextStyle(fontSize: 11),
                    ),
                    onDeleted: () {
                      setState(() {
                        attachedFiles.remove(file);
                      });
                      snackBar('Removed ${file.name}');
                    },
                  );
                }),
              ],
            ),
            const SizedBox(height: 16),

            // Target Audience Selector
            const Text('Target Audience', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 6),
            EchoSphereDropdown(
              label: 'Audience',
              icon: Icons.groups_rounded,
              selectedItem: DropdownItem(value: selectedAudience, text: selectedAudience),
              items: audiences.map((a) => DropdownItem(value: a, text: a)).toList(),
              onChanged: (item) {
                setState(() => selectedAudience = item.value);
                final title = titleController.text.trim();
                final desc = descController.text.trim();
                if (desc.length > 15) {
                  _runAiValidation(title, desc);
                }
              },
            ),
            const SizedBox(height: 16),

            // Delivery Channels
            const Text('Delivery Channels', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilterChip(
                  label: const Text('In-App Feed', style: TextStyle(fontSize: 12)),
                  selected: deliverInApp,
                  onSelected: (val) => setState(() => deliverInApp = val),
                ),
                FilterChip(
                  label: const Text('Push Notification', style: TextStyle(fontSize: 12)),
                  selected: deliverPush,
                  onSelected: (val) => setState(() => deliverPush = val),
                ),
                FilterChip(
                  label: const Text('Speaker Announcement', style: TextStyle(fontSize: 12)),
                  selected: deliverSpeaker,
                  onSelected: (val) => setState(() => deliverSpeaker = val),
                ),
              ],
            ),
            if (deliverSpeaker) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: theme.colorScheme.primary.withOpacity(0.25)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.volume_up_rounded, size: 16, color: theme.colorScheme.primary),
                        const SizedBox(width: 6),
                        const Expanded(
                          child: Text(
                            'Target Speaker Node (Auto-plays if idle)',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        ChoiceChip(
                          label: const Text('All Nodes (College-Wide)', style: TextStyle(fontSize: 11)),
                          selected: selectedSpeakerNodeId == null,
                          onSelected: (val) {
                            if (val) setState(() => selectedSpeakerNodeId = null);
                          },
                        ),
                        ...availableSpeakerNodes.map((node) {
                          final nId = node['id'] as int?;
                          final nName = (node['name'] ?? 'Speaker #$nId').toString();
                          final isSel = selectedSpeakerNodeId == nId;
                          return ChoiceChip(
                            label: Text(nName, style: const TextStyle(fontSize: 11)),
                            selected: isSel,
                            onSelected: (val) {
                              setState(() => selectedSpeakerNodeId = val ? nId : null);
                            },
                          );
                        }),
                      ],
                    ),
                    const SizedBox(height: 10),
                    const Divider(height: 1),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Icon(Icons.record_voice_over_rounded, size: 16, color: theme.colorScheme.primary),
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
                          selected: speakerVoice == 'female',
                          onSelected: (val) {
                            if (val) setState(() => speakerVoice = 'female');
                          },
                        ),
                        ChoiceChip(
                          avatar: const Icon(Icons.male_rounded, size: 14),
                          label: const Text('Male Voice', style: TextStyle(fontSize: 11)),
                          selected: speakerVoice == 'male',
                          onSelected: (val) {
                            if (val) setState(() => speakerVoice = 'male');
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 14),

            // AI Smart Badges (Category & Priority)
            const Text('AI Category & Priority Recommendation', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                EchoSphereBadge.secondary(label: 'Category: $aiDetectedCategory'),
                PopupMenuButton<String>(
                  tooltip: 'Change Priority Level',
                  initialValue: aiDetectedPriority,
                  onSelected: (val) {
                    setState(() {
                      aiDetectedPriority = val;
                    });
                  },
                  itemBuilder: (ctx) => [
                    const PopupMenuItem(value: 'HIGH', child: Text('HIGH (Repeats 3x)')),
                    const PopupMenuItem(value: 'NORMAL', child: Text('NORMAL / MEDIUM (Repeats 2x)')),
                    const PopupMenuItem(value: 'LOW', child: Text('LOW (Repeats 1x)')),
                    if (user.role.toUpperCase() == 'HOD' || user.role.toUpperCase() == 'COLLEGE ADMIN' || user.role.toUpperCase() == 'PRINCIPAL' || user.role.toUpperCase().contains('ADMIN'))
                      const PopupMenuItem(value: 'EMERGENCY', child: Text('EMERGENCY (Continuous Loop)')),
                  ],
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      EchoSphereBadge.priority(priority: aiDetectedPriority),
                      const SizedBox(width: 4),
                      Icon(Icons.arrow_drop_down_rounded, size: 16, color: theme.colorScheme.primary),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),

            // Schedule Options
            const Text('Publish & Broadcast Timing', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ChoiceChip(
                  label: const Text('Publish Now', style: TextStyle(fontSize: 12)),
                  selected: !isScheduleLater,
                  onSelected: (val) => setState(() => isScheduleLater = !val),
                ),
                ChoiceChip(
                  label: const Text('Schedule Later (Max 2 Days)', style: TextStyle(fontSize: 12)),
                  selected: isScheduleLater,
                  onSelected: (val) => setState(() => isScheduleLater = val),
                ),
              ],
            ),
            if (isScheduleLater) ...[
              const SizedBox(height: 10),
              InkWell(
                onTap: _selectScheduleDateTime,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    border: Border.all(color: theme.colorScheme.primary.withOpacity(0.4)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.event_rounded, size: 18),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Scheduled for: ${formatCampusTime(scheduledDateTime, "MMM dd, yyyy \u2022 hh:mm a")}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                      ),
                      const Icon(Icons.edit_calendar_rounded, size: 16),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 14),

            // Repeat Announcement Schedule Section
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: enableRepeatSchedule
                    ? theme.colorScheme.primary.withOpacity(0.06)
                    : theme.colorScheme.surfaceContainer.withOpacity(0.35),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: enableRepeatSchedule
                      ? theme.colorScheme.primary.withOpacity(0.35)
                      : theme.dividerColor.withOpacity(0.2),
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
                          color: theme.colorScheme.primary.withOpacity(0.12),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(Icons.repeat_rounded, size: 18, color: theme.colorScheme.primary),
                      ),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Repeat Broadcast Schedule',
                              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                            ),
                            Text(
                              'Replay notice automatically across campus speakers',
                              style: TextStyle(fontSize: 10, color: Colors.grey),
                            ),
                          ],
                        ),
                      ),
                      Switch(
                        value: enableRepeatSchedule,
                        onChanged: (val) {
                          setState(() {
                            enableRepeatSchedule = val;
                            if (val) {
                              deliverSpeaker = true;
                            }
                          });
                        },
                      ),
                    ],
                  ),
                  if (enableRepeatSchedule) ...[
                    const SizedBox(height: 10),
                    const Divider(height: 1),
                    const SizedBox(height: 10),

                    // Preset Break Schedules
                    const Text('Campus Break Schedules:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11)),
                    const SizedBox(height: 6),
                    ListView.separated(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: _breakWindows.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 5),
                      itemBuilder: (ctx, idx) {
                        final bw = _breakWindows[idx];
                        final key = bw['key'] as String;
                        final isSelected = repeatSlots.contains(key);
                        return InkWell(
                          borderRadius: BorderRadius.circular(8),
                          onTap: () {
                            setState(() {
                              if (isSelected) {
                                repeatSlots.remove(key);
                              } else {
                                repeatSlots.add(key);
                              }
                            });
                          },
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: isSelected
                                  ? theme.colorScheme.primary.withOpacity(0.1)
                                  : theme.colorScheme.surfaceContainer.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: isSelected
                                    ? theme.colorScheme.primary
                                    : theme.dividerColor.withOpacity(0.2),
                                width: isSelected ? 1.5 : 1.0,
                              ),
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  bw['icon'] as IconData,
                                  size: 16,
                                  color: isSelected ? theme.colorScheme.primary : theme.hintColor,
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        bw['title'] as String,
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                                          color: isSelected ? theme.colorScheme.primary : null,
                                        ),
                                      ),
                                      Text(
                                        '${bw['time']} • ${bw['duration']}',
                                        style: TextStyle(
                                          fontSize: 9,
                                          color: theme.textTheme.bodySmall?.color?.withOpacity(0.7),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Checkbox(
                                  value: isSelected,
                                  onChanged: (val) {
                                    setState(() {
                                      if (val == true) {
                                        repeatSlots.add(key);
                                      } else {
                                        repeatSlots.remove(key);
                                      }
                                    });
                                  },
                                  activeColor: theme.colorScheme.primary,
                                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                  visualDensity: VisualDensity.compact,
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),

                    const SizedBox(height: 8),

                    // Custom Time Window Option
                    InkWell(
                      borderRadius: BorderRadius.circular(8),
                      onTap: () {
                        setState(() {
                          if (repeatSlots.contains('CUSTOM_WINDOW')) {
                            repeatSlots.remove('CUSTOM_WINDOW');
                          } else {
                            repeatSlots.add('CUSTOM_WINDOW');
                          }
                        });
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                        decoration: BoxDecoration(
                          color: repeatSlots.contains('CUSTOM_WINDOW')
                              ? theme.colorScheme.primary.withOpacity(0.1)
                              : theme.colorScheme.surfaceContainer.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: repeatSlots.contains('CUSTOM_WINDOW')
                                ? theme.colorScheme.primary
                                : theme.dividerColor.withOpacity(0.2),
                            width: repeatSlots.contains('CUSTOM_WINDOW') ? 1.5 : 1.0,
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.access_time_filled_rounded,
                              size: 16,
                              color: repeatSlots.contains('CUSTOM_WINDOW')
                                  ? theme.colorScheme.primary
                                  : theme.hintColor,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Custom Time Window',
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: repeatSlots.contains('CUSTOM_WINDOW')
                                          ? FontWeight.bold
                                          : FontWeight.w600,
                                      color: repeatSlots.contains('CUSTOM_WINDOW')
                                          ? theme.colorScheme.primary
                                          : null,
                                    ),
                                  ),
                                  Text(
                                    'Define custom start and end time range for repeats',
                                    style: TextStyle(
                                      fontSize: 9,
                                      color: theme.textTheme.bodySmall?.color?.withOpacity(0.7),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Checkbox(
                              value: repeatSlots.contains('CUSTOM_WINDOW'),
                              onChanged: (val) {
                                setState(() {
                                  if (val == true) {
                                    repeatSlots.add('CUSTOM_WINDOW');
                                  } else {
                                    repeatSlots.remove('CUSTOM_WINDOW');
                                  }
                                });
                              },
                              activeColor: theme.colorScheme.primary,
                              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              visualDensity: VisualDensity.compact,
                            ),
                          ],
                        ),
                      ),
                    ),

                    if (repeatSlots.contains('CUSTOM_WINDOW')) ...[
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.surfaceContainer.withOpacity(0.35),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: theme.colorScheme.primary.withOpacity(0.25)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Set Repeat Window (Start – End)',
                              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 6),
                            Row(
                              children: [
                                Expanded(
                                  child: InkWell(
                                    onTap: () => _pickRepeatTime(isStart: true),
                                    child: AbsorbPointer(
                                      child: TextField(
                                        controller: repeatStartCtrl,
                                        decoration: const InputDecoration(
                                          labelText: 'Start Time',
                                          hintText: '10:00',
                                          isDense: true,
                                          suffixIcon: Icon(Icons.schedule_rounded, size: 15),
                                          border: OutlineInputBorder(),
                                        ),
                                        style: const TextStyle(fontSize: 11),
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: InkWell(
                                    onTap: () => _pickRepeatTime(isStart: false),
                                    child: AbsorbPointer(
                                      child: TextField(
                                        controller: repeatEndCtrl,
                                        decoration: const InputDecoration(
                                          labelText: 'End Time',
                                          hintText: '11:00',
                                          isDense: true,
                                          suffixIcon: Icon(Icons.schedule_rounded, size: 15),
                                          border: OutlineInputBorder(),
                                        ),
                                        style: const TextStyle(fontSize: 11),
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            // Calculated Repeat Window Range Badge
                            Builder(
                              builder: (ctx) {
                                final customRangeInfo = _calculateCustomWindowDuration(
                                  repeatStartCtrl.text,
                                  repeatEndCtrl.text,
                                );
                                return Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: customRangeInfo['isValid'] == true
                                        ? theme.colorScheme.primary.withOpacity(0.08)
                                        : Colors.orange.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(6),
                                    border: Border.all(
                                      color: customRangeInfo['isValid'] == true
                                          ? theme.colorScheme.primary.withOpacity(0.3)
                                          : Colors.orange.withOpacity(0.3),
                                    ),
                                  ),
                                  child: Row(
                                    children: [
                                      Icon(
                                        customRangeInfo['isValid'] == true
                                            ? Icons.timelapse_rounded
                                            : Icons.warning_amber_rounded,
                                        size: 14,
                                        color: customRangeInfo['isValid'] == true
                                            ? theme.colorScheme.primary
                                            : Colors.orange,
                                      ),
                                      const SizedBox(width: 6),
                                      Expanded(
                                        child: Text(
                                          customRangeInfo['isValid'] == true
                                              ? 'Calculated Repeat Window: ${customRangeInfo['displayRange']} • ${customRangeInfo['duration']}'
                                              : '${customRangeInfo['message']}',
                                          style: TextStyle(
                                            fontSize: 10,
                                            fontWeight: FontWeight.w600,
                                            color: customRangeInfo['isValid'] == true
                                                ? theme.colorScheme.primary
                                                : Colors.orange.shade800,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                    ],

                    if (!isScheduleLater) ...[
                      const SizedBox(height: 8),
                      InkWell(
                        onTap: () => setState(() => repeatPlayOnPublish = !repeatPlayOnPublish),
                        borderRadius: BorderRadius.circular(8),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            children: [
                              Checkbox(
                                value: repeatPlayOnPublish,
                                onChanged: (val) => setState(() => repeatPlayOnPublish = val ?? true),
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                visualDensity: VisualDensity.compact,
                                activeColor: theme.colorScheme.primary,
                              ),
                              const SizedBox(width: 4),
                              const Expanded(
                                child: Text(
                                  'Broadcast immediately on publish, then repeat during selected windows',
                                  style: TextStyle(fontSize: 11),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],

                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary.withOpacity(0.06),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: theme.colorScheme.primary.withOpacity(0.2)),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.info_outline_rounded, size: 14, color: theme.colorScheme.primary),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              repeatSlots.isEmpty
                                  ? 'Please select at least one break schedule or custom time window.'
                                  : 'Notice will automatically repeat during the selected break windows on campus speakers.',
                              style: TextStyle(fontSize: 10, color: theme.colorScheme.primary, fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
      onConfirm: () async {
        final title = titleController.text.trim();
        var desc = descController.text.trim();

        if (title.isEmpty || desc.isEmpty) {
          errorSnackBar('Title and description cannot be empty.');
          return;
        }

        // Automatic text expansion for short messages (< 80 chars)
        if (desc.length < 80) {
          desc =
              'This is an official announcement to inform all concerned that $desc. Please strictly adhere to these instructions and check the portal for updates.';
        }

        if (isScheduleLater) {
          final now = DateTime.now();
          final maxDate = now.add(const Duration(days: 2));
          if (scheduledDateTime.isAfter(maxDate)) {
            errorSnackBar('Scheduling Policy: Announcements cannot be scheduled more than 2 days in advance.');
            return;
          }
          if (scheduledDateTime.isBefore(now.add(const Duration(minutes: 5)))) {
            errorSnackBar('Scheduling Policy: Scheduled broadcast time must be at least 5 minutes in the future.');
            return;
          }
        }

        Map<String, dynamic>? repeatData;
        if (enableRepeatSchedule) {
          final now = DateTime.now();
          if (repeatSlots.isEmpty) {
            errorSnackBar('Please select at least one break schedule or custom time window.');
            return;
          }

          String? normStart;
          String? normEnd;
          if (repeatSlots.contains('CUSTOM_WINDOW')) {
            normStart = _normalizeRepeatTime(repeatStartCtrl.text);
            normEnd = _normalizeRepeatTime(repeatEndCtrl.text);
            final rangeInfo = _calculateCustomWindowDuration(normStart, normEnd);
            if (rangeInfo['isValid'] != true) {
              errorSnackBar(rangeInfo['message'] as String? ?? 'Invalid custom time window');
              return;
            }
            repeatStartCtrl.text = normStart;
            repeatEndCtrl.text = normEnd;
          }

          repeatData = {
            'is_active': true,
            'repeat_mode': 'BREAK_SLOTS',
            'interval_minutes': 0,
            'max_repeats': repeatSlots.length * 5 + (!isScheduleLater && repeatPlayOnPublish ? 1 : 0),
            'play_on_publish': !isScheduleLater && repeatPlayOnPublish,
            'selected_slots': repeatSlots.toList(),
            'target_scope': 'COLLEGE_WIDE',
            'event_datetime': now.add(const Duration(hours: 24)).toUtc().toIso8601String(),
            'start_date': now.subtract(const Duration(minutes: 5)).toUtc().toIso8601String(),
            'end_date': now.add(const Duration(hours: 48)).toUtc().toIso8601String(),
            'force_enable_speaker': true,
            if (repeatSlots.contains('CUSTOM_WINDOW') && normStart != null && normEnd != null) ...{
              'custom_start_time': normStart,
              'custom_end_time': normEnd,
            },
          };
        }

        final isTeacher = user.role == 'Teacher';
        final isHod = user.role == 'HoD';
        final target = selectedAudience.trim().toLowerCase();
        final userDept = (user.department ?? 'AIML').trim().toLowerCase();
        final isHodCrossDept = isHod && (!target.contains(userDept) || target.contains('entire') || target.contains('all'));

        String statusMessage = '';
        if (isTeacher) {
          statusMessage = isScheduleLater
              ? 'Notice submitted for HoD/Principal approval (Scheduled for ${formatCampusTime(scheduledDateTime, "MMM dd, yyyy \u2022 hh:mm a")})!'
              : 'Notice submitted for HoD/Principal approval!';
        } else if (isHodCrossDept) {
          statusMessage = isScheduleLater
              ? 'Institution-wide notice submitted for Principal/College Admin approval (Scheduled for ${formatCampusTime(scheduledDateTime, "MMM dd, yyyy \u2022 hh:mm a")})!'
              : 'Institution-wide notice submitted for Principal/College Admin approval!';
        } else if (isScheduleLater) {
          statusMessage = 'Announcement scheduled for ${formatCampusTime(scheduledDateTime, "MMM dd, yyyy \u2022 hh:mm a")}!';
        } else {
          statusMessage = deliverSpeaker
              ? 'Notice published and queued for speaker broadcast!'
              : 'Notice published successfully to $selectedAudience!';
        }

        // Upload the attached files first: the notice keeps their cloud links (only names were kept before)
        final uploaded = <NoticeAttachment>[];
        for (final f in attachedFiles) {
          if (f.bytes == null) {
            errorSnackBar('Could not read "${f.name}". Please attach it again.');
            return;
          }
          if (f.size > 10 * 1024 * 1024) {
            errorSnackBar('"${f.name}" is larger than 10 MB.');
            return;
          }
          try {
            uploaded.add(NoticeAttachment.fromJson(await EchosphereApiService().uploadAttachment(f.name, f.bytes!)));
          } catch (e) {
            errorSnackBar(e.toString().replaceAll('Exception: ', ''));
            return;
          }
        }

        final ok = await annController.createAnnouncement(
          title: title,
          description: desc,
          category: aiDetectedCategory,
          priority: aiDetectedPriority,
          creatorRole: user.role,
          creatorName: user.fullName,
          department: user.department ?? 'AIML',
          targetAudience: selectedAudience,
          isScheduleLater: isScheduleLater,
          scheduledDateTime: scheduledDateTime,
          deliverSpeaker: deliverSpeaker || isScheduleLater || repeatData != null,
          deliverInApp: deliverInApp,
          deliverPush: deliverPush,
          speakerVoice: speakerVoice,
          speakerNodeId: selectedSpeakerNodeId,
          attachments: uploaded,
          repeatSchedule: repeatData,
        );

        if (ok) {
          if (Get.isRegistered<SpeakerQueueController>()) {
            final SpeakerQueueController queueCtrl = Get.find<SpeakerQueueController>();
            queueCtrl.refreshQueue(silent: false);
          }
          snackBar(statusMessage);
        }
      },
    );
  }

  void _applyAlternativeSlot(Map<String, dynamic> slot) {
    final label = slot['label'] as String? ?? '';
    final venue = slot['venue'] as String?;
    final startTimeStr = slot['start_time'] as String?;

    DateTime? newStart;
    if (startTimeStr != null) {
      newStart = parseServerTime(startTimeStr)?.toLocal();
    }

    if (newStart != null) {
      setState(() {
        scheduledDateTime = newStart!;
      });
    }

    var currentText = descController.text;
    final conflicts = (activeConflictReport?['conflicts'] as List?)?.whereType<Map>().toList() ?? [];
    final firstConflict = conflicts.isNotEmpty ? conflicts.first : null;

    final oldVenue = firstConflict?['conflicting_venue'] as String?;
    final cleanSlotTime = label.split(' (').first;

    if (slot['slot_type'] == 'alternative_venue' && venue != null) {
      if (oldVenue != null && currentText.contains(oldVenue)) {
        currentText = currentText.replaceAll(oldVenue, venue);
      } else {
        currentText = '$currentText\n(Venue updated to: $venue)';
      }
    } else {
      final timeRegex = RegExp(r'\b(1[0-2]|0?[1-9])(?::([0-5][0-9]))?\s*(AM|PM|am|pm)\b', caseSensitive: false);
      if (timeRegex.hasMatch(currentText)) {
        final replacementTime = cleanSlotTime.split(' - ').first.split(', ').last;
        currentText = currentText.replaceFirst(timeRegex, replacementTime);
        currentText = '$currentText [Rescheduled: $label]';
      } else {
        currentText = '$currentText\n[Rescheduled: $label]';
      }
    }

    _isResolvingConflict = true;
    setState(() {
      descController.text = currentText.trim();
      activeConflictReport = null;
    });
    Future.microtask(() => _isResolvingConflict = false);

    snackBar('Applied alternative time slot: $label', title: 'Schedule Conflict Resolved');
  }

  Widget _buildScheduleConflictCard(ThemeData theme) {
    if (activeConflictReport == null) return const SizedBox.shrink();
    final conflicts = (activeConflictReport!['conflicts'] as List?)?.whereType<Map>().toList() ?? [];
    final alternatives = (activeConflictReport!['suggested_alternatives'] as List?)?.whereType<Map>().toList() ?? [];
    if (conflicts.isEmpty) return const SizedBox.shrink();

    final accentColor = theme.colorScheme.primary;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accentColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accentColor.withOpacity(0.4), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.event_busy_rounded, size: 18, color: accentColor),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Schedule Conflict Detected',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: accentColor,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: accentColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  '${conflicts.length} Overlap',
                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: accentColor),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...conflicts.map((c) {
            final msg = c['conflict_message'] as String? ?? 'Conflict detected with existing circular.';
            return Padding(
              padding: const EdgeInsets.only(bottom: 6.0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('\u2022 ', style: TextStyle(color: accentColor, fontWeight: FontWeight.bold)),
                  Expanded(
                    child: Text(
                      msg,
                      style: const TextStyle(fontSize: 11, height: 1.3),
                    ),
                  ),
                ],
              ),
            );
          }),
          if (alternatives.isNotEmpty) ...[
            const SizedBox(height: 6),
            Row(
              children: [
                Icon(Icons.auto_awesome, size: 14, color: theme.colorScheme.primary),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Suggest Alternative Time Slots:',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.onSurface.withOpacity(0.9),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: alternatives.map((alt) {
                final label = alt['label'] as String? ?? 'Alternative Slot';
                final isAltVenue = alt['slot_type'] == 'alternative_venue';
                return ActionChip(
                  avatar: Icon(
                    isAltVenue ? Icons.room_preferences_rounded : Icons.calendar_month_rounded,
                    size: 13,
                    color: theme.colorScheme.primary,
                  ),
                  label: Text(
                    label,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  backgroundColor: theme.colorScheme.primary.withOpacity(0.08),
                  side: BorderSide(color: theme.colorScheme.primary.withOpacity(0.3)),
                  onPressed: () => _applyAlternativeSlot(Map<String, dynamic>.from(alt)),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAudienceWarningCard(ThemeData theme) {
    if (activeAudienceWarning == null) return const SizedBox.shrink();
    final warningMsg = activeAudienceWarning!['warning_message'] as String? ?? 'Audience mismatch detected.';
    final suggested = (activeAudienceWarning!['suggested_audiences'] as List?)?.whereType<String>().toList() ?? [];
    final accentColor = theme.colorScheme.primary;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accentColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accentColor.withOpacity(0.4), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.groups_rounded, size: 18, color: accentColor),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Audience Recommendation (Anti-Spam Guard)',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: accentColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            warningMsg,
            style: const TextStyle(fontSize: 11, height: 1.3),
          ),
          if (suggested.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(Icons.auto_awesome, size: 13, color: accentColor),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    '1-Tap Audience Narrowing:',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.onSurface.withOpacity(0.9),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: suggested.map((target) {
                return ActionChip(
                  avatar: Icon(Icons.gps_fixed_rounded, size: 13, color: accentColor),
                  label: Text(
                    'Narrow to: $target',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: accentColor,
                    ),
                  ),
                  backgroundColor: accentColor.withOpacity(0.08),
                  side: BorderSide(color: accentColor.withOpacity(0.3)),
                  onPressed: () {
                    setState(() {
                      selectedAudience = target;
                      activeAudienceWarning = null;
                    });
                    snackBar('Target audience narrowed to $target!', title: 'Anti-Spam Guard');
                  },
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}
