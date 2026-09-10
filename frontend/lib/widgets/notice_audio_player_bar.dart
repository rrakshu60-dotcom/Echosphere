import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:anymex/services/tts_audio_service.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';

class NoticeAudioPlayerBar extends StatelessWidget {
  final int announcementId;
  final String title;
  final String? directAudioUrl;
  final bool hasAiSummary;

  const NoticeAudioPlayerBar({
    super.key,
    required this.announcementId,
    required this.title,
    this.directAudioUrl,
    this.hasAiSummary = false,
  });

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes.remainder(60).toString().padLeft(1, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
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
      final currentAccent = audio.selectedAccent.value;
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
                                      : 'Listen to Notice (Neural TTS)',
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

                // Accent Toggles
                _buildConfigChip(
                  context: context,
                  label: '🇮🇳 Indian',
                  isSelected: currentAccent == 'indian',
                  onTap: () => audio.setVoiceConfig(accent: 'indian'),
                ),
                _buildConfigChip(
                  context: context,
                  label: '🇺🇸 American',
                  isSelected: currentAccent == 'american',
                  onTap: () => audio.setVoiceConfig(accent: 'american'),
                ),
                _buildConfigChip(
                  context: context,
                  label: '🇬🇧 British',
                  isSelected: currentAccent == 'british',
                  onTap: () => audio.setVoiceConfig(accent: 'british'),
                ),

                // Read Mode Toggle (Full notice vs AI Summary)
                _buildConfigChip(
                  context: context,
                  label: '📄 Full Notice',
                  isSelected: currentMode == 'full',
                  onTap: () => audio.setVoiceConfig(mode: 'full'),
                ),
                _buildConfigChip(
                  context: context,
                  label: '✨ AI Summary',
                  isSelected: currentMode == 'summary',
                  onTap: () => audio.setVoiceConfig(mode: 'summary'),
                ),
              ],
            ),
          ],
        ),
      );
    });
  }
}

