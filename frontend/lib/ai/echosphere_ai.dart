import 'package:anymex/controllers/auth_controller.dart';
import 'package:anymex/controllers/echosphere_ai_controller.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_button.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_chip.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_container.dart';
import 'package:anymex/widgets/custom_widgets/custom_text.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class EchosphereAi extends StatefulWidget {
  const EchosphereAi({super.key});

  @override
  State<EchosphereAi> createState() => _EchosphereAiState();
}

class _EchosphereAiState extends State<EchosphereAi> {
  final EchosphereAiController aiController = Get.find<EchosphereAiController>();
  final AuthController authController = Get.find<AuthController>();
  final TextEditingController inputController = TextEditingController();
  final ScrollController scrollController = ScrollController();

  void _sendMessage([String? text]) {
    final prompt = text ?? inputController.text.trim();
    if (prompt.isEmpty) return;

    inputController.clear();
    aiController.sendQuery(prompt);

    Future.delayed(const Duration(milliseconds: 300), () {
      if (scrollController.hasClients) {
        scrollController.animateTo(
          scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = authController.currentUser.value;
    final role = user?.role ?? 'Student';
    final dept = user?.department ?? 'CSE';

    return Column(
      children: [
        // Top Header Bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.amber.withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.auto_awesome, color: Colors.amber, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const EchoSphereText(
                      text: 'EchoSphere AI Assistant',
                      size: 16,
                      variant: TextVariant.bold,
                    ),
                    Text(
                      'Context-Aware Institutional Knowledge Assistant',
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
              Flexible(
                child: EchoSphereChip(
                  label: '$dept Dept',
                  isSelected: true,
                  onSelected: (_) {},
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1),

        // Quick Prompts Preset Bar (Context-Aware based on role)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 12.0),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: role == 'Student'
                  ? [
                      _buildPresetChip('🚨 Emergency Alert Status', 'Check heavy rain emergency alert status'),
                      _buildPresetChip('📝 Exam Schedule Info', 'What is the CSE lab exam timetable?'),
                      _buildPresetChip('💼 Placement Drives', 'Which companies have active placement drives?'),
                      _buildPresetChip('⚙️ Where is Settings?', 'How do I change dark mode settings?'),
                    ]
                  : [
                      _buildPresetChip('📌 How to Post Notice', 'How do I create a new announcement?'),
                      _buildPresetChip('🔐 Change Password', 'How do I change my account password?'),
                      _buildPresetChip('✅ Approval Rules', 'Who approves teacher announcements?'),
                      _buildPresetChip('🚨 Emergency Status', 'Check active emergency weather warnings'),
                    ],
            ),
          ),
        ),
        const Divider(height: 1),

        // Chat Messages List
        Expanded(
          child: Obx(() => ListView.builder(
                controller: scrollController,
                padding: const EdgeInsets.all(16.0),
                itemCount: aiController.messages.length,
                itemBuilder: (context, index) {
                  final msg = aiController.messages[index];
                  return _buildMessageBubble(msg, theme);
                },
              )),
        ),

        // Processing Indicator
        Obx(() => aiController.isProcessing.value
            ? Padding(
                padding: const EdgeInsets.all(8.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                    const SizedBox(width: 10),
                    Flexible(
                      child: Text(
                        'EchoSphere AI is querying database context & grounding response...',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 12,
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                    ),
                  ],
                ),
              )
            : const SizedBox.shrink()),

        // Input Field Container
        Container(
          padding: const EdgeInsets.all(12.0),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            border: Border(top: BorderSide(color: theme.dividerColor)),
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: inputController,
                  onSubmitted: (_) => _sendMessage(),
                  decoration: InputDecoration(
                    hintText: 'Ask AI about announcements, exams, or departments...',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide.none,
                    ),
                    filled: true,
                    fillColor: theme.colorScheme.surfaceContainerHighest.withOpacity(0.4),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              EchoSphereButton(
                height: 44,
                width: 44,
                padding: EdgeInsets.zero,
                onTap: () => _sendMessage(),
                child: const Icon(Icons.send, size: 20),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPresetChip(String label, String prompt) {
    return Padding(
      padding: const EdgeInsets.only(right: 8.0),
      child: ActionChip(
        label: Text(label, style: const TextStyle(fontSize: 12)),
        onPressed: () => _sendMessage(prompt),
      ),
    );
  }

  Widget _buildMessageBubble(AiChatMessage msg, ThemeData theme) {
    final isUser = msg.isUser;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 16.0),
        constraints: const BoxConstraints(maxWidth: 680),
        child: Column(
          crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            // Badges Row
            if (!isUser) ...[
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.smart_toy, size: 14, color: Colors.amber),
                  const SizedBox(width: 4),
                  Text(
                    msg.categoryBadge ?? 'EchoSphere AI',
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.amber),
                  ),
                  if (msg.contextBadge != null) ...[
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        msg.contextBadge!,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: theme.colorScheme.primary,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 6),
            ],

            // Message Body Container
            EchoSphereContainer(
              padding: const EdgeInsets.all(16.0),
              color: isUser
                  ? theme.colorScheme.primary.withOpacity(0.85)
                  : theme.colorScheme.surfaceContainerHighest.withOpacity(0.4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SelectableText(
                    msg.text,
                    style: TextStyle(
                      fontSize: 14,
                      height: 1.45,
                      color: isUser ? theme.colorScheme.onPrimary : theme.colorScheme.onSurface,
                    ),
                  ),

                  // Matched DB Announcements Attachment Cards
                  if (!isUser && msg.matchedAnnouncements.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    Text(
                      'Live Announcements Matched in System:',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ...msg.matchedAnnouncements.map((ann) => Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.5),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: theme.colorScheme.primary.withOpacity(0.2)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Wrap(
                                spacing: 6,
                                runSpacing: 4,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                alignment: WrapAlignment.spaceBetween,
                                children: [
                                  EchoSphereChip(
                                    label: ann['category'] ?? 'General',
                                    isSelected: true,
                                    onSelected: (_) {},
                                  ),
                                  Text(
                                    ann['department'] ?? 'College-Wide',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                                  ),
                                  Text(
                                    ann['created_at'] ?? '',
                                    style: TextStyle(fontSize: 10, color: theme.colorScheme.onSurface.withOpacity(0.5)),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                ann['title'] ?? '',
                                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                ann['content'] ?? '',
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(fontSize: 11, color: theme.colorScheme.onSurface.withOpacity(0.7)),
                              ),
                            ],
                          ),
                        )),
                  ],
                ],
              ),
            ),

            // Interactive Action Chips Row
            if (!isUser && msg.suggestedActions.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: msg.suggestedActions
                    .map((act) => ActionChip(
                          avatar: const Icon(Icons.touch_app_rounded, size: 14, color: Colors.blue),
                          label: Text(act, style: const TextStyle(fontSize: 11)),
                          onPressed: () => _sendMessage(act),
                        ))
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// Compatibility Alias
typedef AnimeoAI = EchosphereAi;
