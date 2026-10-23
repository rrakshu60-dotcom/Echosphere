import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/utils/theme_extensions.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:echosphere/utils/campus_time.dart';

/// Minimal and user-friendly dialog to configure automated repeat announcement
/// broadcasts using campus break schedules and custom time windows.
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
  // Preset Campus Break Windows
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

  final Set<String> _selectedSlots = {'SHORT_BREAK'};
  late final TextEditingController _customStartCtrl;
  late final TextEditingController _customEndCtrl;
  bool _playOnPublish = true;

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

    final slots = (data['selected_slots'] as List?)?.map((e) => e.toString().toUpperCase()).toList();
    if (slots != null && slots.isNotEmpty) {
      _selectedSlots.clear();
      _selectedSlots.addAll(slots.where((s) => s != 'INTERVAL'));
    }

    if (data['custom_start_time'] != null && data['custom_start_time'].toString().isNotEmpty) {
      _customStartCtrl.text = data['custom_start_time'].toString();
      _selectedSlots.add('CUSTOM_WINDOW');
    }
    if (data['custom_end_time'] != null && data['custom_end_time'].toString().isNotEmpty) {
      _customEndCtrl.text = data['custom_end_time'].toString();
    }

    if (_selectedSlots.isEmpty) {
      _selectedSlots.add('SHORT_BREAK');
    }

    if (data['play_on_publish'] != null) {
      _playOnPublish = data['play_on_publish'] == true || data['play_on_publish'].toString().toLowerCase() == 'true';
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

  String _normalizeTime(String raw) {
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
    final norm = _normalizeTime(hhmm);
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
    final startNorm = _normalizeTime(startRaw);
    final endNorm = _normalizeTime(endRaw);
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

  Future<void> _pickTime({required bool isStart}) async {
    final currentStr = _normalizeTime(isStart ? _customStartCtrl.text : _customEndCtrl.text);
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
      helpText: isStart ? 'Select Repeat Window Start Time' : 'Select Repeat Window End Time',
    );

    if (picked != null && mounted) {
      final h = picked.hour.toString().padLeft(2, '0');
      final m = picked.minute.toString().padLeft(2, '0');
      setState(() {
        if (isStart) {
          _customStartCtrl.text = '$h:$m';
          // Auto-adjust end time if it falls behind or equals start
          final curEnd = _normalizeTime(_customEndCtrl.text);
          if (curEnd.isEmpty || curEnd.compareTo('$h:$m') <= 0) {
            final endHour = (picked.hour + 1) % 24;
            _customEndCtrl.text = '${endHour.toString().padLeft(2, '0')}:$m';
          }
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
      errorSnackBar('Please select at least one break schedule or custom time window.');
      return;
    }

    final now = DateTime.now();
    String? normStart;
    String? normEnd;

    if (_selectedSlots.contains('CUSTOM_WINDOW')) {
      normStart = _normalizeTime(_customStartCtrl.text);
      normEnd = _normalizeTime(_customEndCtrl.text);
      final rangeInfo = _calculateCustomWindowDuration(normStart, normEnd);
      if (rangeInfo['isValid'] != true) {
        errorSnackBar(rangeInfo['message'] as String? ?? 'Invalid custom time window');
        return;
      }
      _customStartCtrl.text = normStart;
      _customEndCtrl.text = normEnd;
    }

    final payload = <String, dynamic>{
      'repeat_mode': 'BREAK_SLOTS',
      'interval_minutes': 0,
      'max_repeats': _selectedSlots.length * 5 + (_playOnPublish ? 1 : 0),
      'play_on_publish': _playOnPublish,
      'selected_slots': _selectedSlots.toList(),
      'target_scope': 'COLLEGE_WIDE',
      'event_datetime': now.add(const Duration(hours: 24)).toUtc().toIso8601String(),
      'start_date': now.subtract(const Duration(minutes: 5)).toUtc().toIso8601String(),
      'end_date': now.add(const Duration(hours: 48)).toUtc().toIso8601String(),
      'force_enable_speaker': true,
      if (_selectedSlots.contains('CUSTOM_WINDOW') && normStart != null && normEnd != null) ...{
        'custom_start_time': normStart,
        'custom_end_time': normEnd,
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
        snackBar('Evaluation complete! Slot: $slotLabel \u2022 Dispatched: $enqueuedCount \u2022 Expired: $expiredCount');
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

    final hasCustom = _selectedSlots.contains('CUSTOM_WINDOW');
    final customRangeInfo = hasCustom ? _calculateCustomWindowDuration(_customStartCtrl.text, _customEndCtrl.text) : null;

    return Dialog(
      backgroundColor: context.colors.surface,
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480, maxHeight: 680),
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
                          text: 'Repeat Broadcast',
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
                          )
                        else
                          EchoSphereText(
                            text: 'Replay automatically across campus speakers',
                            size: 11,
                            color: context.colors.onSurface.opaque(0.65),
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
                                        ? (isActive ? Colors.green.withOpacity(0.08) : Colors.orange.withOpacity(0.08))
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
                                            : Icons.repeat_on_rounded,
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
                                          ? 'View-Only Mode: You are viewing this schedule as a student.'
                                          : hasExistingSchedule
                                              ? (isActive
                                                  ? 'Active Repeat Schedule \u2022 Total Dispatched: ${_loadedSchedule?['total_played_count'] ?? 0} time(s).'
                                                  : 'Inactive: Schedule is currently paused.')
                                              : 'Choose campus break windows or set a custom time window to replay this voice notice.',
                                      size: 11,
                                      color: context.colors.onSurface.opaque(0.85),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 14),

                            // SECTION 1: BREAK SCHEDULES PRESETS
                            const EchoSphereText(
                              text: 'Campus Break Schedules',
                              size: 12,
                              variant: TextVariant.bold,
                            ),
                            const SizedBox(height: 6),
                            ListView.separated(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: _breakWindows.length,
                              separatorBuilder: (_, __) => const SizedBox(height: 6),
                              itemBuilder: (ctx, idx) {
                                final bw = _breakWindows[idx];
                                final key = bw['key'] as String;
                                final isSelected = _selectedSlots.contains(key);
                                return InkWell(
                                  borderRadius: BorderRadius.circular(10),
                                  onTap: () {
                                    setState(() {
                                      if (isSelected) {
                                        _selectedSlots.remove(key);
                                      } else {
                                        _selectedSlots.add(key);
                                      }
                                    });
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                    decoration: BoxDecoration(
                                      color: isSelected
                                          ? context.colors.primary.opaque(0.1)
                                          : context.colors.surfaceContainer.opaque(0.3),
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(
                                        color: isSelected
                                            ? context.colors.primary
                                            : context.colors.outline.opaque(0.15),
                                        width: isSelected ? 1.5 : 1.0,
                                      ),
                                    ),
                                    child: Row(
                                      children: [
                                        Icon(
                                          bw['icon'] as IconData,
                                          size: 18,
                                          color: isSelected ? context.colors.primary : context.colors.onSurface.opaque(0.6),
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                bw['title'] as String,
                                                style: TextStyle(
                                                  fontSize: 12,
                                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                                                  color: isSelected ? context.colors.primary : null,
                                                ),
                                              ),
                                              Text(
                                                '${bw['time']} \u2022 ${bw['duration']}',
                                                style: TextStyle(
                                                  fontSize: 10,
                                                  color: context.colors.onSurface.opaque(0.65),
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
                                                _selectedSlots.add(key);
                                              } else {
                                                _selectedSlots.remove(key);
                                              }
                                            });
                                          },
                                          activeColor: context.colors.primary,
                                          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                          visualDensity: VisualDensity.compact,
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),

                            const SizedBox(height: 12),

                            // SECTION 2: CUSTOM TIME WINDOW
                            InkWell(
                              borderRadius: BorderRadius.circular(10),
                              onTap: () {
                                setState(() {
                                  if (hasCustom) {
                                    _selectedSlots.remove('CUSTOM_WINDOW');
                                  } else {
                                    _selectedSlots.add('CUSTOM_WINDOW');
                                  }
                                });
                              },
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                decoration: BoxDecoration(
                                  color: hasCustom
                                      ? context.colors.primary.opaque(0.1)
                                      : context.colors.surfaceContainer.opaque(0.3),
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(
                                    color: hasCustom
                                        ? context.colors.primary
                                        : context.colors.outline.opaque(0.15),
                                    width: hasCustom ? 1.5 : 1.0,
                                  ),
                                ),
                                child: Row(
                                  children: [
                                    Icon(
                                      Icons.access_time_filled_rounded,
                                      size: 18,
                                      color: hasCustom ? context.colors.primary : context.colors.onSurface.opaque(0.6),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'Custom Time Window',
                                            style: TextStyle(
                                              fontSize: 12,
                                              fontWeight: hasCustom ? FontWeight.bold : FontWeight.w600,
                                              color: hasCustom ? context.colors.primary : null,
                                            ),
                                          ),
                                          Text(
                                            'Define a custom start and end time range for repeats',
                                            style: TextStyle(
                                              fontSize: 10,
                                              color: context.colors.onSurface.opaque(0.65),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    Checkbox(
                                      value: hasCustom,
                                      onChanged: (val) {
                                        setState(() {
                                          if (val == true) {
                                            _selectedSlots.add('CUSTOM_WINDOW');
                                          } else {
                                            _selectedSlots.remove('CUSTOM_WINDOW');
                                          }
                                        });
                                      },
                                      activeColor: context.colors.primary,
                                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                      visualDensity: VisualDensity.compact,
                                    ),
                                  ],
                                ),
                              ),
                            ),

                            // CUSTOM TIME WINDOW INPUTS & LIVE CALCULATED RANGE
                            if (hasCustom) ...[
                              const SizedBox(height: 10),
                              Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: context.colors.surfaceContainer.opaque(0.4),
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(color: context.colors.primary.opaque(0.25)),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const EchoSphereText(
                                      text: 'Set Repeat Window (Start \u2013 End)',
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
                                                decoration: InputDecoration(
                                                  labelText: 'Start Time',
                                                  hintText: '10:00',
                                                  isDense: true,
                                                  suffixIcon: const Icon(Icons.schedule_rounded, size: 16),
                                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                                                ),
                                                style: const TextStyle(fontSize: 12),
                                              ),
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: InkWell(
                                            onTap: () => _pickTime(isStart: false),
                                            child: AbsorbPointer(
                                              child: TextField(
                                                controller: _customEndCtrl,
                                                decoration: InputDecoration(
                                                  labelText: 'End Time',
                                                  hintText: '11:00',
                                                  isDense: true,
                                                  suffixIcon: const Icon(Icons.schedule_rounded, size: 16),
                                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                                                ),
                                                style: const TextStyle(fontSize: 12),
                                              ),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 10),
                                    // DYNAMIC CALCULATED TIME RANGE BADGE
                                    if (customRangeInfo != null)
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                                        decoration: BoxDecoration(
                                          color: customRangeInfo['isValid'] == true
                                              ? context.colors.primary.opaque(0.08)
                                              : Colors.orange.withOpacity(0.1),
                                          borderRadius: BorderRadius.circular(8),
                                          border: Border.all(
                                            color: customRangeInfo['isValid'] == true
                                                ? context.colors.primary.opaque(0.3)
                                                : Colors.orange.withOpacity(0.3),
                                          ),
                                        ),
                                        child: Row(
                                          children: [
                                            Icon(
                                              customRangeInfo['isValid'] == true
                                                  ? Icons.timelapse_rounded
                                                  : Icons.warning_amber_rounded,
                                              size: 15,
                                              color: customRangeInfo['isValid'] == true
                                                  ? context.colors.primary
                                                  : Colors.orange,
                                            ),
                                            const SizedBox(width: 6),
                                            Expanded(
                                              child: Text(
                                                customRangeInfo['isValid'] == true
                                                    ? 'Calculated Repeat Window: ${customRangeInfo['displayRange']} \u2022 ${customRangeInfo['duration']}'
                                                    : '${customRangeInfo['message']}',
                                                style: TextStyle(
                                                  fontSize: 11,
                                                  fontWeight: FontWeight.w600,
                                                  color: customRangeInfo['isValid'] == true
                                                      ? context.colors.primary
                                                      : Colors.orange.shade800,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            ],

                            const SizedBox(height: 12),

                            // SECTION 3: PLAY ON PUBLISH TOGGLE
                            InkWell(
                              onTap: () => setState(() => _playOnPublish = !_playOnPublish),
                              borderRadius: BorderRadius.circular(8),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(vertical: 4),
                                child: Row(
                                  children: [
                                    Checkbox(
                                      value: _playOnPublish,
                                      onChanged: (v) => setState(() => _playOnPublish = v ?? true),
                                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                      visualDensity: VisualDensity.compact,
                                      activeColor: context.colors.primary,
                                    ),
                                    const SizedBox(width: 6),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          const Text(
                                            'Broadcast immediately on publish',
                                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                                          ),
                                          Text(
                                            'Notice plays once immediately upon publishing, then repeats during selected windows',
                                            style: TextStyle(fontSize: 10, color: context.colors.onSurface.opaque(0.6)),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),

                            // Execution Logs (if any)
                            if (logs.isNotEmpty) ...[
                              const SizedBox(height: 14),
                              const EchoSphereText(
                                text: 'Recent Repeat Executions',
                                size: 12,
                                variant: TextVariant.bold,
                              ),
                              const SizedBox(height: 6),
                              Container(
                                constraints: const BoxConstraints(maxHeight: 90),
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
                                        ? formatCampusTime(parseServerTime(time) ?? DateTime.now(), 'MMM dd, hh:mm a')
                                        : '';
                                    return Padding(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
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

                            // Test Trigger Action (Testing & Validation for Faculty/Admin)
                            if (!_isStudent && widget.announcementId != null) ...[
                              const SizedBox(height: 12),
                              OutlinedButton.icon(
                                style: OutlinedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                  side: BorderSide(color: context.colors.primary.opaque(0.4)),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                                onPressed: _isTestingSlot ? null : _handleTestTrigger,
                                icon: _isTestingSlot
                                    ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2))
                                    : Icon(Icons.play_circle_outline_rounded, size: 15, color: context.colors.primary),
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

              const SizedBox(height: 12),
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
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
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
