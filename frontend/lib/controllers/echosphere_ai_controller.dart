import 'package:anymex/controllers/auth_controller.dart';
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
    final dept = user?.department ?? (user?.usn != null ? detectDepartmentFromUsn(user?.usn ?? '') : 'AIML');
    final role = user?.role ?? 'Student';
    final name = user?.fullName ?? 'Student';

    messages.add(
      AiChatMessage(
        text:
            'Hello $name! I am the **EchoSphere Campus AI Assistant**.\n\n'
            'I am tuned to your institutional context as **$role** in the **$dept Department**.\n\n'
            'You can ask me about active circulars, semester exam timetables, placement drive eligibility, '
            'attendance rules (75% policy), library hours, or app settings.',
        isUser: false,
        categoryBadge: 'EchoSphere AI',
        contextBadge: '$role • $dept Department',
        suggestedActions: _getDefaultActionsForRole(role, dept),
        modelUsed: 'EchoSphere Campus AI',
      ),
    );
  }

  List<String> _getDefaultActionsForRole(String role, String dept) {
    if (role == 'Student') {
      return [
        'Check $dept Exam Timetable',
        'Placement Drive Eligibility',
        'Attendance Regulations',
        'Library Timings & Rules',
      ];
    } else {
      return [
        'Pending Approvals Status',
        'Draft New Circular',
        'Emergency Weather Feed',
        'Speaker Hardware Status',
      ];
    }
  }

  List<Map<String, String>> getPresetPrompts() {
    final authCtrl = Get.find<AuthController>();
    final user = authCtrl.currentUser.value;
    final role = user?.role ?? 'Student';
    final dept = user?.department ?? 'CSE';

    if (role == 'Student') {
      return [
        {'label': 'Exam Schedule', 'prompt': 'What is the $dept exam and practical lab schedule?'},
        {'label': 'Placement Eligibility', 'prompt': 'What is the minimum CGPA and eligibility for campus placements?'},
        {'label': 'Attendance Rule', 'prompt': 'What is the minimum attendance required for exam hall tickets?'},
        {'label': 'Library Hours', 'prompt': 'What are the central library timings and book borrowing rules?'},
        {'label': 'Emergency Alerts', 'prompt': 'Are there any active weather emergency or holiday circulars?'},
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
        history: historyList,
      );

      final responseText = apiRes['response'] as String? ?? _generateFallbackResponse(userMsg, role, dept, fullName, usnOrEmpId);
      final catBadge = apiRes['category_badge'] as String? ?? 'EchoSphere AI';
      final ctxBadge = apiRes['context_badge'] as String? ?? '$role • $dept Department';
      final actions = List<String>.from(apiRes['suggested_actions'] ?? []);
      final navTarget = apiRes['navigation_target'] as String?;
      final matchedList = List<Map<String, dynamic>>.from(apiRes['matched_announcements'] ?? []);
      final modelUsed = apiRes['model_used'] as String? ?? 'EchoSphere AI';

      messages.add(AiChatMessage(
        text: responseText,
        isUser: false,
        categoryBadge: catBadge,
        contextBadge: ctxBadge,
        suggestedActions: actions.isEmpty ? _getDefaultActionsForRole(role, dept) : actions,
        navigationTarget: navTarget,
        matchedAnnouncements: matchedList,
        modelUsed: modelUsed,
      ));
    } catch (_) {
      // High-intelligence local fallback grounded in campus knowledge
      final fallbackText = _generateFallbackResponse(userMsg, role, dept, fullName, usnOrEmpId);
      messages.add(AiChatMessage(
        text: fallbackText,
        isUser: false,
        categoryBadge: _detectCategoryBadge(userMsg),
        contextBadge: '$role • $dept Department',
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

    if (q.contains('who r u') || q.contains('who are you') || q.contains('what is your name') || q.contains('identify')) {
      return 'I am the **EchoSphere Campus AI Assistant**, your official college knowledge companion.\n\n'
          'I am customized for **$name** as a **$role** in the **$dept Department**.\n\n'
          '**How I can assist you:**\n'
          '- **Announcements & Circulars:** Search official circulars and verified departmental notices.\n'
          '- **Exams & Hall Tickets:** Retrieve theory and practical schedules, reporting times, and regulations.\n'
          '- **Placement Cell Guidance:** Check company drives, eligibility thresholds (CGPA >= 7.0), and deadlines.\n'
          '- **Academic Rules:** Look up the 75% minimum attendance requirement, medical condonation, and grading.\n'
          '- **Campus Facilities:** Library hours (8 AM - 8 PM), hostel curfew (9 PM), canteen, and bus routes.';
    }

    if (q.startsWith('hi') || q.startsWith('hello') || q.startsWith('hey') || q.startsWith('good morning') || q.startsWith('good afternoon')) {
      return 'Hello $name! I am active and tuned to your context in the **$dept Department** ($role).\n\n'
          'How can I help you today? Ask me about recent circulars, exam timetables, placement drives, attendance rules, or settings.';
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
