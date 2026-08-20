import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:get/get.dart';

class AiChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final String? categoryBadge;
  final String? contextBadge;
  final List<String> suggestedActions;
  final String? navigationTarget;
  final List<Map<String, dynamic>> matchedAnnouncements;

  AiChatMessage({
    required this.text,
    required this.isUser,
    DateTime? timestamp,
    this.categoryBadge,
    this.contextBadge,
    this.suggestedActions = const [],
    this.navigationTarget,
    this.matchedAnnouncements = const [],
  }) : timestamp = timestamp ?? DateTime.now();
}

class EchosphereAiController extends GetxController {
  final RxList<AiChatMessage> messages = <AiChatMessage>[].obs;
  final RxBool isProcessing = false.obs;

  @override
  void onInit() {
    super.onInit();
    final authCtrl = Get.find<AuthController>();
    final user = authCtrl.currentUser.value;
    final dept = user?.department ?? 'CSE';
    final role = user?.role ?? 'Student';
    final name = user?.fullName ?? 'Student';

    messages.add(
      AiChatMessage(
        text:
            'Hello $name! I am EchoSphere AI Assistant.\n\n'
            'I am tuned to your context as **$role** in the **$dept Department**.\n\n'
            'How can I help you today? Ask me about recent announcements, exam schedules, placement drives, or app settings.',
        isUser: false,
        categoryBadge: 'EchoSphere AI',
        contextBadge: '$role • $dept Department',
        suggestedActions: [
          'Show Examination Notices',
          'Check Weather Advisory',
          'View Placement Drives',
          'Where is Settings?',
        ],
      ),
    );
  }

  Future<void> sendQuery(String prompt) async {
    if (prompt.trim().isEmpty) return;

    final authCtrl = Get.find<AuthController>();
    final user = authCtrl.currentUser.value;
    final role = user?.role ?? 'Student';
    final dept = user?.department ?? 'CSE';
    final fullName = user?.fullName ?? 'Student';
    final usnOrEmpId = user?.usn ?? user?.employeeId ?? '';

    final userMsg = prompt.trim();
    messages.add(AiChatMessage(text: userMsg, isUser: true));
    isProcessing.value = true;

    try {
      final apiRes = await EchosphereApiService().sendAiChat(
        userMsg,
        userRole: role,
        department: dept,
        fullName: fullName,
        usnOrEmpId: usnOrEmpId,
      );

      final responseText = apiRes['response'] as String? ?? _generateFallbackResponse(userMsg, role, dept, fullName);
      final catBadge = apiRes['category_badge'] as String? ?? 'EchoSphere AI';
      final ctxBadge = apiRes['context_badge'] as String? ?? '$role • $dept Department';
      final actions = List<String>.from(apiRes['suggested_actions'] ?? []);
      final navTarget = apiRes['navigation_target'] as String?;
      final matchedList = List<Map<String, dynamic>>.from(apiRes['matched_announcements'] ?? []);

      messages.add(AiChatMessage(
        text: responseText,
        isUser: false,
        categoryBadge: catBadge,
        contextBadge: ctxBadge,
        suggestedActions: actions.isEmpty ? ['Browse Announcements', 'Check Categories'] : actions,
        navigationTarget: navTarget,
        matchedAnnouncements: matchedList,
      ));
    } catch (_) {
      final fallbackText = _generateFallbackResponse(userMsg, role, dept, fullName);
      messages.add(AiChatMessage(
        text: fallbackText,
        isUser: false,
        categoryBadge: 'EchoSphere AI',
        contextBadge: '$role • $dept Department',
        suggestedActions: ['Browse Announcements', 'Check Categories'],
      ));
    } finally {
      isProcessing.value = false;
    }
  }

  String summarizeText(String content) {
    if (content.length < 60) return content;
    final sentences = content.split(RegExp(r'(?<=[.!?])\s+'));
    if (sentences.isNotEmpty) {
      return 'Summary: ${sentences.first}';
    }
    return 'Summary: ${content.substring(0, 80)}...';
  }

  Map<String, String> recommendPriorityAndCategory(String title, String description, {String? userRole}) {
    final combined = '$title $description'.toLowerCase();
    final role = (userRole ?? 'Student').toUpperCase();

    String priority = 'NORMAL';
    String category = 'Academics';

    if (combined.contains('rain') ||
        combined.contains('flood') ||
        combined.contains('closed') ||
        combined.contains('urgent') ||
        combined.contains('emergency') ||
        combined.contains('suspended')) {
      priority = (role == 'HOD' || role == 'COLLEGE ADMIN' || role == 'PRINCIPAL' || role == 'DEVELOPER' || role == 'DEV ADMIN') ? 'EMERGENCY' : 'HIGH';
      category = 'Emergency';
    } else if (combined.contains('exam') ||
        combined.contains('timetable') ||
        combined.contains('test') ||
        combined.contains('hall ticket')) {
      priority = 'HIGH';
      category = 'Examinations';
    } else if (combined.contains('placement') ||
        combined.contains('drive') ||
        combined.contains('google') ||
        combined.contains('microsoft') ||
        combined.contains('interview')) {
      priority = 'HIGH';
      category = 'Placements';
    } else if (combined.contains('hackathon') ||
        combined.contains('symposium') ||
        combined.contains('event') ||
        combined.contains('fest')) {
      priority = 'NORMAL';
      category = 'Events';
    } else if (combined.contains('sports') ||
        combined.contains('match') ||
        combined.contains('tournament')) {
      priority = 'NORMAL';
      category = 'Sports';
    }

    return {
      'priority': priority,
      'category': category,
    };
  }

  String _generateFallbackResponse(String input, String role, String dept, String name) {
    final query = input.toLowerCase();

    if (query.contains('who r u') || query.contains('who are you') || query.contains('what is your name') || query.contains('identify yourself')) {
      return 'I am the **EchoSphere AI Assistant**, your intelligent campus communication companion.\n\n'
          'I am customized for **$name** as a **$role** in the **$dept Department**.\n\n'
          '**How I can assist you:**\n'
          '- **Announcements & Notices:** Search circulars for $dept or college-wide updates.\n'
          '- **Exams & Schedules:** Retrieve lab timetables, exam dates, and hall ticket requirements.\n'
          '- **Placements & Events:** Track active recruitment drives and campus events.\n'
          '- **Notice Creation:** Expand short notes into formal circulars and polish tone using AI.\n'
          '- **App Navigation:** Guide you to profile settings, theme toggles, or password updates.';
    }

    if (query.startsWith('hi') || query.startsWith('hello') || query.startsWith('hey') || query.startsWith('good morning') || query.startsWith('good afternoon')) {
      return 'Hello $name! Welcome to EchoSphere. I am tuned to your context in the **$dept Department** ($role).\n\n'
          'How can I help you today? Ask me about recent announcements, exam timetables, placement drives, or app settings.';
    }

    if (query.contains('thank') || query.contains('thanks') || query.contains('awesome') || query.contains('great')) {
      return 'You\'re very welcome, $name! I am always here to keep you updated on campus announcements and department circulars.';
    }

    if (query.contains('how are you') || query.contains('how r u') || query.contains('how\'s it going')) {
      return 'I\'m doing great and ready to assist you! How can I help you today in **$dept Department**?';
    }

    if (query.contains('setting') || query.contains('theme') || query.contains('dark mode')) {
      return 'To customize your application interface:\n\n'
          '1. Open the **Profile** tab on the navigation bar.\n'
          '2. Tap **Dark Mode Theme** to switch light/dark glassmorphism modes.\n'
          '3. Configure notification channels and speaker preferences.';
    }

    if (query.contains('password') || query.contains('change password')) {
      if (role == 'Student') {
        return 'As a **Student**, password resets are managed through your Department HoD or Class Teacher.\n\n'
            'You can also tap **Forgot Password?** on the sign-in screen to generate a reset token.';
      }
      return 'Go to **Profile** → **Preferences & Security** → Tap **Change Password**.';
    }

    if (query.contains('exam') || query.contains('timetable') || query.contains('test')) {
      return 'Here is the examination guidance for **$dept Department**:\n\n'
          '- Practical lab & theory timetables are published under the **Examinations** category.\n'
          '- Students must carry their official College ID Card and Hall Ticket.';
    }

    if (query.contains('rain') || query.contains('weather') || query.contains('holiday') || query.contains('closed')) {
      return '**Emergency Status Update:**\n\n'
          '- Weather advisories and emergency alerts are broadcasted college-wide with highest priority.\n'
          '- Class suspension notices appear at the top of your feed and play via campus speakers.';
    }

    if (query.contains('placement') || query.contains('job') || query.contains('company')) {
      return '**Placements & Recruitment Drives:**\n\n'
          '- Active drives for Google, Microsoft, TCS, and Infosys are listed under **Placements**.\n'
          '- Minimum Eligibility: CGPA ≥ 7.0 with no active backlogs.';
    }

    if (query.contains('create') || query.contains('submit') || query.contains('notice') || query.contains('how to')) {
      if (role == 'Student') {
        return 'Students have read-only access to preserve official notice authenticity.\n\n'
            'Please contact your **Department Faculty Advisor** or **HoD** to publish a notice.';
      }
      return 'To post a notice:\n\n'
          '1. Click the floating **+ New Notice** button on your Home screen.\n'
          '2. Fill in details and use **AI Expand** for instant formal circular formatting.';
    }

    return 'I am ready to assist **$name** ($role · $dept Department).\n\n'
        'You can ask me to search campus notices, check exam timetables, view placement drives, or navigate settings.';
  }
}
