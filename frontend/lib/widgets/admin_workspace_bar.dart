import 'package:echosphere/constants/themes.dart';
import 'package:echosphere/screens/admin/audit_logs_page.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

/// Admin Quick Workspace Bar on the home page (staff and admins). Dev Admin and College Admin also get
/// Audit & Logs; with four tiles the bar becomes a 2 x 2 grid on narrow screens.
class AdminWorkspaceBar extends StatelessWidget {
  final String role;

  const AdminWorkspaceBar({super.key, required this.role});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final tiles = <Widget>[
      _WorkspaceActionTile(
        title: 'Notice Hub',
        subtitle: 'Moderate notices',
        icon: Icons.auto_fix_high_rounded,
        onTap: () => Get.toNamed('/announcement-management'),
      ),
      _WorkspaceActionTile(
        title: 'User Hub',
        subtitle: 'Directory & roles',
        icon: Icons.manage_accounts_rounded,
        onTap: () => Get.toNamed('/user-management'),
      ),
      _WorkspaceActionTile(
        title: 'Smart Speakers',
        subtitle: 'Hardware PA & nodes',
        icon: Icons.podcasts_rounded,
        onTap: () => Get.toNamed('/speaker-queue'),
      ),
      if (canOpenAuditLogs(role))
        _WorkspaceActionTile(
          title: 'Audit & Logs',
          subtitle: 'Records & access',
          icon: Icons.policy_rounded,
          onTap: () => Get.toNamed('/audit-logs'),
        ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Flexible(
              child: Text(
                'Admin Workspace',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.85),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Text(
                  'MANAGEMENT CONSOLE',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.6,
                    color: theme.colorScheme.primary,
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        LayoutBuilder(builder: (context, constraints) {
          // One row when every tile gets at least ~120px, otherwise two per row
          final perRow = tiles.length > 3 && constraints.maxWidth < tiles.length * 128 ? 2 : tiles.length;
          final rows = <Widget>[];
          for (var i = 0; i < tiles.length; i += perRow) {
            final rowTiles = tiles.sublist(i, (i + perRow).clamp(0, tiles.length));
            rows.add(Row(
              children: [
                for (var k = 0; k < rowTiles.length; k++) ...[
                  if (k > 0) const SizedBox(width: 8),
                  Expanded(child: rowTiles[k]),
                ],
              ],
            ));
          }
          return Column(
            children: [
              for (var r = 0; r < rows.length; r++) ...[
                if (r > 0) const SizedBox(height: 8),
                rows[r],
              ],
            ],
          );
        }),
      ],
    );
  }
}

class _WorkspaceActionTile extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  const _WorkspaceActionTile({required this.title, required this.subtitle, required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final color = theme.colorScheme.primary;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
        decoration: BoxDecoration(
          color: isDark ? EchoSpherePalette.darkSurface : EchoSpherePalette.lightSurface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder,
            width: 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon, size: 16, color: color),
            ),
            const SizedBox(height: 8),
            Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 10,
                color: isDark ? theme.colorScheme.onSurface.withValues(alpha: 0.6) : const Color(0xFF64748B),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
