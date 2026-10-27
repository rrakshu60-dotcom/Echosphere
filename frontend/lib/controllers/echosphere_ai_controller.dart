import 'dart:convert';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/services/copilot_client.dart';
import 'package:echosphere/services/echosphere_api_service.dart';
import 'package:echosphere/utils/usn_parser.dart';
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
    syncUserGreeting();
    final authCtrl = Get.find<AuthController>();
    ever(authCtrl.currentUser, (_) => syncUserGreeting());
  }

  void syncUserGreeting() {
    final authCtrl = Get.find<AuthController>();
    final user = authCtrl.currentUser.value;
    final dept = user?.department ?? (user?.usn != null ? detectDepartmentFromUsn(user?.usn ?? '') : 'AIML');
    final role = user?.role ?? 'Student';
    final rawName = user?.fullName;
    final firstName = (rawName != null && rawName.trim().isNotEmpty && rawName.trim().toLowerCase() != 'student')
        ? rawName.trim().split(' ').first
        : '';
    final greeting = firstName.isNotEmpty
        ? 'Hello $firstName! How can I assist you today?'
        : 'Hello! How can I assist you with campus announcements and knowledge today?';

    final initialMsg = AiChatMessage(
      text: greeting,
      isUser: false,
      categoryBadge: 'EchoSphere AI',
      suggestedActions: _getDefaultActionsForRole(role, dept),
      modelUsed: 'EchoSphere Campus AI',
    );

    if (messages.isEmpty) {
      messages.add(initialMsg);
    } else if (!messages.first.isUser && messages.first.text.startsWith('Hello')) {
      messages[0] = initialMsg;
    }
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
      final isItem = RegExp(r'^[ \t]*[-\u2022*]\s+').hasMatch(line) || RegExp(r'^[ \t]*\d+\.\s+').hasMatch(line);
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

  List<String> _getDefaultActionsForRole(String role, String dept) {
    if (role.toLowerCase() == 'student') {
      return [
        'Check $dept Exam Timetable',
        'Placement Drive Circulars',
        'Ask an ML / Branch Question',
        'Upcoming Hackathons & Events',
      ];
    } else {
      return [
        'Pending Approvals Status',
        'Draft New Circular',
        'Emergency Broadcast Feed',
        'Speaker Hardware Status',
      ];
    }
  }

  List<Map<String, String>> getPresetPrompts() {
    final authCtrl = Get.find<AuthController>();
    final user = authCtrl.currentUser.value;
    final role = user?.role ?? 'Student';
    final dept = user?.department ?? 'CSE';

    if (role.toLowerCase() == 'student') {
      return [
        {'label': 'Exam Schedule', 'prompt': 'What is the $dept exam and practical lab schedule?'},
        {'label': 'Placement Circulars', 'prompt': 'What are the latest placement drives and eligibility criteria?'},
        {'label': 'ML Coursework', 'prompt': 'Explain backpropagation in machine learning'},
        {'label': 'App Guide', 'prompt': 'How do I bookmark circulars and switch to dark mode?'},
        {'label': 'Events & Hackathons', 'prompt': 'Are there any upcoming hackathons or technical events?'},
      ];
    } else {
      return [
        {'label': 'Draft Circular', 'prompt': 'Draft an official circular for upcoming department symposium'},
        {'label': 'Approval Guidelines', 'prompt': 'What is the notice approval hierarchy for faculty members?'},
        {'label': 'Speaker Broadcast', 'prompt': 'How do I broadcast high priority notices to smart speaker nodes?'},
        {'label': 'Emergency Protocol', 'prompt': 'Check active campus emergency advisories and procedures'},
      ];
    }
  }

  Future<void> sendQuery(String prompt) async {
    if (prompt.trim().isEmpty) return;

    final authCtrl = Get.find<AuthController>();
    final user = authCtrl.currentUser.value;
    final role = user?.role ?? 'Student';
    final dept = user?.department ?? (user?.usn != null ? detectDepartmentFromUsn(user?.usn ?? '') : 'AIML');
    final fullName = user?.fullName ?? 'Student';
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
        userId: user?.id,
        history: historyList,
      );

      final rawResponse = apiRes['response'] as String? ?? _generateFallbackResponse(userMsg, role, dept, fullName, usnOrEmpId);
      final responseText = sanitizeClientMarkdown(rawResponse);
      final catBadge = apiRes['category_badge'] as String? ?? 'EchoSphere AI';
      final actions = List<String>.from(apiRes['suggested_actions'] ?? []);
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
        contextBadge: null,
        suggestedActions: actions.isEmpty ? _getDefaultActionsForRole(role, dept) : actions,
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
        contextBadge: null,
        suggestedActions: _getDefaultActionsForRole(role, dept),
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
    final clean = content.trim();
    if (clean.length < 60) return clean;
    final sentences = clean.split(RegExp(r'(?<=[.!?])\s+'));
    if (sentences.isNotEmpty) {
      final first = sentences.first.trim();
      return first.toLowerCase().startsWith('summary:') ? first.substring(8).trim() : first;
    }
    final sub = clean.substring(0, 80).trim();
    return sub.toLowerCase().startsWith('summary:') ? sub.substring(8).trim() : '$sub...';
  }

  // Emergency check (kept in step with detect_emergency in the backend). Whole words only: matching parts of
  // words flagged "training" (contains "rain") and "closed" as emergencies and missed a fire or a gas leak.
  static final List<RegExp> _emergencyPatterns = [
    r'\bfires?\b', r'\bsmoke\b', r'\bevacuat\w*', r'\bearthquakes?\b', r'\btremors?\b', r'\bfloods?\b',
    r'\bflooding\b', r'\bcyclones?\b', r'\btsunami\b', r'\blandslides?\b', r'\bgas leak', r'\bchemical (leak|spill)',
    r'\bexplosions?\b', r'\bblast\b', r'\bbomb\b', r'\blockdown\b', r'\bshooter\b', r'\bintruders?\b',
    r'\bstampede\b', r'\bcollaps\w*', r'\bmedical emergency\b', r'\bambulance\b', r'\b(red|orange) alert\b',
    r'\bheavy rain\w*', r'\bstorm\b', r'\bemergency\b', r'\belectrocut\w*', r'\bshort circuit\b',
  ].map(RegExp.new).toList();
  static final RegExp _exerciseWords = RegExp(
      r'\b(drills?|mock|awareness|workshops?|training|seminars?|webinars?|preparedness|rehearsals?|lectures?|quiz|competition|week)\b');
  static final RegExp _urgentWords = RegExp(r'\b(now|immediately|right away|urgent(ly)?|asap|currently|ongoing|in progress|at once)\b');

  /// Is this text about an emergency happening now (not a drill, training or awareness session)?
  static bool isEmergencyText(String text) {
    final lower = text.toLowerCase();
    if (!_emergencyPatterns.any((p) => p.hasMatch(lower))) return false;
    return !(_exerciseWords.hasMatch(lower) && !_urgentWords.hasMatch(lower));
  }

  static bool _hasAny(String text, List<String> words) =>
      words.any((w) => RegExp('\\b${RegExp.escape(w)}\\b').hasMatch(text));

  Map<String, String> recommendPriorityAndCategory(String title, String description, {String? userRole}) {
    final combined = '$title $description'.toLowerCase();
    final role = (userRole ?? 'Student').toUpperCase();
    const emergencyRoles = ['HOD', 'COLLEGE ADMIN', 'PRINCIPAL', 'DEVELOPER', 'DEV ADMIN'];

    String priority = 'NORMAL';
    String category = 'Academics';

    if (isEmergencyText(combined)) {
      priority = emergencyRoles.contains(role) ? 'EMERGENCY' : 'HIGH';
      category = 'Emergency';
    } else if (_hasAny(combined, ['exam', 'exams', 'examination', 'examinations', 'timetable', 'test', 'tests', 'viva', 'semester', 'sem exam', 'hall ticket'])) {
      priority = 'HIGH';
      category = 'Examinations';
    } else if (_hasAny(combined, ['placement', 'placements', 'drive', 'interview', 'interviews', 'recruitment', 'deadline', 'fee payment'])) {
      priority = 'HIGH';
      category = 'Placements';
    } else if (_hasAny(combined, ['lost and found', 'lost & found', 'lost item', 'found item', 'lost', 'found', 'canteen', 'maintenance', 'reminder'])) {
      priority = 'LOW';
      category = 'General';
    } else if (_hasAny(combined, ['volley', 'volleyball', 'selection', 'trials', 'sports', 'cricket', 'football', 'match', 'tournament', 'athletics'])) {
      priority = 'NORMAL';
      category = 'Sports';
    } else if (_hasAny(combined, ['hackathon', 'symposium', 'event', 'events', 'workshop', 'seminar', 'fest'])) {
      priority = 'NORMAL';
      category = 'Events';
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
          '- **Node Client:** Corridor nodes fetch queued audio from the server over HTTPS.';
    }

    if (q.contains('create') || q.contains('submit') || q.contains('post notice') || q.contains('publish')) {
      if (role.toLowerCase() == 'student') {
        return "I don't have the authority to author or publish announcements directly from this account. If you have an event or club announcement that needs to be published, please coordinate with your faculty advisor or department office.";
      }
      return '### Publishing an Announcement ($role)\n\n'
          '1. Tap the **+ New Notice** button on your home dashboard.\n'
          '2. Enter circular details, or use **AI Auto-Draft** or **Voice Dictate** to start from your notes.\n'
          '3. Faculty notices route to HoD for approval; HoDs and Admins publish immediately with smart speaker broadcast options.';
    }

    // Campus facts (dates, timings, rules, recruiters) come only from the notices on the server. Without it,
    // say so instead of guessing.
    return "I can't reach the campus notices right now, so I can't answer that reliably. "
        'Please check the notices feed when you are back online, or ask your department office.';
  }
}
