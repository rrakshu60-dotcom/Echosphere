import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:echosphere/services/tts_audio_service.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/screens/announcements/announcement_detail_page.dart';

/// A sleek, floating mini player docked above the navigation bar
/// on the Home screen whenever TTS audio is active anywhere in the app.
/// Allows the user to pause, resume, stop, or tap to open the full detail page.
class HomeMiniTtsPlayerBar extends StatelessWidget {
  const HomeMiniTtsPlayerBar({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Obx(() {
      final audio = TtsAudioService.instance;
      final activeId = audio.currentAnnouncementId.value;
      final isPlaying = audio.isPlaying.value;
      final isBuffering = audio.isBuffering.value;

      // When no announcement audio is loaded or playing, collapse to zero height
      if (activeId == null && !isPlaying && !isBuffering) {
        return const SizedBox.shrink();
      }

      final title = audio.activeAnnouncementTitle.value.isNotEmpty
          ? audio.activeAnnouncementTitle.value
          : 'Campus Notice Audio';
      final isSummaryMode = audio.readMode.value == 'summary';

      return SafeArea(
        top: false,
        bottom: false,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: isDark
                ? const Color(0xFF1E293B).withOpacity(0.95)
                : Colors.white.withOpacity(0.96),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(isDark ? 0.4 : 0.10),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
            border: Border.all(
              color: isPlaying
                  ? theme.colorScheme.primary.withOpacity(0.4)
                  : (isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0)),
              width: 1.2,
            ),
          ),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () {
                if (activeId != null && Get.isRegistered<AnnouncementController>()) {
                  final annCtrl = Get.find<AnnouncementController>();
                  final notice = annCtrl.allAnnouncements.firstWhereOrNull((a) => a.id == activeId);
                  if (notice != null) {
                    Get.to(() => AnnouncementDetailPage(announcement: notice));
                  }
                }
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                child: Row(
                  children: [
                    // Animated / status icon
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary.withOpacity(isDark ? 0.22 : 0.12),
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: isBuffering
                            ? SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: theme.colorScheme.primary,
                                ),
                              )
                            : Icon(
                                isPlaying ? Icons.graphic_eq_rounded : Icons.volume_up_rounded,
                                size: 20,
                                color: theme.colorScheme.primary,
                              ),
                      ),
                    ),
                    const SizedBox(width: 10),

                    // Title & mode badge with flexible constraint (Zero Overflow)
                    Expanded(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: isSummaryMode
                                      ? (isDark ? Colors.purple.shade900.withOpacity(0.5) : const Color(0xFFFAF5FF))
                                      : (isDark ? theme.colorScheme.primary.withOpacity(0.2) : const Color(0xFFEEF2FF)),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(
                                    color: isSummaryMode
                                        ? (isDark ? Colors.purple.shade400 : const Color(0xFFD8B4FE))
                                        : (isDark ? theme.colorScheme.primary.withOpacity(0.4) : const Color(0xFFC7D2FE)),
                                    width: 0.8,
                                  ),
                                ),
                                child: Text(
                                  isSummaryMode ? 'AI Summary' : 'Notice Audio',
                                  style: TextStyle(
                                    fontSize: 9.5,
                                    fontWeight: FontWeight.bold,
                                    color: isSummaryMode
                                        ? (isDark ? Colors.purple.shade200 : const Color(0xFF7E22CE))
                                        : theme.colorScheme.primary,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 6),
                              if (isBuffering)
                                Text(
                                  'Loading speech...',
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontStyle: FontStyle.italic,
                                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 3),
                          Text(
                            title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(width: 6),

                    // Play / Pause toggle button
                    IconButton(
                      iconSize: 24,
                      splashRadius: 20,
                      padding: const EdgeInsets.all(4),
                      constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
                      tooltip: isPlaying ? 'Pause' : 'Resume',
                      icon: Icon(
                        isPlaying ? Icons.pause_circle_filled_rounded : Icons.play_circle_fill_rounded,
                        color: theme.colorScheme.primary,
                      ),
                      onPressed: () {
                        if (isPlaying) {
                          audio.pause();
                        } else {
                          audio.resume();
                        }
                      },
                    ),

                    // Stop & Close button
                    IconButton(
                      iconSize: 20,
                      splashRadius: 20,
                      padding: const EdgeInsets.all(4),
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                      tooltip: 'Stop & Dismiss',
                      icon: Icon(
                        Icons.stop_circle_outlined,
                        color: isDark ? const Color(0xFFF87171) : const Color(0xFFDC2626),
                      ),
                      onPressed: () {
                        audio.stop();
                      },
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    });
  }
}
