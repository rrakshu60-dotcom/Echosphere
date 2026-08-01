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

class _SpeakerQueuePageState extends State<SpeakerQueuePage> {
  bool isPlaying = false;
  int activeIndex = 0;

  final List<Map<String, dynamic>> queueItems = [
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final canPop = ModalRoute.of(context)?.canPop ?? false;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Header Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 10.0),
              child: Row(
                children: [
                  if (canPop) ...[
                    IconButton(
                      icon: const Icon(Icons.arrow_back_rounded),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    const SizedBox(width: 4),
                  ],
                  const Icon(Icons.volume_up_rounded, size: 22, color: Colors.blue),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Speaker Queue',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: 'Poppins-Bold',
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Flexible(
                    child: EchoSphereChip(
                      label: '${queueItems.length} In Queue',
                      isSelected: true,
                      onSelected: (_) {},
                    ),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),

            // Active Speaker Banner
            Padding(
              padding: const EdgeInsets.all(12.0),
              child: EchoSphereContainer(
                padding: const EdgeInsets.all(14.0),
                color: theme.colorScheme.primary.withOpacity(0.12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          isPlaying ? Icons.graphic_eq_rounded : Icons.pause_circle_filled_rounded,
                          color: theme.colorScheme.primary,
                          size: 26,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                isPlaying ? 'Broadcasting Now' : 'Speaker Queue Ready',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                  color: theme.colorScheme.primary,
                                ),
                              ),
                              Text(
                                queueItems.isNotEmpty
                                    ? queueItems[activeIndex]['title']
                                    : 'No active speaker announcement',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
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
                              snackBar(
                                isPlaying ? 'Started speaker playback...' : 'Paused speaker queue.',
                              );
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
                                    color: const Color(0xFF8B5CF6).withOpacity(0.35),
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
                                  Text(
                                    isPlaying ? 'Pause' : 'Play',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.white,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Minimum 2-minute gap strictly maintained between speaker announcements.',
                      style: TextStyle(
                        fontSize: 11,
                        color: theme.colorScheme.onSurface.withOpacity(0.6),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const Divider(height: 1),

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
                      color: isCurrent ? theme.colorScheme.primary.withOpacity(0.08) : null,
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: theme.colorScheme.primary.withOpacity(0.15),
                            ),
                            child: Text(
                              '#${i + 1}',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                                color: theme.colorScheme.primary,
                              ),
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
                                      label: item['type'],
                                      isSelected: true,
                                      onSelected: (_) {},
                                    ),
                                    Text(
                                      item['department'],
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                        color: theme.colorScheme.primary,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  item['title'],
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Scheduled: ${DateFormat("hh:mm a").format(item["scheduledTime"])} • Duration: ${item["duration"]}',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                                  ),
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
                                    : theme.colorScheme.primary.withOpacity(0.15),
                              ),
                              child: Icon(
                                isCurrent && isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                                size: 18,
                                color: isCurrent && isPlaying ? Colors.white : theme.colorScheme.primary,
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
                              snackBar(
                                isPlaying
                                    ? 'Broadcasting: ${item['title']}'
                                    : 'Paused speaker queue.',
                              );
                            },
                          ),
                          IconButton(
                            icon: const Icon(Icons.arrow_upward_rounded, size: 18),
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
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
