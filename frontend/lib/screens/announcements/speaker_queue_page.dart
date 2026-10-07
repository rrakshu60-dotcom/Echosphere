import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/speaker_queue_controller.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/utils/theme_extensions.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_button.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_chip.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_container.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:echosphere/services/tts_audio_service.dart';
import 'package:echosphere/widgets/custom_widgets/audio_waveform_visualizer.dart';
import 'package:echosphere/widgets/custom_widgets/repeat_schedule_dialog.dart';
import 'package:echosphere/utils/navigation_helper.dart';

class SpeakerQueuePage extends StatefulWidget {
  const SpeakerQueuePage({super.key});

  @override
  State<SpeakerQueuePage> createState() => _SpeakerQueuePageState();
}

class _SpeakerQueuePageState extends State<SpeakerQueuePage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  SpeakerQueueController get _queueCtrl => Get.isRegistered<SpeakerQueueController>()
      ? Get.find<SpeakerQueueController>()
      : Get.put(SpeakerQueueController());

  bool get _isStudent {
    if (!Get.isRegistered<AuthController>()) return false;
    final user = Get.find<AuthController>().currentUser.value;
    if (user == null) return false;
    return user.role.toLowerCase() == 'student';
  }

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _queueCtrl.refreshQueue();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  String _formatTime(dynamic rawScheduled, dynamic rawFallback) {
    if (rawScheduled is DateTime) {
      return DateFormat("hh:mm a").format(rawScheduled);
    }
    final val = (rawScheduled ?? rawFallback)?.toString();
    if (val == null || val.isEmpty || val == 'null') {
      return 'Immediate';
    }
    try {
      final dt = DateTime.parse(val);
      return DateFormat("hh:mm a").format(dt);
    } catch (_) {
      return val;
    }
  }

  String _formatMetric(dynamic val, {String suffix = '%', String fallback = '0.0'}) {
    if (val == null) return '$fallback$suffix';
    if (val is num) return '${val.toStringAsFixed(1)}$suffix';
    return '${val.toString()}$suffix';
  }

  void _previewAudio() {
    if (_queueCtrl.queueItems.isEmpty) {
      snackBar('No announcement selected for preview.');
      return;
    }
    final activeItem = _queueCtrl.queueItems.firstWhereOrNull((i) => i['status'] == 'Playing') ??
        _queueCtrl.queueItems.first;
    final noticeId = activeItem['announcement_id'] as int?;
    final title = _queueCtrl.activeTitle;
    final audioUrl = activeItem['audio_url'] as String?;

    if (noticeId != null) {
      TtsAudioService.instance.playAnnouncement(noticeId, directUrl: audioUrl);
      snackBar('Playing voice broadcast: "$title"');
    } else {
      snackBar('Synthesizing and previewing voice announcement: "$title"');
    }
  }

  void _openRepeatScheduleForQueueItem(Map<String, dynamic> item) {
    if (_isStudent) {
      snackBar('Only faculty and administrators can configure repeat broadcast schedules.');
      return;
    }
    final annId = item['announcement_id'] as int? ?? item['id'] as int?;
    if (annId != null) {
      RepeatScheduleDialog.show(
        context,
        announcementId: annId,
        announcementTitle: (item['title'] ?? 'Notice #$annId').toString(),
      );
    } else {
      snackBar('No associated announcement found for this queue item.');
    }
  }

  void _showEmergencyDialog(BuildContext context) {
    final titleController = TextEditingController(text: "EMERGENCY CAMPUS ADVISORY");
    final msgController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: context.colors.surface,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: context.colors.primary, size: 24),
              const SizedBox(width: 8),
              const Expanded(
                child: EchoSphereText(
                  text: 'Emergency Speaker Override',
                  size: 15,
                  variant: TextVariant.bold,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: titleController,
                  style: TextStyle(color: context.colors.onSurface),
                  decoration: InputDecoration(
                    labelText: 'Emergency Title',
                    labelStyle: TextStyle(color: context.colors.primary),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: msgController,
                  maxLines: 3,
                  style: TextStyle(color: context.colors.onSurface),
                  decoration: InputDecoration(
                    labelText: 'Emergency Broadcast Text',
                    labelStyle: TextStyle(color: context.colors.primary),
                    hintText: 'Enter urgent voice announcement text...',
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: EchoSphereText(
                text: 'Cancel',
                color: context.colors.onSurface.opaque(0.7),
              ),
            ),
            EchoSphereButton(
              color: context.colors.primary,
              radius: 12,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              onTap: () async {
                final msg = msgController.text.trim();
                if (msg.isEmpty) {
                  snackBar('Please enter emergency text.');
                  return;
                }
                Navigator.pop(ctx);
                snackBar('Emergency override activated!', title: 'Emergency Alert');

                final title = titleController.text.trim().isEmpty
                    ? 'Emergency Campus Broadcast'
                    : titleController.text.trim();

                await _queueCtrl.triggerEmergency(title: title, message: msg);
              },
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.warning_rounded, size: 14, color: Colors.white),
                  SizedBox(width: 6),
                  EchoSphereText(
                    text: 'BROADCAST NOW',
                    size: 11,
                    variant: TextVariant.bold,
                    color: Colors.white,
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  void _showEnqueueDialog(BuildContext context) {
    int? selectedAnnouncementId;
    int? selectedSpeakerNodeId;
    String selectedAudioType = 'AI Speech';
    List<Map<String, dynamic>> eligibleAnnouncements = [];
    bool loadingAnnouncements = true;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            if (loadingAnnouncements && eligibleAnnouncements.isEmpty) {
              // 1. Check AnnouncementController for published announcements
              if (Get.isRegistered<AnnouncementController>()) {
                final annCtrl = Get.find<AnnouncementController>();
                for (var ann in annCtrl.allAnnouncements) {
                  if (ann.status == 'PUBLISHED' || ann.status == 'APPROVED') {
                    eligibleAnnouncements.add({
                      'id': ann.id,
                      'title': ann.title,
                      'department': ann.department,
                    });
                  }
                }
              }

              // 2. Fetch from backend as well
              EchosphereApiService().getAnnouncements().then((data) {
                if (ctx.mounted) {
                  setDialogState(() {
                    loadingAnnouncements = false;
                    for (var d in data) {
                      final id = d['id'] as int? ?? 0;
                      if (id > 0 && !eligibleAnnouncements.any((e) => e['id'] == id)) {
                        eligibleAnnouncements.add({
                          'id': id,
                          'title': d['title'] ?? 'Notice #$id',
                          'department': d['department'] ?? 'College-Wide',
                        });
                      }
                    }
                    if (eligibleAnnouncements.isNotEmpty && selectedAnnouncementId == null) {
                      selectedAnnouncementId = eligibleAnnouncements.first['id'] as int?;
                    }
                  });
                }
              }).catchError((_) {
                if (ctx.mounted) {
                  setDialogState(() {
                    loadingAnnouncements = false;
                    if (eligibleAnnouncements.isNotEmpty && selectedAnnouncementId == null) {
                      selectedAnnouncementId = eligibleAnnouncements.first['id'] as int?;
                    }
                  });
                }
              });
            }

            return AlertDialog(
              backgroundColor: context.colors.surface,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              title: const Row(
                children: [
                  Icon(Icons.add_to_queue_rounded, size: 20),
                  SizedBox(width: 8),
                  Expanded(
                    child: EchoSphereText(
                      text: 'Enqueue Notice to PA System',
                      size: 15,
                      variant: TextVariant.bold,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (loadingAnnouncements && eligibleAnnouncements.isEmpty)
                      const Center(
                        child: Padding(
                          padding: EdgeInsets.all(16.0),
                          child: CircularProgressIndicator(),
                        ),
                      )
                    else if (eligibleAnnouncements.isEmpty)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12.0),
                        child: EchoSphereText(
                          text: 'No published announcements available to enqueue.',
                          size: 12,
                          color: context.colors.onSurface.opaque(0.7),
                        ),
                      )
                    else ...[
                      const EchoSphereText(
                        text: 'Select Notice to Broadcast:',
                        size: 11,
                        variant: TextVariant.semiBold,
                      ),
                      const SizedBox(height: 6),
                      DropdownButtonFormField<int>(
                        value: selectedAnnouncementId,
                        isExpanded: true,
                        dropdownColor: context.colors.surface,
                        decoration: InputDecoration(
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        items: eligibleAnnouncements.map((ann) {
                          final id = ann['id'] as int? ?? 0;
                          final title = (ann['title'] ?? 'Notice #$id').toString();
                          return DropdownMenuItem<int>(
                            value: id,
                            child: Text(
                              title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(color: context.colors.onSurface, fontSize: 12),
                            ),
                          );
                        }).toList(),
                        onChanged: (val) {
                          if (val != null) setDialogState(() => selectedAnnouncementId = val);
                        },
                      ),
                      const SizedBox(height: 12),
                      const EchoSphereText(
                        text: 'Target Speaker Node:',
                        size: 11,
                        variant: TextVariant.semiBold,
                      ),
                      const SizedBox(height: 6),
                      DropdownButtonFormField<int?>(
                        value: selectedSpeakerNodeId,
                        isExpanded: true,
                        dropdownColor: context.colors.surface,
                        decoration: InputDecoration(
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        items: [
                          const DropdownMenuItem<int?>(
                            value: null,
                            child: Text('All Nodes (College-Wide)', style: TextStyle(fontSize: 12)),
                          ),
                          ..._queueCtrl.speakerNodes.map((n) {
                            final nId = n['id'] as int?;
                            final nName = (n['name'] ?? 'Speaker #$nId').toString();
                            final isOnline = (n['status'] ?? 'OFFLINE').toString().toUpperCase() == 'ONLINE';
                            return DropdownMenuItem<int?>(
                              value: nId,
                              child: Row(
                                children: [
                                  Container(
                                    width: 7,
                                    height: 7,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: isOnline ? context.colors.primary : context.colors.onSurface.opaque(0.3),
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      '$nName (${isOnline ? "ONLINE" : "OFFLINE"})',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: isOnline ? context.colors.onSurface : context.colors.onSurface.opaque(0.6),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          }),
                        ],
                        onChanged: (val) {
                          setDialogState(() => selectedSpeakerNodeId = val);
                        },
                      ),
                      const SizedBox(height: 12),
                      const EchoSphereText(
                        text: 'Audio Engine:',
                        size: 11,
                        variant: TextVariant.semiBold,
                      ),
                      const SizedBox(height: 6),
                      DropdownButtonFormField<String>(
                        value: selectedAudioType,
                        isExpanded: true,
                        dropdownColor: context.colors.surface,
                        decoration: InputDecoration(
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 'AI Speech',
                            child: Text('AI Speech Synthesis (TTS)', style: TextStyle(fontSize: 12)),
                          ),
                          DropdownMenuItem(
                            value: 'Recorded Voice',
                            child: Text('Recorded Voice Clip', style: TextStyle(fontSize: 12)),
                          ),
                        ],
                        onChanged: (val) {
                          if (val != null) setDialogState(() => selectedAudioType = val);
                        },
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        icon: const Icon(Icons.repeat_rounded, size: 16),
                        label: const Text('Configure Repeat Schedule', style: TextStyle(fontSize: 12)),
                        onPressed: selectedAnnouncementId == null
                            ? null
                            : () {
                                final selAnn = eligibleAnnouncements.firstWhereOrNull((a) => a['id'] == selectedAnnouncementId);
                                RepeatScheduleDialog.show(
                                  context,
                                  announcementId: selectedAnnouncementId,
                                  announcementTitle: (selAnn?['title'] ?? 'Notice #$selectedAnnouncementId').toString(),
                                );
                              },
                      ),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: EchoSphereText(
                    text: 'Cancel',
                    color: context.colors.onSurface.opaque(0.7),
                  ),
                ),
                EchoSphereButton(
                  color: context.colors.primary,
                  radius: 12,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  onTap: selectedAnnouncementId == null
                      ? null
                      : () async {
                          Navigator.pop(ctx);
                          await _queueCtrl.enqueueNotice(
                            announcementId: selectedAnnouncementId!,
                            audioType: selectedAudioType,
                            speakerNodeId: selectedSpeakerNodeId,
                          );
                        },
                  child: const EchoSphereText(
                    text: 'Add to Queue',
                    size: 12,
                    variant: TextVariant.bold,
                    color: Colors.white,
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _showRegisterNodeDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    final macCtrl = TextEditingController();
    final ipCtrl = TextEditingController();
    String selectedZone = 'Block A';
    String selectedDept = 'College-Wide';

    const zones = ['College-Wide', 'Block A', 'Block B', 'Auditorium', 'Library', 'Hostel', 'Lab-Block'];
    const depts = ['College-Wide', 'CSE', 'ECE', 'MECH', 'CIVIL', 'AIML'];

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              backgroundColor: context.colors.surface,
              insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
              actionsOverflowDirection: VerticalDirection.down,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              title: const EchoSphereText(
                text: 'Register Hardware Speaker Node',
                size: 15,
                variant: TextVariant.bold,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.bolt_rounded, size: 14, color: context.colors.primary),
                        const SizedBox(width: 4),
                        EchoSphereText(
                          text: 'Quick Setup Presets',
                          size: 11,
                          variant: TextVariant.bold,
                          color: context.colors.primary,
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        ActionChip(
                          avatar: const Icon(Icons.podcasts_rounded, size: 13),
                          label: const Text('Corridor Speaker', style: TextStyle(fontSize: 10)),
                          onPressed: () {
                            setDialogState(() {
                              nameCtrl.text = 'Campus Smart Speaker';
                              macCtrl.text = 'D4:F3:2D:22:2A:CD';
                              ipCtrl.text = '192.168.1.100';
                              selectedZone = 'Campus Main Corridor';
                              selectedDept = 'College-Wide';
                            });
                          },
                        ),
                        ActionChip(
                          avatar: const Icon(Icons.campaign_rounded, size: 13),
                          label: const Text('Client 1', style: TextStyle(fontSize: 10)),
                          onPressed: () {
                            setDialogState(() {
                              nameCtrl.text = 'Hardware Speaker Client 1';
                              macCtrl.text = 'D4:F3:2D:22:2A:CB';
                              ipCtrl.text = '127.0.0.1';
                              selectedZone = 'Auditorium / Campus';
                              selectedDept = 'College-Wide';
                            });
                          },
                        ),
                        ActionChip(
                          avatar: const Icon(Icons.memory_rounded, size: 13),
                          label: const Text('Client 2', style: TextStyle(fontSize: 10)),
                          onPressed: () {
                            setDialogState(() {
                              nameCtrl.text = 'Hardware Speaker Client 2';
                              macCtrl.text = 'D4:F3:2D:22:2A:CC';
                              ipCtrl.text = '127.0.0.1';
                              selectedZone = 'Block B - AI Lab';
                              selectedDept = 'AIML';
                            });
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: nameCtrl,
                      style: TextStyle(color: context.colors.onSurface),
                      decoration: InputDecoration(
                        labelText: 'Device Name',
                        hintText: 'e.g. CSE Horn Speaker 1',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: macCtrl,
                      style: TextStyle(color: context.colors.onSurface),
                      decoration: InputDecoration(
                        labelText: 'MAC Address',
                        hintText: 'AA:BB:CC:DD:EE:FF',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: ipCtrl,
                      style: TextStyle(color: context.colors.onSurface),
                      decoration: InputDecoration(
                        labelText: 'IP Address (Optional)',
                        hintText: '192.168.1.105',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      value: selectedZone,
                      isExpanded: true,
                      dropdownColor: context.colors.surface,
                      decoration: InputDecoration(
                        labelText: 'Zone',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      items: zones
                          .map((z) => DropdownMenuItem(
                                value: z,
                                child: Text(z, style: TextStyle(color: context.colors.onSurface)),
                              ))
                          .toList(),
                      onChanged: (val) {
                        if (val != null) setDialogState(() => selectedZone = val);
                      },
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      value: selectedDept,
                      isExpanded: true,
                      dropdownColor: context.colors.surface,
                      decoration: InputDecoration(
                        labelText: 'Department',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      items: depts
                          .map((d) => DropdownMenuItem(
                                value: d,
                                child: Text(d, style: TextStyle(color: context.colors.onSurface)),
                              ))
                          .toList(),
                      onChanged: (val) {
                        if (val != null) setDialogState(() => selectedDept = val);
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: EchoSphereText(
                    text: 'Cancel',
                    color: context.colors.onSurface.opaque(0.7),
                  ),
                ),
                EchoSphereButton(
                  color: context.colors.primary,
                  radius: 12,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  onTap: () async {
                    if (nameCtrl.text.trim().isEmpty || macCtrl.text.trim().isEmpty) {
                      snackBar('Name and MAC Address are required.');
                      return;
                    }
                    Navigator.pop(ctx);
                    await _queueCtrl.registerNode(
                      name: nameCtrl.text.trim(),
                      macAddress: macCtrl.text.trim(),
                      ipAddress: ipCtrl.text.trim().isEmpty ? null : ipCtrl.text.trim(),
                      zone: selectedZone,
                      department: selectedDept,
                    );
                  },
                  child: const EchoSphereText(
                    text: 'Register Node',
                    size: 12,
                    variant: TextVariant.bold,
                    color: Colors.white,
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _showEditNodeDialog(BuildContext context, Map<String, dynamic> node) {
    final nameCtrl = TextEditingController(text: node['name']?.toString() ?? '');
    String selectedZone = (node['zone']?.toString() ?? 'Block A');
    String selectedDept = (node['department']?.toString() ?? node['department_name']?.toString() ?? 'College-Wide');
    double currentVolume = ((node['volume'] as num?)?.toDouble() ?? 80.0).clamp(0.0, 100.0);

    const zones = ['College-Wide', 'Block A', 'Block B', 'Auditorium', 'Library', 'Hostel', 'Lab-Block'];
    if (!zones.contains(selectedZone)) selectedZone = 'College-Wide';

    const depts = ['College-Wide', 'CSE', 'ECE', 'MECH', 'CIVIL', 'AIML'];
    if (!depts.contains(selectedDept)) selectedDept = 'College-Wide';

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              backgroundColor: context.colors.surface,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              title: const EchoSphereText(
                text: 'Configure Speaker Node',
                size: 15,
                variant: TextVariant.bold,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextField(
                      controller: nameCtrl,
                      style: TextStyle(color: context.colors.onSurface),
                      decoration: InputDecoration(
                        labelText: 'Device Name',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      value: selectedZone,
                      isExpanded: true,
                      dropdownColor: context.colors.surface,
                      decoration: InputDecoration(
                        labelText: 'Zone',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      items: zones
                          .map((z) => DropdownMenuItem(
                                value: z,
                                child: Text(z, style: TextStyle(color: context.colors.onSurface)),
                              ))
                          .toList(),
                      onChanged: (val) {
                        if (val != null) setDialogState(() => selectedZone = val);
                      },
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      value: selectedDept,
                      isExpanded: true,
                      dropdownColor: context.colors.surface,
                      decoration: InputDecoration(
                        labelText: 'Department',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      items: depts
                          .map((d) => DropdownMenuItem(
                                value: d,
                                child: Text(d, style: TextStyle(color: context.colors.onSurface)),
                              ))
                          .toList(),
                      onChanged: (val) {
                        if (val != null) setDialogState(() => selectedDept = val);
                      },
                    ),
                    const SizedBox(height: 14),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        EchoSphereText(
                          text: 'Volume Level',
                          size: 12,
                          variant: TextVariant.bold,
                          color: context.colors.onSurface,
                        ),
                        EchoSphereText(
                          text: '${currentVolume.round()}%',
                          size: 12,
                          variant: TextVariant.bold,
                          color: context.colors.primary,
                        ),
                      ],
                    ),
                    Slider(
                      value: currentVolume,
                      min: 0,
                      max: 100,
                      divisions: 20,
                      activeColor: context.colors.primary,
                      onChanged: (val) {
                        setDialogState(() => currentVolume = val);
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: EchoSphereText(
                    text: 'Cancel',
                    color: context.colors.onSurface.opaque(0.7),
                  ),
                ),
                EchoSphereButton(
                  color: context.colors.primary,
                  radius: 12,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  onTap: () async {
                    Navigator.pop(ctx);
                    final nodeId = node['id'];
                    if (nodeId != null && nodeId is int) {
                      await _queueCtrl.updateNode(
                        nodeId,
                        name: nameCtrl.text.trim().isNotEmpty ? nameCtrl.text.trim() : null,
                        zone: selectedZone,
                        department: selectedDept,
                        volume: currentVolume.round(),
                      );
                    }
                  },
                  child: const EchoSphereText(
                    text: 'Save Changes',
                    size: 12,
                    variant: TextVariant.bold,
                    color: Colors.white,
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _showDirectBroadcastDialog(BuildContext context, int nodeId, String nodeName) {
    final annCtrl = Get.isRegistered<AnnouncementController>() ? Get.find<AnnouncementController>() : null;
    final announcements = annCtrl?.allAnnouncements.where((a) => a.status == 'PUBLISHED' || a.status == 'APPROVED').toList() ?? [];

    int? selectedAnnouncementId = announcements.isNotEmpty ? announcements.first.id : null;
    final quickTitleCtrl = TextEditingController();
    final quickContentCtrl = TextEditingController();
    bool isQuickMode = announcements.isEmpty;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              backgroundColor: context.colors.surface,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              title: Row(
                children: [
                  Icon(Icons.campaign_rounded, color: context.colors.primary, size: 22),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: EchoSphereText(
                      text: 'Broadcast to Node',
                      size: 16,
                      variant: TextVariant.bold,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: context.colors.primary.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: context.colors.primary.withOpacity(0.2)),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.podcasts_rounded, size: 16, color: context.colors.primary),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                EchoSphereText(
                                  text: nodeName,
                                  size: 12,
                                  variant: TextVariant.bold,
                                  color: context.colors.onSurface,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                EchoSphereText(
                                  text: 'Speaker Node #$nodeId \u2022 Live Audio & Display',
                                  size: 10,
                                  color: context.colors.onSurface.opaque(0.7),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Toggle: Select Existing or Quick Dispatch
                    Row(
                      children: [
                        Expanded(
                          child: ChoiceChip(
                            label: const Center(
                              child: Text('Existing Notice', style: TextStyle(fontSize: 11)),
                            ),
                            selected: !isQuickMode,
                            onSelected: (val) {
                              if (val && announcements.isNotEmpty) {
                                setDialogState(() => isQuickMode = false);
                              }
                            },
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: ChoiceChip(
                            label: const Center(
                              child: Text('Quick Notice', style: TextStyle(fontSize: 11)),
                            ),
                            selected: isQuickMode,
                            onSelected: (val) {
                              if (val) setDialogState(() => isQuickMode = true);
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    if (!isQuickMode && announcements.isNotEmpty) ...[
                      EchoSphereText(
                        text: 'Select Notice to Broadcast:',
                        size: 11,
                        variant: TextVariant.bold,
                        color: context.colors.onSurface.opaque(0.8),
                      ),
                      const SizedBox(height: 6),
                      DropdownButtonFormField<int>(
                        value: selectedAnnouncementId,
                        isExpanded: true,
                        dropdownColor: context.colors.surface,
                        decoration: InputDecoration(
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                        items: announcements.map((a) {
                          return DropdownMenuItem<int>(
                            value: a.id,
                            child: Text(
                              '[#${a.id}] ${a.title}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontSize: 12, color: context.colors.onSurface),
                            ),
                          );
                        }).toList(),
                        onChanged: (val) {
                          if (val != null) {
                            setDialogState(() => selectedAnnouncementId = val);
                          }
                        },
                      ),
                    ] else ...[
                      TextField(
                        controller: quickTitleCtrl,
                        style: TextStyle(color: context.colors.onSurface),
                        decoration: InputDecoration(
                          labelText: 'Notice Title',
                          hintText: 'e.g. Lab Session Rescheduled',
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: quickContentCtrl,
                        maxLines: 3,
                        style: TextStyle(color: context.colors.onSurface),
                        decoration: InputDecoration(
                          labelText: 'Message Body',
                          hintText: 'e.g. All CSE 3rd sem students please report to Lab 3.',
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: EchoSphereText(
                    text: 'Cancel',
                    color: context.colors.onSurface.opaque(0.7),
                  ),
                ),
                EchoSphereButton(
                  color: context.colors.primary,
                  radius: 12,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  onTap: () async {
                    Navigator.pop(ctx);
                    if (!isQuickMode && selectedAnnouncementId != null) {
                      await _queueCtrl.enqueueNotice(
                        announcementId: selectedAnnouncementId!,
                        speakerNodeId: nodeId,
                      );
                      snackBar('Notice broadcast queued for $nodeName!');
                    } else if (isQuickMode) {
                      final title = quickTitleCtrl.text.trim();
                      final content = quickContentCtrl.text.trim();
                      if (title.isEmpty) {
                        snackBar('Please enter a notice title.');
                        return;
                      }
                      if (annCtrl != null) {
                        final auth = Get.isRegistered<AuthController>() ? Get.find<AuthController>() : null;
                        final user = auth?.currentUser.value;
                        final ok = await annCtrl.createAnnouncement(
                          title: title,
                          description: content.isNotEmpty ? content : title,
                          category: 'Academic',
                          priority: 'HIGH',
                          creatorRole: user?.role ?? 'Teacher',
                          creatorName: user?.fullName ?? 'Faculty',
                          department: user?.department ?? 'College-Wide',
                          targetAudience: 'All College',
                          deliverSpeaker: true,
                          deliverInApp: true,
                          speakerNodeId: nodeId,
                        );
                        if (ok) {
                          _queueCtrl.refreshQueue();
                          snackBar('Quick notice broadcast to $nodeName!');
                        }
                      }
                    }
                  },
                  child: const EchoSphereText(
                    text: 'Broadcast to Node',
                    size: 12,
                    variant: TextVariant.bold,
                    color: Colors.white,
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final canPop = ModalRoute.of(context)?.canPop ?? false;
    final authRegistered = Get.isRegistered<AuthController>();
    final user = authRegistered ? Get.find<AuthController>().currentUser.value : null;
    final role = user?.role ?? 'Teacher';
    final isStudent = user != null && role.toLowerCase() == 'student';

    if (isStudent) {
      return Scaffold(
        backgroundColor: context.colors.surface,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          leading: canPop ? const EchoSphereBackButton(fallbackRoute: '/home') : null,
          title: const EchoSphereText(
            text: 'Access Restricted',
            size: 16,
            variant: TextVariant.bold,
          ),
        ),
        body: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: EchoSphereContainer(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: context.colors.primary.withOpacity(0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.gpp_bad_rounded,
                      size: 48,
                      color: context.colors.primary,
                    ),
                  ),
                  const SizedBox(height: 16),
                  const EchoSphereText(
                    text: 'Smart Speaker System',
                    size: 16,
                    variant: TextVariant.bold,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  EchoSphereText(
                    text:
                        "I don't have the authority to display the smart speaker dashboard or playback queue. Please consult your department office or system administrator for assistance.",
                    size: 12,
                    textAlign: TextAlign.center,
                    color: context.colors.onSurface.opaque(0.7),
                  ),
                  const SizedBox(height: 20),
                  EchoSphereButton(
                    onTap: () {
                      if (canPop) {
                        Navigator.of(context).pop();
                      } else {
                        Get.offAllNamed('/home');
                      }
                    },
                    child: const EchoSphereText(
                      text: 'Return to Dashboard',
                      size: 12,
                      variant: TextVariant.bold,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: context.colors.surface,
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar Header with EchoSphere design aesthetics
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
              child: Row(
                children: [
                  if (canPop) ...[
                    const EchoSphereBackButton(fallbackRoute: '/home'),
                    const SizedBox(width: 4),
                  ],
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: context.colors.primary.opaque(0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.podcasts_rounded, size: 18, color: context.colors.primary),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        EchoSphereText(
                          text: 'Smart Speaker System',
                          size: 15,
                          variant: TextVariant.bold,
                          color: context.colors.primary,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        EchoSphereText(
                          text: 'Hardware PA Dashboard & Live Queue',
                          size: 10,
                          color: context.colors.onSurface.opaque(0.6),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 4),
                  IconButton(
                    icon: Icon(Icons.refresh_rounded, size: 20, color: context.colors.primary),
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    padding: EdgeInsets.zero,
                    tooltip: 'Refresh',
                    onPressed: () => _queueCtrl.refreshQueue(),
                  ),
                  const SizedBox(width: 4),
                  EchoSphereButton(
                    color: context.colors.primary,
                    radius: 12,
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    onTap: () => _showEmergencyDialog(context),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.warning_rounded, size: 13, color: Colors.white),
                        SizedBox(width: 4),
                        EchoSphereText(
                          text: 'EMERGENCY',
                          size: 10,
                          variant: TextVariant.bold,
                          color: Colors.white,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Divider(height: 1, color: context.colors.outline.opaque(0.15)),

            // Tab Bar with reactive count badges
            Obx(() => TabBar(
                  controller: _tabController,
                  labelColor: context.colors.primary,
                  unselectedLabelColor: context.colors.onSurface.opaque(0.6),
                  indicatorColor: context.colors.primary,
                  labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                  unselectedLabelStyle: const TextStyle(fontSize: 12),
                  tabs: [
                    Tab(
                      icon: const Icon(Icons.queue_music_rounded, size: 16),
                      text: 'Queue (${_queueCtrl.queueItems.length})',
                    ),
                    Tab(
                      icon: const Icon(Icons.developer_board_rounded, size: 16),
                      text: 'Nodes (${_queueCtrl.speakerNodes.length})',
                    ),
                  ],
                )),

            Obx(() {
              if (_queueCtrl.isLoading.value) {
                return const LinearProgressIndicator(minHeight: 2);
              }
              return const SizedBox.shrink();
            }),

            // Tab Content
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  _buildSpeakerQueueTab(context),
                  _buildHardwareDevicesTab(context),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSpeakerQueueTab(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () => _queueCtrl.refreshQueue(),
      child: Obx(() {
        final isPlaying = _queueCtrl.isPlaying.value;
        final hasItems = _queueCtrl.queueItems.isNotEmpty;
        final activeIdx = _queueCtrl.activeIndex.value;
        final activeItem = (hasItems && activeIdx >= 0 && activeIdx < _queueCtrl.queueItems.length)
            ? _queueCtrl.queueItems[activeIdx]
            : (hasItems ? _queueCtrl.queueItems.first : null);

        return Column(
          children: [
            // Active Player Glassmorphic Card
            Padding(
              padding: const EdgeInsets.all(12.0),
              child: EchoSphereContainer(
                padding: const EdgeInsets.all(12.0),
                enableGlow: true,
                color: context.colors.primary.opaque(0.08),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: context.colors.primary.opaque(0.15),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            isPlaying
                                ? Icons.graphic_eq_rounded
                                : Icons.pause_circle_filled_rounded,
                            color: context.colors.primary,
                            size: 20,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: EchoSphereText(
                                      text: isPlaying ? 'Broadcasting Now' : 'Speaker Queue Ready',
                                      size: 12,
                                      variant: TextVariant.bold,
                                      color: context.colors.primary,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  if (isPlaying) ...[
                                    const SizedBox(width: 6),
                                    AudioWaveformVisualizer(
                                      isPlaying: isPlaying,
                                      barCount: 6,
                                      height: 12,
                                      barWidth: 2.0,
                                      barSpacing: 1.5,
                                      color: context.colors.primary,
                                    ),
                                  ],
                                ],
                              ),
                              const SizedBox(height: 2),
                              EchoSphereText(
                                text: _queueCtrl.activeTitle,
                                size: 13,
                                variant: TextVariant.semiBold,
                                color: context.colors.onSurface,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 2),
                              EchoSphereText(
                                text: _queueCtrl.activeSubtitle,
                                size: 10,
                                color: context.colors.onSurface.opaque(0.6),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: () => _queueCtrl.togglePlayPause(),
                            borderRadius: BorderRadius.circular(18),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 250),
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: isPlaying
                                      ? [context.colors.primary, const Color(0xFF7C3AED)]
                                      : [const Color(0xFF8B5CF6), const Color(0xFF6D28D9)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                                borderRadius: BorderRadius.circular(18),
                                boxShadow: [
                                  BoxShadow(
                                    color: context.colors.primary.opaque(0.35),
                                    blurRadius: 8,
                                    spreadRadius: 1,
                                    offset: const Offset(0, 2),
                                  ),
                                ],
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                                    size: 16,
                                    color: Colors.white,
                                  ),
                                  const SizedBox(width: 4),
                                  EchoSphereText(
                                    text: isPlaying ? 'Pause' : 'Play',
                                    size: 11,
                                    variant: TextVariant.bold,
                                    color: Colors.white,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),

                    // Progress Bar & Live Countdown
                    if (hasItems) ...[
                      const SizedBox(height: 8),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: _queueCtrl.playbackProgress,
                          minHeight: 4,
                          backgroundColor: context.colors.outline.opaque(0.15),
                          valueColor: AlwaysStoppedAnimation<Color>(
                            context.colors.primary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: EchoSphereText(
                              text: isPlaying
                                  ? 'Playing once \u2022 auto-removes on finish'
                                  : 'Paused',
                              size: 9,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              color: context.colors.primary,
                            ),
                          ),
                          const SizedBox(width: 6),
                          EchoSphereText(
                            text: '${_queueCtrl.currentElapsedFormatted} / ${_queueCtrl.currentTotalFormatted}',
                            size: 9,
                            variant: TextVariant.bold,
                            color: context.colors.onSurface.opaque(0.7),
                          ),
                        ],
                      ),
                    ],

                    const SizedBox(height: 8),
                    Wrap(
                      alignment: WrapAlignment.spaceEvenly,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 4,
                      runSpacing: 4,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.skip_previous_rounded, size: 20),
                          tooltip: 'Previous',
                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                          padding: EdgeInsets.zero,
                          onPressed: (activeIdx > 0 && hasItems)
                              ? () => _queueCtrl.togglePlayPause(index: activeIdx - 1)
                              : null,
                        ),
                        IconButton(
                          icon: Icon(Icons.stop_rounded, size: 20, color: context.colors.primary),
                          tooltip: 'Stop Playback',
                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                          padding: EdgeInsets.zero,
                          onPressed: isPlaying ? () => _queueCtrl.stopCurrent() : null,
                        ),
                        IconButton(
                          icon: const Icon(Icons.skip_next_rounded, size: 20),
                          tooltip: 'Skip to Next',
                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                          padding: EdgeInsets.zero,
                          onPressed: hasItems ? () => _queueCtrl.skipCurrent() : null,
                        ),
                        IconButton(
                          icon: Icon(Icons.fast_forward_rounded, size: 20, color: context.colors.primary),
                          tooltip: 'Advance Hardware Queue',
                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                          padding: EdgeInsets.zero,
                          onPressed: () => _queueCtrl.advanceHardwareQueue(),
                        ),
                        IconButton(
                          icon: Icon(Icons.volume_up_rounded, size: 20, color: context.colors.primary),
                          tooltip: 'Voice Preview',
                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                          padding: EdgeInsets.zero,
                          onPressed: hasItems ? _previewAudio : null,
                        ),
                        if (!_isStudent)
                          IconButton(
                            icon: Icon(Icons.repeat_rounded, size: 20, color: context.colors.primary),
                            tooltip: 'Repeat Broadcast Schedule',
                            constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                            padding: EdgeInsets.zero,
                            onPressed: (hasItems && activeItem != null) ? () => _openRepeatScheduleForQueueItem(activeItem) : null,
                          ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Icon(Icons.info_outline_rounded,
                            size: 12, color: context.colors.onSurface.opaque(0.6)),
                        const SizedBox(width: 4),
                        Expanded(
                          child: EchoSphereText(
                            text: 'Plays each notice once and removes it upon completion.',
                            size: 10,
                            color: context.colors.onSurface.opaque(0.6),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            Divider(height: 1, color: context.colors.outline.opaque(0.12)),

            // Queue Action Bar (Header with Enqueue Notice button)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 6.0),
              child: Row(
                children: [
                  Expanded(
                    child: EchoSphereText(
                      text: 'Live Speaker Queue (${_queueCtrl.queueItems.length})',
                      size: 13,
                      variant: TextVariant.bold,
                      color: context.colors.primary,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  EchoSphereButton(
                    color: context.colors.primary,
                    radius: 12,
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    onTap: () => _showEnqueueDialog(context),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.add_to_queue_rounded, size: 13, color: Colors.white),
                        SizedBox(width: 4),
                        EchoSphereText(
                          text: 'Enqueue Notice',
                          size: 11,
                          variant: TextVariant.bold,
                          color: Colors.white,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // Queue Items List or Empty State
            Expanded(
              child: _queueCtrl.queueItems.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.queue_music_rounded,
                              size: 44,
                              color: context.colors.primary.opaque(0.4),
                            ),
                            const SizedBox(height: 10),
                            const EchoSphereText(
                              text: 'Speaker Queue is Empty',
                              size: 14,
                              variant: TextVariant.bold,
                            ),
                            const SizedBox(height: 4),
                            EchoSphereText(
                              text: 'No voice announcements waiting in queue. Publish a notice with speaker broadcast enabled or click "Enqueue Notice" above.',
                              size: 11,
                              color: context.colors.onSurface.opaque(0.6),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(12.0),
                      itemCount: _queueCtrl.queueItems.length,
                      itemBuilder: (ctx, i) {
                        final item = _queueCtrl.queueItems[i];
                        final isCurrent = (i == activeIdx);
                        final isCurrentlyPlaying = isCurrent && isPlaying;
                        final scheduledDisplay = _formatTime(
                          item['scheduledTime'],
                          item['scheduled_time'],
                        );
                        final titleStr = (item['title'] ?? 'Announcement').toString();
                        final deptStr = (item['department'] ?? 'College-Wide').toString();
                        final typeStr = (item['type'] ?? 'AI Speech').toString();
                        final statusStr = (item['status'] ?? 'Queued').toString();

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10.0),
                          child: EchoSphereContainer(
                            padding: const EdgeInsets.all(10.0),
                            color: isCurrentlyPlaying
                                ? context.colors.primary.opaque(0.12)
                                : isCurrent
                                    ? context.colors.primary.opaque(0.08)
                                    : null,
                            child: Row(
                              children: [
                                Container(
                                  width: 28,
                                  height: 28,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: isCurrentlyPlaying || isCurrent
                                        ? context.colors.primary
                                        : context.colors.primary.opaque(0.15),
                                  ),
                                  alignment: Alignment.center,
                                  child: EchoSphereText(
                                    text: '${i + 1}',
                                    size: 11,
                                    variant: TextVariant.bold,
                                    color: (isCurrentlyPlaying || isCurrent)
                                        ? Colors.white
                                        : context.colors.primary,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Wrap(
                                        spacing: 6,
                                        runSpacing: 4,
                                        crossAxisAlignment: WrapCrossAlignment.center,
                                        children: [
                                          EchoSphereBadge.secondary(
                                            label: typeStr,
                                          ),
                                          EchoSphereText(
                                            text: deptStr,
                                            size: 10,
                                            variant: TextVariant.bold,
                                            color: context.colors.primary,
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                          Builder(builder: (context) {
                                            final targetNodeId = item['speaker_node_id'] as int?;
                                            final nodeName = (item['node_name'] ?? _queueCtrl.getNodeName(targetNodeId)).toString();
                                            final isOnline = _queueCtrl.isNodeOnline(targetNodeId);
                                            return ConstrainedBox(
                                              constraints: const BoxConstraints(maxWidth: 130),
                                              child: Container(
                                                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                                decoration: BoxDecoration(
                                                  color: (isOnline ? context.colors.primary : context.colors.onSurface.opaque(0.3)).opaque(0.12),
                                                  borderRadius: BorderRadius.circular(6),
                                                  border: Border.all(
                                                    color: (isOnline ? context.colors.primary : context.colors.onSurface.opaque(0.3)).opaque(0.3),
                                                    width: 0.8,
                                                  ),
                                                ),
                                                child: Row(
                                                  mainAxisSize: MainAxisSize.min,
                                                  children: [
                                                    Container(
                                                      width: 5,
                                                      height: 5,
                                                      decoration: BoxDecoration(
                                                        shape: BoxShape.circle,
                                                        color: isOnline ? context.colors.primary : context.colors.onSurface.opaque(0.3),
                                                      ),
                                                    ),
                                                    const SizedBox(width: 4),
                                                    Flexible(
                                                      child: EchoSphereText(
                                                        text: '$nodeName \u2022 ${isOnline ? "ONLINE" : "OFFLINE"}',
                                                        size: 9,
                                                        variant: TextVariant.semiBold,
                                                        color: isOnline ? context.colors.primary : context.colors.onSurface.opaque(0.3),
                                                        maxLines: 1,
                                                        overflow: TextOverflow.ellipsis,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            );
                                          }),
                                          if (isCurrentlyPlaying)
                                            Container(
                                              padding: const EdgeInsets.symmetric(
                                                  horizontal: 6, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: context.colors.primary.opaque(0.15),
                                                borderRadius: BorderRadius.circular(8),
                                              ),
                                              child: FittedBox(
                                                fit: BoxFit.scaleDown,
                                                child: Row(
                                                  mainAxisSize: MainAxisSize.min,
                                                  children: [
                                                    AudioWaveformVisualizer(
                                                      isPlaying: isCurrentlyPlaying,
                                                      barCount: 5,
                                                      height: 10,
                                                      barWidth: 2,
                                                      barSpacing: 1.5,
                                                      color: context.colors.primary,
                                                    ),
                                                    const SizedBox(width: 4),
                                                    EchoSphereText(
                                                      text: 'PLAYING',
                                                      size: 9,
                                                      variant: TextVariant.bold,
                                                      color: context.colors.primary,
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: 3),
                                      EchoSphereText(
                                        text: titleStr,
                                        size: 13,
                                        variant: TextVariant.bold,
                                        color: context.colors.onSurface,
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: 3),
                                      EchoSphereText(
                                        text: 'Scheduled: $scheduledDisplay \u2022 Status: $statusStr',
                                        size: 10,
                                        color: context.colors.onSurface.opaque(0.6),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ],
                                  ),
                                ),
                                IconButton(
                                  tooltip: isCurrentlyPlaying ? 'Pause' : 'Play Now',
                                  constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
                                  padding: EdgeInsets.zero,
                                  icon: Container(
                                    padding: const EdgeInsets.all(5),
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: isCurrentlyPlaying
                                          ? context.colors.primary
                                          : context.colors.primary.opaque(0.15),
                                    ),
                                    child: Icon(
                                      isCurrentlyPlaying
                                          ? Icons.pause_rounded
                                          : Icons.play_arrow_rounded,
                                      size: 16,
                                      color: isCurrentlyPlaying
                                          ? Colors.white
                                          : context.colors.primary,
                                    ),
                                  ),
                                  onPressed: () => _queueCtrl.togglePlayPause(index: i),
                                ),
                                IconButton(
                                  constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                                  padding: EdgeInsets.zero,
                                  tooltip: 'Move Up',
                                  icon: Icon(
                                    Icons.arrow_upward_rounded,
                                    size: 16,
                                    color: context.colors.onSurface.opaque(i == 0 ? 0.2 : 0.7),
                                  ),
                                  onPressed: i == 0 ? null : () => _queueCtrl.reorderQueue(i, i - 1),
                                ),
                                IconButton(
                                  constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                                  padding: EdgeInsets.zero,
                                  tooltip: 'Move Down',
                                  icon: Icon(
                                    Icons.arrow_downward_rounded,
                                    size: 16,
                                    color: context.colors.onSurface.opaque(
                                        i == _queueCtrl.queueItems.length - 1 ? 0.2 : 0.7),
                                  ),
                                  onPressed: i == _queueCtrl.queueItems.length - 1
                                      ? null
                                      : () => _queueCtrl.reorderQueue(i, i + 1),
                                ),
                                if (!_isStudent)
                                  IconButton(
                                    constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                                    padding: EdgeInsets.zero,
                                    icon: Icon(Icons.repeat_rounded,
                                        size: 16, color: context.colors.primary),
                                    tooltip: 'Repeat Broadcast Schedule',
                                    onPressed: () => _openRepeatScheduleForQueueItem(item),
                                  ),
                                IconButton(
                                  constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                                  padding: EdgeInsets.zero,
                                  icon: Icon(Icons.delete_outline_rounded,
                                      size: 16, color: context.colors.primary),
                                  tooltip: 'Remove from Queue',
                                  onPressed: () => _queueCtrl.removeNotice(i),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        );
      }),
    );
  }

  Widget _buildHardwareDevicesTab(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () => _queueCtrl.refreshQueue(),
      child: Obx(() {
        final nodes = _queueCtrl.speakerNodes;

        return Column(
          children: [
            // Action Bar for Device Management
            Padding(
              padding: const EdgeInsets.all(12.0),
              child: Row(
                children: [
                  Expanded(
                    child: EchoSphereText(
                      text: 'Connected Microcontroller Nodes',
                      size: 13,
                      variant: TextVariant.bold,
                      color: context.colors.primary,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (!_isStudent)
                    EchoSphereButton(
                      color: context.colors.primary,
                      radius: 12,
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      onTap: () => _showRegisterNodeDialog(context),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.add_rounded, size: 13, color: Colors.white),
                          SizedBox(width: 4),
                          EchoSphereText(
                            text: 'Add Node',
                            size: 11,
                            variant: TextVariant.bold,
                            color: Colors.white,
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),

            // Device Cards List or Empty State
            Expanded(
              child: nodes.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.developer_board_rounded,
                              size: 44,
                              color: context.colors.primary.opaque(0.4),
                            ),
                            const SizedBox(height: 10),
                            const EchoSphereText(
                              text: 'No Microcontroller Nodes Registered',
                              size: 14,
                              variant: TextVariant.bold,
                            ),
                            const SizedBox(height: 4),
                            EchoSphereText(
                              text: 'Click "Add Node" above to register physical ESP32 PA speaker drivers.',
                              size: 11,
                              color: context.colors.onSurface.opaque(0.6),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 12.0),
                      itemCount: nodes.length,
                      itemBuilder: (ctx, i) {
                        final node = nodes[i];
                        final statusStr = (node['status'] ?? 'OFFLINE').toString().toUpperCase();
                        final bool isOnline = statusStr == 'ONLINE';
                        final nameStr = (node['name'] ?? 'Speaker Node').toString();
                        final ipStr = (node['ip_address'] ?? 'Not Assigned').toString();
                        final macStr = (node['mac_address'] ?? 'AA:BB:CC:DD:EE:00').toString();
                        final zoneStr = (node['zone'] ?? 'College-Wide').toString();
                        final cpuStr = _formatMetric(node['cpu_usage']);
                        final ramStr = _formatMetric(node['memory_usage']);
                        final volStr = _formatMetric(node['volume'], fallback: '80');

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10.0),
                          child: EchoSphereContainer(
                            padding: const EdgeInsets.all(12.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Node Header Row
                                Row(
                                  children: [
                                    Container(
                                      width: 8,
                                      height: 8,
                                      decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        color: isOnline ? context.colors.primary : context.colors.onSurface.opaque(0.3),
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    Expanded(
                                      child: EchoSphereText(
                                        text: nameStr,
                                        size: 13,
                                        variant: TextVariant.bold,
                                        color: context.colors.onSurface,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                    isOnline
                                        ? const EchoSphereBadge.secondary(label: 'ONLINE')
                                        : const EchoSphereBadge.muted(label: 'OFFLINE'),
                                  ],
                                ),
                                const SizedBox(height: 6),

                                // Telemetry & Details Row
                                Wrap(
                                  spacing: 10,
                                  runSpacing: 4,
                                  children: [
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.wifi_rounded, size: 12, color: context.colors.primary),
                                        const SizedBox(width: 4),
                                        Flexible(
                                          child: EchoSphereText(
                                            text: 'IP: $ipStr',
                                            size: 10,
                                            color: context.colors.onSurface.opaque(0.8),
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                      ],
                                    ),
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.numbers_rounded,
                                            size: 12, color: context.colors.primary),
                                        const SizedBox(width: 4),
                                        Flexible(
                                          child: EchoSphereText(
                                            text: 'MAC: $macStr',
                                            size: 10,
                                            color: context.colors.onSurface.opaque(0.8),
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                      ],
                                    ),
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.location_on_rounded,
                                            size: 12, color: context.colors.primary),
                                        const SizedBox(width: 4),
                                        Flexible(
                                          child: EchoSphereText(
                                            text: 'Zone: $zoneStr',
                                            size: 10,
                                            color: context.colors.onSurface.opaque(0.8),
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),

                                // Metrics
                                EchoSphereText(
                                  text: 'CPU: $cpuStr | RAM: $ramStr | Vol: $volStr',
                                  size: 10,
                                  color: context.colors.onSurface.opaque(0.6),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                const SizedBox(height: 4),

                                // Controls Wrap (Guarantees Zero Overflow on all screen sizes down to 320px)
                                Wrap(
                                  spacing: 4,
                                  runSpacing: 4,
                                  crossAxisAlignment: WrapCrossAlignment.center,
                                  children: [
                                    IconButton(
                                      icon: Icon(Icons.campaign_rounded,
                                          size: 16, color: context.colors.primary),
                                      constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                                      padding: EdgeInsets.zero,
                                      tooltip: 'Broadcast Notice to Node',
                                      onPressed: () {
                                        final nodeId = node['id'];
                                        if (nodeId == null || nodeId is! int) {
                                          snackBar('Invalid node id.');
                                          return;
                                        }
                                        _showDirectBroadcastDialog(context, nodeId, nameStr);
                                      },
                                    ),
                                    IconButton(
                                      icon: Icon(Icons.equalizer_rounded,
                                          size: 16, color: context.colors.primary),
                                      constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                                      padding: EdgeInsets.zero,
                                      tooltip: 'Test Tone',
                                      onPressed: () {
                                        final nodeId = node['id'];
                                        if (nodeId == null || nodeId is! int) {
                                          snackBar('Invalid node id.');
                                          return;
                                        }
                                        _queueCtrl.controlNode(nodeId, 'TEST_SPEAKER', nameStr);
                                      },
                                    ),
                                    IconButton(
                                      icon: Icon(Icons.volume_up_rounded,
                                          size: 16, color: context.colors.primary),
                                      constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                                      padding: EdgeInsets.zero,
                                      tooltip: 'Node Volume Slider',
                                      onPressed: () {
                                        final nodeId = node['id'];
                                        if (nodeId == null || nodeId is! int) {
                                          snackBar('Invalid node id.');
                                          return;
                                        }
                                        _showNodeVolumeDialog(context, nodeId, nameStr, (node['volume'] as num?)?.toDouble() ?? 80.0);
                                      },
                                    ),
                                    IconButton(
                                      icon: Icon(Icons.restart_alt_rounded,
                                          size: 16, color: context.colors.primary),
                                      constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                                      padding: EdgeInsets.zero,
                                      tooltip: 'Restart Node',
                                      onPressed: () {
                                        final nodeId = node['id'];
                                        if (nodeId == null || nodeId is! int) {
                                          snackBar('Invalid node id.');
                                          return;
                                        }
                                        _queueCtrl.controlNode(nodeId, 'RESTART', nameStr);
                                      },
                                    ),
                                    IconButton(
                                      icon: Icon(Icons.edit_rounded,
                                          size: 16, color: context.colors.primary),
                                      constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                                      padding: EdgeInsets.zero,
                                      tooltip: 'Configure Node',
                                      onPressed: () => _showEditNodeDialog(context, node),
                                    ),
                                    IconButton(
                                      icon: Icon(Icons.delete_outline_rounded,
                                          size: 16, color: context.colors.primary),
                                      constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                                      padding: EdgeInsets.zero,
                                      tooltip: 'Delete Node',
                                      onPressed: () {
                                        final nodeId = node['id'];
                                        if (nodeId != null && nodeId is int) {
                                          _queueCtrl.deleteNode(i, nodeId);
                                        }
                                      },
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        );
      }),
    );
  }

  void _showNodeVolumeDialog(BuildContext context, int nodeId, String nodeName, double currentVol) {
    double vol = currentVol.clamp(0.0, 100.0);
    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) => AlertDialog(
          title: Row(
            children: [
              Icon(Icons.volume_up_rounded, size: 20, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 8),
              Expanded(
                child: EchoSphereText(
                  text: '$nodeName Volume',
                  size: 15,
                  variant: TextVariant.bold,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const EchoSphereText(text: 'Hardware Output Level', size: 12),
                  EchoSphereText(
                    text: '${vol.round()}%',
                    size: 14,
                    variant: TextVariant.bold,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Slider(
                value: vol,
                min: 0,
                max: 100,
                divisions: 20,
                label: '${vol.round()}%',
                activeColor: Theme.of(context).colorScheme.primary,
                onChanged: (val) => setDlgState(() => vol = val),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(ctx);
                _queueCtrl.setNodeVolume(nodeId, vol.round(), nodeName);
              },
              child: const Text('Apply Volume'),
            ),
          ],
        ),
      ),
    );
  }
}
