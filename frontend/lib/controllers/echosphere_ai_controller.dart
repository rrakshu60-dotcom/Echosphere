import 'dart:convert';
import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/services/copilot_client.dart';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/utils/usn_parser.dart';
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
  final String? modelUsed;
  final Map<String, dynamic>? copilotAction;

  AiChatMessage({
    required this.text,
    required this.isUser,
    DateTime? timestamp,
    this.categoryBadge,
    this.contextBadge,
    this.suggestedActions = const [],
    this.navigationTarget,
    this.matchedAnnouncements = const [],
    this.modelUsed,
    this.copilotAction,
  }) : timestamp = timestamp ?? DateTime.now();
}

class EchosphereAiController extends GetxController {
  final RxList<AiChatMessage> messages = <AiChatMessage>[].obs;
  final RxBool isProcessing = false.obs;

  @override
  void onInit() {
    super.onInit();
    resetGreeting();
    final authCtrl = Get.find<AuthController>();
    ever(authCtrl.currentUser, (_) {
      resetGreeting();
    });
  }

  void resetGreeting() {
    final authCtrl = Get.find<AuthController>();
    final user = authCtrl.currentUser.value;
    final role = user?.role ?? 'Dev Admin';
    final name = user?.fullName ?? 'Dev Admin';

    String dept = 'College-Wide';
    if (user?.department != null && user!.department!.trim().isNotEmpty) {
      dept = user.department!.trim();
    } else if (user?.usn != null && user!.usn!.trim().isNotEmpty) {
      dept = detectDepartmentFromUsn(user.usn!);
    } else if (role == 'Dev Admin' || role == 'Developer' || role == 'College Admin' || role == 'Principal') {
      dept = 'College-Wide';
    }

    final contextLabel = (role == 'Dev Admin' || role == 'College Admin' || role == 'Principal' || role == 'Developer')
        ? '$role • College-Wide'
        : '$role • $dept Department';

    messages.clear();
    messages.add(
      AiChatMessage(
        text: 'Hello $name! How can I help you today?',
        isUser: false,
        categoryBadge: 'EchoSphere AI',
        contextBadge: contextLabel,
        suggestedActions: const [],
        modelUsed: 'EchoSphere Campus AI',
      ),
    );
  }

  String sanitizeClientMarkdown(String text) {
    var cleaned = text;
    // Strip [[ACTION:...]] tags completely from visible bubble
    cleaned = cleaned.replaceAll(RegExp(r'\[\[ACTION:[\s\S]*?\]\]'), '');
    // Strip patronizing phrasing
    cleaned = cleaned.replaceAll(RegExp(r'\s*Feel free to ask about[^\.\n]*\.?', caseSensitive: false), '');
    cleaned = cleaned.replaceAll(RegExp(r'\s*Ask me about recent circulars[^\.\n]*\.?', caseSensitive: false), '');
    cleaned = cleaned.replaceAll(RegExp(r'\s*Ask me about[^\.\n]*\.?', caseSensitive: false), '');
    // Fix dollar-prefixed headers (##$ or ###$)
    cleaned = cleaned.replaceAllMapped(RegExp(r'^(#{1,6})\s*\$([a-zA-Z0-9_]+)', multiLine: true), (m) => '${m[1]} ${m[2]}');
    cleaned = cleaned.replaceAllMapped(RegExp(r'^(#{1,6})\s*\$', multiLine: true), (m) => '${m[1]} ');
    // Strip raw asterisks / dashes clutter (---, ***, ___, ****)
    cleaned = cleaned.replaceAll(RegExp(r'\*{4,}'), '**');
    cleaned = cleaned.replaceAll(RegExp(r'^[ \t]*(\*{3,}|-{3,}|_{3,}|={3,})[ \t]*$', multiLine: true), '\n');
    cleaned = cleaned.replaceAllMapped(RegExp(r'\*{3}([^\*\n]+)\*{3}'), (m) => '**${m[1]}**');
    cleaned = cleaned.replaceAll(RegExp(r'^[ \t]*\*{3}[ \t]*', multiLine: true), '');
    cleaned = cleaned.replaceAll(RegExp(r'[ \t]*\*{3}[ \t]*$', multiLine: true), '');
    // De-synthesize bolding in conversational greetings and roles
    cleaned = cleaned.replaceAllMapped(RegExp(r'I am (?:the )?\*\*([^\*]+)\*\*'), (m) => 'I am ${m[1]}');
    cleaned = cleaned.replaceAllMapped(RegExp(r'Hello,?\s*\*\*([^\*]+)\*\*'), (m) => 'Hello ${m[1]}');
    cleaned = cleaned.replaceAllMapped(RegExp(r'as \*\*([^\*]+)\*\*'), (m) => 'as ${m[1]}');
    cleaned = cleaned.replaceAllMapped(RegExp(r'\*\*(EchoSphere Campus AI Assistant|EchoSphere AI|EchoSphere|Dev Admin|College Admin|Principal|Teacher|Student|HoD)\*\*', caseSensitive: false), (m) => m[1] ?? '');
    // Space after **: or :** if immediately followed by text
    cleaned = cleaned.replaceAllMapped(RegExp(r'(:\*\*)([^\s\n])'), (m) => '${m[1]} ${m[2]}');
    cleaned = cleaned.replaceAllMapped(RegExp(r'(\*\*:)([^\s\n])'), (m) => '${m[1]} ${m[2]}');
    cleaned = cleaned.replaceAllMapped(RegExp(r'(\*\*:\*\*)([^\s\n])'), (m) => '${m[1]} ${m[2]}');
    // Ensure list items are preceded by a newline for CommonMark
    final lines = cleaned.split('\n');
    final processed = <String>[];
    bool inList = false;
    for (final line in lines) {
      final isItem = RegExp(r'^[ \t]*[-•*]\s+').hasMatch(line) || RegExp(r'^[ \t]*\d+\.\s+').hasMatch(line);
      if (isItem) {
        if (!inList && processed.isNotEmpty && processed.last.trim().isNotEmpty) {
          processed.add('');
        }
        inList = true;
      } else if (line.trim().isEmpty) {
        inList = false;
      } else {
        inList = false;
      }
      processed.add(line);
    }
    return processed.join('\n').trim();
  }

  List<Map<String, String>> getPresetPrompts() {
    return const [];
  }

  Future<void> sendQuery(String prompt) async {
    if (prompt.trim().isEmpty) return;

    final authCtrl = Get.find<AuthController>();
    final user = authCtrl.currentUser.value;
    final role = user?.role ?? 'Dev Admin';
    String dept = 'College-Wide';
    if (user?.department != null && user!.department!.trim().isNotEmpty) {
      dept = user.department!.trim();
    } else if (user?.usn != null && user!.usn!.trim().isNotEmpty) {
      dept = detectDepartmentFromUsn(user.usn!);
    } else if (role == 'Dev Admin' || role == 'Developer' || role == 'College Admin' || role == 'Principal') {
      dept = 'College-Wide';
    }
    final fullName = user?.fullName ?? 'Dev Admin';
    final usnOrEmpId = user?.usn ?? user?.employeeId ?? '';

    final userMsg = prompt.trim();
    messages.add(AiChatMessage(text: userMsg, isUser: true));
    isProcessing.value = true;

    // Build multi-turn history payload
    final historyList = messages
        .take(messages.length - 1)
        .map((m) => {
              'role': m.isUser ? 'user' : 'model',
              'text': m.text,
            })
        .toList();

    try {
      final apiRes = await EchosphereApiService().sendAiChat(
        userMsg,
        userRole: role,
        department: dept,
        fullName: fullName,
        usnOrEmpId: usnOrEmpId,
        history: historyList,
      );

      final rawResponse = apiRes['response'] as String? ?? _generateFallbackResponse(userMsg, role, dept, fullName, usnOrEmpId);
      final responseText = sanitizeClientMarkdown(rawResponse);
      final catBadge = apiRes['category_badge'] as String? ?? 'EchoSphere AI';
      final ctxBadge = apiRes['context_badge'] as String? ?? '$role • $dept Department';
      final navTarget = apiRes['navigation_target'] as String?;
      final matchedList = List<Map<String, dynamic>>.from(apiRes['matched_announcements'] ?? []);
      final modelUsed = apiRes['model_used'] as String? ?? 'EchoSphere AI';

      // Parse CopilotKit / Gemma action from API response or embedded tags
      Map<String, dynamic>? copilotAction;
      final rawAction = apiRes['copilot_action'];
      if (rawAction is Map<String, dynamic>) {
        copilotAction = Map<String, dynamic>.from(rawAction);
      } else {
        // Fallback: extract from raw response text if model emitted [[ACTION:name:{...}]]
        final actionMatch = RegExp(r'\[\[ACTION:([a-zA-Z0-9_]+):(\{[\s\S]*?\}|[a-zA-Z0-9_:]+)\]\]').firstMatch(rawResponse);
        if (actionMatch != null) {
          try {
            final actName = actionMatch.group(1);
            final paramStr = actionMatch.group(2)!;
            if (paramStr.startsWith('{')) {
              final params = jsonDecode(paramStr);
              copilotAction = {'action': actName, 'parameters': params};
            } else {
              copilotAction = {'action': actName, 'parameters': {'screen': paramStr}};
            }
          } catch (_) {}
        }
      }

      if (copilotAction == null && navTarget != null && navTarget.isNotEmpty) {
        if (navTarget.contains('speaker')) {
          copilotAction = {'action': 'navigate', 'parameters': {'screen': 'speaker_queue'}};
        } else if (navTarget.contains('filter:')) {
          final cat = navTarget.split(':').last;
          copilotAction = {'action': 'navigate', 'parameters': {'screen': 'notices', 'filter_category': cat}};
        } else if (navTarget.contains('create_notice')) {
          copilotAction = {'action': 'create_announcement_draft', 'parameters': {}};
        } else if (navTarget.contains('profile') || navTarget.contains('preference') || navTarget.contains('security')) {
          copilotAction = {'action': 'navigate', 'parameters': {'screen': 'profile'}};
        }
      }

      // Automatically execute immediate visual actions like theme toggling
      if (copilotAction != null && copilotAction['action'] == 'toggle_theme') {
        CopilotClient().executeAction(copilotAction);
      }

      messages.add(AiChatMessage(
        text: responseText,
        isUser: false,
        categoryBadge: catBadge,
        contextBadge: ctxBadge,
        suggestedActions: const [],
        navigationTarget: navTarget,
        matchedAnnouncements: matchedList,
        modelUsed: modelUsed,
        copilotAction: copilotAction,
      ));
    } catch (_) {
      // High-intelligence local fallback grounded in campus knowledge
      final rawFallback = _generateFallbackResponse(userMsg, role, dept, fullName, usnOrEmpId);
      final fallbackText = sanitizeClientMarkdown(rawFallback);
      messages.add(AiChatMessage(
        text: fallbackText,
        isUser: false,
        categoryBadge: _detectCategoryBadge(userMsg),
        contextBadge: '$role • $dept Department',
        suggestedActions: const [],
        modelUsed: 'EchoSphere Campus AI (Offline)',
      ));
    } finally {
      isProcessing.value = false;
    }
  }

  String _detectCategoryBadge(String query) {
    final q = query.toLowerCase();
    if (q.contains('exam') || q.contains('timetable') || q.contains('test') || q.contains('viva')) return 'Examinations';
    if (q.contains('placement') || q.contains('job') || q.contains('hiring') || q.contains('cgpa')) return 'Placements';
    if (q.contains('rain') || q.contains('weather') || q.contains('flood') || q.contains('closed')) return 'Emergency Alert';
    if (q.contains('library') || q.contains('hostel') || q.contains('canteen') || q.contains('bus')) return 'Campus Facilities';
    if (q.contains('attendance') || q.contains('condonation') || q.contains('75%')) return 'Academic Regulations';
    return 'EchoSphere AI';
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

  String _generateFallbackResponse(String input, String role, String dept, String name, [String? usnOrEmpId]) {
    final q = input.toLowerCase();

    // Direct, polite refusal for non-permitted student prompts
    if (role.toLowerCase() == 'student' &&
        (q.contains('joke') || q.contains('movie') || q.contains('song') || q.contains('game') ||
         q.contains('cricket') || q.contains('dating') || q.contains('recipe') || q.contains('funny'))) {
      return "Sorry, I'm not allowed to do that.";
    }

    if (q.contains('who r u') || q.contains('who are you') || q.contains('what is your name') || q.contains('identify')) {
      return 'I am the EchoSphere AI Assistant, your campus and academic companion. How can I help you today?';
    }

    if (q.startsWith('hi') || q.startsWith('hello') || q.startsWith('hey') || q.startsWith('good morning') || q.startsWith('good afternoon')) {
      return 'Hello $name! How can I help you today?';
    }

    if (q.contains('thank') || q.contains('thanks') || q.contains('awesome') || q.contains('great')) {
      return 'You are very welcome, $name! I am always here to keep you informed on **$dept Department** circulars and campus events.';
    }

    if (q.contains('exam') || q.contains('timetable') || q.contains('test') || q.contains('viva') || q.contains('hall ticket')) {
      return '### Examination Guidelines for $dept Department\n\n'
          '- **Timetables & Batches:** Practical lab and theory schedules are released under the **Examinations** category.\n'
          '- **Mandatory Requirements:** You must carry your physical **College ID Card** and official **Hall Ticket** to all exam rooms.\n'
          '- **Reporting Time:** Arrive at least 15 minutes prior to scheduled exam and viva slots.';
    }

    if (q.contains('placement') || q.contains('job') || q.contains('drive') || q.contains('company') || q.contains('interview') || q.contains('cgpa')) {
      return '### Campus Placements & Recruitment ($dept)\n\n'
          '- **Eligibility Threshold:** Aggregate **CGPA >= 7.0** with zero active backlogs for tier-1 recruitment drives.\n'
          '- **Top Recruiters:** Google, Microsoft, TCS, Infosys, and Accenture.\n'
          '- **Checklist:** Register with the Training & Placement Cell, keep your resume updated, and attend all pre-placement talks.';
    }

    if (q.contains('attendance') || q.contains('shortage') || q.contains('condonation') || q.contains('75%')) {
      return '### Academic Regulations & Attendance Policy\n\n'
          '- **Mandatory Rule:** A minimum of **75% attendance** in each subject is required to be eligible for semester examinations.\n'
          '- **Medical Exemption:** Attendance between 65% and 74% may be condoned with verified medical documentation submitted to the HoD.\n'
          '- **Below 65%:** Strictly not permitted to sit for exams as per university regulations.';
    }

    if (q.contains('rain') || q.contains('weather') || q.contains('holiday') || q.contains('closed') || q.contains('flood')) {
      return '### Campus Safety & Emergency Advisory\n\n'
          '- **Emergency Status:** During severe weather or red alerts, closure circulars are issued with EMERGENCY priority.\n'
          '- **Broadcast Delivery:** Critical announcements play over campus smart speaker nodes and pin to the top of your feed.\n'
          '- Please adhere to official district administration advisories.';
    }

    if (q.contains('library') || q.contains('book') || q.contains('borrow')) {
      return '### Central Library Guidelines\n\n'
          '- **Timings:** Monday through Saturday from **8:00 AM to 8:00 PM** (extended during exam weeks).\n'
          '- **Circulation:** Undergraduate students may borrow up to 4 books for 14 days.\n'
          '- **Digital Access:** IEEE, ACM, and Springer journals are accessible on the campus Wi-Fi network.';
    }

    if (q.contains('hostel') || q.contains('curfew') || q.contains('mess')) {
      return '### Hostel Guidelines\n\n'
          '- **Curfew Timings:** Strictly **9:00 PM** on weekdays and **9:30 PM** on weekends.\n'
          '- **Out-Passes:** Must be requested through the Hostel Warden at least 24 hours in advance.\n'
          '- **Mess Timings:** Breakfast (7:30 - 9:00 AM), Lunch (12:30 - 2:00 PM), Dinner (7:30 - 9:00 PM).';
    }

    if (q.contains('setting') || q.contains('theme') || q.contains('dark mode') || q.contains('appearance')) {
      return '### Application Customization\n\n'
          '1. Navigate to the **Profile** tab in the main navigation bar.\n'
          '2. Tap **Dark Mode Theme** to switch between dark glassmorphic styling and light mode.\n'
          '3. Configure notification sounds and audio broadcast options in your preferences.';
    }

    if (q.contains('password') || q.contains('change password') || q.contains('security')) {
      if (role == 'Student') {
        return '### Password Recovery for Students\n\n'
            '- Tap **Forgot Password?** on the sign-in screen to generate a reset token.\n'
            '- Alternatively, request your Department HoD or Class Teacher to issue a credential reset.';
      }
      return '### Change Password ($role)\n\n'
          '1. Open the **Profile** tab.\n'
          '2. Go to **Preferences & Security**.\n'
          '3. Tap **Change Password** and enter your new credentials.';
    }

    if (q.contains('speaker') || q.contains('queue') || q.contains('hardware node') || q.contains('pa system')) {
      if (role.toLowerCase() == 'student') {
        return "I don't have the authority to answer that question or disclose operational details about the smart speaker system. Please consult your department office or faculty coordinator for assistance.";
      }
      return '### EchoSphere Smart Speaker System\n\n'
          '- **Hardware Network:** Smart speaker nodes broadcast critical announcements to assigned campus zones.\n'
          '- **Queue System:** Audio files are queued and prioritized by announcement severity.\n'
          '- **Node Client:** Corridor nodes communicate over secure MQTT with automatic TTS synthesis.';
    }

    if (q.contains('create') || q.contains('submit') || q.contains('post notice') || q.contains('publish')) {
      if (role.toLowerCase() == 'student') {
        return "I don't have the authority to author or publish announcements directly from this account. If you have an event or club announcement that needs to be published, please coordinate with your faculty advisor or department office.";
      }
      return '### Publishing an Announcement ($role)\n\n'
          '1. Tap the **+ New Notice** button on your home dashboard.\n'
          '2. Enter circular details and use **AI Expand** to format into an official circular.\n'
          '3. Faculty notices route to HoD for approval; HoDs and Admins publish immediately with smart speaker broadcast options.';
    }

    return '### Guidance for $name ($role · $dept Department)\n\n'
        'Your question has been matched against EchoSphere institutional knowledge.\n\n'
        '- **Recent Circulars:** View the latest department updates under the **Notices** tab.\n'
        '- **Support:** Consult your Class Teacher or Department HoD for official academic signatures and approvals.';
  }
}
