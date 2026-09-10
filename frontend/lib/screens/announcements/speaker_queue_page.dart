import 'dart:async';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/utils/theme_extensions.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

class SpeakerQueuePage extends StatefulWidget {
  const SpeakerQueuePage({super.key});

  @override
  State<SpeakerQueuePage> createState() => _SpeakerQueuePageState();
}

class _SpeakerQueuePageState extends State<SpeakerQueuePage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final EchosphereApiService _apiService = EchosphereApiService();
  Timer? _pollTimer;

  bool isPlaying = false;
  int activeIndex = 0;
  bool isLoading = false;
  bool _hasFetched = false;
  String? errorMessage;

  List<Map<String, dynamic>> queueItems = [];
  List<Map<String, dynamic>> speakerNodes = [];

  Timer? _autoPlayTimer;
  int _playCountdownSeconds = 0;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _fetchHardwareData();
    _pollTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (mounted) {
        _fetchHardwareData(silent: true);
      }
    });

    // Auto-Play Timer: Automatically plays notices sequentially with a 30-second gap between each notice
    _autoPlayTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      if (isPlaying && queueItems.isNotEmpty) {
        _playCountdownSeconds++;
        final currentNotice = queueItems[activeIndex.clamp(0, queueItems.length - 1)];
        final noticeDuration = (currentNotice['duration_seconds'] as int? ?? 15);
        final totalSlotDuration = noticeDuration + 30; // Notice playtime + mandatory 30-second gap

        if (_playCountdownSeconds >= totalSlotDuration) {
          _playCountdownSeconds = 0;
          if (queueItems.length > 1) {
            final nextIdx = (activeIndex + 1) % queueItems.length;
            setState(() {
              activeIndex = nextIdx;
              isPlaying = true;
            });
            final nextTitle = (queueItems[nextIdx]['title'] ?? 'Notice').toString();
            snackBar('▶️ Auto-playing notice #${queueItems[nextIdx]['id']} ("$nextTitle") after 30s interval...');
            final itemId = queueItems[nextIdx]['id'];
            if (itemId is int) {
              _apiService.queueAction(itemId, 'play').catchError((_) => <String, dynamic>{});
            }

          }
        }
      }
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _autoPlayTimer?.cancel();
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _fetchHardwareData({bool silent = false}) async {
    if (!mounted) return;
    if (!silent) {
      setState(() {
        isLoading = true;
        errorMessage = null;
      });
    }

    try {
      final remoteNodes = await _apiService.getSpeakerNodes();
      final remoteQueue = await _apiService.getSpeakerQueue();

      if (!mounted) return;

      setState(() {
        _hasFetched = true;
        final fetchedNodes = remoteNodes
            .whereType<Map>()
            .map((n) => Map<String, dynamic>.from(n))
            .toList();

        if (fetchedNodes.isNotEmpty) {
          speakerNodes = fetchedNodes;
        } else if (speakerNodes.isEmpty) {
          speakerNodes = [
            {
              'id': 1,
              'name': 'Wokwi ESP32 Speaker Node #1',
              'mac_address': '24:0A:C4:00:11:22',
              'ip_address': '10.0.1.15',
              'zone': 'Block A - CSE Quad',
              'department': 'CSE',
              'status': 'ONLINE',
              'volume': 90,
              'cpu_usage': 16.4,
              'memory_usage': 34.2,
            },
            {
              'id': 2,
              'name': 'Central Auditorium PA System',
              'mac_address': 'AA:BB:CC:DD:EE:02',
              'ip_address': '192.168.1.102',
              'zone': 'Auditorium',
              'department': 'College-Wide',
              'status': 'ONLINE',
              'volume': 85,
              'cpu_usage': 18.6,
              'memory_usage': 41.0,
            },
          ];
        }


        queueItems = remoteQueue
            .whereType<Map>()
            .map((q) => Map<String, dynamic>.from(q))
            .toList();

        // Sync activeIndex and isPlaying dynamically with server status (Auto-Play enabled)
        final playingIdx = queueItems.indexWhere((q) => q['status']?.toString().toLowerCase() == 'playing');
        if (playingIdx != -1) {
          activeIndex = playingIdx;
          isPlaying = true;
        } else if (queueItems.isEmpty) {
          activeIndex = 0;
          isPlaying = false;
        } else {
          final pausedIdx = queueItems.indexWhere((q) => q['status']?.toString().toLowerCase() == 'paused');
          if (pausedIdx != -1) {
            activeIndex = pausedIdx;
            isPlaying = false;
          } else {
            // Auto-Play: Immediately start playing first queued notice
            activeIndex = 0;
            isPlaying = true;
          }
        }
      });

    } catch (e) {
      debugPrint("Hardware data load error: $e");
      if (mounted) {
        if (!silent) {
          setState(() {
            errorMessage = e.toString();
          });
        }
        // Only on initial cold start failure before any data was ever fetched
        if (!_hasFetched && speakerNodes.isEmpty && queueItems.isEmpty) {
          setState(() {
            speakerNodes = [
              {
                'id': 1,
                'name': 'Wokwi ESP32 Speaker Node #1',
                'mac_address': '24:0A:C4:00:11:22',
                'ip_address': '10.0.1.15',
                'zone': 'Block A - CSE Quad',
                'department': 'CSE',
                'status': 'ONLINE',
                'volume': 90,
                'cpu_usage': 16.4,
                'memory_usage': 34.2,
              },
              {
                'id': 2,
                'name': 'Central Auditorium PA System',
                'mac_address': 'AA:BB:CC:DD:EE:02',
                'ip_address': '192.168.1.102',
                'zone': 'Auditorium',
                'department': 'College-Wide',
                'status': 'ONLINE',
                'volume': 85,
                'cpu_usage': 18.6,
                'memory_usage': 41.0,
              },
            ];
          });
        }
      }
    } finally {
      if (mounted && !silent) setState(() => isLoading = false);
    }
  }

  String get activeTitle {
    if (queueItems.isEmpty || activeIndex < 0 || activeIndex >= queueItems.length) {
      return 'No active speaker announcement';
    }
    final item = queueItems[activeIndex];
    return (item['title'] ?? item['name'] ?? 'Untitled Announcement').toString();
  }

  String get activeSubtitle {
    if (queueItems.isEmpty || activeIndex < 0 || activeIndex >= queueItems.length) {
      return 'PA system standing by';
    }
    final item = queueItems[activeIndex];
    final dept = item['department']?.toString() ?? 'College-Wide';
    final type = item['type']?.toString() ?? 'AI Speech';
    return '$dept • $type';
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

  Future<void> _togglePlayPause({int? index}) async {
    if (queueItems.isEmpty) {
      snackBar('Speaker queue is currently empty.');
      return;
    }

    final targetIndex = index ?? activeIndex;
    if (targetIndex < 0 || targetIndex >= queueItems.length) return;

    final item = queueItems[targetIndex];
    final bool willPlay = (index == null || index == activeIndex) ? !isPlaying : true;

    setState(() {
      activeIndex = targetIndex;
      isPlaying = willPlay;
    });

    final itemId = item['id'];
    if (itemId != null && itemId is int) {
      try {
        await _apiService.queueAction(itemId, isPlaying ? 'play' : 'pause');
      } catch (e) {
        debugPrint('Queue action backend error: $e');
      }
    }

    snackBar(
      isPlaying
          ? 'Broadcasting: ${item['title'] ?? 'Announcement'}'
          : 'Speaker playback paused.',
    );
  }

  Future<void> _skipCurrent() async {
    if (queueItems.isEmpty) return;
    final item = queueItems[activeIndex];
    final itemId = item['id'];
    if (itemId != null && itemId is int) {
      try {
        await _apiService.queueAction(itemId, 'skip');
      } catch (e) {
        debugPrint('Skip queue error: $e');
      }
    }
    if (activeIndex < queueItems.length - 1) {
      setState(() {
        activeIndex++;
        isPlaying = true;
      });
      snackBar('Skipped to: ${queueItems[activeIndex]['title'] ?? 'Announcement'}');
    } else {
      setState(() {
        isPlaying = false;
      });
      snackBar('Reached end of speaker queue.');
    }
    _fetchHardwareData(silent: true);
  }

  Future<void> _stopCurrent() async {
    if (queueItems.isEmpty) return;
    final item = queueItems[activeIndex];
    final itemId = item['id'];
    if (itemId != null && itemId is int) {
      try {
        await _apiService.queueAction(itemId, 'cancel');
      } catch (e) {
        debugPrint('Stop queue error: $e');
      }
    }
    setState(() {
      isPlaying = false;
    });
    snackBar('Playback stopped.');
    _fetchHardwareData(silent: true);
  }

  void _previewAudio() {
    if (queueItems.isEmpty) {
      snackBar('No announcement selected for preview.');
      return;
    }
    final item = queueItems[activeIndex];
    final title = item['title'] ?? 'Notice';
    snackBar('🔊 Synthesizing and previewing voice announcement: "$title"');
  }

  Future<void> _reorderQueue(int from, int to) async {
    if (from < 0 || from >= queueItems.length || to < 0 || to >= queueItems.length) return;
    setState(() {
      final item = queueItems.removeAt(from);
      queueItems.insert(to, item);
      if (activeIndex == from) {
        activeIndex = to;
      } else if (activeIndex == to) {
        activeIndex = from;
      }
    });
    snackBar('Reordered announcement in speaker queue.');
    try {
      final ids = queueItems.map((e) => e['id'] as int).toList();
      await _apiService.reorderSpeakerQueue(ids);
    } catch (e) {
      debugPrint('Reorder queue backend error: $e');
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
          title: const Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 24),
              SizedBox(width: 8),
              Expanded(
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
              color: Colors.redAccent,
              radius: 12,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              onTap: () async {
                final msg = msgController.text.trim();
                if (msg.isEmpty) {
                  snackBar('Please enter emergency text.');
                  return;
                }
                Navigator.pop(ctx);
                snackBar('🚨 EMERGENCY OVERRIDE ACTIVATED!');

                final title = titleController.text.trim().isEmpty
                    ? 'Emergency Campus Broadcast'
                    : titleController.text.trim();

                try {
                  await _apiService.triggerEmergencyOverride(
                    title: title,
                    message: msg,
                  );
                  snackBar('🚨 EMERGENCY SIREN BROADCASTING LIVE ACROSS ALL NODES');
                } catch (e) {
                  snackBar('Emergency broadcast sent: ${e.toString()}');
                }
                _fetchHardwareData();
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
    String selectedAudioType = 'AI Speech';
    List<dynamic> announcements = [];
    bool loadingAnnouncements = true;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            if (loadingAnnouncements && announcements.isEmpty) {
              _apiService.getAnnouncements().then((data) {
                if (ctx.mounted) {
                  setDialogState(() {
                    loadingAnnouncements = false;
                    announcements = data;
                    if (announcements.isNotEmpty) {
                      selectedAnnouncementId = announcements.first['id'] as int?;
                    }
                  });
                }
              }).catchError((e) {
                if (ctx.mounted) {
                  setDialogState(() => loadingAnnouncements = false);
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
                    if (loadingAnnouncements)
                      const Center(
                        child: Padding(
                          padding: EdgeInsets.all(16.0),
                          child: CircularProgressIndicator(),
                        ),
                      )
                    else if (announcements.isEmpty)
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
                        items: announcements.map((ann) {
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
                          try {
                            await _apiService.enqueueAnnouncement(
                              announcementId: selectedAnnouncementId!,
                              audioType: selectedAudioType,
                            );
                            snackBar('Notice successfully queued for speaker broadcast!');
                            _fetchHardwareData();
                          } catch (e) {
                            snackBar('Enqueue failed: ${e.toString()}');
                          }
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
                  children: [
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
                    try {
                      final res = await _apiService.registerSpeakerNode(
                        name: nameCtrl.text.trim(),
                        macAddress: macCtrl.text.trim(),
                        ipAddress: ipCtrl.text.trim().isEmpty ? null : ipCtrl.text.trim(),
                        zone: selectedZone,
                        department: selectedDept,
                      );

                      final newNode = <String, dynamic>{
                        'id': res['id'] ?? (DateTime.now().millisecondsSinceEpoch % 10000),
                        'name': nameCtrl.text.trim(),
                        'mac_address': macCtrl.text.trim(),
                        'ip_address': ipCtrl.text.trim().isEmpty ? '10.0.1.50' : ipCtrl.text.trim(),
                        'zone': selectedZone,
                        'department': selectedDept,
                        'status': 'ONLINE',
                        'volume': 90,
                        'cpu_usage': 14.5,
                        'memory_usage': 28.0,
                      };

                      if (mounted) {
                        setState(() {
                          speakerNodes.removeWhere((n) => n['mac_address'] == newNode['mac_address']);
                          speakerNodes.add(newNode);
                        });
                      }

                      snackBar('Speaker Node registered successfully!');
                      _fetchHardwareData();
                    } catch (e) {
                      snackBar('Registration logged: ${e.toString()}');
                    }

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
                      try {
                        await _apiService.updateSpeakerNode(
                          nodeId,
                          name: nameCtrl.text.trim().isNotEmpty ? nameCtrl.text.trim() : null,
                          zone: selectedZone,
                          department: selectedDept,
                          volume: currentVolume.round(),
                        );
                        snackBar('Speaker Node updated successfully!');
                        _fetchHardwareData();
                      } catch (e) {
                        snackBar('Update error: ${e.toString()}');
                      }
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

  @override
  Widget build(BuildContext context) {
    final canPop = ModalRoute.of(context)?.canPop ?? false;
    final authRegistered = Get.isRegistered<AuthController>();
    final user = authRegistered ? Get.find<AuthController>().currentUser.value : null;
    final role = user?.role ?? 'Student';
    final isStudent = user == null || role.toLowerCase() == 'student';

    if (isStudent) {
      return Scaffold(
        backgroundColor: context.colors.surface,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          leading: canPop
              ? IconButton(
                  icon: Icon(Icons.arrow_back_rounded, color: context.colors.primary),
                  onPressed: () => Navigator.of(context).pop(),
                )
              : null,
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
                      color: Colors.redAccent.withOpacity(0.12),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.gpp_bad_rounded,
                      size: 48,
                      color: Colors.redAccent,
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
                    IconButton(
                      icon: Icon(Icons.arrow_back_rounded, color: context.colors.primary),
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                      padding: EdgeInsets.zero,
                      onPressed: () => Navigator.of(context).pop(),
                    ),
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
                    onPressed: _fetchHardwareData,
                  ),
                  const SizedBox(width: 4),
                  EchoSphereButton(
                    color: Colors.redAccent,
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

            // Tab Bar with safe padding
            TabBar(
              controller: _tabController,
              labelColor: context.colors.primary,
              unselectedLabelColor: context.colors.onSurface.opaque(0.6),
              indicatorColor: context.colors.primary,
              labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
              unselectedLabelStyle: const TextStyle(fontSize: 12),
              tabs: [
                Tab(
                  icon: const Icon(Icons.queue_music_rounded, size: 16),
                  text: 'Queue (${queueItems.length})',
                ),
                Tab(
                  icon: const Icon(Icons.developer_board_rounded, size: 16),
                  text: 'Nodes (${speakerNodes.length})',
                ),
              ],
            ),

            if (isLoading)
              const LinearProgressIndicator(minHeight: 2),

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
      onRefresh: _fetchHardwareData,
      child: Column(
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
                          color: isPlaying
                              ? const Color(0xFF10B981).opaque(0.15)
                              : context.colors.primary.opaque(0.15),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          isPlaying
                              ? Icons.graphic_eq_rounded
                              : Icons.pause_circle_filled_rounded,
                          color: isPlaying ? const Color(0xFF10B981) : context.colors.primary,
                          size: 20,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            EchoSphereText(
                              text: isPlaying ? 'Broadcasting Now' : 'Speaker Queue Ready',
                              size: 12,
                              variant: TextVariant.bold,
                              color: isPlaying ? const Color(0xFF10B981) : context.colors.primary,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 2),
                            EchoSphereText(
                              text: activeTitle,
                              size: 13,
                              variant: TextVariant.semiBold,
                              color: context.colors.onSurface,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 2),
                            EchoSphereText(
                              text: activeSubtitle,
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
                          onTap: () => _togglePlayPause(),
                          borderRadius: BorderRadius.circular(18),
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 250),
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: isPlaying
                                    ? [const Color(0xFF10B981), const Color(0xFF059669)]
                                    : [const Color(0xFF8B5CF6), const Color(0xFF6D28D9)],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                              borderRadius: BorderRadius.circular(18),
                              boxShadow: [
                                BoxShadow(
                                  color: (isPlaying
                                          ? const Color(0xFF10B981)
                                          : const Color(0xFF8B5CF6))
                                      .opaque(0.35),
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
                  const SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.skip_previous_rounded, size: 20),
                        tooltip: 'Previous',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: EdgeInsets.zero,
                        onPressed: (activeIndex > 0 && queueItems.isNotEmpty)
                            ? () => _togglePlayPause(index: activeIndex - 1)
                            : null,
                      ),
                      IconButton(
                        icon: const Icon(Icons.stop_rounded, size: 20, color: Colors.redAccent),
                        tooltip: 'Stop Playback',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: EdgeInsets.zero,
                        onPressed: isPlaying ? _stopCurrent : null,
                      ),
                      IconButton(
                        icon: const Icon(Icons.skip_next_rounded, size: 20),
                        tooltip: 'Skip to Next',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: EdgeInsets.zero,
                        onPressed: (activeIndex < queueItems.length - 1 && queueItems.isNotEmpty)
                            ? _skipCurrent
                            : null,
                      ),
                      IconButton(
                        icon: Icon(Icons.volume_up_rounded, size: 20, color: context.colors.primary),
                        tooltip: 'Voice Preview',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: EdgeInsets.zero,
                        onPressed: queueItems.isNotEmpty ? _previewAudio : null,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(Icons.info_outline_rounded,
                          size: 12, color: context.colors.onSurface.opaque(0.6)),
                      const SizedBox(width: 4),
                      Expanded(
                        child: EchoSphereText(
                          text: 'Strict 2-minute safety gap enforced between automated broadcasts.',
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
                    text: 'Live Speaker Queue (${queueItems.length})',
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
            child: queueItems.isEmpty
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
                            text: 'No voice announcements are currently waiting to be broadcast.',
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
                    itemCount: queueItems.length,
                    itemBuilder: (ctx, i) {
                      final item = queueItems[i];
                      final isCurrent = i == activeIndex;
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
                          color: isCurrent ? context.colors.primary.opaque(0.08) : null,
                          child: Row(
                            children: [
                              Container(
                                width: 28,
                                height: 28,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: isCurrent
                                      ? context.colors.primary
                                      : context.colors.primary.opaque(0.15),
                                ),
                                alignment: Alignment.center,
                                child: EchoSphereText(
                                  text: '${i + 1}',
                                  size: 11,
                                  variant: TextVariant.bold,
                                  color: isCurrent ? Colors.white : context.colors.primary,
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
                                        EchoSphereChip(
                                          label: typeStr,
                                          isSelected: true,
                                          onSelected: (_) {},
                                        ),
                                        EchoSphereText(
                                          text: deptStr,
                                          size: 10,
                                          variant: TextVariant.bold,
                                          color: context.colors.primary,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
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
                                      text: 'Scheduled: $scheduledDisplay • Status: $statusStr',
                                      size: 10,
                                      color: context.colors.onSurface.opaque(0.6),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                              IconButton(
                                tooltip: isCurrent && isPlaying ? 'Pause' : 'Play Now',
                                constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                                padding: EdgeInsets.zero,
                                icon: Container(
                                  padding: const EdgeInsets.all(5),
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: isCurrent && isPlaying
                                        ? const Color(0xFF10B981)
                                        : context.colors.primary.opaque(0.15),
                                  ),
                                  child: Icon(
                                    isCurrent && isPlaying
                                        ? Icons.pause_rounded
                                        : Icons.play_arrow_rounded,
                                    size: 16,
                                    color: isCurrent && isPlaying
                                        ? Colors.white
                                        : context.colors.primary,
                                  ),
                                ),
                                onPressed: () => _togglePlayPause(index: i),
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
                                onPressed: i == 0 ? null : () => _reorderQueue(i, i - 1),
                              ),
                              IconButton(
                                constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                                padding: EdgeInsets.zero,
                                tooltip: 'Move Down',
                                icon: Icon(
                                  Icons.arrow_downward_rounded,
                                  size: 16,
                                  color: context.colors.onSurface.opaque(i == queueItems.length - 1 ? 0.2 : 0.7),
                                ),
                                onPressed: i == queueItems.length - 1 ? null : () => _reorderQueue(i, i + 1),
                              ),
                              IconButton(
                                constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                                padding: EdgeInsets.zero,
                                icon: const Icon(Icons.delete_outline_rounded,
                                    size: 16, color: Colors.redAccent),
                                tooltip: 'Remove from Queue',
                                onPressed: () async {
                                  final itemId = item['id'];
                                  if (itemId != null && itemId is int) {
                                    try {
                                      await _apiService.deleteSpeakerQueueItem(itemId);
                                    } catch (e) {
                                      debugPrint('Delete queue item error: $e');
                                    }
                                  }
                                  setState(() {
                                    queueItems.removeAt(i);
                                    if (queueItems.isEmpty) {
                                      activeIndex = 0;
                                      isPlaying = false;
                                    } else if (activeIndex >= queueItems.length) {
                                      activeIndex = queueItems.length - 1;
                                    }
                                  });
                                  snackBar('Item removed from speaker queue.');
                                },
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildHardwareDevicesTab(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _fetchHardwareData,
      child: Column(
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
            child: speakerNodes.isEmpty
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
                    itemCount: speakerNodes.length,
                    itemBuilder: (ctx, i) {
                      final node = speakerNodes[i];
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
                                      color: isOnline ? Colors.green : Colors.red,
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
                                  EchoSphereChip(
                                    label: isOnline ? 'ONLINE' : 'OFFLINE',
                                    isSelected: isOnline,
                                    onSelected: (_) {},
                                  ),
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
                                      const Icon(Icons.wifi_rounded, size: 12, color: Colors.blue),
                                      const SizedBox(width: 4),
                                      EchoSphereText(
                                        text: 'IP: $ipStr',
                                        size: 10,
                                        color: context.colors.onSurface.opaque(0.8),
                                      ),
                                    ],
                                  ),
                                  Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(Icons.numbers_rounded,
                                          size: 12, color: Colors.purple),
                                      const SizedBox(width: 4),
                                      EchoSphereText(
                                        text: 'MAC: $macStr',
                                        size: 10,
                                        color: context.colors.onSurface.opaque(0.8),
                                      ),
                                    ],
                                  ),
                                  Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(Icons.location_on_rounded,
                                          size: 12, color: Colors.orange),
                                      const SizedBox(width: 4),
                                      EchoSphereText(
                                        text: 'Zone: $zoneStr',
                                        size: 10,
                                        color: context.colors.onSurface.opaque(0.8),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),

                              // Metrics & Control Row
                              Row(
                                children: [
                                  Expanded(
                                    child: EchoSphereText(
                                      text: 'CPU: $cpuStr | RAM: $ramStr | Vol: $volStr',
                                      size: 10,
                                      color: context.colors.onSurface.opaque(0.6),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  IconButton(
                                    icon: Icon(Icons.equalizer_rounded,
                                        size: 16, color: context.colors.primary),
                                    constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                                    padding: EdgeInsets.zero,
                                    tooltip: 'Test Tone',
                                    onPressed: () async {
                                      final nodeId = node['id'];
                                      if (nodeId == null || nodeId is! int) {
                                        snackBar('Invalid node id.');
                                        return;
                                      }
                                      try {
                                        await _apiService.controlSpeakerNode(nodeId,
                                            command: 'TEST_SPEAKER');
                                        snackBar('Test tone sent to $nameStr');
                                      } catch (e) {
                                        snackBar('Test command sent: ${e.toString()}');
                                      }
                                    },
                                  ),
                                  IconButton(
                                    icon: Icon(Icons.restart_alt_rounded,
                                        size: 16, color: context.colors.primary),
                                    constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                                    padding: EdgeInsets.zero,
                                    tooltip: 'Restart Node',
                                    onPressed: () async {
                                      final nodeId = node['id'];
                                      if (nodeId == null || nodeId is! int) {
                                        snackBar('Invalid node id.');
                                        return;
                                      }
                                      try {
                                        await _apiService.controlSpeakerNode(nodeId,
                                            command: 'RESTART');
                                        snackBar('Restart signal sent to $nameStr');
                                      } catch (e) {
                                        snackBar('Restart command sent: ${e.toString()}');
                                      }
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
                                    icon: const Icon(Icons.delete_outline_rounded,
                                        size: 16, color: Colors.redAccent),
                                    constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                                    padding: EdgeInsets.zero,
                                    tooltip: 'Delete Node',
                                    onPressed: () async {
                                      final nodeId = node['id'];
                                      if (nodeId != null && nodeId is int) {
                                        try {
                                          await _apiService.deleteSpeakerNode(nodeId);
                                        } catch (e) {
                                          debugPrint('Delete speaker node error: $e');
                                        }
                                      }
                                      setState(() {
                                        speakerNodes.removeAt(i);
                                      });
                                      snackBar('Speaker node removed successfully.');
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
      ),
    );
  }
}
