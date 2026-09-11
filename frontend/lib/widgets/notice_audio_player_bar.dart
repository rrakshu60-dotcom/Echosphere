import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:anymex/services/tts_audio_service.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';

class NoticeAudioPlayerBar extends StatelessWidget {
  final int announcementId;
  final String title;
  final String? content;
  final String? directAudioUrl;
  final bool hasAiSummary;
  final String? aiSummary;

  const NoticeAudioPlayerBar({
    super.key,
    required this.announcementId,
    required this.title,
    this.content,
    this.directAudioUrl,
    this.hasAiSummary = false,
    this.aiSummary,
  });

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes.remainder(60).toString().padLeft(1, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  String _getChimeDisplayLabel(String type) {
    switch (type) {
      case 'urgent_academic':
        return 'Double-Beep';
      case 'events_sports':
        return 'Upbeat Ding';
      case 'emergency':
        return 'Siren Pulse';
      case 'standard':
        return 'Standard';
      case 'auto':
      default:
        return 'AI Auto';
    }
  }

  void _showChimeSelectorSheet(BuildContext context) {
    final theme = Theme.of(context);
    final audio = TtsAudioService.instance;

    final chimeOptions = [
      {
        'id': 'auto',
        'title': '⚡ AI Auto-Select',
        'desc': 'Intelligently selects chime based on notice urgency and topic',
        'chimeType': 'urgent_academic',
      },
      {
        'id': 'urgent_academic',
        'title': '🔔 Professional Double-Beep',
        'desc': 'Crisp attention-grabbing chime for exams, deadlines & circulars',
        'chimeType': 'urgent_academic',
      },
      {
        'id': 'events_sports',
        'title': '🎉 Upbeat Acoustic Ding',
        'desc': 'Cheerful 3-tone arpeggio for fests, sports, clubs & activities',
        'chimeType': 'events_sports',
      },
      {
        'id': 'emergency',
        'title': '🚨 Sweeping Siren Pulse',
        'desc': 'Rapid acoustic siren sweep to command hallway silence',
        'chimeType': 'emergency',
      },
      {
        'id': 'standard',
        'title': '🎵 Gentle Campus Chime',
        'desc': 'Warm dual-tone marimba chime for daily campus announcements',
        'chimeType': 'standard',
      },
    ];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          border: Border.all(color: theme.dividerColor.withOpacity(0.15)),
        ),
        padding: const EdgeInsets.all(20),
        child: SafeArea(
          top: false,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 36,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: theme.dividerColor.withOpacity(0.4),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Expanded(
                      child: Text(
                        'Broadcast Intro Chimes',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Obx(() => Switch.adaptive(
                          value: audio.includeChime.value,
                          activeColor: const Color(0xFF10B981),
                          onChanged: (val) => audio.toggleChime(val),
                        )),
                  ],
                ),
                Text(
                  'Prepends speech with an acoustic chime so broadcasts cut through hallway chatter',
                  style: TextStyle(fontSize: 11.5, color: theme.colorScheme.onSurface.withOpacity(0.6)),
                ),
                const SizedBox(height: 16),
                ...chimeOptions.map((opt) {
                  return Obx(() {
                    final isSelected = audio.selectedChime.value == opt['id'];
                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: isSelected
                            ? theme.colorScheme.primary.withOpacity(0.1)
                            : theme.colorScheme.surface.withOpacity(0.4),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isSelected ? theme.colorScheme.primary : theme.dividerColor.withOpacity(0.15),
                        ),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: InkWell(
                              onTap: () {
                                audio.setChimeType(opt['id']!);
                                Navigator.of(ctx).pop();
                              },
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    opt['title']!,
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                                      color: isSelected ? theme.colorScheme.primary : theme.colorScheme.onSurface,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    opt['desc']!,
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: theme.colorScheme.onSurface.withOpacity(0.6),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          IconButton(
                            onPressed: () => audio.previewChime(opt['chimeType']!),
                            icon: const Icon(Icons.volume_up_rounded, size: 18),
                            tooltip: 'Preview chime sound',
                            color: const Color(0xFF10B981),
                          ),
                        ],
                      ),
                    );
                  });
                }),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildConfigChip({
    required BuildContext context,
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
    IconData? icon,
  }) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: isSelected
              ? theme.colorScheme.primary.withOpacity(0.2)
              : theme.colorScheme.surface.withOpacity(0.3),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected
                ? theme.colorScheme.primary
                : theme.colorScheme.outline.withOpacity(0.2),
            width: isSelected ? 1.2 : 0.8,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: 13,
                color: isSelected
                    ? theme.colorScheme.primary
                    : theme.colorScheme.onSurface.withOpacity(0.65),
              ),
              const SizedBox(width: 4),
            ],
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                color: isSelected
                    ? theme.colorScheme.primary
                    : theme.colorScheme.onSurface.withOpacity(0.75),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final audio = TtsAudioService.instance;

    return Obx(() {
      final isActive = audio.isAnnouncementActive(announcementId);
      final isPlaying = audio.isAnnouncementPlaying(announcementId);
      final isBuffering = isActive && audio.isBuffering.value;
      final pos = audio.position.value;
      final dur = audio.duration.value;
      final maxSec = dur.inMilliseconds > 0 ? dur.inMilliseconds.toDouble() : 1.0;
      final curSec = pos.inMilliseconds.toDouble().clamp(0.0, maxSec);

      final currentGender = audio.selectedGender.value;
      final currentMode = audio.readMode.value;

      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16.0),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: LinearGradient(
            colors: isPlaying
                ? [
                    theme.colorScheme.primary.withOpacity(0.18),
                    theme.colorScheme.secondary.withOpacity(0.10),
                  ]
                : [
                    theme.colorScheme.surfaceVariant.withOpacity(0.35),
                    theme.colorScheme.surface.withOpacity(0.20),
                  ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          border: Border.all(
            color: isPlaying
                ? theme.colorScheme.primary.withOpacity(0.4)
                : theme.colorScheme.outline.withOpacity(0.15),
            width: isPlaying ? 1.5 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Top Row: Play/Pause Button + Status Info + Stop
            Row(
              children: [
                InkWell(
                  onTap: () => audio.playAnnouncement(
                    announcementId,
                    title: title,
                    content: content,
                    summary: aiSummary,
                    directUrl: directAudioUrl,
                  ),
                  borderRadius: BorderRadius.circular(24),
                  child: Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: [
                          theme.colorScheme.primary,
                          theme.colorScheme.secondary,
                        ],
                      ),
                      boxShadow: isPlaying
                          ? [
                              BoxShadow(
                                color: theme.colorScheme.primary.withOpacity(0.35),
                                blurRadius: 10,
                                spreadRadius: 1,
                              )
                            ]
                          : [],
                    ),
                    child: Center(
                      child: isBuffering
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            )
                          : Icon(
                              isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                              color: Colors.white,
                              size: 28,
                            ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),

                // Title & Subtitle Info
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: EchoSphereText(
                              text: isPlaying
                                  ? (currentMode == 'summary'
                                      ? 'Reading AI Summary Aloud'
                                      : 'Reading Full Notice Aloud')
                                  : isBuffering
                                      ? 'Synthesizing Voice...'
                                      : 'Listen to Notice',
                              size: 13,
                              variant: TextVariant.bold,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (isPlaying) ...[
                            const SizedBox(width: 6),
                            Container(
                              width: 8,
                              height: 8,
                              decoration: const BoxDecoration(
                                color: Colors.greenAccent,
                                shape: BoxShape.circle,
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${audio.engine.value} • ${audio.voiceName.value}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 11,
                          color: theme.colorScheme.primary.withOpacity(0.9),
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),

                // Stop button
                if (isActive) ...[
                  IconButton(
                    icon: const Icon(Icons.stop_rounded, size: 22),
                    tooltip: 'Stop Playback',
                    color: theme.colorScheme.onSurface.withOpacity(0.7),
                    onPressed: () => audio.stop(),
                  ),
                ],
              ],
            ),

            // Progress Slider & Timers (Visible when active)
            if (isActive && dur.inSeconds > 0) ...[
              const SizedBox(height: 8),
              SliderTheme(
                data: SliderTheme.of(context).copyWith(
                  trackHeight: 3.5,
                  thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                  overlayShape: const RoundSliderOverlayShape(overlayRadius: 14),
                  activeTrackColor: theme.colorScheme.primary,
                  inactiveTrackColor: theme.colorScheme.onSurface.withOpacity(0.12),
                  thumbColor: theme.colorScheme.primary,
                ),
                child: Slider(
                  value: curSec,
                  min: 0.0,
                  max: maxSec,
                  onChanged: (val) {
                    audio.seek(Duration(milliseconds: val.toInt()));
                  },
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      _formatDuration(pos),
                      style: TextStyle(
                        fontSize: 11,
                        color: theme.colorScheme.onSurface.withOpacity(0.6),
                      ),
                    ),
                    Text(
                      _formatDuration(dur),
                      style: TextStyle(
                        fontSize: 11,
                        color: theme.colorScheme.onSurface.withOpacity(0.6),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 12),
            const Divider(height: 1),
            const SizedBox(height: 10),

            // Voice & Accent & Read Mode Controls Row (Wrap for zero overflow guarantee)
            Wrap(
              spacing: 8,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                // Gender Toggles
                _buildConfigChip(
                  context: context,
                  label: '♀ Female',
                  isSelected: currentGender == 'female',
                  onTap: () => audio.setVoiceConfig(gender: 'female'),
                ),
                _buildConfigChip(
                  context: context,
                  label: '♂ Male',
                  isSelected: currentGender == 'male',
                  onTap: () => audio.setVoiceConfig(gender: 'male'),
                ),


                // Read Mode Toggle (Full notice vs AI Summary)
                _buildConfigChip(
                  context: context,
                  label: '📄 Full Notice',
                  isSelected: currentMode == 'full',
                  onTap: () {
                    audio.playAnnouncement(
                      announcementId,
                      title: title,
                      content: content,
                      summary: aiSummary,
                      directUrl: directAudioUrl,
                      forceMode: 'full',
                    );
                  },
                ),
                _buildConfigChip(
                  context: context,
                  label: '✨ AI Summary',
                  isSelected: currentMode == 'summary',
                  onTap: () {
                    audio.playAnnouncement(
                      announcementId,
                      title: title,
                      content: content,
                      summary: aiSummary,
                      directUrl: directAudioUrl,
                      forceMode: 'summary',
                    );
                  },
                ),

                // Intro Chime Configuration Chip
                _buildConfigChip(
                  context: context,
                  label: audio.includeChime.value
                      ? '🔔 Chime: ${_getChimeDisplayLabel(audio.selectedChime.value)}'
                      : '🔕 Chime: OFF',
                  icon: audio.includeChime.value
                      ? Icons.notifications_active_outlined
                      : Icons.notifications_off_outlined,
                  isSelected: audio.includeChime.value,
                  onTap: () => _showChimeSelectorSheet(context),
                ),
              ],
            ),
          ],
        ),
      );
    });
  }
}

