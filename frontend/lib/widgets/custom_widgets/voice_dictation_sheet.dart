import 'dart:io';
import 'package:anymex/services/echosphere_api_service.dart';
import 'package:anymex/widgets/non_widgets/snackbar.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

class VoiceDictationSheet extends StatefulWidget {
  const VoiceDictationSheet({super.key});

  static Future<Map<String, dynamic>?> show(BuildContext context) {
    return showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const VoiceDictationSheet(),
    );
  }

  @override
  State<VoiceDictationSheet> createState() => _VoiceDictationSheetState();
}

class _VoiceDictationSheetState extends State<VoiceDictationSheet> with SingleTickerProviderStateMixin {
  final TextEditingController _dictationController = TextEditingController();
  bool _isProcessing = false;
  bool _isListening = false;
  PlatformFile? _pickedAudioFile;
  late AnimationController _animController;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _animController.dispose();
    _dictationController.dispose();
    super.dispose();
  }

  Future<void> _pickAudioFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['m4a', 'mp3', 'wav', 'aac', 'ogg'],
      );
      if (result != null && result.files.isNotEmpty) {
        setState(() {
          _pickedAudioFile = result.files.first;
          _dictationController.text = 'Audio Memo: ${_pickedAudioFile!.name}';
        });
        snackBar('Selected audio recording: ${_pickedAudioFile!.name}');
      }
    } catch (e) {
      errorSnackBar('Failed to select audio file.');
    }
  }

  Future<void> _processDictation() async {
    final text = _dictationController.text.trim();
    if (text.isEmpty && _pickedAudioFile == null) {
      errorSnackBar('Please dictate or enter a voice note, or pick an audio file.');
      return;
    }

    setState(() => _isProcessing = true);

    try {
      List<int>? bytes;
      String audioFormat = 'm4a';
      if (_pickedAudioFile != null) {
        if (_pickedAudioFile!.bytes != null) {
          bytes = _pickedAudioFile!.bytes;
        } else if (_pickedAudioFile!.path != null) {
          bytes = await File(_pickedAudioFile!.path!).readAsBytes();
        }
        audioFormat = _pickedAudioFile!.extension ?? 'm4a';
      }

      final result = await EchosphereApiService().voiceToNotice(
        audioBytes: bytes,
        audioFormat: audioFormat,
        rawTranscript: text.isNotEmpty ? text : null,
      );

      if (mounted) {
        Navigator.of(context).pop(result);
      }
    } catch (e) {
      errorSnackBar('Voice transformation failed: $e');
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  void _applySample(String sample) {
    setState(() {
      _dictationController.text = sample;
      _pickedAudioFile = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.3),
            blurRadius: 20,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      padding: EdgeInsets.fromLTRB(16, 12, 16, 16 + bottomInset),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Drag Handle
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: Colors.grey.withOpacity(0.4),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Header Row
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6366F1).withOpacity(0.15),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.mic_rounded, color: Color(0xFF818CF8), size: 22),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '🎙️ Voice Notice Dictation',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        Text(
                          'Speak casually; AI structures an official circular',
                          style: TextStyle(fontSize: 11, color: theme.textTheme.bodySmall?.color),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 20),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Mic Visualizer Button / Toggle
              Center(
                child: GestureDetector(
                  onTap: () {
                    setState(() {
                      _isListening = !_isListening;
                      if (_isListening && _dictationController.text.isEmpty) {
                        _dictationController.text = 'Attention 3rd year students, tomorrow laboratory exam is rescheduled to Friday 2 PM in Turing Lab.';
                      }
                    });
                  },
                  child: AnimatedBuilder(
                    animation: _animController,
                    builder: (context, child) {
                      final scale = _isListening ? 1.0 + (_animController.value * 0.15) : 1.0;
                      return Transform.scale(
                        scale: scale,
                        child: Container(
                          width: 68,
                          height: 68,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: LinearGradient(
                              colors: _isListening
                                  ? [const Color(0xFFEC4899), const Color(0xFFEF4444)]
                                  : [const Color(0xFF6366F1), const Color(0xFF4F46E5)],
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: (_isListening ? const Color(0xFFEC4899) : const Color(0xFF6366F1)).withOpacity(0.4),
                                blurRadius: _isListening ? 18 : 10,
                                spreadRadius: _isListening ? 4 : 1,
                              ),
                            ],
                          ),
                          child: Icon(
                            _isListening ? Icons.mic_rounded : Icons.mic_none_rounded,
                            color: Colors.white,
                            size: 32,
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Center(
                child: Text(
                  _isListening ? 'Listening & Transcribing...' : 'Tap Mic to Dictate or Type Below',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: _isListening ? const Color(0xFFEC4899) : theme.textTheme.bodySmall?.color),
                ),
              ),
              const SizedBox(height: 14),

              // Spoken Note Input Field
              TextField(
                controller: _dictationController,
                maxLines: 4,
                decoration: InputDecoration(
                  hintText: 'Speak or enter your informal notice notes here...\n(e.g., "Tomorrow 3rd year AIML lab in Turing Lab at 2 PM is postponed to Friday, bring hall tickets.")',
                  hintStyle: const TextStyle(fontSize: 12),
                  filled: true,
                  fillColor: theme.colorScheme.surfaceVariant.withOpacity(0.4),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: theme.dividerColor.withOpacity(0.3)),
                  ),
                ),
              ),
              const SizedBox(height: 10),

              // Audio File Attachment Pill (if picked)
              if (_pickedAudioFile != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  margin: const EdgeInsets.only(bottom: 10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF10B981).withOpacity(0.4)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.audio_file_rounded, color: Color(0xFF10B981), size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _pickedAudioFile!.name,
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      GestureDetector(
                        onTap: () => setState(() => _pickedAudioFile = null),
                        child: const Icon(Icons.close_rounded, size: 16),
                      ),
                    ],
                  ),
                ),

              // Presets & File Upload Options
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                runSpacing: 6,
                children: [
                  OutlinedButton.icon(
                    onPressed: _pickAudioFile,
                    icon: const Icon(Icons.upload_file_rounded, size: 14),
                    label: const Text('Pick Audio File', style: TextStyle(fontSize: 11)),
                    style: OutlinedButton.styleFrom(
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    ),
                  ),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      ActionChip(
                        label: const Text('📝 Lab Change', style: TextStyle(fontSize: 10)),
                        padding: EdgeInsets.zero,
                        visualDensity: VisualDensity.compact,
                        onPressed: () => _applySample('Attention 3rd year CSE students: Tomorrow lab at 2 PM in Turing Lab is postponed to Friday due to faculty meeting. Hall tickets required.'),
                      ),
                      ActionChip(
                        label: const Text('🚨 Emergency Drill', style: TextStyle(fontSize: 10)),
                        padding: EdgeInsets.zero,
                        visualDensity: VisualDensity.compact,
                        onPressed: () => _applySample('Urgent emergency alert: Mandatory campus fire evacuation drill starting in 10 minutes at main ground.'),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Action Button
              ElevatedButton.icon(
                onPressed: _isProcessing ? null : _processDictation,
                icon: _isProcessing
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.auto_fix_high_rounded, size: 18),
                label: Text(
                  _isProcessing ? 'AI Transforming to Circular...' : '✨ Transform into Official Circular',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
