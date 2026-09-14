import 'package:flutter/material.dart';
import 'package:echosphere/utils/theme_extensions.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/custom_widgets/echosphere_button.dart';

void showEchoSpherePrivacyPolicy(BuildContext context) {
  showDialog(
    context: context,
    builder: (ctx) {
      return Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        backgroundColor: ctx.colors.surface,
        insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 550, maxHeight: 600),
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: ctx.colors.primary.opaque(0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.security_rounded,
                      color: ctx.colors.primary,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const EchoSphereText(
                          text: 'Privacy Policy & Data Safety',
                          size: 16,
                          variant: TextVariant.bold,
                        ),
                        EchoSphereText(
                          text: 'EchoSphere Campus PA & Notification System',
                          size: 11,
                          color: ctx.colors.onSurface.opaque(0.6),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 20),
                    onPressed: () => Navigator.of(ctx).pop(),
                  ),
                ],
              ),
              const Divider(height: 24),

              // Scrollable Policy Content
              Expanded(
                child: SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSectionTitle('1. Institutional Purpose & Scope'),
                      _buildParagraph(
                        'EchoSphere is designed specifically for academic institutions to broadcast official circulars, emergency announcements, and audio notices across campus speakers. We respect your digital privacy and ensure full transparency regarding information handled by this app.',
                      ),
                      const SizedBox(height: 14),

                      _buildSectionTitle('2. Information Handled'),
                      _buildBullet('Authentication Identity: USN (University Seat Number), Employee ID, official institutional email, and hashed credentials.'),
                      _buildBullet('Role & Permissions: Department assignment and authorization level (Student, Teacher, HoD, Admin, Principal).'),
                      _buildBullet('Notice Content: Circular text, category tags, priority levels, audio TTS synthesize requests, and document attachments.'),
                      _buildBullet('Hardware Telemetry: ESP32 speaker node status, Wi-Fi connectivity, audio volume, and playback state.'),
                      const SizedBox(height: 14),

                      _buildSectionTitle('3. Device Permissions & Scoped Storage'),
                      _buildParagraph(
                        'EchoSphere strictly obeys modern Android Scoped Storage and Google Play Store policies:\n'
                        'â€¢ File Downloads: Official notices and circular attachments are saved directly to your device without requiring broad storage permissions.\n'
                        'â€¢ Media Upload: Media permissions (READ_MEDIA_IMAGES/VIDEO) are only requested when you explicitly choose to attach an image or PDF to a notice.\n'
                        'â€¢ Audio Recording: Audio permission is used solely for optional speech-to-text dictation when drafting announcements.\n'
                        'â€¢ Notifications: POST_NOTIFICATIONS is requested on Android 13+ to deliver critical campus emergency alerts.',
                      ),
                      const SizedBox(height: 14),

                      _buildSectionTitle('4. Data Protection & Zero-Sharing Commitment'),
                      _buildParagraph(
                        'All network communication occurs over secure HTTPS and WSS protocols with cryptographic token authorization. We do NOT track users across third-party apps, sell personal data, or serve third-party commercial advertisements.',
                      ),
                      const SizedBox(height: 14),

                      _buildSectionTitle('5. Institutional Administration & Data Rights'),
                      _buildParagraph(
                        'Your campus account is managed by your institution\'s authorized College Administrator. You may request account password resets (up to 5 per calendar year for students/faculty) or ask your administration to rectify any departmental records.',
                      ),
                      const SizedBox(height: 14),

                      _buildSectionTitle('6. Contact & Support'),
                      _buildParagraph(
                        'For questions regarding campus data handling or system privacy, contact the Campus IT Cell or email: support@echosphere.edu.',
                      ),
                    ],
                  ),
                ),
              ),
              const Divider(height: 24),

              // Footer Button
              Align(
                alignment: Alignment.centerRight,
                child: EchoSphereButton(
                  color: ctx.colors.primary,
                  radius: 12,
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  onTap: () => Navigator.of(ctx).pop(),
                  child: const Text(
                    'I Understand',
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    },
  );
}

Widget _buildSectionTitle(String title) {
  return Text(
    title,
    style: const TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.bold,
      letterSpacing: 0.2,
    ),
  );
}

Widget _buildParagraph(String text) {
  return Padding(
    padding: const EdgeInsets.only(top: 4.0),
    child: Text(
      text,
      style: const TextStyle(
        fontSize: 12,
        height: 1.45,
        color: Colors.grey,
      ),
    ),
  );
}

Widget _buildBullet(String text) {
  return Padding(
    padding: const EdgeInsets.only(top: 3.0, left: 6.0),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('â€¢ ', style: TextStyle(fontSize: 12, color: Colors.grey, fontWeight: FontWeight.bold)),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(fontSize: 12, height: 1.4, color: Colors.grey),
          ),
        ),
      ],
    ),
  );
}
