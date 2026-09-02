import 'package:anymex/ai/echosphere_ai.dart';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/screens/admin/user_management_page.dart';
import 'package:anymex/screens/announcements/speaker_queue_page.dart';
import 'package:anymex/screens/announcements/approval_queue_page.dart';
import 'package:anymex/screens/announcements/archive_page.dart';
import 'package:anymex/screens/announcements/create_announcement_dialog.dart';
import 'package:anymex/screens/auth/login_screen.dart';
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

  final AuthController authController = Get.put(AuthController());
  final AnnouncementController annController = Get.put(AnnouncementController());

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDesktop = MediaQuery.of(context).size.width > 750;

    return Scaffold(
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
    );
  }

  List<Widget> _buildPages(BuildContext context, ThemeData theme) {
    final user = authController.currentUser.value;
    final role = user?.role ?? 'Student';

    Widget secondPage;
    if (role == 'HoD' || role == 'Teacher' || role == 'Developer' || role == 'College Admin' || role == 'Principal' || role == 'Dev Admin') {
      secondPage = const ApprovalQueuePage();
    } else {
      secondPage = _buildSearchPage(context, theme);
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

    IconData secondSelectedIcon = Icons.search_rounded;
    IconData secondUnselectedIcon = Icons.search_outlined;
    String secondLabel = 'Search';

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
        onTap: (index) => setState(() => _selectedNavIndex = index),
      ),
      NavItem(
        selectedIcon: secondSelectedIcon,
        unselectedIcon: secondUnselectedIcon,
        label: secondLabel,
        onTap: (index) => setState(() => _selectedNavIndex = index),
      ),
      NavItem(
        selectedIcon: Icons.auto_awesome_rounded,
        unselectedIcon: Icons.auto_awesome_outlined,
        label: 'AI Assistant',
        onTap: (index) => setState(() => _selectedNavIndex = index),
      ),
      NavItem(
        selectedIcon: Icons.notifications_rounded,
        unselectedIcon: Icons.notifications_outlined,
        label: 'Alerts',
        onTap: (index) => setState(() => _selectedNavIndex = index),
      ),
      NavItem(
        selectedIcon: Icons.person_rounded,
        unselectedIcon: Icons.person_outline_rounded,
        label: 'Profile',
        onTap: (index) => setState(() => _selectedNavIndex = index),
      ),
    ];
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Central Dashboard — The Home Screen
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildAnnouncementsDashboard(BuildContext context, ThemeData theme) {
    return Obx(() {
      // Show shimmer skeleton only on initial load when data is empty
      if (annController.isLoading.value && annController.announcements.isEmpty) {
        return const DashboardSkeleton();
      }

      return RefreshIndicator(
        onRefresh: annController.fetchAnnouncements,
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ─── Section 1: Welcome Banner ─────────────────────────
              _buildWelcomeBanner(theme),
              const SizedBox(height: 16),

              // ─── Section 2: Stats Dashboard Panel ──────────────────
              _buildStatsPanel(theme),
              const SizedBox(height: 20),

              // ─── Section 3: Priority Announcements Carousel ────────
              Obx(() {
                final priorityList = annController.priorityAnnouncements;
                if (priorityList.isEmpty) return const SizedBox.shrink();
                return Padding(
                  padding: const EdgeInsets.only(bottom: 20),
                  child: PriorityCarousel(items: priorityList),
                );
              }),

              // ─── Section 4: Category Filter Chips ──────────────────
              _buildCategoryFilters(theme),
              const SizedBox(height: 16),

              // ─── Section 5: Announcement Feed ──────────────────────
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
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                theme.colorScheme.primary.withOpacity(0.15),
                theme.colorScheme.secondary.withOpacity(0.08),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: theme.colorScheme.primary.withOpacity(0.15),
            ),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  Icons.notifications_active,
                  size: 28,
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      user != null
                          ? 'Welcome back, ${user.fullName}'
                          : 'Welcome to EchoSphere',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        fontFamily: 'Poppins-Bold',
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      user != null
                          ? '${user.department ?? "College-Wide"} Department'
                          : 'Log in to access college announcements.',
                      style: TextStyle(
                        fontSize: 13,
                        color: theme.colorScheme.onSurface.withOpacity(0.65),
                      ),
                    ),
                  ],
                ),
              ),
              if (user == null)
                EchoSphereButton(
                  height: 38,
                  onTap: () => Get.to(() => const LoginScreen()),
                  child: const Text('Login'),
                )
              else if (role == 'College Admin' || role == 'Principal' || role == 'Dev Admin' || role == 'Developer') ...[
                IconButton(
                  tooltip: 'Smart Speaker System',
                  icon: const Icon(Icons.podcasts_rounded),
                  onPressed: () => Get.to(() => const SpeakerQueuePage(), routeName: '/speaker-queue'),
                ),
                IconButton(
                  tooltip: 'User Management Hub',
                  icon: const Icon(Icons.manage_accounts_rounded),
                  onPressed: () => Get.to(() => const UserManagementPage(), routeName: '/user-management'),
                ),
              ],
            ],
          ),
        ),
      );
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Stats Dashboard Panel — Animated metric cards
  // ──────────────────────────────────────────────────────────────────────────
  Widget _buildStatsPanel(ThemeData theme) {
    return Obx(() {
      final user = authController.currentUser.value;
      final role = user?.role ?? 'Student';
      final isAdmin = role == 'College Admin' ||
          role == 'HoD' ||
          role == 'Principal' ||
          role == 'Dev Admin' ||
          role == 'Developer';

      return TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.0, end: 1.0),
        duration: const Duration(milliseconds: 700),
        curve: Curves.easeOutCubic,
        builder: (context, value, child) => Opacity(
          opacity: value,
          child: Transform.translate(
            offset: Offset(0, 16 * (1 - value)),
            child: child,
          ),
        ),
        child: Row(
          children: [
            StatCard(
              label: 'Total Notices',
              value: annController.announcements.length,
              icon: Icons.rss_feed_rounded,
              color: theme.colorScheme.primary,
              onTap: () {
                annController.showTodayOnly.value = false;
                annController.selectedCategory.value = 'All';
                annController.searchQuery.value = '';
              },
            ),
            const SizedBox(width: 10),
            StatCard(
              label: 'Today',
              value: annController.todayAnnouncements.length,
              icon: Icons.today_rounded,
              color: const Color(0xFF10B981),
              onTap: () {
                annController.filterTodayOnly();
              },
            ),
            const SizedBox(width: 10),
            if (isAdmin || role == 'Teacher')
              StatCard(
                label: 'Pending',
                value: annController.pendingApprovals.length,
                icon: Icons.pending_actions_rounded,
                color: const Color(0xFFF59E0B),
                onTap: () => Get.to(() => const ApprovalQueuePage()),
              )
            else
              StatCard(
                label: 'Urgent',
                value: annController.emergencyCount,
                icon: Icons.warning_amber_rounded,
                color: const Color(0xFFEF4444),
                onTap: () {
                  annController.selectedCategory.value = 'All';
                  annController.searchQuery.value = 'EMERGENCY';
                },
              ),
          ],
        ),
      );
    });
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
            fontFamily: 'Poppins-Bold',
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 10),
        Obx(
          () => SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: AnnouncementController.categories.map((cat) {
                final isSelected =
                    annController.selectedCategory.value == cat;
                return Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: EchoSphereChip(
                    label: cat,
                    isSelected: isSelected,
                    onSelected: (val) {
                      if (val) {
                        annController.showTodayOnly.value = false;
                        annController.searchQuery.value = '';
                        annController.selectedCategory.value = cat;
                      }
                    },
                  ),
                );
              }).toList(),
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
                fontFamily: 'Poppins-Bold',
                fontSize: 16,
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
                            const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primary.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(8),
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
                    onTap: () => Get.to(() => const ArchivePage()),
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.amber.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.amber.withOpacity(0.4)),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.inventory_2_rounded, size: 13, color: Colors.amber),
                          SizedBox(width: 4),
                          Text(
                            'Archive',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: Colors.amber,
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
                        color: theme.colorScheme.onSurface.withOpacity(0.2)),
                    const SizedBox(height: 16),
                    Text(
                      'No announcements match your search or filter.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: theme.colorScheme.onSurface.withOpacity(0.4),
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Try a different category or clear your search.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: theme.colorScheme.onSurface.withOpacity(0.3),
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

  Widget _buildSearchPage(BuildContext context, ThemeData theme) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Search Announcements',
            style: TextStyle(
              fontFamily: 'Poppins-Bold',
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 14),

          // Purple Rounded Pill Search Input
          Container(
            decoration: BoxDecoration(
              color: theme.colorScheme.primary.withOpacity(0.12),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: theme.colorScheme.primary.withOpacity(0.25),
                width: 1,
              ),
            ),
            child: TextField(
              onChanged: (val) => annController.searchQuery.value = val,
              decoration: InputDecoration(
                isDense: true,
                filled: false,
                fillColor: Colors.transparent,
                hintText: 'Search by title, department, or keyword...',
                hintStyle: TextStyle(
                  fontSize: 13,
                  color: theme.colorScheme.onSurface.withOpacity(0.5),
                ),
                prefixIcon: Padding(
                  padding: const EdgeInsets.only(left: 12, right: 8),
                  child: Icon(Icons.search_rounded,
                      size: 20,
                      color: theme.colorScheme.primary),
                ),
                prefixIconConstraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                disabledBorder: InputBorder.none,
                errorBorder: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Category Filters
          _buildCategoryFilters(theme),
          const SizedBox(height: 16),

          // Search Results
          Obx(() {
            final feed = annController.filteredAnnouncements;
            if (feed.isEmpty) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(40.0),
                  child: Column(
                    children: [
                      Icon(Icons.search_off_rounded,
                          size: 56,
                          color: theme.colorScheme.onSurface.withOpacity(0.2)),
                      const SizedBox(height: 16),
                      Text(
                        'No announcements found matching your search.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: theme.colorScheme.onSurface.withOpacity(0.5),
                          fontSize: 14,
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
      ),
    );
  }
}
