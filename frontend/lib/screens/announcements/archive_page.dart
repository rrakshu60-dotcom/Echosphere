import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/utils/navigation_helper.dart';
import 'package:echosphere/widgets/common/glow.dart';
import 'package:echosphere/widgets/custom_widgets/attachment_viewer_dialog.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_chip.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_container.dart';
import 'package:echosphere/widgets/custom_widgets/notice_sort_button.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

class ArchivePage extends StatefulWidget {
  const ArchivePage({super.key});

  @override
  State<ArchivePage> createState() => _ArchivePageState();
}

class _ArchivePageState extends State<ArchivePage> {
  final AnnouncementController controller = Get.find<AnnouncementController>();
  final TextEditingController searchController = TextEditingController();
  String searchQuery = '';



  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SubPagePopScope(
      fallbackRoute: '/home',
      child: Scaffold(
        body: Glow(
          child: SafeArea(
            child: Column(
              children: [
                // Header
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 10.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const EchoSphereBackButton(fallbackRoute: '/home'),
                          const SizedBox(width: 4),
                          Icon(Icons.inventory_2_rounded, size: 22, color: theme.colorScheme.primary),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Notice Archive',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                    color: theme.colorScheme.onSurface,
                                  ),
                                ),
                                Text(
                                  'Historical notices older than 1 week',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    const SizedBox(height: 8),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          const NoticeSortButton(compact: true),
                          const SizedBox(width: 8),
                          Obx(() => EchoSphereChip(
                                label: '${controller.archivedAnnouncements.length} Archived',
                                isSelected: true,
                                onSelected: (_) {},
                              )),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),

              // Search Bar
              Padding(
                padding: const EdgeInsets.all(14.0),
                child: TextField(
                  controller: searchController,
                  onChanged: (val) => setState(() => searchQuery = val),
                  decoration: InputDecoration(
                    hintText: 'Search archive by title, author, or department...',
                    prefixIcon: Icon(Icons.search_rounded, color: theme.colorScheme.primary),
                    suffixIcon: searchQuery.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear_rounded),
                            onPressed: () {
                              searchController.clear();
                              setState(() => searchQuery = '');
                            },
                          )
                        : null,
                    filled: true,
                    fillColor: theme.colorScheme.primary.withOpacity(0.08),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide(color: theme.colorScheme.primary.withOpacity(0.2), width: 1),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide(color: theme.colorScheme.primary.withOpacity(0.2), width: 1),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  ),
                ),
              ),

              // List of Archived Announcements
              Expanded(
                child: Obx(() {
                  final archives = controller.archivedAnnouncements.where((a) {
                    final q = searchQuery.toLowerCase();
                    return q.isEmpty ||
                        a.title.toLowerCase().contains(q) ||
                        a.creatorName.toLowerCase().contains(q) ||
                        a.department.toLowerCase().contains(q) ||
                        a.category.toLowerCase().contains(q);
                  }).toList();

                  if (archives.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.archive_outlined, size: 56, color: theme.colorScheme.onSurface.withOpacity(0.25)),
                          const SizedBox(height: 12),
                          Text(
                            'No archived announcements found.',
                            style: TextStyle(color: theme.colorScheme.onSurface.withOpacity(0.5), fontSize: 14),
                          ),
                        ],
                      ),
                    );
                  }

                  return ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 6.0),
                    itemCount: archives.length,
                    itemBuilder: (ctx, i) {
                      final item = archives[i];

                      return Padding(
                        padding: const EdgeInsets.only(bottom: 14.0),
                        child: EchoSphereContainer(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Top Badges & Date
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                children: [
                                  EchoSphereBadge.secondary(label: item.category),
                                  EchoSphereBadge.outline(label: item.department),
                                  const EchoSphereBadge.muted(label: 'ARCHIVED'),
                                  Text(
                                    DateFormat('MMM dd, yyyy').format(item.createdAt),
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: theme.colorScheme.onSurface.withOpacity(0.5),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),

                              // Title
                              Text(
                                item.title,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 8),

                              // Author & Delivery Info
                              Row(
                                children: [
                                  Icon(Icons.person_outline_rounded, size: 15, color: theme.colorScheme.primary),
                                  const SizedBox(width: 4),
                                  Text(
                                    'Author: ${item.creatorName}',
                                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                                  ),
                                  const SizedBox(width: 12),
                                  Icon(Icons.cell_tower_rounded, size: 15, color: theme.colorScheme.primary),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      'Delivery: In-App, Push & Speakers',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontSize: 11,
                                        color: theme.colorScheme.onSurface.withOpacity(0.6),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),

                              // AI Summary
                              if (item.aiSummary != null && item.aiSummary!.isNotEmpty) ...[
                                Container(
                                  padding: const EdgeInsets.all(10),
                                  decoration: BoxDecoration(
                                    color: theme.colorScheme.primary.withOpacity(0.08),
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: theme.colorScheme.primary.withOpacity(0.25)),
                                  ),
                                  child: Row(
                                    children: [
                                      Icon(Icons.auto_awesome, color: theme.colorScheme.primary, size: 18),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          'AI Summary: ${item.aiSummary}',
                                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 10),
                              ],

                              // Description Content Preview
                              Text(
                                item.description,
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 13,
                                  color: theme.colorScheme.onSurface.withOpacity(0.85),
                                  height: 1.4,
                                ),
                              ),
                              const SizedBox(height: 12),

                              // Attachments & View Button
                              Row(
                                children: [
                                  Expanded(
                                    child: item.attachments.isNotEmpty
                                        ? Wrap(
                                            spacing: 8,
                                            runSpacing: 6,
                                            children: item.attachments.map((file) {
                                              IconData icon = Icons.insert_drive_file_rounded;
                                              final Color iconCol = theme.colorScheme.primary;
                                              final lower = file.toLowerCase();
                                              if (lower.endsWith('.pdf')) {
                                                icon = Icons.picture_as_pdf_rounded;
                                              } else if (lower.endsWith('.xls') || lower.endsWith('.xlsx') || lower.endsWith('.csv')) {
                                                icon = Icons.table_chart_rounded;
                                              } else if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg')) {
                                                icon = Icons.image_rounded;
                                              } else if (lower.endsWith('.doc') || lower.endsWith('.docx')) {
                                                icon = Icons.description_rounded;
                                              }
                                              return ActionChip(
                                                avatar: Icon(icon, color: iconCol, size: 16),
                                                label: Text(file, style: const TextStyle(fontSize: 11), maxLines: 1, overflow: TextOverflow.ellipsis),
                                                onPressed: () => AttachmentViewerDialog.show(
                                                  context,
                                                  filename: file,
                                                  notice: item,
                                                ),
                                              );
                                            }).toList(),
                                          )
                                        : Text(
                                            'No attachments',
                                            style: TextStyle(
                                              fontSize: 11,
                                              fontStyle: FontStyle.italic,
                                              color: theme.colorScheme.onSurface.withOpacity(0.5),
                                            ),
                                          ),
                                  ),
                                  const SizedBox(width: 8),
                                  IconButton(
                                    tooltip: 'View Full Notice',
                                    icon: const Icon(Icons.open_in_new_rounded),
                                    onPressed: () => openAnnouncementDetail(context, item),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  );
                }),
              ),
            ],
          ),
        ),
      ),
    ),
    );
  }
}
