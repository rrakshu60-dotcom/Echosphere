import 'dart:async';
import 'package:flutter/services.dart';
import 'package:anymex/ai/echosphere_ai.dart';
import 'package:anymex/constants/themes.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/screens/announcements/approval_queue_page.dart';
import 'package:anymex/screens/announcements/create_announcement_dialog.dart';
import 'package:anymex/screens/announcements/speaker_queue_page.dart';
import 'package:anymex/screens/home/home_dashboard_widgets.dart';
import 'package:anymex/screens/notifications/notifications_page.dart';
import 'package:anymex/screens/profile/profile_page.dart';
import 'package:anymex/widgets/common/glow.dart';
import 'package:anymex/widgets/common/navbar.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/notice_sort_button.dart';
import 'package:anymex/widgets/header.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedNavIndex = 0;
  final List<int> _navHistory = [0];

  final AuthController authController = Get.put(AuthController());
  final AnnouncementController annController = Get.put(AnnouncementController());

  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();
  Timer? _searchDebounce;

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  void _onSearchChanged(String val) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 250), () {
      annController.searchQuery.value = val;
    });
  }

  void _clearSearch() {
    _searchDebounce?.cancel();
    _searchController.clear();
    annController.searchQuery.value = '';
  }

  void _onSelectTab(int index) {
    if (_selectedNavIndex == index) return;
    setState(() {
      _navHistory.add(index);
      _selectedNavIndex = index;
    });
  }

  void _handleBack() {
    if (_navHistory.length > 1) {
      setState(() {
        _navHistory.removeLast();
        _selectedNavIndex = _navHistory.last;
      });
    } else if (_selectedNavIndex != 0) {
      setState(() {
        _selectedNavIndex = 0;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDesktop = MediaQuery.of(context).size.width > 750;

    return Focus(
      autofocus: false,
      onKeyEvent: (node, event) {
        if (event is KeyDownEvent) {
          if (event.logicalKey == LogicalKeyboardKey.slash && !_searchFocusNode.hasFocus) {
            _searchFocusNode.requestFocus();
            return KeyEventResult.handled;
          }
          if (event.logicalKey == LogicalKeyboardKey.escape) {
            if (_searchFocusNode.hasFocus) {
              _searchFocusNode.unfocus();
              return KeyEventResult.handled;
            }
          }
        }
        return KeyEventResult.ignored;
      },
      child: PopScope(
      canPop: _selectedNavIndex == 0 && _navHistory.length <= 1,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        _handleBack();
      },
      child: Scaffold(
      body: Glow(
        child: SafeArea(
          top: true,
          bottom: false,
          child: Column(
            children: [
              const Header(type: PageType.home),
              const Divider(height: 1),

              Expanded(
                child: Obx(() {
                  final _ = authController.currentUser.value;
                  final navItems = _buildNavItems(context);
                  final pages = _buildPages(context, theme);

                  // Reset index if out of range when role changes
                  final safeIndex = _selectedNavIndex >= navItems.length ? 0 : _selectedNavIndex;

                  return Row(
                    children: [
                      // Desktop Side Navigation Bar
                      if (isDesktop)
                        ResponsiveNavBar(
                          isDesktop: true,
                          currentIndex: safeIndex,
                          items: navItems,
                        ),

                      // Main View Content
                      Expanded(
                        child: IndexedStack(
                          index: safeIndex,
                          children: pages,
                        ),
                      ),
                    ],
                  );
                }),
              ),
            ],
          ),
        ),
      ),

      // Mobile Bottom Navigation Bar (Uniform DevAdmin Glassmorphic Design)
      bottomNavigationBar: Obx(() {
        final _ = authController.currentUser.value;
        final navItems = _buildNavItems(context);
        final safeIndex = _selectedNavIndex >= navItems.length ? 0 : _selectedNavIndex;

        return isDesktop
            ? const SizedBox.shrink()
            : ResponsiveNavBar(
                isDesktop: false,
                currentIndex: safeIndex,
                items: navItems,
              );
      }),

      // Floating Creation Button for authorized users (Non-Student)
      floatingActionButton: Obx(() {
        final user = authController.currentUser.value;
        final canCreate = user != null && user.role != 'Student';

        if (_selectedNavIndex == 0 && canCreate) {
          return FloatingActionButton.extended(
            onPressed: () {
              showDialog(
                context: context,
                builder: (_) => const CreateAnnouncementDialog(),
              );
            },
            icon: const Icon(Icons.add),
            label: const Text('New Notice'),
            backgroundColor: theme.colorScheme.primary,
          );
        }
        return const SizedBox.shrink();
      }),
    )));
  }

  List<Widget> _buildPages(BuildContext context, ThemeData theme) {
    final user = authController.currentUser.value;
    final role = user?.role ?? 'Student';

    Widget secondPage;
    if (role == 'HoD' || role == 'Teacher' || role == 'Developer' || role == 'College Admin' || role == 'Principal' || role == 'Dev Admin') {
      secondPage = const ApprovalQueuePage();
    } else {
      secondPage = const SpeakerQueuePage();
    }

    return [
      _buildAnnouncementsDashboard(context, theme),
      secondPage,
      const EchosphereAi(),
      const NotificationsPage(),
      const ProfilePage(),
    ];
  }

  List<NavItem> _buildNavItems(BuildContext context) {
    final user = authController.currentUser.value;
    final role = user?.role ?? 'Student';

    IconData secondSelectedIcon = Icons.podcasts_rounded;
    IconData secondUnselectedIcon = Icons.podcasts_outlined;
    String secondLabel = 'Broadcasts';

    if (role == 'HoD' || role == 'Teacher' || role == 'Developer' || role == 'College Admin' || role == 'Principal' || role == 'Dev Admin') {
      secondSelectedIcon = Icons.fact_check_rounded;
      secondUnselectedIcon = Icons.fact_check_outlined;
      secondLabel = 'Approvals';
    }

    return [
      NavItem(
        selectedIcon: Icons.grid_view_rounded,
        unselectedIcon: Icons.grid_view_outlined,
        label: 'Notices',
        onTap: (index) => _onSelectTab(index),
      ),
      NavItem(
        selectedIcon: secondSelectedIcon,
        unselectedIcon: secondUnselectedIcon,
        label: secondLabel,
        onTap: (index) => _onSelectTab(index),
      ),
      NavItem(
        selectedIcon: Icons.auto_awesome_rounded,
        unselectedIcon: Icons.auto_awesome_outlined,
        label: 'AI Assistant',
        onTap: (index) => _onSelectTab(index),
      ),
      NavItem(
        selectedIcon: Icons.notifications_rounded,
        unselectedIcon: Icons.notifications_outlined,
        label: 'Alerts',
        onTap: (index) => _onSelectTab(index),
      ),
      NavItem(
        selectedIcon: Icons.person_rounded,
        unselectedIcon: Icons.person_outline_rounded,
        label: 'Profile',
        onTap: (index) => _onSelectTab(index),
      ),
    ];
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Central Dashboard — The Home Screen
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildAnnouncementsDashboard(BuildContext context, ThemeData theme) {
    final isDark = theme.brightness == Brightness.dark;

    return Obx(() {
      // Show shimmer skeleton only on initial load when data is empty
      if (annController.isLoading.value && annController.announcements.isEmpty) {
        return const DashboardSkeleton();
      }

      final user = authController.currentUser.value;
      final role = user?.role ?? 'Student';
      final isStaffOrAdmin = role != 'Student';

      return RefreshIndicator(
        onRefresh: () async {
          try {
            HapticFeedback.lightImpact();
          } catch (_) {}
          await annController.fetchAnnouncements();
        },
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ─── Section 1: Welcome Banner ─────────────────────────
              _buildWelcomeBanner(theme),
              const SizedBox(height: 16),

              // ─── Section 2: Admin Quick Workspace Console (for Staff/Admin) ─
              if (isStaffOrAdmin) ...[
                _buildAdminWorkspaceBar(theme, role),
                const SizedBox(height: 18),
              ],

              // ─── Section 4: Priority Announcements Carousel ────────
              Obx(() {
                final priorityList = annController.priorityAnnouncements;
                if (priorityList.isEmpty) return const SizedBox.shrink();
                return Padding(
                  padding: const EdgeInsets.only(bottom: 20),
                  child: PriorityCarousel(items: priorityList),
                );
              }),

              // ─── Section 5: Integrated Dashboard Search Bar ─────────
              Container(
                decoration: BoxDecoration(
                  color: isDark ? EchoSpherePalette.darkSurface : EchoSpherePalette.lightSurface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder,
                    width: 1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: isDark ? Colors.black.withValues(alpha: 0.4) : const Color(0xFF0F172A).withValues(alpha: 0.03),
                      blurRadius: 12,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: TextField(
                  controller: _searchController,
                  focusNode: _searchFocusNode,
                  onChanged: _onSearchChanged,
                  decoration: InputDecoration(
                    isDense: true,
                    filled: false,
                    hintText: 'Search notices by title, department, or keyword... (Press / to focus)',
                    hintStyle: TextStyle(
                      fontSize: 12.5,
                      color: isDark ? theme.colorScheme.onSurface.withValues(alpha: 0.5) : const Color(0xFF64748B),
                    ),
                    prefixIcon: Icon(
                      Icons.search_rounded,
                      size: 20,
                      color: theme.colorScheme.primary,
                    ),
                    prefixIconConstraints: const BoxConstraints(minWidth: 40, minHeight: 40),
                    suffixIcon: Obx(() {
                      if (annController.searchQuery.value.isEmpty) {
                        return const SizedBox.shrink();
                      }
                      return IconButton(
                        icon: const Icon(Icons.clear_rounded, size: 16),
                        onPressed: _clearSearch,
                      );
                    }),
                    suffixIconConstraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // ─── Section 6: Category Filter Chips ──────────────────
              _buildCategoryFilters(theme),
              const SizedBox(height: 16),

              // ─── Section 7: Announcement Feed ──────────────────────
              _buildAnnouncementFeed(theme),
            ],
          ),
        ),
      );
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Welcome Banner
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildWelcomeBanner(ThemeData theme) {
    return Obx(() {
      final user = authController.currentUser.value;
      final role = user?.role ?? 'Student';
      final isDark = theme.brightness == Brightness.dark;

      return TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.0, end: 1.0),
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeOutCubic,
        builder: (context, value, child) => Opacity(
          opacity: value,
          child: Transform.translate(
            offset: Offset(0, 12 * (1 - value)),
            child: child,
          ),
        ),
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: isDark ? EchoSpherePalette.darkSurface : EchoSpherePalette.lightSurface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder,
              width: 1.0,
            ),
            boxShadow: [
              BoxShadow(
                color: isDark
                    ? Colors.black.withValues(alpha: 0.4)
                    : const Color(0xFF0F172A).withValues(alpha: 0.03),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      theme.colorScheme.primary,
                      theme.colorScheme.primary.withValues(alpha: 0.7),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(
                  Icons.campaign_rounded,
                  size: 24,
                  color: Colors.white,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            user != null
                                ? 'Welcome back, ${user.fullName}'
                                : 'Welcome to EchoSphere',
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (user != null) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: isDark ? theme.colorScheme.primary.withValues(alpha: 0.15) : const Color(0xFFEEF2FF),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                color: isDark ? theme.colorScheme.primary.withValues(alpha: 0.3) : const Color(0xFFC7D2FE),
                                width: 0.8,
                              ),
                            ),
                            child: Text(
                              role.toUpperCase(),
                              style: TextStyle(
                                fontSize: 9.5,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 0.5,
                                color: theme.colorScheme.primary,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      user != null
                          ? '${user.department ?? "College-Wide"} Department'
                          : 'Log in to access college announcements.',
                      style: TextStyle(
                        fontSize: 12,
                        color: isDark ? theme.colorScheme.onSurface.withValues(alpha: 0.65) : const Color(0xFF475569),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Obx(() {
                      final total = annController.announcements.length;
                      final today = annController.todayAnnouncements.length;
                      final urgent = annController.emergencyCount;

                      return Row(
                        children: [
                          Icon(Icons.feed_outlined, size: 13, color: theme.colorScheme.primary),
                          const SizedBox(width: 4),
                          Text(
                            '$total Total Notices',
                            style: TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w600,
                              color: isDark ? theme.colorScheme.onSurface.withValues(alpha: 0.8) : const Color(0xFF334155),
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 6.0),
                            child: Text('•', style: TextStyle(fontSize: 11, color: isDark ? theme.colorScheme.onSurface.withValues(alpha: 0.4) : const Color(0xFF94A3B8))),
                          ),
                          Text(
                            '$today Today',
                            style: TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w600,
                              color: theme.colorScheme.primary,
                            ),
                          ),
                          if (urgent > 0) ...[
                            Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 6.0),
                              child: Text('•', style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.35))),
                            ),
                            Text(
                              '$urgent Urgent',
                              style: TextStyle(
                                fontSize: 11.5,
                                fontWeight: FontWeight.w600,
                                color: isDark ? EchoSpherePalette.darkDestructive : EchoSpherePalette.lightDestructive,
                              ),
                            ),
                          ],
                        ],
                      );
                    }),
                  ],
                ),
              ),
              if (user == null)
                EchoSphereButton(
                  height: 36,
                  onTap: () => Get.toNamed('/login'),
                  child: const Text('Login'),
                ),
            ],
          ),
        ),
      );
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Admin Quick Workspace Bar (For Staff / Admins)
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildAdminWorkspaceBar(ThemeData theme, String role) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Admin Workspace',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.85),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Text(
                'MANAGEMENT CONSOLE',
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.6,
                  color: theme.colorScheme.primary,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _buildWorkspaceActionTile(
                theme: theme,
                title: 'Notice Hub',
                subtitle: 'Moderate notices',
                icon: Icons.auto_fix_high_rounded,
                color: theme.colorScheme.primary,
                onTap: () => Get.toNamed('/announcement-management'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildWorkspaceActionTile(
                theme: theme,
                title: 'User Hub',
                subtitle: 'Directory & roles',
                icon: Icons.manage_accounts_rounded,
                color: theme.colorScheme.primary,
                onTap: () => Get.toNamed('/user-management'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildWorkspaceActionTile({
    required ThemeData theme,
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    final isDark = theme.brightness == Brightness.dark;

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

  // ──────────────────────────────────────────────────────────────────────────
  // Category Filter Chips
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildCategoryFilters(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Categories',
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 10),
        Obx(
          () => SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: EchoSphereChip(
                    label: 'For You',
                    icon: Icons.auto_awesome_rounded,
                    isSelected: annController.showForYouOnly.value,
                    onSelected: (val) {
                      annController.showForYouOnly.value = val;
                      if (val) {
                        annController.showBookmarkedOnly.value = false;
                        annController.showTodayOnly.value = false;
                        annController.searchQuery.value = '';
                        annController.selectedCategory.value = 'All';
                      }
                    },
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: EchoSphereChip(
                    label: annController.bookmarkedNoticeIds.isNotEmpty
                        ? 'Saved (${annController.bookmarkedNoticeIds.length})'
                        : 'Saved',
                    icon: Icons.bookmark_rounded,
                    isSelected: annController.showBookmarkedOnly.value,
                    onSelected: (val) {
                      annController.showBookmarkedOnly.value = val;
                      if (val) {
                        annController.showForYouOnly.value = false;
                        annController.showTodayOnly.value = false;
                        annController.searchQuery.value = '';
                        annController.selectedCategory.value = 'All';
                      }
                    },
                  ),
                ),
                ...AnnouncementController.categories.map((cat) {
                  final isSelected = !annController.showForYouOnly.value &&
                      !annController.showBookmarkedOnly.value &&
                      annController.selectedCategory.value == cat;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: EchoSphereChip(
                      label: cat,
                      isSelected: isSelected,
                      onSelected: (val) {
                        if (val) {
                          annController.showForYouOnly.value = false;
                          annController.showBookmarkedOnly.value = false;
                          annController.showTodayOnly.value = false;
                          annController.searchQuery.value = '';
                          annController.selectedCategory.value = cat;
                        }
                      },
                    ),
                  );
                }),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Announcement Feed List
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildAnnouncementFeed(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          runSpacing: 8,
          spacing: 8,
          children: [
            const Text(
              'Recent Announcements',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
              ),
            ),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const NoticeSortButton(),
                  const SizedBox(width: 6),
                  Obx(() => Container(
                        padding:
                            const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Text(
                          '${annController.filteredAnnouncements.length} Notices',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                      )),
                  const SizedBox(width: 6),
                  InkWell(
                    onTap: () => Get.toNamed('/archive'),
                    borderRadius: BorderRadius.circular(14),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.6),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: theme.colorScheme.outline.withValues(alpha: 0.3),
                          width: 0.8,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.inventory_2_outlined,
                            size: 13,
                            color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Archive',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: theme.colorScheme.onSurface.withValues(alpha: 0.8),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),

        Obx(() {
          final feed = annController.filteredAnnouncements;

          if (feed.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(40.0),
                child: Column(
                  children: [
                    Icon(Icons.inbox_outlined,
                        size: 56,
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.2)),
                    const SizedBox(height: 16),
                    Text(
                      'No announcements match your search or filter.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Try a different category or clear your search.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.35),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }

          return ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: feed.length,
            itemBuilder: (context, index) {
              return AnnouncementFeedCard(
                notice: feed[index],
                index: index,
              );
            },
          );
        }),
      ],
    );
  }
}
