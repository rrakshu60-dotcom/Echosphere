import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/services/live_mic_stream_service.dart';
import 'package:echosphere/utils/theme_extensions.dart';
import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:echosphere/widgets/custom_widgets/audio_waveform_visualizer.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';

class LiveMicBroadcastSheet extends StatefulWidget {
  const LiveMicBroadcastSheet({super.key});

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => const LiveMicBroadcastSheet(),
    );
  }

  @override
  State<LiveMicBroadcastSheet> createState() => _LiveMicBroadcastSheetState();
}

class _LiveMicBroadcastSheetState extends State<LiveMicBroadcastSheet>
    with SingleTickerProviderStateMixin {
  final LiveMicStreamService _micService = LiveMicStreamService.instance;
  String _selectedZone = 'College-Wide';
  bool _isEmergency = false;
  Timer? _durationTimer;
  int _secondsElapsed = 0;

  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  final List<String> _zones = [
    'College-Wide',
    'Auditorium / Campus',
    'Block A',
    'Block B',
    'Block B - AI Lab',
    'Library',
    'Hostel',
    'Lab-Block',
  ];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.95, end: 1.15).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _micService.stateNotifier.addListener(_onStateChange);
  }

  @override
  void dispose() {
    _durationTimer?.cancel();
    _pulseController.dispose();
    _micService.stateNotifier.removeListener(_onStateChange);
    // Auto-stop broadcast if user closes sheet
    if (_micService.isStreaming) {
      _micService.stopBroadcast();
    }
    super.dispose();
  }

  void _onStateChange() {
    if (mounted) {
      setState(() {
        if (_micService.isStreaming) {
          _startTimer();
        } else {
          _stopTimer();
        }
      });
    }
  }

  void _startTimer() {
    _durationTimer?.cancel();
    _secondsElapsed = 0;
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) {
        setState(() {
          _secondsElapsed++;
        });
      }
    });
  }

  void _stopTimer() {
    _durationTimer?.cancel();
    _durationTimer = null;
    _secondsElapsed = 0;
  }

  String _formatDuration(int sec) {
    final m = (sec ~/ 60).toString().padLeft(2, '0');
    final s = (sec % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  Future<void> _toggleBroadcast() async {
    if (_micService.isStreaming) {
      await _micService.stopBroadcast();
      snackBar('Live PA Broadcast ended.');
    } else {
      String? token;
      if (Get.isRegistered<AuthController>()) {
        token = Get.find<AuthController>().token.value;
      }

      final success = await _micService.startBroadcast(
        zone: _selectedZone,
        isEmergency: _isEmergency,
        token: token,
      );

      if (success) {
        snackBar(
          _isEmergency
              ? '🚨 Emergency live PA broadcast active on campus speakers!'
              : '🎙️ Live PA broadcast connected to campus speakers!',
          title: 'Live PA Active',
        );
      } else {
        final err = _micService.errorNotifier.value ?? 'Unable to connect to live stream.';
        snackBar(err, title: 'Broadcast Failed');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isStreaming = _micService.isStreaming;
    final isConnecting = _micService.stateNotifier.value == LiveMicState.connecting;
    final activeColor = _isEmergency ? Colors.redAccent : context.colors.primary;

    return Container(
      decoration: BoxDecoration(
        color: context.colors.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.35),
            blurRadius: 24,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      padding: EdgeInsets.only(
        top: 16,
        left: 20,
        right: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag handle
          Container(
            width: 44,
            height: 4,
            decoration: BoxDecoration(
              color: context.colors.onSurface.opaque(0.2),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 16),

          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: activeColor.withOpacity(0.12),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  isStreaming ? Icons.podcasts_rounded : Icons.mic_rounded,
                  color: activeColor,
                  size: 24,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    EchoSphereText(
                      text: _isEmergency
                          ? '🚨 Emergency Live Campus PA'
                          : '🎙️ Live Campus PA Broadcast',
                      size: 16,
                      variant: TextVariant.bold,
                      color: activeColor,
                    ),
                    EchoSphereText(
                      text: 'Ultra-low latency (<120ms) hardware corridor transmission',
                      size: 10,
                      color: context.colors.onSurface.opaque(0.6),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close_rounded),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Emergency Override Toggle
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: _isEmergency
                  ? Colors.red.withOpacity(0.12)
                  : context.colors.onSurface.opaque(0.04),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: _isEmergency
                    ? Colors.red.withOpacity(0.4)
                    : context.colors.outline.opaque(0.1),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.warning_amber_rounded,
                  color: _isEmergency ? Colors.redAccent : context.colors.onSurface.opaque(0.5),
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      EchoSphereText(
                        text: 'Emergency Preemption Siren',
                        size: 12,
                        variant: TextVariant.bold,
                        color: _isEmergency ? Colors.redAccent : context.colors.onSurface,
                      ),
                      EchoSphereText(
                        text: 'Preempts queue and maximizes speaker volume',
                        size: 9,
                        color: context.colors.onSurface.opaque(0.6),
                      ),
                    ],
                  ),
                ),
                Switch(
                  value: _isEmergency,
                  activeColor: Colors.redAccent,
                  onChanged: isStreaming
                      ? null
                      : (val) {
                          setState(() {
                            _isEmergency = val;
                          });
                        },
                ),
              ],
            ),
          ),

          const SizedBox(height: 14),

          // Target Zone Selector
          Row(
            children: [
              EchoSphereText(
                text: 'Target Zone:',
                size: 11,
                variant: TextVariant.semiBold,
                color: context.colors.onSurface.opaque(0.8),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _selectedZone,
                  isExpanded: true,
                  dropdownColor: context.colors.surface,
                  decoration: InputDecoration(
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  items: _zones
                      .map((z) => DropdownMenuItem(
                            value: z,
                            child: Text(
                              z,
                              style: TextStyle(
                                fontSize: 12,
                                color: context.colors.onSurface,
                              ),
                            ),
                          ))
                      .toList(),
                  onChanged: isStreaming
                      ? null
                      : (val) {
                          if (val != null) setState(() => _selectedZone = val);
                        },
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Center Live Visualizer & Broadcast Button
          if (isStreaming) ...[
            // Waveform animation
            const SizedBox(
              height: 48,
              child: AudioWaveformVisualizer(
                isPlaying: true,
                barCount: 28,
              ),
            ),
            const SizedBox(height: 12),

            // Live Duration Counter
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: Colors.red,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                EchoSphereText(
                  text: 'LIVE ${_formatDuration(_secondsElapsed)}',
                  size: 15,
                  variant: TextVariant.bold,
                  color: activeColor,
                ),
                const SizedBox(width: 14),
                ValueListenableBuilder<int>(
                  valueListenable: _micService.listenerCountNotifier,
                  builder: (ctx, count, _) {
                    return EchoSphereText(
                      text: '\u2022 $count Speakers Online',
                      size: 11,
                      color: context.colors.onSurface.opaque(0.7),
                    );
                  },
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Chunks / Bytes Streamed Counter
            ValueListenableBuilder<int>(
              valueListenable: _micService.bytesStreamedNotifier,
              builder: (ctx, bytes, _) {
                final kb = (bytes / 1024).toStringAsFixed(1);
                return EchoSphereText(
                  text: '$kb KB streamed live to $_selectedZone',
                  size: 10,
                  color: context.colors.onSurface.opaque(0.5),
                );
              },
            ),
          ] else ...[
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: EchoSphereText(
                text: isConnecting
                    ? 'Connecting to campus speaker network...'
                    : 'Tap the microphone button below to broadcast your voice live to corridor speakers.',
                size: 11,
                textAlign: TextAlign.center,
                color: context.colors.onSurface.opaque(0.6),
              ),
            ),
          ],

          const SizedBox(height: 20),

          // Big Mic Broadcast Button with Pulse effect
          GestureDetector(
            onTap: isConnecting ? null : _toggleBroadcast,
            child: ScaleTransition(
              scale: isStreaming ? _pulseAnimation : const AlwaysStoppedAnimation(1.0),
              child: Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: isStreaming
                        ? [Colors.redAccent, Colors.red.shade800]
                        : [activeColor, activeColor.withOpacity(0.8)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: (isStreaming ? Colors.redAccent : activeColor).withOpacity(0.4),
                      blurRadius: isStreaming ? 24 : 12,
                      spreadRadius: isStreaming ? 4 : 1,
                    ),
                  ],
                ),
                child: Center(
                  child: isConnecting
                      ? const SizedBox(
                          width: 28,
                          height: 28,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            valueColor: AlwaysStoppedAnimation(Colors.white),
                          ),
                        )
                      : Icon(
                          isStreaming ? Icons.stop_rounded : Icons.mic_rounded,
                          size: 38,
                          color: Colors.white,
                        ),
                ),
              ),
            ),
          ),

          const SizedBox(height: 12),
          EchoSphereText(
            text: isStreaming ? 'TAP TO STOP' : 'START LIVE BROADCAST',
            size: 11,
            variant: TextVariant.bold,
            color: isStreaming ? Colors.redAccent : context.colors.onSurface,
          ),

          const SizedBox(height: 8),
        ],
      ),
    );
  }
}
