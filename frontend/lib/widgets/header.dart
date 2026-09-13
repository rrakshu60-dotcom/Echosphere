import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/theme.dart';
import 'package:anymex/screens/announcements/speaker_queue_page.dart';
import 'package:anymex/services/tts_audio_service.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_animated_logo.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';

enum PageType { home, announcements, broadcasts, profile }

class Header extends StatelessWidget {
  final PageType type;
  const Header({super.key, this.type = PageType.home});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final themeProvider = Provider.of<ThemeProvider>(context);
    final isDark = theme.brightness == Brightness.dark;

    final screenWidth = MediaQuery.of(context).size.width;
    final isMobile = screenWidth <= 650;

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isMobile ? 14.0 : 20.0,
        vertical: 10.0,
      ),
      child: Row(
        children: [
          // Left: Logo, Branding & Campus Hub Badge
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              EchoSphereAnimatedLogo(size: isMobile ? 24 : 28),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'EchoSphere',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontFamily: 'Poppins-Bold',
                          fontSize: isMobile ? 18 : 20,
                          fontWeight: FontWeight.bold,
                          color: theme.colorScheme.primary,
                          letterSpacing: -0.2,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: theme.colorScheme.primary.withValues(alpha: 0.2),
                            width: 0.8,
                          ),
                        ),
                        child: Text(
                          'CAMPUS HUB',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.8,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),

          const Spacer(),

          // Right: Theme Toggle
          IconButton(
            tooltip: isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode',
            constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
            padding: EdgeInsets.zero,
            icon: Icon(
              isDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
              size: isMobile ? 19 : 21,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.75),
            ),
            onPressed: () => themeProvider.toggleTheme(),
          ),

          const SizedBox(width: 4),

          // Right: Smart PA Speaker Shortcut with live activity indicator
          Obx(() {
            if (!Get.isRegistered<AuthController>()) {
              return const SizedBox.shrink();
            }
            final auth = Get.find<AuthController>();
            if (auth.currentUser.value == null) {
              return const SizedBox.shrink();
            }

            final isPlaying = TtsAudioService.instance.isPlaying.value;

            return Stack(
              clipBehavior: Clip.none,
              children: [
                IconButton(
                  tooltip: 'Smart Speaker PA System',
                  constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
                  padding: EdgeInsets.zero,
                  icon: Icon(
                    Icons.podcasts_rounded,
                    size: isMobile ? 20 : 22,
                    color: isPlaying
                        ? theme.colorScheme.primary
                        : theme.colorScheme.onSurface.withValues(alpha: 0.7),
                  ),
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const SpeakerQueuePage()),
                  ),
                ),
                if (isPlaying)
                  Positioned(
                    top: 6,
                    right: 6,
                    child: Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary,
                        shape: BoxShape.circle,
                        border: Border.all(color: theme.scaffoldBackgroundColor, width: 1.5),
                      ),
                    ),
                  ),
              ],
            );
          }),
        ],
      ),
    );
  }
}
