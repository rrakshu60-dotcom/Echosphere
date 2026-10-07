import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/utils/theme_extensions.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

/// Interactive dialog to configure, modify, view logs, test, and remove
/// automated repeat announcement broadcasts for speaker queue playback.
class RepeatScheduleDialog extends StatefulWidget {
  final int? announcementId;
  final String? announcementTitle;
  final Map<String, dynamic>? initialSchedule;
  final ValueChanged<Map<String, dynamic>>? onScheduleSaved;
  final VoidCallback? onScheduleDeleted;

  const RepeatScheduleDialog({
    super.key,
    this.announcementId,
    this.announcementTitle,
    this.initialSchedule,
    this.onScheduleSaved,
    this.onScheduleDeleted,
  });

  static Future<void> show(
    BuildContext context, {
    int? announcementId,
    String? announcementTitle,
    Map<String, dynamic>? initialSchedule,
    ValueChanged<Map<String, dynamic>>? onScheduleSaved,
    VoidCallback? onScheduleDeleted,
  }) {
    return showDialog(
      context: context,
      barrierDismissible: true,
      builder: (ctx) => RepeatScheduleDialog(
        announcementId: announcementId,
        announcementTitle: announcementTitle,
        initialSchedule: initialSchedule,
        onScheduleSaved: onScheduleSaved,
        onScheduleDeleted: onScheduleDeleted,
      ),
    );
  }

  @override
  State<RepeatScheduleDialog> createState() => _RepeatScheduleDialogState();
}

class _RepeatScheduleDialogState extends State<RepeatScheduleDialog> {
  final Set<String> _selectedSlots = {'SHORT_BREAK'};
  String _selectedScope = 'DEPARTMENT';
  late final TextEditingController _customStartCtrl;
  late final TextEditingController _customEndCtrl;

  bool _isLoading = false;
  bool _isSaving = false;
  bool _isDeleting = false;
  bool _isTestingSlot = false;
  Map<String, dynamic>? _loadedSchedule;

  bool get _isStudent {
    final auth = Get.isRegistered<AuthController>() ? Get.find<AuthController>() : null;
    return (auth?.currentUser.value?.role ?? 'Student').toLowerCase() == 'student';
  }

  @override
  void initState() {
    super.initState();
    _customStartCtrl = TextEditingController(text: '10:00');
    _customEndCtrl = TextEditingController(text: '11:00');

    if (widget.initialSchedule != null) {
      _applyScheduleData(widget.initialSchedule!);
    } else if (widget.announcementId != null) {
      _fetchSchedule();
    }
  }

  @override
  void dispose() {
    _customStartCtrl.dispose();
    _customEndCtrl.dispose();
    super.dispose();
  }

  void _applyScheduleData(Map<String, dynamic> data) {
    _loadedSchedule = data;
    final slots = (data['selected_slots'] as List?)?.map((e) => e.toString()).toList();
    if (slots != null && slots.isNotEmpty) {
      _selectedSlots.clear();
      _selectedSlots.addAll(slots);
    }
    if (data['target_scope'] != null) {
      _selectedScope = data['target_scope'].toString();
    }
    if (data['custom_start_time'] != null) {
      _customStartCtrl.text = data['custom_start_time'].toString();
    }
    if (data['custom_end_time'] != null) {
      _customEndCtrl.text = data['custom_end_time'].toString();
    }
  }

  Future<void> _fetchSchedule() async {
    if (widget.announcementId == null) return;
    setState(() => _isLoading = true);
    try {
      final schedule = await EchosphereApiService().getRepeatSchedule(widget.announcementId!);
      if (mounted) {
        setState(() {
          _isLoading = false;
          if (schedule != null) {
            _applyScheduleData(schedule);
          }
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _pickTime({required bool isStart}) async {
    final currentStr = isStart ? _customStartCtrl.text : _customEndCtrl.text;
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
      helpText: isStart ? 'Select Custom Window Start Time' : 'Select Custom Window End Time',
    );

    if (picked != null && mounted) {
      final h = picked.hour.toString().padLeft(2, '0');
      final m = picked.minute.toString().padLeft(2, '0');
      setState(() {
        if (isStart) {
          _customStartCtrl.text = '$h:$m';
        } else {
          _customEndCtrl.text = '$h:$m';
        }
      });
    }
  }

  Future<void> _handleSave() async {
    if (_isStudent) {
      errorSnackBar('Permission Denied: Students cannot configure or modify repeat schedules.');
      return;
    }
    if (_selectedSlots.isEmpty) {
      errorSnackBar('Please select at least one repeat broadcast slot.');
      return;
    }

    if (_selectedSlots.contains('CUSTOM_WINDOW')) {
      final start = _customStartCtrl.text.trim();
      final end = _customEndCtrl.text.trim();
      final timeRegex = RegExp(r'^([01]\d|2[0-3]):[0-5]\d$');
      if (!timeRegex.hasMatch(start) || !timeRegex.hasMatch(end)) {
        errorSnackBar('Please enter valid 24-hr times in HH:MM format (e.g. 10:30).');
        return;
      }
      if (start.compareTo(end) >= 0) {
        errorSnackBar('Custom Window start time must be before end time.');
        return;
      }
    }

    final now = DateTime.now();
    final payload = <String, dynamic>{
      'selected_slots': _selectedSlots.toList(),
      'target_scope': _selectedScope,
      'event_datetime': now.add(const Duration(hours: 24)).toIso8601String(),
      'start_date': now.toIso8601String(),
      'end_date': now.add(const Duration(hours: 48)).toIso8601String(),
      'force_enable_speaker': true,
      if (_selectedSlots.contains('CUSTOM_WINDOW')) ...{
        'custom_start_time': _customStartCtrl.text.trim(),
        'custom_end_time': _customEndCtrl.text.trim(),
      },
    };

    if (widget.announcementId != null) {
      setState(() => _isSaving = true);
      try {
        final res = await EchosphereApiService().setRepeatSchedule(widget.announcementId!, payload);
        if (mounted) {
          setState(() {
            _isSaving = false;
            _loadedSchedule = res;
          });
          widget.onScheduleSaved?.call(res);
          snackBar('Repeat broadcast schedule successfully saved!');
          Navigator.of(context).pop();
        }
      } catch (e) {
        if (mounted) {
          setState(() => _isSaving = false);
          errorSnackBar('Failed to save repeat schedule: ${e.toString().replaceAll("Exception: ", "")}');
        }
      }
    } else {
      widget.onScheduleSaved?.call(payload);
      Navigator.of(context).pop();
    }
  }

  Future<void> _handleDelete() async {
    if (_isStudent) {
      errorSnackBar('Permission Denied: Students cannot remove repeat schedules.');
      return;
    }
    if (widget.announcementId == null) return;
    setState(() => _isDeleting = true);
    try {
      await EchosphereApiService().deleteRepeatSchedule(widget.announcementId!);
      if (mounted) {
        setState(() {
          _isDeleting = false;
          _loadedSchedule = null;
        });
        widget.onScheduleDeleted?.call();
        snackBar('Repeat broadcast schedule removed.');
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isDeleting = false);
        errorSnackBar('Failed to remove repeat schedule: $e');
      }
    }
  }

  Future<void> _handleTestTrigger() async {
    if (_isStudent) return;
    setState(() => _isTestingSlot = true);
    try {
      final res = await EchosphereApiService().evaluateAndDispatchRepeatSchedules();
      if (mounted) {
        setState(() => _isTestingSlot = false);
        final resultInfo = res['result'];
        final enqueuedCount = resultInfo is Map ? (resultInfo['dispatched_count'] ?? 0) : 0;
        final expiredCount = resultInfo is Map ? (resultInfo['expired_ttl_count'] ?? 0) : 0;
        final activeSlots = resultInfo is Map ? (resultInfo['active_slots'] as List? ?? []) : [];
        final slotLabel = activeSlots.isNotEmpty ? activeSlots.join(', ') : 'Outside Acoustic Windows';
        snackBar('Evaluation complete! Slot: $slotLabel \u2022 Dispatched: $enqueuedCount \u2022 Expired (TTL): $expiredCount');
        _fetchSchedule();
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isTestingSlot = false);
        errorSnackBar('Test evaluation failed: $e');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasExistingSchedule = _loadedSchedule != null;
    final isActive = hasExistingSchedule && (_loadedSchedule!['is_active'] ?? true);
    final logs = hasExistingSchedule ? (_loadedSchedule!['execution_logs'] as List? ?? []) : [];

    return Dialog(
      backgroundColor: context.colors.surface,
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480, maxHeight: 650),
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: context.colors.primary.opaque(0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.repeat_rounded, size: 20, color: context.colors.primary),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const EchoSphereText(
                          text: 'Repeat Broadcast Schedule',
                          size: 15,
                          variant: TextVariant.bold,
                        ),
                        if (widget.announcementTitle != null)
                          EchoSphereText(
                            text: widget.announcementTitle!,
                            size: 11,
                            color: context.colors.onSurface.opaque(0.65),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 18),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Divider(height: 1, color: context.colors.outline.opaque(0.12)),
              const SizedBox(height: 12),

              // Scrollable Body
              Flexible(
                child: _isLoading
                    ? const Center(
                        child: Padding(
                          padding: EdgeInsets.all(32.0),
                          child: CircularProgressIndicator(),
                        ),
                      )
                    : SingleChildScrollView(
                        physics: const BouncingScrollPhysics(),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Status Banner
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              decoration: BoxDecoration(
                                color: _isStudent
                                    ? Colors.blue.withOpacity(0.08)
                                    : hasExistingSchedule
                                        ? (isActive ? Colors.green.withOpacity(0.1) : Colors.orange.withOpacity(0.1))
                                        : context.colors.primary.opaque(0.08),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: _isStudent
                                      ? Colors.blue.withOpacity(0.3)
                                      : hasExistingSchedule
                                          ? (isActive ? Colors.green.withOpacity(0.3) : Colors.orange.withOpacity(0.3))
                                          : context.colors.primary.opaque(0.2),
                                ),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    _isStudent
                                        ? Icons.info_outline_rounded
                                        : hasExistingSchedule
                                            ? (isActive ? Icons.check_circle_rounded : Icons.pause_circle_rounded)
                                            : Icons.info_outline_rounded,
                                    size: 16,
                                    color: _isStudent
                                        ? Colors.blue
                                        : hasExistingSchedule
                                            ? (isActive ? Colors.green : Colors.orange)
                                            : context.colors.primary,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: EchoSphereText(
                                      text: _isStudent
                                          ? 'View-Only Mode: You are viewing this schedule as a student. Broadcast timing updates require faculty or administrative privileges.'
                                          : hasExistingSchedule
                                              ? (isActive
                                                  ? 'Active: Rebroadcasts during designated campus break windows. Total Dispatched: ${_loadedSchedule?['total_played_count'] ?? 0} time(s).'
                                                  : 'Inactive: Schedule is currently paused.')
                                              : 'Select campus break windows to automatically repeat this voice broadcast.',
                                      size: 11,
                                      color: context.colors.onSurface.opaque(0.85),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Container(
                              margin: const EdgeInsets.only(top: 8),
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              decoration: BoxDecoration(
                                color: Colors.amber.withOpacity(0.08),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.amber.withOpacity(0.3)),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.volume_off_rounded, size: 14, color: Colors.amber),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: EchoSphereText(
                                      text: 'Lecture Silence Protected: Unplayed repeat notices automatically expire at slot cutoff (TTL) to prevent academic interruption.',
                                      size: 10,
                                      color: context.colors.onSurface.opaque(0.8),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 16),

                            // Slot Selection
                            const EchoSphereText(
                              text: 'Campus Acoustic Windows (Lecture Silence Protected)',
                              size: 12,
                              variant: TextVariant.bold,
                            ),
                            const SizedBox(height: 6),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                FilterChip(
                                  avatar: const Icon(Icons.coffee_rounded, size: 14),
                                  label: const Text('Short Break (11:00 AM)', style: TextStyle(fontSize: 11)),
                                  selected: _selectedSlots.contains('SHORT_BREAK'),
                                  onSelected: (val) {
                                    setState(() {
                                      if (val) {
                                        _selectedSlots.add('SHORT_BREAK');
                                      } else {
                                        _selectedSlots.remove('SHORT_BREAK');
                                      }
                                    });
                                  },
                                ),
                                FilterChip(
                                  avatar: const Icon(Icons.restaurant_rounded, size: 14),
                                  label: const Text('Lunch Break (1:15 PM)', style: TextStyle(fontSize: 11)),
                                  selected: _selectedSlots.contains('LUNCH_BREAK'),
                                  onSelected: (val) {
                                    setState(() {
                                      if (val) {
                                        _selectedSlots.add('LUNCH_BREAK');
                                      } else {
                                        _selectedSlots.remove('LUNCH_BREAK');
                                      }
                                    });
                                  },
                                ),
                                FilterChip(
                                  avatar: const Icon(Icons.wb_twilight_rounded, size: 14),
                                  label: const Text('Evening Break (4:30 PM)', style: TextStyle(fontSize: 11)),
                                  selected: _selectedSlots.contains('EVENING_BREAK'),
                                  onSelected: (val) {
                                    setState(() {
                                      if (val) {
                                        _selectedSlots.add('EVENING_BREAK');
                                      } else {
                                        _selectedSlots.remove('EVENING_BREAK');
                                      }
                                    });
                                  },
                                ),
                                FilterChip(
                                  avatar: const Icon(Icons.night_shelter_rounded, size: 14),
                                  label: const Text('Hostel Window (7:30 PM)', style: TextStyle(fontSize: 11)),
                                  selected: _selectedSlots.contains('HOSTEL_WINDOW'),
                                  onSelected: (val) {
                                    setState(() {
                                      if (val) {
                                        _selectedSlots.add('HOSTEL_WINDOW');
                                      } else {
                                        _selectedSlots.remove('HOSTEL_WINDOW');
                                      }
                                    });
                                  },
                                ),
                                FilterChip(
                                  avatar: const Icon(Icons.access_time_rounded, size: 14),
                                  label: const Text('Custom Window', style: TextStyle(fontSize: 11)),
                                  selected: _selectedSlots.contains('CUSTOM_WINDOW'),
                                  onSelected: (val) {
                                    setState(() {
                                      if (val) {
                                        _selectedSlots.add('CUSTOM_WINDOW');
                                      } else {
                                        _selectedSlots.remove('CUSTOM_WINDOW');
                                      }
                                    });
                                  },
                                ),
                              ],
                            ),


                            // Custom Window Time Fields
                            if (_selectedSlots.contains('CUSTOM_WINDOW')) ...[
                              const SizedBox(height: 12),
                              Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: context.colors.surfaceContainer.opaque(0.5),
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(color: context.colors.outline.opaque(0.15)),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const EchoSphereText(
                                      text: 'Custom Time Window (24-Hour Format)',
                                      size: 11,
                                      variant: TextVariant.bold,
                                    ),
                                    const SizedBox(height: 8),
                                    Row(
                                      children: [
                                        Expanded(
                                          child: InkWell(
                                            onTap: () => _pickTime(isStart: true),
                                            child: AbsorbPointer(
                                              child: TextField(
                                                controller: _customStartCtrl,
                                                decoration: const InputDecoration(
                                                  labelText: 'Start Time',
                                                  hintText: '10:00',
                                                  isDense: true,
                                                  suffixIcon: Icon(Icons.schedule_rounded, size: 16),
                                                  border: OutlineInputBorder(),
                                                ),
                                                style: const TextStyle(fontSize: 12),
                                              ),
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: InkWell(
                                            onTap: () => _pickTime(isStart: false),
                                            child: AbsorbPointer(
                                              child: TextField(
                                                controller: _customEndCtrl,
                                                decoration: const InputDecoration(
                                                  labelText: 'End Time',
                                                  hintText: '11:00',
                                                  isDense: true,
                                                  suffixIcon: Icon(Icons.schedule_rounded, size: 16),
                                                  border: OutlineInputBorder(),
                                                ),
                                                style: const TextStyle(fontSize: 12),
                                              ),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ],

                            const SizedBox(height: 16),

                            // Target Scope Dropdown
                            const EchoSphereText(
                              text: 'Target Speaker Scope',
                              size: 12,
                              variant: TextVariant.bold,
                            ),
                            const SizedBox(height: 6),
                            DropdownButtonFormField<String>(
                              value: _selectedScope,
                              decoration: InputDecoration(
                                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                              ),
                              items: const [
                                DropdownMenuItem(
                                  value: 'DEPARTMENT',
                                  child: Text('Department Nodes Only', style: TextStyle(fontSize: 12)),
                                ),
                                DropdownMenuItem(
                                  value: 'COLLEGE_WIDE',
                                  child: Text('College-Wide (All Nodes)', style: TextStyle(fontSize: 12)),
                                ),
                                DropdownMenuItem(
                                  value: 'HOSTEL',
                                  child: Text('Hostel & Common Areas', style: TextStyle(fontSize: 12)),
                                ),
                              ],
                              onChanged: (val) {
                                if (val != null) setState(() => _selectedScope = val);
                              },
                            ),

                            const SizedBox(height: 12),
                            // Horizon & Lifespan hint
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(Icons.security_rounded, size: 14, color: context.colors.primary),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: EchoSphereText(
                                    text: 'Automated repeat broadcasts remain active for up to 48 hours to ensure fresh campus communications.',
                                    size: 10,
                                    color: context.colors.onSurface.opaque(0.6),
                                  ),
                                ),
                              ],
                            ),

                            // Execution Logs (if any)
                            if (logs.isNotEmpty) ...[
                              const SizedBox(height: 16),
                              const EchoSphereText(
                                text: 'Recent Repeat Executions',
                                size: 12,
                                variant: TextVariant.bold,
                              ),
                              const SizedBox(height: 6),
                              Container(
                                constraints: const BoxConstraints(maxHeight: 110),
                                decoration: BoxDecoration(
                                  color: context.colors.surfaceContainer.opaque(0.3),
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(color: context.colors.outline.opaque(0.12)),
                                ),
                                child: ListView.builder(
                                  shrinkWrap: true,
                                  itemCount: logs.length,
                                  itemBuilder: (ctx, idx) {
                                    final log = logs[logs.length - 1 - idx];
                                    final slot = log['slot'] ?? 'BREAK';
                                    final time = log['dispatched_at'] ?? log['timestamp'] ?? '';
                                    final formattedTime = time.isNotEmpty
                                        ? DateFormat('MMM dd, hh:mm a').format(DateTime.tryParse(time.toString()) ?? DateTime.now())
                                        : '';
                                    return Padding(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                      child: Row(
                                        children: [
                                          const Icon(Icons.check_circle_outline_rounded, size: 12, color: Colors.green),
                                          const SizedBox(width: 6),
                                          Expanded(
                                            child: EchoSphereText(
                                              text: 'Rebroadcast triggered for $slot ($formattedTime)',
                                              size: 10,
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                        ],
                                      ),
                                    );
                                  },
                                ),
                              ),
                            ],

                            // Test Trigger Action (Testing & Validation)
                            if (!_isStudent && widget.announcementId != null) ...[
                              const SizedBox(height: 14),
                              OutlinedButton.icon(
                                style: OutlinedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                  side: BorderSide(color: context.colors.primary.opaque(0.4)),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                                onPressed: _isTestingSlot ? null : _handleTestTrigger,
                                icon: _isTestingSlot
                                    ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2))
                                    : Icon(Icons.play_circle_outline_rounded, size: 16, color: context.colors.primary),
                                label: EchoSphereText(
                                  text: _isTestingSlot ? 'Evaluating Break Slot...' : 'Test Slot Evaluation Now',
                                  size: 11,
                                  variant: TextVariant.bold,
                                  color: context.colors.primary,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
              ),

              const SizedBox(height: 14),
              Divider(height: 1, color: context.colors.outline.opaque(0.12)),
              const SizedBox(height: 12),

              // Bottom Actions
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (_isStudent) ...[
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text('Close', style: TextStyle(fontSize: 12)),
                    ),
                  ] else ...[
                    if (hasExistingSchedule && widget.announcementId != null) ...[
                      TextButton.icon(
                        style: TextButton.styleFrom(
                          foregroundColor: Colors.redAccent,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        ),
                        onPressed: (_isDeleting || _isSaving) ? null : _handleDelete,
                        icon: _isDeleting
                            ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.redAccent))
                            : const Icon(Icons.delete_outline_rounded, size: 15),
                        label: const Text('Remove', style: TextStyle(fontSize: 12)),
                      ),
                      const Spacer(),
                    ],
                    TextButton(
                      onPressed: (_isSaving || _isDeleting) ? null : () => Navigator.of(context).pop(),
                      child: const Text('Cancel', style: TextStyle(fontSize: 12)),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: context.colors.primary,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      ),
                      onPressed: (_isSaving || _isDeleting) ? null : _handleSave,
                      child: _isSaving
                          ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Text('Save Schedule', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
