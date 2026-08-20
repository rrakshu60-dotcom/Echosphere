import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/utils/theme_extensions.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class SpeakerQueuePage extends StatefulWidget {
  const SpeakerQueuePage({super.key});

  @override
  State<SpeakerQueuePage> createState() => _SpeakerQueuePageState();
}

class _SpeakerQueuePageState extends State<SpeakerQueuePage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final EchosphereApiService _apiService = EchosphereApiService();

  bool isPlaying = false;
  int activeIndex = 0;
  bool isLoading = false;

  List<Map<String, dynamic>> queueItems = [
    {
      'id': 101,
      'title': 'Emergency Campus Weather Advisory',
      'department': 'College-Wide',
      'duration': '00:45',
      'scheduledTime': DateTime.now().add(const Duration(minutes: 2)),
      'type': 'AI Speech',
      'status': 'Next in Queue',
    },
    {
      'id': 102,
      'title': 'End Semester Practical Exam Guidelines',
      'department': 'CSE Dept',
      'duration': '01:20',
      'scheduledTime': DateTime.now().add(const Duration(minutes: 8)),
      'type': 'Recorded Voice',
      'status': 'Queued',
    },
    {
      'id': 103,
      'title': 'Placement Drive Briefing - TCS & Infosys',
      'department': 'Placement Cell',
      'duration': '01:00',
      'scheduledTime': DateTime.now().add(const Duration(minutes: 15)),
      'type': 'AI Speech',
      'status': 'Queued',
    },
  ];

  List<Map<String, dynamic>> speakerNodes = [
    {
      'id': 1,
      'name': 'CSE Block A Horn Speaker',
      'mac_address': 'AA:BB:CC:DD:EE:01',
      'ip_address': '192.168.1.101',
      'zone': 'Block A',
      'department': 'CSE',
      'status': 'ONLINE',
      'volume': 85,
      'cpu_usage': 14.2,
      'memory_usage': 32.5,
    },
    {
      'id': 2,
      'name': 'Central Auditorium PA System',
      'mac_address': 'AA:BB:CC:DD:EE:02',
      'ip_address': '192.168.1.102',
      'zone': 'Auditorium',
      'department': 'College-Wide',
      'status': 'ONLINE',
      'volume': 90,
      'cpu_usage': 18.6,
      'memory_usage': 41.0,
    },
    {
      'id': 3,
      'name': 'Library Reading Hall Speaker',
      'mac_address': 'AA:BB:CC:DD:EE:03',
      'ip_address': '192.168.1.103',
      'zone': 'Library',
      'department': 'College-Wide',
      'status': 'OFFLINE',
      'volume': 70,
      'cpu_usage': 0.0,
      'memory_usage': 0.0,
    },
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _fetchHardwareData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _fetchHardwareData() async {
    if (!mounted) return;
    setState(() => isLoading = true);
    try {
      final remoteNodes = await _apiService.getSpeakerNodes();
      final remoteQueue = await _apiService.getSpeakerQueue();

      if (!mounted) return;
      if (remoteNodes.isNotEmpty) {
        setState(() {
          speakerNodes = remoteNodes.map((n) => Map<String, dynamic>.from(n)).toList();
        });
      }
      if (remoteQueue.isNotEmpty) {
        setState(() {
          queueItems = remoteQueue.map((q) => Map<String, dynamic>.from(q)).toList();
        });
      }
    } catch (e) {
      debugPrint("Loaded fallback state: $e");
    } finally {
      if (mounted) setState(() => isLoading = false);
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
              child: EchoSphereText(text: 'Cancel', color: context.colors.onSurface.opaque(0.7)),
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
                snackBar('Triggering Emergency Override...');
                try {
                  await _apiService.triggerEmergencyOverride(
                    title: titleController.text,
                    message: msg,
                  );
                  snackBar('EMERGENCY BROADCAST LIVE ACROSS CAMPUS');
                } catch (e) {
                  snackBar('Emergency override sent: ${e.toString()}');
                }
              },
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.warning_rounded, size: 16, color: Colors.white),
                  SizedBox(width: 6),
                  EchoSphereText(
                    text: 'BROADCAST NOW',
                    size: 12,
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

  void _showRegisterNodeDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    final macCtrl = TextEditingController();
    final ipCtrl = TextEditingController();
    String selectedZone = 'Block A';

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
                size: 16,
                variant: TextVariant.bold,
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
                      dropdownColor: context.colors.surface,
                      decoration: InputDecoration(
                        labelText: 'Zone',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      items: ['College-Wide', 'Block A', 'Block B', 'Auditorium', 'Library', 'Hostel']
                          .map((z) => DropdownMenuItem(value: z, child: Text(z, style: TextStyle(color: context.colors.onSurface))))
                          .toList(),
                      onChanged: (val) {
                        if (val != null) setDialogState(() => selectedZone = val);
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: EchoSphereText(text: 'Cancel', color: context.colors.onSurface.opaque(0.7)),
                ),
                EchoSphereButton(
                  color: context.colors.primary,
                  radius: 12,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  onTap: () async {
                    if (nameCtrl.text.isEmpty || macCtrl.text.isEmpty) {
                      snackBar('Name and MAC Address are required.');
                      return;
                    }
                    Navigator.pop(ctx);
                    try {
                      await _apiService.registerSpeakerNode(
                        name: nameCtrl.text.trim(),
                        macAddress: macCtrl.text.trim(),
                        ipAddress: ipCtrl.text.trim().isEmpty ? null : ipCtrl.text.trim(),
                        zone: selectedZone,
                      );
                      snackBar('Speaker Node registered successfully!');
                      _fetchHardwareData();
                    } catch (e) {
                      snackBar('Registration error: ${e.toString()}');
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

  @override
  Widget build(BuildContext context) {
    final canPop = ModalRoute.of(context)?.canPop ?? false;

    return Scaffold(
      backgroundColor: context.colors.background,
      body: SafeArea(
        child: Column(
          children: [
            // Header Bar matching EchoSphere theme styling
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
              child: Row(
                children: [
                  if (canPop) ...[
                    IconButton(
                      icon: Icon(Icons.arrow_back_rounded, color: context.colors.primary),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    const SizedBox(width: 4),
                  ],
                  Icon(Icons.speaker_group_rounded, size: 24, color: context.colors.primary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        EchoSphereText(
                          text: 'Smart Speaker System',
                          size: 16,
                          variant: TextVariant.bold,
                          color: context.colors.primary,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        EchoSphereText(
                          text: 'Hardware Dashboard & Live Broadcast',
                          size: 11,
                          color: context.colors.onSurface.opaque(0.6),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton(
                    icon: Icon(Icons.refresh_rounded, color: context.colors.primary),
                    tooltip: 'Refresh',
                    onPressed: _fetchHardwareData,
                  ),
                  EchoSphereButton(
                    color: Colors.redAccent,
                    radius: 14,
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    onTap: () => _showEmergencyDialog(context),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.warning_rounded, size: 14, color: Colors.white),
                        SizedBox(width: 4),
                        EchoSphereText(
                          text: 'EMERGENCY',
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
            Divider(height: 1, color: context.colors.outline.opaque(0.2)),

            // Navigation Tabs styled with context.colors
            TabBar(
              controller: _tabController,
              labelColor: context.colors.primary,
              unselectedLabelColor: context.colors.onSurface.opaque(0.6),
              indicatorColor: context.colors.primary,
              tabs: const [
                Tab(
                  icon: Icon(Icons.queue_music_rounded, size: 18),
                  text: 'Speaker Queue',
                ),
                Tab(
                  icon: Icon(Icons.developer_board_rounded, size: 18),
                  text: 'Hardware Devices',
                ),
              ],
            ),

            // Tab Body Content
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
    return Column(
      children: [
        // Active Speaker Player Card with Theme Glassmorphism Glow
        Padding(
          padding: const EdgeInsets.all(12.0),
          child: EchoSphereContainer(
            padding: const EdgeInsets.all(14.0),
            enableGlow: true,
            color: context.colors.primary.opaque(0.10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      isPlaying ? Icons.graphic_eq_rounded : Icons.pause_circle_filled_rounded,
                      color: context.colors.primary,
                      size: 26,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          EchoSphereText(
                            text: isPlaying ? 'Broadcasting Now' : 'Speaker Queue Ready',
                            size: 13,
                            variant: TextVariant.bold,
                            color: context.colors.primary,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          EchoSphereText(
                            text: queueItems.isNotEmpty ? queueItems[activeIndex]['title'] : 'No active speaker announcement',
                            size: 12,
                            variant: TextVariant.semiBold,
                            color: context.colors.onSurface,
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
                        onTap: () {
                          setState(() => isPlaying = !isPlaying);
                          snackBar(isPlaying ? 'Started speaker playback...' : 'Paused speaker queue.');
                        },
                        borderRadius: BorderRadius.circular(20),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 250),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: isPlaying
                                  ? [const Color(0xFF9333EA), const Color(0xFF6366F1)]
                                  : [const Color(0xFF8B5CF6), const Color(0xFF7C3AED)],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFF8B5CF6).opaque(0.35),
                                blurRadius: 10,
                                spreadRadius: 1,
                                offset: const Offset(0, 3),
                              ),
                            ],
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                                size: 18,
                                color: Colors.white,
                              ),
                              const SizedBox(width: 6),
                              EchoSphereText(
                                text: isPlaying ? 'Pause' : 'Play',
                                size: 12,
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
                EchoSphereText(
                  text: 'Minimum 2-minute gap strictly maintained between speaker announcements.',
                  size: 11,
                  color: context.colors.onSurface.opaque(0.6),
                ),
              ],
            ),
          ),
        ),
        Divider(height: 1, color: context.colors.outline.opaque(0.15)),

        // Queue Items List
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(12.0),
            itemCount: queueItems.length,
            itemBuilder: (ctx, i) {
              final item = queueItems[i];
              final isCurrent = i == activeIndex;

              return Padding(
                padding: const EdgeInsets.only(bottom: 10.0),
                child: EchoSphereContainer(
                  padding: const EdgeInsets.all(12.0),
                  color: isCurrent ? context.colors.primary.opaque(0.08) : null,
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: context.colors.primary.opaque(0.15),
                        ),
                        child: EchoSphereText(
                          text: '#${i + 1}',
                          size: 12,
                          variant: TextVariant.bold,
                          color: context.colors.primary,
                        ),
                      ),
                      const SizedBox(width: 10),
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
                                  label: item['type'] ?? 'AI Speech',
                                  isSelected: true,
                                  onSelected: (_) {},
                                ),
                                EchoSphereText(
                                  text: item['department'] ?? 'College-Wide',
                                  size: 11,
                                  variant: TextVariant.bold,
                                  color: context.colors.primary,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            EchoSphereText(
                              text: item['title'] ?? 'Announcement',
                              size: 14,
                              variant: TextVariant.bold,
                              color: context.colors.onSurface,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 4),
                            EchoSphereText(
                              text: 'Scheduled: ${item["scheduledTime"] is DateTime ? DateFormat("hh:mm a").format(item["scheduledTime"]) : item["scheduled_time"] ?? "Immediate"} • Status: ${item["status"]}',
                              size: 11,
                              color: context.colors.onSurface.opaque(0.6),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        tooltip: isCurrent && isPlaying ? 'Pause' : 'Play Now',
                        icon: Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: isCurrent && isPlaying
                                ? const Color(0xFF8B5CF6)
                                : context.colors.primary.opaque(0.15),
                          ),
                          child: Icon(
                            isCurrent && isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                            size: 18,
                            color: isCurrent && isPlaying ? Colors.white : context.colors.primary,
                          ),
                        ),
                        onPressed: () {
                          setState(() {
                            if (activeIndex == i) {
                              isPlaying = !isPlaying;
                            } else {
                              activeIndex = i;
                              isPlaying = true;
                            }
                          });
                          snackBar(isPlaying ? 'Broadcasting: ${item['title']}' : 'Paused speaker queue.');
                        },
                      ),
                      IconButton(
                        icon: Icon(Icons.arrow_upward_rounded, size: 18, color: context.colors.onSurface.opaque(0.6)),
                        onPressed: i == 0
                            ? null
                            : () {
                                setState(() {
                                  final temp = queueItems[i];
                                  queueItems[i] = queueItems[i - 1];
                                  queueItems[i - 1] = temp;
                                });
                                snackBar('Reordered announcement in speaker queue.');
                              },
                      ),
                      IconButton(
                        icon: const Icon(Icons.delete_outline_rounded, size: 18, color: Colors.redAccent),
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
    );
  }

  Widget _buildHardwareDevicesTab(BuildContext context) {
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
                  size: 14,
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
                    Icon(Icons.add_rounded, size: 14, color: Colors.white),
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

        // Device Cards Grid / List
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 12.0),
            itemCount: speakerNodes.length,
            itemBuilder: (ctx, i) {
              final node = speakerNodes[i];
              final bool isOnline = node['status'] == 'ONLINE';

              return Padding(
                padding: const EdgeInsets.only(bottom: 12.0),
                child: EchoSphereContainer(
                  padding: const EdgeInsets.all(14.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Node Header Row
                      Row(
                        children: [
                          Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: isOnline ? Colors.green : Colors.red,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: EchoSphereText(
                              text: node['name'] ?? 'Speaker Node',
                              size: 14,
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
                      const SizedBox(height: 8),

                      // Telemetry & Details Row
                      Wrap(
                        spacing: 12,
                        runSpacing: 6,
                        children: [
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.wifi_rounded, size: 14, color: Colors.blue),
                              const SizedBox(width: 4),
                              EchoSphereText(
                                text: 'IP: ${node['ip_address'] ?? "Unknown"}',
                                size: 11,
                                color: context.colors.onSurface.opaque(0.8),
                              ),
                            ],
                          ),
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.numbers_rounded, size: 14, color: Colors.purple),
                              const SizedBox(width: 4),
                              EchoSphereText(
                                text: 'MAC: ${node['mac_address']}',
                                size: 11,
                                color: context.colors.onSurface.opaque(0.8),
                              ),
                            ],
                          ),
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.location_on_rounded, size: 14, color: Colors.orange),
                              const SizedBox(width: 4),
                              EchoSphereText(
                                text: 'Zone: ${node['zone']}',
                                size: 11,
                                color: context.colors.onSurface.opaque(0.8),
                              ),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),

                      // Metrics & Control Row
                      Row(
                        children: [
                          Expanded(
                            child: EchoSphereText(
                              text: 'CPU: ${node['cpu_usage']}%  |  RAM: ${node['memory_usage']}%  |  Vol: ${node['volume']}%',
                              size: 11,
                              color: context.colors.onSurface.opaque(0.6),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          IconButton(
                            icon: Icon(Icons.volume_up_rounded, size: 18, color: context.colors.primary),
                            tooltip: 'Test Speaker',
                            onPressed: () async {
                              try {
                                await _apiService.controlSpeakerNode(node['id'], command: 'TEST_SPEAKER');
                                snackBar('Test tone sent to ${node['name']}');
                              } catch (e) {
                                snackBar('Test command sent: ${e.toString()}');
                              }
                            },
                          ),
                          IconButton(
                            icon: Icon(Icons.restart_alt_rounded, size: 18, color: context.colors.primary),
                            tooltip: 'Restart Node',
                            onPressed: () async {
                              try {
                                await _apiService.controlSpeakerNode(node['id'], command: 'RESTART');
                                snackBar('Restart signal sent to ${node['name']}');
                              } catch (e) {
                                snackBar('Restart command sent: ${e.toString()}');
                              }
                            },
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline_rounded, size: 18, color: Colors.redAccent),
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
    );
  }
}
