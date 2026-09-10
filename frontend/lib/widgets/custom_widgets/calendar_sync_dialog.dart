import 'package:anymex/services/calendar_sync_service.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

/// Displays a responsive modal bottom sheet to review AI-extracted calendar event
/// and sync to Google Calendar or export as .ics with zero layout overflow on 320px.
void showCalendarSyncSheet(BuildContext context, CalendarEventData event) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (ctx) => CalendarSyncSheet(event: event),
  );
}

class CalendarSyncSheet extends StatelessWidget {
  final CalendarEventData event;

  const CalendarSyncSheet({super.key, required this.event});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final dateFmt = DateFormat('EEE, MMM d, yyyy');
    final timeFmt = DateFormat('h:mm a');

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border.all(color: theme.dividerColor.withOpacity(0.15)),
      ),
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Drag Handle
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

              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withOpacity(0.12),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.event_available_rounded,
                      color: Color(0xFF10B981),
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Add to Calendar',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          'AI Extracted Campus Schedule',
                          style: TextStyle(
                            fontSize: 11,
                            color: theme.colorScheme.onSurface.withOpacity(0.6),
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close_rounded, size: 20),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Event Summary Box
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: isDark
                      ? const Color(0xFF1E293B)
                      : const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: const Color(0xFF10B981).withOpacity(0.25),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Event Title
                    Text(
                      event.title,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        height: 1.3,
                      ),
                    ),
                    const SizedBox(height: 10),

                    // Date & Time Row
                    _buildMetaRow(
                      icon: Icons.calendar_today_rounded,
                      iconColor: const Color(0xFF10B981),
                      label: dateFmt.format(event.startTime),
                      subLabel: '${timeFmt.format(event.startTime)} - ${timeFmt.format(event.endTime)}',
                      theme: theme,
                    ),
                    const SizedBox(height: 8),

                    // Location Row
                    _buildMetaRow(
                      icon: Icons.location_on_outlined,
                      iconColor: Colors.amber.shade700,
                      label: event.location,
                      theme: theme,
                    ),

                    // Action Required Row
                    if (event.actionRequired.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      _buildMetaRow(
                        icon: Icons.assignment_outlined,
                        iconColor: Colors.blue.shade600,
                        label: event.actionRequired,
                        theme: theme,
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Action Buttons: 1-Tap Google Calendar & Device Calendar (.ics)
              Column(
                children: [
                  // 1. Google Calendar Button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: () async {
                        final ok = await CalendarSyncService.launchGoogleCalendar(event);
                        if (context.mounted) {
                          Navigator.of(context).pop();
                          if (ok) {
                            snackBar('Opening Google Calendar...');
                          } else {
                            snackBar('Opening calendar browser link...');
                          }
                        }
                      },
                      icon: const Icon(Icons.calendar_month_rounded, size: 18),
                      label: const Text(
                        'Add to Google Calendar (1-Tap)',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF10B981),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 0,
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),

                  // 2. Export / Device Calendar Button
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () async {
                        final ok = await CalendarSyncService.exportAndShareIcs(event);
                        if (context.mounted) {
                          Navigator.of(context).pop();
                          if (ok) {
                            snackBar('Exported .ics event to device');
                          }
                        }
                      },
                      icon: const Icon(Icons.share_outlined, size: 16),
                      label: const Text(
                        'Device Calendar / Export (.ics)',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: theme.colorScheme.onSurface,
                        side: BorderSide(color: theme.dividerColor),
                        padding: const EdgeInsets.symmetric(vertical: 11),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),

                  // 3. Copy Details to Clipboard
                  Center(
                    child: TextButton.icon(
                      onPressed: () {
                        final text = '📅 ${event.title}\n⏰ ${dateFmt.format(event.startTime)} at ${timeFmt.format(event.startTime)}\n📍 ${event.location}\n📌 ${event.actionRequired}';
                        Clipboard.setData(ClipboardData(text: text));
                        snackBar('Event details copied to clipboard');
                      },
                      icon: const Icon(Icons.copy_rounded, size: 14),
                      label: const Text('Copy Details', style: TextStyle(fontSize: 12)),
                      style: TextButton.styleFrom(
                        foregroundColor: theme.colorScheme.onSurface.withOpacity(0.6),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetaRow({
    required IconData icon,
    required Color iconColor,
    required String label,
    String? subLabel,
    required ThemeData theme,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 15, color: iconColor),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                  height: 1.2,
                ),
              ),
              if (subLabel != null) ...[
                const SizedBox(height: 2),
                Text(
                  subLabel,
                  style: TextStyle(
                    fontSize: 11,
                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
