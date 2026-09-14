import 'package:echosphere/utils/theme_extensions.dart';
import 'package:flutter/material.dart';

class EchoSphereIcon extends StatelessWidget {
  final IconData icon;
  final Color? color;
  final double? size;
  const EchoSphereIcon(this.icon, {super.key, this.color, this.size});

  @override
  Widget build(BuildContext context) {
    final theme = context.colors;
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            theme.primary.opaque(0.2, iReallyMeanIt: true),
            theme.primary.opaque(0.1, iReallyMeanIt: true),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Icon(
        icon,
        size: size ?? 20,
        color: color,
      ),
    );
  }
}

class EchoSphereIconWrapper extends StatelessWidget {
  final Widget child;
  const EchoSphereIconWrapper({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final theme = context.colors;
    return Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              theme.primary.opaque(0.2),
              theme.primary.opaque(0.1),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(10),
        ),
        child: child);
  }
}
