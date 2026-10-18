import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:record/record.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:echosphere/services/echosphere_api_service.dart';

/// State of the Live Campus PA Broadcast
enum LiveMicState {
  idle,
  connecting,
  streaming,
  stopping,
  error,
}

class LiveMicStreamService {
  LiveMicStreamService._();
  static final LiveMicStreamService instance = LiveMicStreamService._();

  final AudioRecorder _audioRecorder = AudioRecorder();
  WebSocketChannel? _channel;
  StreamSubscription<Uint8List>? _micSub;
  StreamSubscription? _wsSub;

  final ValueNotifier<LiveMicState> stateNotifier = ValueNotifier(LiveMicState.idle);
  final ValueNotifier<int> bytesStreamedNotifier = ValueNotifier(0);
  final ValueNotifier<int> chunksSentNotifier = ValueNotifier(0);
  final ValueNotifier<int> listenerCountNotifier = ValueNotifier(0);
  final ValueNotifier<String?> sessionIdNotifier = ValueNotifier(null);
  final ValueNotifier<String?> errorNotifier = ValueNotifier(null);

  bool get isStreaming => stateNotifier.value == LiveMicState.streaming;

  /// Starts live microphone PA broadcast
  Future<bool> startBroadcast({
    String zone = 'College-Wide',
    bool isEmergency = false,
    String? token,
  }) async {
    if (stateNotifier.value == LiveMicState.streaming ||
        stateNotifier.value == LiveMicState.connecting) {
      return true;
    }

    try {
      stateNotifier.value = LiveMicState.connecting;
      errorNotifier.value = null;
      bytesStreamedNotifier.value = 0;
      chunksSentNotifier.value = 0;

      // 1. Verify Microphone permissions
      final hasPermission = await _audioRecorder.hasPermission();
      if (!hasPermission) {
        errorNotifier.value = 'Microphone permission denied. Please allow microphone access.';
        stateNotifier.value = LiveMicState.error;
        return false;
      }

      // 2. Resolve WebSocket Server URL
      final baseUrl = EchosphereApiService().baseUrl;
      final uri = Uri.parse(baseUrl);
      final wsScheme = uri.scheme == 'https' ? 'wss' : 'ws';
      final host = uri.host;
      
      final queryParams = <String, String>{
        'zone': zone,
        'is_emergency': isEmergency ? 'true' : 'false',
      };
      if (token != null && token.isNotEmpty) {
        queryParams['token'] = token;
      }

      final wsUri = Uri(
        scheme: wsScheme,
        host: host,
        port: uri.hasPort ? uri.port : null,
        path: '/api/v1/ws/hardware/mic-stream',
        queryParameters: queryParams,
      );

      debugPrint('🎙️ [LiveMicStream] Connecting to WebSocket: $wsUri');
      _channel = WebSocketChannel.connect(wsUri);
      await _channel!.ready;

      // 3. Listen for WebSocket control events
      _wsSub = _channel!.stream.listen(
        (event) {
          if (event is String) {
            try {
              final data = jsonDecode(event);
              if (data is Map<String, dynamic>) {
                final ev = data['event'];
                if (ev == 'SESSION_STARTED') {
                  sessionIdNotifier.value = data['session_id'];
                  listenerCountNotifier.value = data['listener_count'] ?? 0;
                  stateNotifier.value = LiveMicState.streaming;
                  debugPrint('🎙️ [LiveMicStream] Broadcast session started: ${data['session_id']}');
                } else if (ev == 'SESSION_ENDED') {
                  stopBroadcast();
                }
              }
            } catch (_) {}
          }
        },
        onError: (err) {
          debugPrint('🎙️ [LiveMicStream] WebSocket error: $err');
          errorNotifier.value = 'Connection lost: $err';
          stateNotifier.value = LiveMicState.error;
        },
        onDone: () {
          debugPrint('🎙️ [LiveMicStream] WebSocket connection closed.');
          if (stateNotifier.value == LiveMicState.streaming) {
            stopBroadcast();
          }
        },
      );

      // 4. Start PCM 16-bit 16kHz mono audio recording stream
      const recordConfig = RecordConfig(
        encoder: AudioEncoder.pcm16bits,
        sampleRate: 16000,
        numChannels: 1,
      );

      final audioStream = await _audioRecorder.startStream(recordConfig);
      stateNotifier.value = LiveMicState.streaming;

      // 5. Pipe binary PCM chunks directly to WebSocket sink
      _micSub = audioStream.listen(
        (chunk) {
          if (stateNotifier.value == LiveMicState.streaming && _channel != null) {
            _channel!.sink.add(chunk);
            bytesStreamedNotifier.value += chunk.length;
            chunksSentNotifier.value += 1;
          }
        },
        onError: (err) {
          debugPrint('🎙️ [LiveMicStream] Audio stream error: $err');
          errorNotifier.value = 'Audio capture error: $err';
        },
      );

      return true;
    } catch (e) {
      debugPrint('🎙️ [LiveMicStream] Failed to start live broadcast: $e');
      errorNotifier.value = 'Failed to start broadcast: $e';
      stateNotifier.value = LiveMicState.error;
      await stopBroadcast();
      return false;
    }
  }

  /// Stops live microphone PA broadcast
  Future<void> stopBroadcast() async {
    if (stateNotifier.value == LiveMicState.idle) return;
    stateNotifier.value = LiveMicState.stopping;

    try {
      await _micSub?.cancel();
      _micSub = null;

      if (await _audioRecorder.isRecording()) {
        await _audioRecorder.stop();
      }

      if (_channel != null) {
        try {
          _channel!.sink.add(jsonEncode({'command': 'STOP'}));
        } catch (_) {}
        await _channel!.sink.close();
        _channel = null;
      }

      await _wsSub?.cancel();
      _wsSub = null;
    } catch (e) {
      debugPrint('🎙️ [LiveMicStream] Error stopping broadcast: $e');
    } finally {
      stateNotifier.value = LiveMicState.idle;
      sessionIdNotifier.value = null;
    }
  }
}
