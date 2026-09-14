import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ServerStatusIndicator extends StatefulWidget {
  const ServerStatusIndicator({super.key});

  @override
  State<ServerStatusIndicator> createState() => _ServerStatusIndicatorState();
}

class _ServerStatusIndicatorState extends State<ServerStatusIndicator> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 0.35, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Obx(() {
      final status = EchosphereApiService().serverStatus.value;
      if (status == ServerConnectionStatus.connected) {
        return const SizedBox.shrink();
      }

      final isConnecting = status == ServerConnectionStatus.connecting;
      final label = isConnecting ? 'Connecting to server...' : 'Offline Mode';
      final dotColor = isConnecting
          ? (isDark ? const Color(0xFFFBBF24) : const Color(0xFFD97706)) // Warm Amber
          : (isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B)); // Slate neutral

      final bgColor = isDark
          ? const Color(0xFF1E293B).withOpacity(0.92)
          : const Color(0xFFF8FAFC).withOpacity(0.95);

      final borderColor = isDark
          ? const Color(0xFF334155)
          : const Color(0xFFCBD5E1);

      final textColor = isDark
          ? const Color(0xFFF1F5F9)
          : const Color(0xFF1E293B);

      // IgnorePointer guarantees that taps, clicks, and gestures pass straight
      // through to underlying buttons and page navigation without obstruction.
      return IgnorePointer(
        ignoring: true,
        child: AnimatedOpacity(
          opacity: 1.0,
          duration: const Duration(milliseconds: 250),
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 4),
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: borderColor, width: 0.9),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(isDark ? 0.25 : 0.05),
                  blurRadius: 6,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                FadeTransition(
                  opacity: _pulseAnimation,
                  child: Container(
                    width: 7,
                    height: 7,
                    decoration: BoxDecoration(
                      color: dotColor,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: textColor,
                    letterSpacing: 0.1,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    });
  }
}
