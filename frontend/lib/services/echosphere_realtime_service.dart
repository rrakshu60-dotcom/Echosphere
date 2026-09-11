import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:anymex/services/echosphere_api_service.dart';

class EchosphereRealtimeEvent {
  final String event;
  final int? announcementId;
  final String? title;
  final String? status;
  final String? remarks;
  final String? approverName;
  final String? creatorName;
  final Map<String, dynamic> rawData;

  EchosphereRealtimeEvent({
    required this.event,
    this.announcementId,
    this.title,
    this.status,
    this.remarks,
    this.approverName,
    this.creatorName,
    required this.rawData,
  });

  factory EchosphereRealtimeEvent.fromJson(Map<String, dynamic> json) {
    return EchosphereRealtimeEvent(
      event: json['event'] ?? 'UNKNOWN',
      announcementId: json['announcement_id'] as int?,
      title: json['title'] as String?,
      status: json['status'] as String?,
      remarks: json['remarks'] as String?,
      approverName: json['approver_name'] as String?,
      creatorName: json['creator_name'] as String?,
      rawData: json,
    );
  }
}

class EchosphereRealtimeService extends GetxService {
  static final EchosphereRealtimeService _instance = EchosphereRealtimeService._internal();
  factory EchosphereRealtimeService() => _instance;
  EchosphereRealtimeService._internal();

  WebSocket? _webSocket;
  Timer? _reconnectTimer;
  Timer? _pingTimer;
  bool _isDisposed = false;

  final RxBool isConnected = false.obs;
  final _eventController = StreamController<EchosphereRealtimeEvent>.broadcast();
  Stream<EchosphereRealtimeEvent> get events => _eventController.stream;

  String get _wsUrl {
    final baseUrl = EchosphereApiService().baseUrl.trim();
    String wsBase = baseUrl;
    if (wsBase.startsWith('https://')) {
      wsBase = 'wss://${wsBase.substring(8)}';
    } else if (wsBase.startsWith('http://')) {
      wsBase = 'ws://${wsBase.substring(7)}';
    } else if (!wsBase.startsWith('ws://') && !wsBase.startsWith('wss://')) {
      wsBase = 'ws://$wsBase';
    }

    if (wsBase.endsWith('/')) {
      wsBase = wsBase.substring(0, wsBase.length - 1);
    }

    return '$wsBase/ws/live';
  }

  void initialize() {
    _isDisposed = false;
    connect();
  }

  Future<void> connect() async {
    if (_isDisposed) return;
    if (isConnected.value && _webSocket != null) return;

    final url = _wsUrl;
    try {
      debugPrint('🔌 Connecting to EchoSphere Live Sync WebSocket: $url');
      _webSocket = await WebSocket.connect(url).timeout(const Duration(seconds: 8));
      isConnected.value = true;
      debugPrint('✅ EchoSphere Live Sync WebSocket connected successfully.');

      _pingTimer?.cancel();
      _pingTimer = Timer.periodic(const Duration(seconds: 25), (_) {
        if (isConnected.value && _webSocket != null) {
          try {
            _webSocket?.add('ping');
          } catch (_) {}
        }
      });

      _webSocket!.listen(
        (data) {
          _handleIncomingMessage(data);
        },
        onError: (err) {
          debugPrint('⚠️ EchoSphere WebSocket error: $err');
          _scheduleReconnect();
        },
        onDone: () {
          debugPrint('ℹ️ EchoSphere WebSocket connection closed.');
          _scheduleReconnect();
        },
        cancelOnError: true,
      );
    } catch (e) {
      debugPrint('❌ EchoSphere WebSocket connect failed: $e. Will retry in 4s.');
      _scheduleReconnect();
    }
  }

  void _handleIncomingMessage(dynamic raw) {
    try {
      final str = raw.toString().trim();
      if (str == '{"event":"pong"}' || str == 'pong') {
        return;
      }
      final decoded = jsonDecode(str);
      if (decoded is Map<String, dynamic>) {
        final event = EchosphereRealtimeEvent.fromJson(decoded);
        debugPrint('🔔 [Live Sync Event] ${event.event} - Notice #${event.announcementId}');
        _eventController.add(event);
      }
    } catch (e) {
      debugPrint('Error parsing incoming WebSocket message: $e');
    }
  }

  void _scheduleReconnect() {
    isConnected.value = false;
    _pingTimer?.cancel();
    _reconnectTimer?.cancel();
    if (_isDisposed) return;

    _reconnectTimer = Timer(const Duration(seconds: 4), () {
      connect();
    });
  }

  void disconnect() {
    _isDisposed = true;
    _pingTimer?.cancel();
    _reconnectTimer?.cancel();
    isConnected.value = false;
    try {
      _webSocket?.close();
    } catch (_) {}
    _webSocket = null;
  }
}
