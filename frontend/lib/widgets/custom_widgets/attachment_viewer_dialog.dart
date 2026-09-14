import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import 'package:echosphere/constants/themes.dart';
import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_button.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_container.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';

class AttachmentViewerDialog extends StatelessWidget {
  final String filename;
  final AnnouncementModel notice;

  const AttachmentViewerDialog({
    super.key,
    required this.filename,
    required this.notice,
  });

  static void show(BuildContext context, {required String filename, required AnnouncementModel notice}) {
    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (ctx) => AttachmentViewerDialog(filename: filename, notice: notice),
    );
  }

  bool get _isImage {
    final lower = filename.toLowerCase();
    return lower.endsWith('.png') ||
        lower.endsWith('.jpg') ||
        lower.endsWith('.jpeg') ||
        lower.endsWith('.webp') ||
        lower.endsWith('.gif');
  }

  bool get _isPdf => filename.toLowerCase().endsWith('.pdf');

  String get _fileTypeLabel {
    final lower = filename.toLowerCase();
    if (lower.endsWith('.pdf')) return 'PDF Document';
    if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'Image File';
    if (lower.endsWith('.xlsx') || lower.endsWith('.xls') || lower.endsWith('.csv')) return 'Spreadsheet Data';
    if (lower.endsWith('.doc') || lower.endsWith('.docx')) return 'Word Document';
    return 'Official Attachment';
  }

  IconData get _fileIcon {
    final lower = filename.toLowerCase();
    if (lower.endsWith('.pdf')) return Icons.picture_as_pdf_rounded;
    if (_isImage) return Icons.image_rounded;
    if (lower.endsWith('.xlsx') || lower.endsWith('.xls') || lower.endsWith('.csv')) return Icons.table_chart_rounded;
    if (lower.endsWith('.doc') || lower.endsWith('.docx')) return Icons.description_rounded;
    return Icons.insert_drive_file_rounded;
  }

  Future<void> _handleDownload(BuildContext context) async {
    HapticFeedback.mediumImpact();
    if (kIsWeb) {
      snackBar('Initiating download for "$filename"...');
      return;
    }

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
                        ECHOSPHERE INSTITUTIONAL NOTICE
================================================================================

TITLE: ${notice.title}
DEPARTMENT: ${notice.department}
CATEGORY: ${notice.category}
PRIORITY: ${notice.priority}
ISSUED BY: ${notice.creatorName} (Designation: ${notice.creatorRole})
DATE: ${DateFormat('MMMM dd, yyyy \u2022 hh:mm a').format(notice.createdAt)}
ATTACHMENT: $filename

--------------------------------------------------------------------------------
OFFICIAL NOTICE CONTENT:
--------------------------------------------------------------------------------
${notice.description}

AI SUMMARY:
${notice.aiSummary ?? 'N/A'}

================================================================================
Downloaded & Saved via EchoSphere Smart Campus System
Generated at: ${DateTime.now().toIso8601String()}
================================================================================
''';
      await file.writeAsString(content);
      snackBar('Saved "$filename" to ${dir.path}');
    } catch (e) {
      snackBar('Failed to save file: $e');
    }
  }

  Future<void> _handleShare() async {
    HapticFeedback.lightImpact();
    try {
      final shareText = '''
ðŸ“¢ ${notice.title}
ðŸ“ Attachment: $filename
ðŸ› Department: ${notice.department}
ðŸ“… Date: ${DateFormat('MMM dd, yyyy').format(notice.createdAt)}

${notice.description}

-- Shared via EchoSphere Smart Campus System
''';
      await Share.share(shareText, subject: notice.title);
    } catch (e) {
      Clipboard.setData(ClipboardData(text: '${notice.title}\n${notice.description}'));
      snackBar('Notice details copied to clipboard');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final primaryColor = theme.colorScheme.primary;

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 540),
        child: EchoSphereContainer(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Row
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: primaryColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: primaryColor.withValues(alpha: 0.25)),
                    ),
                    child: Icon(_fileIcon, size: 22, color: primaryColor),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          filename,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '$_fileTypeLabel \u2022 Attached to "${notice.title}"',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 11,
                            color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 20),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Preview Viewport
              Container(
                width: double.infinity,
                height: 240,
                decoration: BoxDecoration(
                  color: isDark ? EchoSpherePalette.darkSurface : const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark ? EchoSpherePalette.darkBorder : EchoSpherePalette.lightBorder,
                  ),
                ),
                clipBehavior: Clip.antiAlias,
                child: _isImage
                    ? InteractiveViewer(
                        panEnabled: true,
                        boundaryMargin: const EdgeInsets.all(20),
                        minScale: 0.5,
                        maxScale: 3.5,
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.image_rounded,
                                size: 54,
                                color: primaryColor.withValues(alpha: 0.35),
                              ),
                              const SizedBox(height: 10),
                              Text(
                                filename,
                                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Pinch to zoom or pan image preview',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                                ),
                              ),
                            ],
                          ),
                        ),
                      )
                    : SingleChildScrollView(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  _isPdf ? Icons.picture_as_pdf_rounded : Icons.description_rounded,
                                  size: 16,
                                  color: primaryColor,
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'INSTITUTIONAL DOCUMENT VIEW \u2022 ${notice.department.toUpperCase()}',
                                    style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      letterSpacing: 0.6,
                                      color: primaryColor,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 10),
                            Text(
                              notice.title,
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              notice.description,
                              style: TextStyle(
                                fontSize: 12,
                                height: 1.5,
                                color: theme.colorScheme.onSurface.withValues(alpha: 0.8),
                              ),
                            ),
                            const SizedBox(height: 14),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              decoration: BoxDecoration(
                                color: primaryColor.withValues(alpha: 0.08),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.verified_rounded, size: 13, color: primaryColor),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Verified by ${notice.approverName ?? notice.creatorName}',
                                    style: TextStyle(
                                      fontSize: 10.5,
                                      fontWeight: FontWeight.bold,
                                      color: primaryColor,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
              ),
              const SizedBox(height: 16),

              // Action Buttons
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.end,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  OutlinedButton.icon(
                    icon: const Icon(Icons.copy_rounded, size: 15),
                    label: const Text('Copy Content', style: TextStyle(fontSize: 12)),
                    style: OutlinedButton.styleFrom(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    onPressed: () {
                      HapticFeedback.lightImpact();
                      Clipboard.setData(ClipboardData(text: '${notice.title}\n\n${notice.description}'));
                      snackBar('Notice content copied to clipboard');
                    },
                  ),
                  OutlinedButton.icon(
                    icon: const Icon(Icons.share_rounded, size: 15),
                    label: const Text('Share', style: TextStyle(fontSize: 12)),
                    style: OutlinedButton.styleFrom(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    onPressed: _handleShare,
                  ),
                  EchoSphereButton(
                    height: 38,
                    radius: 12,
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    onTap: () => _handleDownload(context),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.download_rounded, size: 16, color: Colors.white),
                        SizedBox(width: 6),
                        Text(
                          'Download File',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                      ],
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
}
