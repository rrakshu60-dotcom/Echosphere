import 'package:anymex/controllers/theme.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_animated_logo.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

enum PageType { manga, anime, home, novel, library, extensions }

class Header extends StatelessWidget {
  final PageType type;
  const Header({super.key, required this.type});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final themeProvider = Provider.of<ThemeProvider>(context);
    final isDark = theme.brightness == Brightness.dark;

    final screenWidth = MediaQuery.of(context).size.width;
    final isMobile = screenWidth <= 650;

    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: isMobile ? 12.0 : 16.0,
        vertical: 8.0,
      ),
      child: Row(
        children: [
          // Theme Toggle
          IconButton(
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
            padding: EdgeInsets.zero,
            icon: Icon(
              isDark ? Icons.light_mode : Icons.dark_mode,
              size: isMobile ? 18 : 20,
            ),
            onPressed: () => themeProvider.toggleTheme(),
          ),
          const Spacer(),

          // Centered Logo & Branding
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              EchoSphereAnimatedLogo(size: isMobile ? 22 : 25),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  'EchoSphere',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontFamily: 'Poppins-Bold',
                    fontSize: isMobile ? 17 : 19,
                    fontWeight: FontWeight.bold,
                    color: theme.colorScheme.primary,
                  ),
                ),
              ),
            ],
          ),
          const Spacer(),

          // Right End Spacer (Balances theme toggle icon for centered branding)
          const SizedBox(width: 36, height: 36),
        ],
      ),
    );
  }
}

