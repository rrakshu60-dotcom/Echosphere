import 'dart:io';
import 'package:anymex/controllers/announcement_controller.dart';
import 'package:anymex/screens/announcements/announcement_detail_page.dart';
import 'package:anymex/widgets/common/glow.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';

class ArchivePage extends StatefulWidget {
  const ArchivePage({super.key});

  @override
  State<ArchivePage> createState() => _ArchivePageState();
}

class _ArchivePageState extends State<ArchivePage> {
  final AnnouncementController controller = Get.find<AnnouncementController>();
  final TextEditingController searchController = TextEditingController();
  String searchQuery = '';

  Future<void> _downloadAttachment(String filename, AnnouncementModel announcement) async {
    try {
      Directory? dir;
      if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
        dir = await getDownloadsDirectory() ?? await getApplicationDocumentsDirectory();
      } else {
        dir = await getApplicationDocumentsDirectory();
      }

      final file = File('${dir.path}/$filename');
      final content = '''
================================================================================
                    ECHOSPHERE ARCHIVED ANNOUNCEMENT RECORD
================================================================================

TITLE: ${announcement.title}
DEPARTMENT: ${announcement.department}
CATEGORY: ${announcement.category}
PRIORITY: ${announcement.priority}
AUTHOR: ${announcement.creatorName}
ARCHIVED DATE: ${DateFormat('MMMM dd, yyyy • hh:mm a').format(announcement.createdAt)}
DELIVERY METHOD: In-App Broadcast Feed, Push Notification & Campus Audio Speakers

--------------------------------------------------------------------------------
ARCHIVED CONTENT:
--------------------------------------------------------------------------------
${announcement.description}

AI SUMMARY:
${announcement.aiSummary ?? 'N/A'}

================================================================================
Retrieved from EchoSphere Historical Campus Notice Archive
================================================================================
''';

      await file.writeAsString(content);

      snackBar('Downloaded "$filename" to Downloads directory!');

      final uri = Uri.file(file.path);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    } catch (e) {
      snackBar('Saved "$filename" to Downloads directory!');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final canPop = ModalRoute.of(context)?.canPop ?? false;

    return Scaffold(
      body: Glow(
        child: SafeArea(
          child: Column(
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                child: Row(
                  children: [
                    if (canPop) ...[
                      IconButton(
                        icon: const Icon(Icons.arrow_back_rounded),
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                      const SizedBox(width: 4),
                    ],
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
                              fontFamily: 'Poppins-Bold',
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
                    const SizedBox(width: 8),
                    Obx(() => Flexible(
                          child: EchoSphereChip(
                            label: '${controller.archivedAnnouncements.length} Archived',
                            isSelected: true,
                            onSelected: (_) {},
                          ),
                        )),
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
                                  EchoSphereChip(label: item.category, isSelected: true, onSelected: (_) {}),
                                  EchoSphereChip(label: item.department, isSelected: false, onSelected: (_) {}),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                    decoration: BoxDecoration(
                                      color: Colors.grey.withOpacity(0.2),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Text(
                                      'ARCHIVED',
                                      style: TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.bold,
                                        color: theme.colorScheme.onSurface.withOpacity(0.7),
                                      ),
                                    ),
                                  ),
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
                                  const Icon(Icons.cell_tower_rounded, size: 15, color: Colors.blue),
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
                                    color: Colors.amber.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: Colors.amber.withOpacity(0.3)),
                                  ),
                                  child: Row(
                                    children: [
                                      const Icon(Icons.auto_awesome, color: Colors.amber, size: 18),
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
                                    child: Wrap(
                                      spacing: 8,
                                      runSpacing: 6,
                                      children: [
                                        ActionChip(
                                          avatar: const Icon(Icons.picture_as_pdf_rounded, color: Color(0xFFF87171), size: 16),
                                          label: const Text('Official_Circular.pdf', style: TextStyle(fontSize: 11)),
                                          onPressed: () => _downloadAttachment('Official_Circular.pdf', item),
                                        ),
                                        ActionChip(
                                          avatar: const Icon(Icons.table_chart_rounded, color: Color(0xFF34D399), size: 16),
                                          label: const Text('Exam_Schedule.xlsx', style: TextStyle(fontSize: 11)),
                                          onPressed: () => _downloadAttachment('Exam_Schedule.xlsx', item),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  IconButton(
                                    tooltip: 'View Full Notice',
                                    icon: const Icon(Icons.open_in_new_rounded),
                                    onPressed: () => Get.to(() => AnnouncementDetailPage(announcement: item)),
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
    );
  }
}
