import 'dart:io';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/echosphere_ai_controller.dart';
import 'package:anymex/controllers/speaker_queue_controller.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dialog.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_dropdown.dart';
import 'package:anymex/widgets/custom_widgets/voice_dictation_sheet.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

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
  bool deliverSpeaker = true;
  String speakerVoice = 'female';
  int? selectedSpeakerNodeId;
  List<Map<String, dynamic>> availableSpeakerNodes = [];

  bool isScheduleLater = false;
  DateTime scheduledDateTime = DateTime.now().add(const Duration(hours: 1));

  bool isAiExpanding = false;
  bool isAiPolishing = false;
  bool isAiDrafting = false;
  bool isAiScanningDoc = false;

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

  Future<void> _pickAttachmentFiles() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        allowMultiple: true,
        type: FileType.custom,
        allowedExtensions: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'txt', 'png', 'jpg', 'jpeg', 'webp'],
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
      snackBar('Voice note transformed into official institutional circular!', title: '🎙️ Voice Notice Dictation');
    }
  }

  Future<void> _scanAndOcrDocument() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg', 'webp'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) return;

      final file = result.files.first;
      setState(() => isAiScanningDoc = true);

      List<int>? bytes = file.bytes;
      if (bytes == null && file.path != null) {
        bytes = await File(file.path!).readAsBytes();
      }

      if (bytes == null || bytes.isEmpty) {
        errorSnackBar('Could not read document bytes.');
        return;
      }

      final ext = file.extension?.toLowerCase() ?? 'jpg';
      final mimeType = ext == 'pdf' ? 'application/pdf' : 'image/$ext';

      final ocrRes = await EchosphereApiService().ocrDocumentToNotice(
        fileBytes: bytes,
        mimeType: mimeType,
        filename: file.name,
      );

      if (mounted) {
        setState(() {
          // Attach original scanned file so students/faculty can access it
          if (!attachedFiles.any((f) => f.name == file.name)) {
            attachedFiles.add(file);
          }

          if (ocrRes['title'] != null && ocrRes['title'].toString().isNotEmpty) {
            titleController.text = ocrRes['title'].toString();
          }
          if (ocrRes['content'] != null && ocrRes['content'].toString().isNotEmpty) {
            descController.text = ocrRes['content'].toString();
          }
          if (ocrRes['suggested_category'] != null) {
            aiDetectedCategory = ocrRes['suggested_category'].toString();
          }
          if (ocrRes['suggested_priority'] != null) {
            aiDetectedPriority = ocrRes['suggested_priority'].toString();
          }
          if (ocrRes['suggested_audience'] != null) {
            final aud = ocrRes['suggested_audience'].toString();
            if (audiences.contains(aud)) {
              selectedAudience = aud;
            }
          }
        });

        snackBar('Scanned circular auto-digitized & original document attached!', title: '📄 Document OCR Digitizer');
      }
    } catch (e) {
      errorSnackBar('Document scanning failed: $e');
    } finally {
      if (mounted) setState(() => isAiScanningDoc = false);
    }
  }

  @override
  void dispose() {
    titleController.removeListener(_autoDetectAndValidate);
    descController.removeListener(_autoDetectAndValidate);
    titleController.dispose();
    descController.dispose();
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

  Future<void> _expandWithAi() async {
    final desc = descController.text.trim();
    if (desc.isEmpty) {
      errorSnackBar('Please enter a brief note first.');
      return;
    }

    setState(() => isAiExpanding = true);

    try {
      final res = await EchosphereApiService().expandText(desc, category: aiDetectedCategory);
      final expandedText = res['expanded_text'] as String?;
      if (mounted && expandedText != null && expandedText.isNotEmpty) {
        setState(() {
          descController.text = expandedText;
        });
        snackBar('AI expanded your announcement into an official circular.', title: 'AI Expander');
      }
    } catch (_) {
      final fallbackExpanded =
          'This is an official announcement to inform all concerned that $desc. Please strictly adhere to these instructions and check the portal for updates.';
      if (mounted) {
        setState(() {
          descController.text = fallbackExpanded;
        });
        snackBar('AI expanded your announcement text.', title: 'AI Expander');
      }
    } finally {
      if (mounted) setState(() => isAiExpanding = false);
    }
  }

  Future<void> _polishGrammar() async {
    final desc = descController.text.trim();
    if (desc.isEmpty) return;

    setState(() => isAiPolishing = true);

    try {
      final res = await EchosphereApiService().grammarCheck(desc);
      final corrected = res['corrected_text'] as String?;
      if (mounted && corrected != null) {
        setState(() {
          descController.text = corrected;
        });
        snackBar('Grammar and professional tone refined by AI.', title: 'AI Tone & Grammar');
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => isAiPolishing = false);
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
        contentWidget: const Padding(
          padding: EdgeInsets.all(16.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.gpp_bad_rounded, color: Colors.redAccent, size: 40),
              SizedBox(height: 12),
              Text(
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
            // AI Fast Intake Studio (Voice Dictation & Document OCR)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              margin: const EdgeInsets.only(bottom: 14),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    const Color(0xFF6366F1).withOpacity(0.12),
                    const Color(0xFF8B5CF6).withOpacity(0.06),
                  ],
                ),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: const Color(0xFF6366F1).withOpacity(0.25),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Flexible(
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.auto_awesome, size: 14, color: Color(0xFF818CF8)),
                            SizedBox(width: 6),
                            Flexible(
                              child: Text(
                                'AI Fast Intake Studio',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Color(0xFF818CF8)),
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (isAiScanningDoc)
                        const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF818CF8)),
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
                        label: const Text('🎙️ Voice Dictate', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF4F46E5),
                          foregroundColor: Colors.white,
                          visualDensity: VisualDensity.compact,
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),
                      OutlinedButton.icon(
                        key: const Key('scan_ocr_button'),
                        onPressed: isAiScanningDoc ? null : _scanAndOcrDocument,
                        icon: const Icon(Icons.document_scanner_rounded, size: 14),
                        label: Text(
                          isAiScanningDoc ? 'Scanning Doc...' : '📄 Scan / OCR Notice',
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                        ),
                        style: OutlinedButton.styleFrom(
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
                  avatar: const Icon(Icons.auto_awesome, size: 14, color: Colors.amber),
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
            // Description Header with AI Tools
            Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 8,
              runSpacing: 6,
              children: [
                const Text('Announcement Content', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: [
                    if (textLength >= 10)
                      ActionChip(
                        avatar: const Icon(Icons.spellcheck_rounded, size: 14, color: Color(0xFF60A5FA)),
                        label: isAiPolishing
                            ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Text('Grammar', style: TextStyle(fontSize: 11)),
                        onPressed: isAiPolishing ? null : _polishGrammar,
                      ),
                    ActionChip(
                      avatar: const Icon(Icons.auto_awesome, size: 14, color: Colors.amber),
                      label: isAiExpanding
                          ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('AI Expand', style: TextStyle(fontSize: 11)),
                      onPressed: isAiExpanding ? null : _expandWithAi,
                    ),
                  ],
                ),
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
                  color: Colors.amber.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.amber.withOpacity(0.4)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.warning_amber_rounded, size: 16, color: Colors.amber),
                        SizedBox(width: 6),
                        Expanded(
                          child: Text('AI Content Assistance Warnings',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.amber)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    if (aiValidationWarning != null)
                      Text('• $aiValidationWarning', style: const TextStyle(fontSize: 11)),
                    if (aiSpamWarning != null)
                      Text('• Spam Alert: $aiSpamWarning', style: const TextStyle(fontSize: 11, color: Color(0xFFF87171))),
                    if (aiDuplicateWarning != null)
                      Text('• Duplicate Alert: $aiDuplicateWarning', style: const TextStyle(fontSize: 11, color: Color(0xFFFB923C))),
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
                  const Icon(Icons.auto_awesome, size: 18, color: Colors.amber),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'AI Auto-Classification',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.amber),
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
                            EchoSphereChip(label: aiDetectedCategory, isSelected: true, onSelected: (_) {}),
                            Text(
                              'Priority:',
                              style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.7)),
                            ),
                            EchoSphereChip(label: aiDetectedPriority, isSelected: true, onSelected: (_) {}),
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

                  final iconColor = isImage
                      ? const Color(0xFFC084FC)
                      : isPdf
                          ? const Color(0xFFF87171)
                          : isExcel
                              ? const Color(0xFF34D399)
                              : const Color(0xFF60A5FA);

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
                EchoSphereChip(label: 'Category: $aiDetectedCategory', isSelected: true, onSelected: (_) {}),
                EchoSphereChip(
                  label: 'Priority: $aiDetectedPriority',
                  isSelected: aiDetectedPriority == 'EMERGENCY' || aiDetectedPriority == 'HIGH',
                  onSelected: (_) {},
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
                          'Scheduled for: ${DateFormat("MMM dd, yyyy • hh:mm a").format(scheduledDateTime)}',
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

        final isTeacher = user.role == 'Teacher';
        final isHod = user.role == 'HoD';
        final target = selectedAudience.trim().toLowerCase();
        final userDept = (user.department ?? 'AIML').trim().toLowerCase();
        final isHodCrossDept = isHod && (!target.contains(userDept) || target.contains('entire') || target.contains('all'));

        String statusMessage = '';
        if (isTeacher) {
          statusMessage = isScheduleLater
              ? 'Notice submitted for HoD/Principal approval (Scheduled for ${DateFormat("MMM dd, yyyy • hh:mm a").format(scheduledDateTime)})!'
              : 'Notice submitted for HoD/Principal approval!';
        } else if (isHodCrossDept) {
          statusMessage = isScheduleLater
              ? 'Institution-wide notice submitted for Principal/College Admin approval (Scheduled for ${DateFormat("MMM dd, yyyy • hh:mm a").format(scheduledDateTime)})!'
              : 'Institution-wide notice submitted for Principal/College Admin approval!';
        } else if (isScheduleLater) {
          statusMessage = 'Announcement scheduled for ${DateFormat("MMM dd, yyyy • hh:mm a").format(scheduledDateTime)}!';
        } else {
          statusMessage = deliverSpeaker
              ? 'Notice published and queued for speaker broadcast!'
              : 'Notice published successfully to $selectedAudience!';
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
          deliverSpeaker: deliverSpeaker,
          deliverInApp: deliverInApp,
          deliverPush: deliverPush,
          speakerVoice: speakerVoice,
          speakerNodeId: selectedSpeakerNodeId,
          attachments: attachedFiles.map((f) => f.name).toList(),
        );

        if (ok) {
          if (Get.isRegistered<SpeakerQueueController>()) {
            final SpeakerQueueController queueCtrl = Get.find<SpeakerQueueController>();
            queueCtrl.refreshQueue(silent: false);
            if (deliverSpeaker && !isScheduleLater && !queueCtrl.isPlaying.value) {
              Future.delayed(const Duration(milliseconds: 300), () {
                if (!queueCtrl.isPlaying.value && queueCtrl.queueItems.isNotEmpty) {
                  queueCtrl.togglePlayPause(index: 0);
                }
              });
            }
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
      newStart = DateTime.tryParse(startTimeStr);
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

    final isSevere = conflicts.any((c) => c['conflict_type'] == 'venue_collision');
    final accentColor = isSevere ? const Color(0xFFEF4444) : Colors.amber;

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
                  Text('• ', style: TextStyle(color: accentColor, fontWeight: FontWeight.bold)),
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
                const Icon(Icons.auto_awesome, size: 14, color: Colors.amber),
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

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.amber.withOpacity(0.4), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.groups_rounded, size: 18, color: Colors.amber),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Audience Recommendation (Anti-Spam Guard)',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: Colors.amber,
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
                const Icon(Icons.auto_awesome, size: 13, color: Colors.amber),
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
                  avatar: const Icon(Icons.gps_fixed_rounded, size: 13, color: Color(0xFF10B981)),
                  label: Text(
                    'Narrow to: $target',
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF10B981),
                    ),
                  ),
                  backgroundColor: const Color(0xFF10B981).withOpacity(0.08),
                  side: BorderSide(color: const Color(0xFF10B981).withOpacity(0.3)),
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
