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

    messages.add(
      AiChatMessage(
        text:
            'Hello ${user?.fullName ?? "there"}! I am EchoSphere AI Assistant 🤖\n'
            'I am tuned to your context for **$dept Department**.\n'
            'Ask me about recent announcements, exam schedules, department queries, or app features.',
        isUser: false,
        categoryBadge: 'EchoSphere AI',
        contextBadge: '$dept Department',
        suggestedActions: [
          'Browse Announcements',
          'Check Categories',
          'Show Examination Notices',
          'Check Weather Advisory',
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
      final ctxBadge = apiRes['context_badge'] as String? ?? '$dept Department';
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
        contextBadge: '$dept Department',
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
      return 'AI Summary: ${sentences.first} (Key notice update)';
    }
    return 'AI Summary: ${content.substring(0, 80)}...';
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
      priority = (role == 'HOD' || role == 'COLLEGE ADMIN' || role == 'PRINCIPAL' || role == 'DEVELOPER') ? 'EMERGENCY' : 'HIGH';
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

    if (query.contains('who r u') || query.contains('who are you') || query.contains('what is your name') || query.contains('what\'s your name') || query.contains('identify yourself')) {
      return '🤖 **I am EchoSphere AI Assistant!**\n\n'
          'I am your intelligent, context-aware college announcement & campus knowledge assistant.\n\n'
          'I am currently tuned for **$name** ($role · $dept Department).\n\n'
          '**What I can do for you:**\n'
          '• 📝 **Exams & Timetables:** Retrieve schedule & hall ticket info.\n'
          '• 🚨 **Emergency Alerts:** Check active weather or campus closure warnings.\n'
          '• 💼 **Placements:** Find company drives & registration deadlines.\n'
          '• 📌 **Notice Creation:** Expand short notes into formal circulars with AI.\n'
          '• ⚙️ **App Navigation:** Guide you to settings, password resets, or approval queues.';
    }

    if (query.startsWith('hi') || query.startsWith('hello') || query.startsWith('hey') || query.startsWith('good morning') || query.startsWith('good afternoon') || query == 'yo' || query == 'sup') {
      return '👋 **Hello $name!**\n\n'
          'Welcome to EchoSphere! How can I help you today with **$dept Department** announcements, exam timetables, or app navigation?';
    }

    if (query.contains('thank') || query.contains('thanks') || query.contains('awesome') || query.contains('great') || query.contains('cool')) {
      return '😊 **You\'re very welcome, $name!**\n\n'
          'I\'m always here to help you stay informed on campus announcements, department circulars, and application features.';
    }

    if (query.contains('how are you') || query.contains('how r u') || query.contains('how\'s it going')) {
      return '😊 **I\'m doing great and ready to help!**\n\n'
          'How can I assist you today, **$name**? Ask me about campus notices, exam schedules, or app settings.';
    }

    if (query.contains('setting') || query.contains('theme') || query.contains('dark mode')) {
      return '⚙️ **App Navigation Assistant - Settings & Themes:**\n\n'
          'Hello $name! Open the **Profile** tab on the navigation bar → Tap **Dark Mode Theme** to toggle light/dark glassmorphism.';
    }

    if (query.contains('password') || query.contains('change password')) {
      if (role == 'Student') {
        return '🔐 **Password Management Assistance:**\n\n'
            'As a **Student**, password resets are handled via your Department HoD or by tapping **Forgot Password?** on the Login screen.';
      }
      return '🔐 **Password Management Assistance:**\n\n'
          'Go to **Profile** → **Preferences & Security** → Tap **Change Password**.';
    }

    if (query.contains('exam') || query.contains('timetable') || query.contains('test')) {
      return '📝 **Examinations Query ($dept Department):**\n\n'
          '• Practical lab & theory timetables for **$dept Department** are published under **Examinations**.\n'
          '• Students must carry their official College ID Card and Hall Ticket.';
    }

    if (query.contains('rain') || query.contains('weather') || query.contains('holiday') || query.contains('closed')) {
      return '🚨 **Emergency Announcement Summary:**\n\n'
          '• **Status:** Emergency Rainfall Alert monitoring active.\n'
          '• Class suspensions will broadcast with top priority on your home feed.';
    }

    if (query.contains('placement') || query.contains('job') || query.contains('company')) {
      return '💼 **Placements Drive Information:**\n\n'
          '• Active recruitment drives for Google, Microsoft, and TCS are tagged under **Placements**.\n'
          '• Eligibility: CGPA ≥ 7.0 with no active backlogs.';
    }

    if (query.contains('create') || query.contains('submit') || query.contains('notice') || query.contains('how to')) {
      if (role == 'Student') {
        return '📌 **Announcement Creation Policy:**\n\n'
            'Students have read-only access to preserve official notice authenticity. Contact your Faculty Advisor to issue a notice.';
      }
      return '📌 **How to Create & Publish Announcements:**\n\n'
          '1. Click the floating **+ New Notice** button on the bottom right.\n'
          '2. Fill in details and use **AI Text Expander** for professional notice formatting.';
    }

    return '🤖 **EchoSphere AI Assistant:**\n\n'
        'I am here to assist **$name** ($role · $dept Department).\n\n'
        'I can help you search campus notices, check exam timetables, find placement drives, or navigate settings. What specific topic or announcement would you like to check?';
  }
}
