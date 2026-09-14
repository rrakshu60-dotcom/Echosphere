import 'package:echosphere/constants/themes.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/services/calendar_sync_service.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/services/tts_audio_service.dart';
import 'package:echosphere/utils/navigation_helper.dart';
import 'package:echosphere/widgets/custom_widgets/attachment_viewer_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/calendar_sync_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_chip.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_container.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:shimmer/shimmer.dart';

// ----------------------------------------------------------------------
// Stat Card -- Animated metric display for the stats panel
// ----------------------------------------------------------------------
class StatCard extends StatelessWidget {
  final String label;
  final int value;
  final IconData icon;
  final Color color;
  final VoidCallback? onTap;

  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    Widget cardContent = InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainer,
          borderRadius: BorderRadius.circular(EchoSpherePalette.radius),
          border: Border.all(
            color: theme.colorScheme.outline,
            width: 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 20),
            ),
            const SizedBox(height: 12),
            TweenAnimationBuilder<int>(
              tween: IntTween(begin: 0, end: value),
              duration: const Duration(milliseconds: 800),
              curve: Curves.easeOutCubic,
              builder: (context, val, _) => FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  '$val',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: theme.colorScheme.onSurface,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: theme.brightness == Brightness.dark
                    ? theme.colorScheme.onSurface.withOpacity(0.65)
                    : const Color(0xFF64748B),
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
    return Expanded(child: cardContent);
  }
}

// ----------------------------------------------------------------------
// Today Summary Banner -- Shows at-a-glance daily summary
// ----------------------------------------------------------------------
class TodaySummaryBanner extends StatelessWidget {
  final int todayCount;
  final int pendingCount;
  final bool isAuthorized;

  const TodaySummaryBanner({
    super.key,
    required this.todayCount,
    required this.pendingCount,
    required this.isAuthorized,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    String message;
    if (isAuthorized && pendingCount > 0) {
      message =
          '$todayCount new announcement${todayCount == 1 ? '' : 's'} today \u2022 $pendingCount pending your approval';
    } else {
      message =
          '$todayCount new announcement${todayCount == 1 ? '' : 's'} today';
    }

    return EchoSphereContainer(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      radius: EchoSpherePalette.radiusSm,
      child: Row(
        children: [
          Icon(
            Icons.today_rounded,
            size: 18,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: theme.colorScheme.onSurface.withOpacity(0.8),
              ),
            ),
          ),
          Text(
            DateFormat('EEE, MMM d').format(DateTime.now()),
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.primary,
            ),
          ),
        ],
      ),
    );
  }
}

// ----------------------------------------------------------------------
// Priority Carousel -- Horizontal scrollable priority announcements
// ----------------------------------------------------------------------
class PriorityCarousel extends StatefulWidget {
  final List<AnnouncementModel> items;

  const PriorityCarousel({super.key, required this.items});

  @override
  State<PriorityCarousel> createState() => _PriorityCarouselState();
}

class _PriorityCarouselState extends State<PriorityCarousel> {
  final PageController _pageController = PageController(viewportFraction: 0.88);
  int _currentPage = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Color _getPriorityColor(String priority) {
    return EchoSpherePalette.getPriorityColor(priority, isDark: Theme.of(context).brightness == Brightness.dark);
  }

  String _timeAgo(DateTime dateTime) {
    final diff = DateTime.now().difference(dateTime);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return DateFormat('MMM dd').format(dateTime);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section Header
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 0),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: theme.colorScheme.secondary,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: theme.colorScheme.outline, width: 1),
                ),
                child: Icon(Icons.campaign_rounded,
                    color: theme.colorScheme.primary, size: 18),
              ),
              const SizedBox(width: 10),
              Text(
                'Urgent & Priority Notices',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.onSurface,
                ),
              ),
              const Spacer(),
              Text(
                '${widget.items.length} active',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: theme.colorScheme.onSurface.withOpacity(0.5),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // PageView Carousel
        SizedBox(
          height: 195,
          child: PageView.builder(
            controller: _pageController,
            onPageChanged: (i) => setState(() => _currentPage = i),
            itemCount: widget.items.length,
            itemBuilder: (context, index) {
              final item = widget.items[index];
              final pColor = _getPriorityColor(item.priority);
              final isEmergency = item.priority.toUpperCase() == 'EMERGENCY';

              return AnimatedPadding(
                duration: const Duration(milliseconds: 300),
                padding: EdgeInsets.only(
                  right: index < widget.items.length - 1 ? 12 : 0,
                ),
                child: InkWell(
                  onTap: () => openAnnouncementDetail(context, item),
                  borderRadius: BorderRadius.circular(18),
                  child: _PriorityCard(
                    item: item,
                    pColor: pColor,
                    isEmergency: isEmergency,
                    timeAgo: _timeAgo(item.createdAt),
                    theme: theme,
                  ),
                ),
              );
            },
          ),
        ),

        // Page Indicator Dots
        if (widget.items.length > 1) ...[
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(
              widget.items.length,
              (index) => AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: _currentPage == index ? 20 : 6,
                height: 6,
                decoration: BoxDecoration(
                  color: _currentPage == index
                      ? theme.colorScheme.primary
                      : theme.colorScheme.onSurface.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _PriorityCard extends StatelessWidget {
  final AnnouncementModel item;
  final Color pColor;
  final bool isEmergency;
  final String timeAgo;
  final ThemeData theme;

  const _PriorityCard({
    required this.item,
    required this.pColor,
    required this.isEmergency,
    required this.timeAgo,
    required this.theme,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = theme.brightness == Brightness.dark;
    final cardBg = theme.colorScheme.surfaceContainer;
    final cardBorder = theme.colorScheme.outline;

    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: cardBorder,
          width: 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: isDark
                ? Colors.black.withValues(alpha: 0.55)
                : const Color(0xFF0F172A).withValues(alpha: 0.04),
            blurRadius: isDark ? 36 : 20,
            offset: Offset(0, isDark ? 16 : 4),
            spreadRadius: isDark ? -8 : -2,
          ),
          if (!isDark)
            BoxShadow(
              color: const Color(0xFF0F172A).withValues(alpha: 0.02),
              blurRadius: 4,
              offset: const Offset(0, 1),
              spreadRadius: 0,
            ),
        ],
      ),
      padding: const EdgeInsets.all(14.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              EchoSphereBadge(
                label: item.priority,
                icon: isEmergency ? Icons.priority_high_rounded : null,
                variant: isEmergency ? BadgeVariant.destructive : BadgeVariant.secondary,
              ),
              const SizedBox(width: 6),
              EchoSphereBadge(
                label: item.department,
                variant: BadgeVariant.outline,
              ),
              const Spacer(),
              Text(
                timeAgo,
                style: TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w500,
                  color: isDark ? theme.colorScheme.onSurface.withOpacity(0.6) : const Color(0xFF64748B),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            item.title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 14.5,
              fontWeight: FontWeight.bold,
              height: 1.25,
            ),
          ),
          const SizedBox(height: 4),
          Expanded(
            child: Text(
              item.description,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 11.5,
                height: 1.35,
                color: isDark ? theme.colorScheme.onSurface.withOpacity(0.85) : const Color(0xFF334155),
              ),
            ),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Icon(Icons.person_outline,
                  size: 13,
                  color: isDark ? theme.colorScheme.onSurface.withOpacity(0.6) : const Color(0xFF64748B)),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  item.creatorName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                    color: isDark ? theme.colorScheme.onSurface.withOpacity(0.6) : const Color(0xFF64748B),
                  ),
                ),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'View',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const SizedBox(width: 2),
                  Icon(
                    Icons.arrow_forward_rounded,
                    size: 12,
                    color: theme.colorScheme.primary,
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ----------------------------------------------------------------------
// Enhanced Announcement Feed Card -- With priority bar & attachment indicator
// ----------------------------------------------------------------------
// Enhanced Announcement Feed Card -- With priority bar, AI Summarizer & Kokoro TTS
// ----------------------------------------------------------------------
class AnnouncementFeedCard extends StatefulWidget {
  final AnnouncementModel notice;
  final int index;

  const AnnouncementFeedCard({
    super.key,
    required this.notice,
    required this.index,
  });

  @override
  State<AnnouncementFeedCard> createState() => _AnnouncementFeedCardState();
}

class _AnnouncementFeedCardState extends State<AnnouncementFeedCard> {
  String? _aiSummary;
  bool _isSummarizing = false;
  bool _showSummary = false;
  bool _isLoadingCalendar = false;

  @override
  void initState() {
    super.initState();
    _aiSummary = widget.notice.aiSummary;
    _showSummary = widget.notice.aiSummary != null && widget.notice.aiSummary!.isNotEmpty;
  }

  @override
  void didUpdateWidget(covariant AnnouncementFeedCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.notice.aiSummary != oldWidget.notice.aiSummary && widget.notice.aiSummary != null) {
      setState(() {
        _aiSummary = widget.notice.aiSummary;
        if (_aiSummary!.isNotEmpty) _showSummary = true;
      });
    }
  }

  Future<void> _handleSummarizeTap() async {
    // If summary already exists in state, toggle display
    if (_aiSummary != null && _aiSummary!.isNotEmpty) {
      setState(() {
        _showSummary = !_showSummary;
      });
      return;
    }

    // Generate fresh summary using trained Qwen 2.5 3B local model via backend
    setState(() => _isSummarizing = true);
    try {
      final summary = await EchosphereApiService().summarizeContent(widget.notice.description);
      if (mounted) {
        setState(() {
          _aiSummary = summary;
          _showSummary = true;
          _isSummarizing = false;
        });

        // Sync with AnnouncementController in memory
        if (Get.isRegistered<AnnouncementController>()) {
          Get.find<AnnouncementController>().updateAnnouncementSummary(widget.notice.id, summary);
        }

        // Pre-warm Kokoro audio for instant zero-latency playback of the summary
        TtsAudioService.instance.prewarmAnnouncement(
          widget.notice.id,
          title: widget.notice.title,
          content: widget.notice.description,
          summary: summary,
        );

        snackBar('AI Summary generated successfully.');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSummarizing = false);
        snackBar('Failed to generate summary: $e');
      }
    }
  }

  Future<void> _handleCalendarTap() async {
    setState(() => _isLoadingCalendar = true);
    try {
      CalendarEventData? ev;
      if (Get.isRegistered<AnnouncementController>()) {
        ev = await Get.find<AnnouncementController>().getOrFetchCalendarEvent(widget.notice);
      } else {
        ev = await EchosphereApiService().getAnnouncementCalendarEvent(
          widget.notice.id,
          title: widget.notice.title,
          content: widget.notice.description,
        );
      }
      if (!mounted) return;
      setState(() => _isLoadingCalendar = false);
      if (ev != null && ev.hasEvent) {
        showCalendarSyncSheet(context, ev);
      } else {
        snackBar('No upcoming deadline or event was detected in this notice.');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoadingCalendar = false);
      snackBar('Could not extract event: $e');
    }
  }

  String _timeAgo(DateTime dateTime) {
    final diff = DateTime.now().difference(dateTime);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return DateFormat('MMM dd, yyyy').format(dateTime);
  }

  void _showRelevanceDialog(BuildContext context, Map<String, dynamic> relevance) {
    final reasons = (relevance['reasons'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final score = (((relevance['score'] as num?)?.toDouble() ?? 0.0) * 100).toInt();
    final theme = Theme.of(context);

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: theme.scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          border: Border.all(color: theme.dividerColor.withOpacity(0.2)),
        ),
        child: SafeArea(
          top: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary.withOpacity(0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.auto_awesome, color: theme.colorScheme.primary, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Personalized Relevance',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: theme.colorScheme.onSurface,
                          ),
                        ),
                        Text(
                          '$score% Affinity for your profile',
                          style: TextStyle(
                            fontSize: 12,
                            color: theme.colorScheme.primary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 18),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Text(
                'Why this notice was prioritized for you:',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 10),
              if (reasons.isEmpty)
                Text(
                  'General campus announcement matching your department and academic calendar.',
                  style: TextStyle(
                    fontSize: 13,
                    color: theme.colorScheme.onSurface.withOpacity(0.75),
                  ),
                )
              else
                ...reasons.map((r) => Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.check_circle_rounded, size: 16, color: theme.colorScheme.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          r,
                          style: TextStyle(
                            fontSize: 13,
                            color: theme.colorScheme.onSurface.withOpacity(0.85),
                          ),
                        ),
                      ),
                    ],
                  ),
                )),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    Map<String, dynamic>? relevance;
    if (Get.isRegistered<AnnouncementController>()) {
      relevance = Get.find<AnnouncementController>().getRelevanceFor(widget.notice);
    }
    final rel = relevance;
    final isHighlyRelevant = rel != null &&
        (rel['is_highly_relevant'] == true ||
            ((rel['score'] as num?)?.toDouble() ?? 0.0) >= 0.65);

    return RepaintBoundary(
        child: TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: Duration(milliseconds: 300 + (widget.index * 60).clamp(0, 300)),
      curve: Curves.easeOutCubic,
      builder: (context, value, child) => Opacity(
        opacity: value,
        child: Transform.translate(
          offset: Offset(0, 16 * (1 - value)),
          child: child,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.only(bottom: 12.0),
        child: InkWell(
          onTap: () => openAnnouncementDetail(context, widget.notice),
          borderRadius: BorderRadius.circular(16),
          child: EchoSphereContainer(
            padding: const EdgeInsets.all(18.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top row: chips + timestamp
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  alignment: WrapAlignment.spaceBetween,
                  children: [
                    EchoSphereBadge(
                      label: widget.notice.category,
                      variant: BadgeVariant.muted,
                    ),
                    if (rel != null && isHighlyRelevant)
                      EchoSphereBadge(
                        label: 'Relevant to You',
                        icon: Icons.auto_awesome_rounded,
                        variant: BadgeVariant.secondary,
                        onTap: () => _showRelevanceDialog(context, rel),
                      ),
                    EchoSphereBadge(
                      label: widget.notice.priority,
                      icon: (widget.notice.priority.toUpperCase() == 'EMERGENCY')
                          ? Icons.priority_high_rounded
                          : null,
                      variant: (widget.notice.priority.toUpperCase() == 'EMERGENCY')
                          ? BadgeVariant.destructive
                          : BadgeVariant.secondary,
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _timeAgo(widget.notice.createdAt),
                          style: TextStyle(
                            fontSize: 11,
                            color: isDark ? theme.colorScheme.onSurface.withOpacity(0.6) : const Color(0xFF64748B),
                          ),
                        ),
                        const SizedBox(width: 4),
                        Obx(() {
                          final isBookmarked = Get.isRegistered<AnnouncementController>() &&
                              Get.find<AnnouncementController>().isBookmarked(widget.notice.id);
                          return InkWell(
                            onTap: () {
                              HapticFeedback.lightImpact();
                              if (Get.isRegistered<AnnouncementController>()) {
                                Get.find<AnnouncementController>().toggleBookmark(widget.notice.id);
                              }
                            },
                            borderRadius: BorderRadius.circular(16),
                            child: Padding(
                              padding: const EdgeInsets.all(4.0),
                              child: Icon(
                                isBookmarked ? Icons.bookmark_rounded : Icons.bookmark_outline_rounded,
                                size: 18,
                                color: isBookmarked
                                    ? theme.colorScheme.primary
                                    : (isDark ? theme.colorScheme.onSurface.withOpacity(0.4) : const Color(0xFF94A3B8)),
                              ),
                            ),
                          );
                        }),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Title
                Text(
                  widget.notice.title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    height: 1.3,
                  ),
                ),
                const SizedBox(height: 8),

                // Description preview
                Text(
                  widget.notice.description,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 13.5,
                    height: 1.5,
                    color: isDark ? theme.colorScheme.onSurface.withOpacity(0.85) : const Color(0xFF334155),
                  ),
                ),

                // Attachments Quick Preview
                if (widget.notice.attachments.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: widget.notice.attachments.map((file) {
                      final lower = file.toLowerCase();
                      final isPdf = lower.endsWith('.pdf');
                      final isImg = lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg');
                      return InkWell(
                        onTap: () => AttachmentViewerDialog.show(
                          context,
                          filename: file,
                          notice: widget.notice,
                        ),
                        borderRadius: BorderRadius.circular(10),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.primary.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                              color: theme.colorScheme.primary.withValues(alpha: 0.20),
                              width: 0.8,
                            ),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                isPdf ? Icons.picture_as_pdf_rounded : (isImg ? Icons.image_rounded : Icons.attachment_rounded),
                                size: 13,
                                color: theme.colorScheme.primary,
                              ),
                              const SizedBox(width: 5),
                              ConstrainedBox(
                                constraints: const BoxConstraints(maxWidth: 160),
                                child: Text(
                                  file,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: theme.colorScheme.primary,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],

                // Dedicated AI Summary Box (Generated by Fine-Tuned Qwen Model)
                if (_showSummary && _aiSummary != null && _aiSummary!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: isDark ? theme.colorScheme.surfaceContainer : const Color(0xFFF5F3FF),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: isDark ? theme.colorScheme.outline : const Color(0xFFDDD6FE)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.auto_awesome,
                                size: 14, color: theme.colorScheme.primary),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                'AI Summary',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                  letterSpacing: 0.2,
                                  color: theme.colorScheme.primary,
                                ),
                              ),
                            ),

                            const SizedBox(width: 4),
                            InkWell(
                              onTap: () {
                                Clipboard.setData(ClipboardData(text: _aiSummary!));
                                snackBar('Summary copied to clipboard');
                              },
                              borderRadius: BorderRadius.circular(12),
                              child: Padding(
                                padding: const EdgeInsets.all(3.0),
                                child: Icon(
                                  Icons.copy_rounded,
                                  size: 13,
                                  color: theme.colorScheme.primary,
                                ),
                              ),
                            ),
                            const SizedBox(width: 4),
                            InkWell(
                              onTap: () => setState(() => _showSummary = false),
                              borderRadius: BorderRadius.circular(12),
                              child: Padding(
                                padding: const EdgeInsets.all(3.0),
                                child: Icon(
                                  Icons.close_rounded,
                                  size: 14,
                                  color: theme.colorScheme.primary,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          _aiSummary!,
                          style: TextStyle(
                            fontSize: 12.5,
                            height: 1.4,
                            color: isDark ? theme.colorScheme.onSurface : const Color(0xFF1E1B4B),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 14),

                // Author Row
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: isDark ? theme.colorScheme.surfaceContainer : const Color(0xFFF1F5F9),
                        shape: BoxShape.circle,
                        border: Border.all(color: isDark ? theme.colorScheme.outline : const Color(0xFFE2E8F0), width: 0.8),
                      ),
                      child: Icon(
                        Icons.person,
                        size: 14,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${widget.notice.creatorName} \u2022 ${widget.notice.department}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: isDark ? theme.colorScheme.onSurface.withOpacity(0.7) : const Color(0xFF475569),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),

                // Action Bar: Wrap to strictly guarantee ZERO layout overflow on Android down to 320px
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  alignment: WrapAlignment.spaceBetween,
                  children: [
                    // 1. Dedicated AI Summarizer Button (Text only, powered by trained model)
                    InkWell(
                      onTap: _isSummarizing ? null : _handleSummarizeTap,
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 9, vertical: 5),
                        decoration: BoxDecoration(
                          color: _showSummary
                              ? (isDark ? theme.colorScheme.primary.withOpacity(0.20) : const Color(0xFFEEF2FF))
                              : (isDark ? theme.colorScheme.surfaceContainer : const Color(0xFFF8FAFC)),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: _showSummary
                                ? (isDark ? theme.colorScheme.primary : const Color(0xFF818CF8))
                                : (isDark ? theme.colorScheme.outline : const Color(0xFFE2E8F0)),
                            width: 1.0,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (_isSummarizing)
                              SizedBox(
                                width: 12,
                                height: 12,
                                child: CircularProgressIndicator(
                                  strokeWidth: 1.5,
                                  color: theme.colorScheme.primary,
                                ),
                              )
                            else
                              Icon(
                                _showSummary
                                    ? Icons.auto_awesome
                                    : Icons.auto_awesome_outlined,
                                size: 13,
                                color: theme.colorScheme.primary,
                              ),
                            const SizedBox(width: 5),
                            Text(
                              _isSummarizing
                                  ? 'Summarizing...'
                                  : (_showSummary
                                      ? 'Hide Summary'
                                      : (_aiSummary != null && _aiSummary!.isNotEmpty
                                          ? 'View Summary'
                                          : 'AI Summarize')),
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: _showSummary ? FontWeight.bold : FontWeight.w600,
                                color: _showSummary
                                    ? theme.colorScheme.primary
                                    : (isDark ? theme.colorScheme.onSurface : const Color(0xFF334155)),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    // 2. Neural Audio Playback (Listen via Kokoro TTS)
                    Obx(() {
                      final audio = TtsAudioService.instance;
                      final isThisPlaying = audio.isAnnouncementPlaying(widget.notice.id);
                      final isThisBuffering = audio.isAnnouncementActive(widget.notice.id) && audio.isBuffering.value;
                      return InkWell(
                        onTap: () => audio.playAnnouncement(
                          widget.notice.id,
                          title: widget.notice.title,
                          content: widget.notice.description,
                          summary: _aiSummary ?? widget.notice.aiSummary,
                          forceMode: _showSummary ? 'summary' : null,
                        ),
                        borderRadius: BorderRadius.circular(14),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 5),
                          decoration: BoxDecoration(
                            color: isThisPlaying
                                ? (isDark ? theme.colorScheme.primary.withOpacity(0.20) : const Color(0xFFEEF2FF))
                                : (isDark ? theme.colorScheme.surfaceContainer : const Color(0xFFF8FAFC)),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: isThisPlaying
                                  ? (isDark ? theme.colorScheme.primary : const Color(0xFF818CF8))
                                  : (isDark ? theme.colorScheme.outline : const Color(0xFFE2E8F0)),
                              width: 1.0,
                            ),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (isThisBuffering)
                                const SizedBox(
                                  width: 12,
                                  height: 12,
                                  child: CircularProgressIndicator(strokeWidth: 1.5),
                                )
                              else
                                Icon(
                                  isThisPlaying
                                      ? Icons.pause_rounded
                                      : Icons.volume_up_rounded,
                                  size: 14,
                                  color: theme.colorScheme.primary,
                                ),
                              const SizedBox(width: 4),
                              Text(
                                isThisPlaying ? 'Playing' : 'Listen',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: isThisPlaying ? FontWeight.bold : FontWeight.w600,
                                  color: isThisPlaying
                                      ? theme.colorScheme.primary
                                      : (isDark ? theme.colorScheme.onSurface : const Color(0xFF334155)),
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }),

                    // 3. Calendar Sync Button
                    InkWell(
                      onTap: _isLoadingCalendar ? null : _handleCalendarTap,
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 5),
                        decoration: BoxDecoration(
                          color: isDark ? theme.colorScheme.surfaceContainer : const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: isDark ? theme.colorScheme.outline : const Color(0xFFE2E8F0),
                            width: 1.0,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (_isLoadingCalendar)
                              SizedBox(
                                width: 12,
                                height: 12,
                                child: CircularProgressIndicator(
                                  strokeWidth: 1.5,
                                  color: theme.colorScheme.primary,
                                ),
                              )
                            else
                              Icon(
                                Icons.calendar_month_outlined,
                                size: 13,
                                color: theme.colorScheme.primary,
                              ),
                            const SizedBox(width: 4),
                            Text(
                              _isLoadingCalendar ? 'Syncing...' : 'Add to Calendar',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: isDark ? theme.colorScheme.onSurface : const Color(0xFF334155),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    // 4. Read Details Button
                    InkWell(
                      onTap: () => openAnnouncementDetail(context, widget.notice),
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: isDark ? theme.colorScheme.surfaceContainer : const Color(0xFFF1F5F9),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: isDark ? theme.colorScheme.outline : const Color(0xFFE2E8F0),
                            width: 1.0,
                          ),
                        ),
                        child: Text(
                          'Read Details \u2192',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    ));
  }
}

// ----------------------------------------------------------------------
// Dashboard Skeleton -- Shimmer loading placeholder
// ----------------------------------------------------------------------
class DashboardSkeleton extends StatelessWidget {
  const DashboardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final baseColor = isDark ? Colors.grey.shade800 : Colors.grey.shade300;
    final highlightColor = isDark ? Colors.grey.shade700 : Colors.grey.shade100;
    final cardColor = isDark ? Colors.grey.shade900 : Colors.white;

    return Shimmer.fromColors(
      baseColor: baseColor,
      highlightColor: highlightColor,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Banner skeleton
            Container(
              height: 80,
              decoration: BoxDecoration(
                color: cardColor,
                borderRadius: BorderRadius.circular(16),
              ),
            ),
            const SizedBox(height: 20),

            // Stats row skeleton
            Row(
              children: List.generate(
                3,
                (_) => Expanded(
                  child: Container(
                    margin: const EdgeInsets.only(right: 10),
                    height: 110,
                    decoration: BoxDecoration(
                      color: cardColor,
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Carousel skeleton
            Container(
              height: 195,
              decoration: BoxDecoration(
                color: cardColor,
                borderRadius: BorderRadius.circular(18),
              ),
            ),
            const SizedBox(height: 24),

            // Feed card skeletons
            ...List.generate(
              3,
              (_) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Container(
                  height: 150,
                  decoration: BoxDecoration(
                    color: cardColor,
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ----------------------------------------------------------------------
// Quick Action Card -- Enhanced with badge support
// ----------------------------------------------------------------------
class QuickActionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;
  final int? badgeCount;

  const QuickActionCard({
    super.key,
    required this.title,
    required this.icon,
    required this.color,
    required this.onTap,
    this.badgeCount,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(right: 12.0),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          width: 130,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                color.withOpacity(0.12),
                color.withOpacity(0.05),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: color.withOpacity(0.2)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Stack(
                clipBehavior: Clip.none,
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(icon, color: color, size: 22),
                  ),
                  if (badgeCount != null && badgeCount! > 0)
                    Positioned(
                      right: -6,
                      top: -6,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive,
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Text(
                          badgeCount! > 99 ? '99+' : '$badgeCount',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                title,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  color: theme.colorScheme.onSurface,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
