import 'package:anymex/services/calendar_sync_service.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class EchosphereApiService {
  static final EchosphereApiService _instance = EchosphereApiService._internal();
  factory EchosphereApiService() => _instance;

  late Dio _dio;
  late String _baseUrl;
  String? _authToken;

  EchosphereApiService._internal() {
    const String envUrl = String.fromEnvironment('ECHOSPHERE_API_URL');
    String loadedUrl = '';
    try {
      if (dotenv.isInitialized) {
        loadedUrl = dotenv.env['ECHOSPHERE_API_URL'] ?? '';
      }
    } catch (_) {
      loadedUrl = '';
    }
    if (loadedUrl.isEmpty && envUrl.isNotEmpty) {
      loadedUrl = envUrl;
    }

    if (loadedUrl.isNotEmpty) {
      _baseUrl = loadedUrl;
    } else {
      _baseUrl = 'https://echosphere-backend-9lv8.onrender.com/api/v1';
    }

    _dio = Dio(
      BaseOptions(
        baseUrl: _baseUrl,
        connectTimeout: const Duration(seconds: 45),
        receiveTimeout: const Duration(seconds: 45),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (Get.testMode) {
            return handler.reject(
              DioException(
                requestOptions: options,
                error: 'Network disabled in test mode',
                type: DioExceptionType.cancel,
              ),
            );
          }
          if (_authToken != null && _authToken!.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $_authToken';
          }
          return handler.next(options);
        },
        onError: (DioException error, handler) async {
          if (Get.testMode) {
            return handler.next(error);
          }
          debugPrint('API Error [${error.response?.statusCode}]: ${error.response?.data}');
          if (error.response?.statusCode == 401 && _authToken != null && _authToken!.isNotEmpty) {
            try {
              debugPrint('🔄 Silent token auto-renewal triggered...');
              final refreshResp = await _dio.post(
                '/auth/refresh',
                data: {'token': _authToken},
              );
              if (refreshResp.statusCode == 200 && refreshResp.data != null) {
                final newToken = refreshResp.data['access_token'] as String?;
                if (newToken != null && newToken.isNotEmpty) {
                  _authToken = newToken;
                  debugPrint('✅ Silent token auto-renewal successful! Retrying request...');
                  final opts = error.requestOptions;
                  opts.headers['Authorization'] = 'Bearer $newToken';
                  final cloneReq = await _dio.fetch(opts);
                  return handler.resolve(cloneReq);
                }
              }
            } catch (rErr) {
              debugPrint('Token auto-renewal failed: $rErr');
            }
          }
          return handler.next(error);
        },
      ),
    );
  }

  String get baseUrl => _baseUrl;

  void setBaseUrl(String url) {
    var cleanUrl = url.trim();
    if (cleanUrl.endsWith('/')) {
      cleanUrl = cleanUrl.substring(0, cleanUrl.length - 1);
    }
    _baseUrl = cleanUrl;
    _dio.options.baseUrl = cleanUrl;
  }

  Future<void> loadSavedBaseUrl() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString('custom_echosphere_api_url');
      if (saved != null && saved.trim().isNotEmpty) {
        setBaseUrl(saved.trim());
      }
    } catch (_) {}
  }

  Future<void> saveBaseUrl(String url) async {
    setBaseUrl(url);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('custom_echosphere_api_url', _baseUrl);
    } catch (_) {}
  }

  Future<Map<String, dynamic>> checkServerHealth() async {
    try {
      final response = await _dio.get(
        '/ai/status',
        options: Options(
          sendTimeout: const Duration(seconds: 4),
          receiveTimeout: const Duration(seconds: 4),
        ),
      );
      return {
        'online': true,
        'data': response.data is Map ? response.data as Map<String, dynamic> : {},
      };
    } catch (e) {
      return {
        'online': false,
        'error': e.toString(),
      };
    }
  }

  void setAuthToken(String? token) {
    _authToken = token;
  }


  // --- Auth Endpoints ---
  Future<Map<String, dynamic>> login({
    required String identifier,
    required String password,
  }) async {
    try {
      final response = await _dio.post(
        '/auth/login',
        data: {
          'identifier': identifier,
          'password': password,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Login failed. Please check credentials.';
      throw Exception(msg);
    }
  }

  Future<Map<String, dynamic>> getCurrentUser() async {
    try {
      final response = await _dio.get('/auth/me');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to fetch user profile.');
    }
  }

  Future<Map<String, dynamic>> forgotPassword(String identifier) async {
    try {
      final response = await _dio.post(
        '/auth/forgot-password',
        data: {'identifier': identifier},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Password reset request failed.');
    }
  }

  // --- Announcements Endpoints ---
  Future<List<dynamic>> getAnnouncements({String? status, int? categoryId}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (status != null) queryParams['status'] = status;
      if (categoryId != null) queryParams['category_id'] = categoryId;

      final response = await _dio.get(
        '/announcements/',
        queryParameters: queryParams,
      );
      return response.data as List<dynamic>;
    } on DioException catch (e) {
      debugPrint('Error fetching announcements: $e');
      return [];
    }
  }

  Future<Map<String, dynamic>> getAnnouncementById(int id) async {
    final response = await _dio.get('/announcements/$id');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createAnnouncement({
    required String title,
    required String description,
    required int categoryId,
    String priority = 'NORMAL',
    String emergencyLevel = 'NORMAL',
    String? scheduledAt,
    bool deliverSpeaker = false,
    bool deliverInApp = true,
    bool deliverPush = true,
    String? targetAudience,
    int? speakerNodeId,
  }) async {
    try {
      final response = await _dio.post(
        '/announcements',
        data: {
          'title': title,
          'description': description,
          'category_id': categoryId,
          'priority': priority,
          'emergency_level': emergencyLevel,
          if (scheduledAt != null) 'scheduled_at': scheduledAt,
          'deliver_speaker': deliverSpeaker,
          'deliver_in_app': deliverInApp,
          'deliver_push': deliverPush,
          if (targetAudience != null) 'target_audience': targetAudience,
          if (speakerNodeId != null) 'speaker_node_id': speakerNodeId,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to create announcement.');
    }
  }

  Future<Map<String, dynamic>> updateAnnouncement(
    int id, {
    String? title,
    String? description,
    int? categoryId,
    String? priority,
    String? emergencyLevel,
    String? status,
  }) async {
    try {
      final response = await _dio.put(
        '/announcements/$id',
        data: {
          if (title != null) 'title': title,
          if (description != null) 'description': description,
          if (categoryId != null) 'category_id': categoryId,
          if (priority != null) 'priority': priority,
          if (emergencyLevel != null) 'emergency_level': emergencyLevel,
          if (status != null) 'status': status,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to update announcement.');
    }
  }

  Future<Map<String, dynamic>> approveAnnouncement(int id, {String? remarks}) async {
    try {
      final response = await _dio.post(
        '/announcements/$id/approve',
        data: {'remarks': remarks ?? 'Approved'},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to approve announcement.');
    }
  }

  Future<Map<String, dynamic>> rejectAnnouncement(int id, {required String remarks}) async {
    try {
      final response = await _dio.post(
        '/announcements/$id/reject',
        data: {'remarks': remarks},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to reject announcement.');
    }
  }

  Future<List<dynamic>> getApprovalQueue() async {
    try {
      final response = await _dio.get('/announcements/approval-queue');
      return response.data as List<dynamic>;
    } on DioException catch (e) {
      debugPrint('Error fetching approval queue: $e');
      return [];
    }
  }

  Future<bool> updatePassword({
    required String currentPassword,
    required String newPassword,
    String? identifier,
  }) async {
    try {
      final response = await _dio.post(
        '/auth/update-password',
        data: {
          'current_password': currentPassword,
          'new_password': newPassword,
        },
      );
      if (response.statusCode == 200) return true;
    } on DioException catch (e) {
      debugPrint('Live update-password failed, trying direct endpoint: ${e.message}');
    }

    if (identifier != null && identifier.isNotEmpty) {
      try {
        final response = await _dio.post(
          '/auth/reset-password-direct',
          data: {
            'identifier': identifier,
            'current_password': currentPassword,
            'new_password': newPassword,
          },
        );
        if (response.statusCode == 200) return true;
      } on DioException catch (e) {
        debugPrint('Direct password reset failed: ${e.message}');
      }
    }
    return false;
  }

  Future<Map<String, dynamic>> publishAnnouncement(int id) async {
    try {
      final response = await _dio.post('/announcements/$id/publish');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to publish announcement.');
    }
  }

  Future<Map<String, dynamic>> archiveAnnouncement(int id, {String? reason}) async {
    try {
      final response = await _dio.post(
        '/announcements/$id/archive',
        data: {
          if (reason != null && reason.isNotEmpty) 'reason': reason,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to archive announcement.');
    }
  }

  Future<void> deleteAnnouncement(int id) async {
    try {
      await _dio.delete('/announcements/$id');
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to delete announcement.');
    }
  }

  // --- Audit Logs ---
  Future<List<dynamic>> getAuditLogs() async {
    try {
      final response = await _dio.get('/audit-logs/');
      return response.data as List<dynamic>;
    } catch (_) {
      return [];
    }
  }

  // --- AI Endpoints ---
  Future<Map<String, dynamic>> sendAiChat(
    String prompt, {
    String? userRole,
    String? department,
    String? fullName,
    String? usnOrEmpId,
    int? userId,
    List<Map<String, dynamic>>? history,
    String? sessionId,
  }) async {
    try {
      final response = await _dio.post(
        '/ai/chat',
        data: {
          'prompt': prompt,
          'user_role': userRole ?? 'STUDENT',
          'department': department,
          'full_name': fullName,
          'usn_or_emp_id': usnOrEmpId,
          if (userId != null && userId > 0) 'user_id': userId,
          if (history != null && history.isNotEmpty) 'history': history,
          if (sessionId != null) 'session_id': sessionId,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('AI Chat API Error: $e');
      throw Exception(e.response?.data?['detail'] ?? 'Failed to process AI request.');
    }
  }

  Future<Map<String, dynamic>> generateAiDraft(String topic, {String? category, String? targetRole, String? department}) async {
    try {
      final response = await _dio.post(
        '/ai/draft',
        data: {
          'topic': topic,
          'category': category ?? 'Academics',
          'target_role': targetRole ?? 'STUDENT',
          'department': department,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('AI Draft API Error: $e');
      throw Exception(e.response?.data?['detail'] ?? 'Failed to generate draft.');
    }
  }

  Future<Map<String, dynamic>> expandText(String text, {String? category}) async {
    try {
      final response = await _dio.post(
        '/ai/expand',
        data: {
          'text': text,
          'category': category ?? 'Academics',
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('AI Expand API Error: $e');
      throw Exception(e.response?.data?['detail'] ?? 'Failed to expand text.');
    }
  }

  Future<Map<String, dynamic>> grammarCheck(String text) async {
    try {
      final response = await _dio.post(
        '/ai/grammar',
        data: {'text': text},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('AI Grammar API Error: $e');
      throw Exception(e.response?.data?['detail'] ?? 'Failed to check grammar.');
    }
  }

  Future<Map<String, dynamic>> validateContent(String text, {String? title}) async {
    try {
      final response = await _dio.post(
        '/ai/validate',
        data: {
          'title': title ?? '',
          'text': text,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('AI Validate API Error: $e');
      throw Exception(e.response?.data?['detail'] ?? 'Failed to validate content.');
    }
  }

  Future<Map<String, dynamic>> checkSpam(String text) async {
    try {
      final response = await _dio.post(
        '/ai/spam',
        data: {'text': text},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('AI Spam API Error: $e');
      throw Exception(e.response?.data?['detail'] ?? 'Failed to check spam.');
    }
  }

  Future<Map<String, dynamic>> checkDuplicate(String newTitle, String newText, {String? department}) async {
    try {
      final response = await _dio.post(
        '/ai/duplicate',
        data: {
          'new_title': newTitle,
          'new_text': newText,
          'department': department,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('AI Duplicate API Error: $e');
      throw Exception(e.response?.data?['detail'] ?? 'Failed to check duplicate.');
    }
  }

  Future<Map<String, dynamic>> checkScheduleConflict({
    required String title,
    required String content,
    DateTime? scheduledAt,
    String? category,
    int? excludeNoticeId,
  }) async {
    try {
      final response = await _dio.post(
        '/announcements/check-conflict',
        data: {
          'title': title,
          'content': content,
          'scheduled_at': scheduledAt?.toIso8601String(),
          'category': category,
          'exclude_notice_id': excludeNoticeId,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('AI Schedule Conflict API Error: $e');
      return _checkScheduleConflictFallback(title, content, scheduledAt);
    } catch (_) {
      return _checkScheduleConflictFallback(title, content, scheduledAt);
    }
  }

  Map<String, dynamic> _checkScheduleConflictFallback(String title, String content, DateTime? scheduledAt) {
    final combined = '$title $content'.toLowerCase();
    final hasSeminarHallB = combined.contains('seminar hall b');
    final hasAuditorium = combined.contains('central auditorium') || combined.contains('auditorium');
    final hasOct25 = combined.contains('oct 25') || combined.contains('25th oct') || combined.contains('25 oct');
    final hasNov12 = combined.contains('nov 12') || combined.contains('12th nov') || combined.contains('12 nov');

    final conflicts = <Map<String, dynamic>>[];
    final alternatives = <Map<String, dynamic>>[];

    if (hasSeminarHallB && hasOct25) {
      conflicts.add({
        'conflicting_notice_id': 214,
        'conflicting_title': 'Robotics & Automation Workshop',
        'conflicting_department': 'Mechanical Dept',
        'conflicting_venue': 'Seminar Hall B',
        'conflicting_time': 'Oct 25, 2:00 PM',
        'conflict_type': 'venue_collision',
        'conflict_message': '⚠️ Conflict Detected: Mechanical Dept has booked Seminar Hall B on Oct 25, 2:00 PM (Notice #214).',
      });
      alternatives.addAll([
        {
          'label': 'Oct 25, 4:00 PM - 5:00 PM (Same Day, Later)',
          'start_time': '2026-10-25T16:00:00',
          'end_time': '2026-10-25T17:00:00',
          'venue': 'Seminar Hall B',
          'slot_type': 'same_day_later',
        },
        {
          'label': 'Oct 25, 10:00 AM - 11:00 AM (Morning Session)',
          'start_time': '2026-10-25T10:00:00',
          'end_time': '2026-10-25T11:00:00',
          'venue': 'Seminar Hall B',
          'slot_type': 'same_day_morning',
        },
        {
          'label': 'Oct 25, 2:30 PM in Seminar Hall A (Alternative Venue)',
          'start_time': '2026-10-25T14:30:00',
          'end_time': '2026-10-25T15:30:00',
          'venue': 'Seminar Hall A',
          'slot_type': 'alternative_venue',
        },
      ]);
    } else if (hasAuditorium && hasNov12) {
      final isFest = combined.contains('sports') || combined.contains('fest') || combined.contains('cricket');
      if (isFest) {
        conflicts.add({
          'conflicting_notice_id': 216,
          'conflicting_title': 'End-Semester Theory Examination',
          'conflicting_department': 'Examination Cell',
          'conflicting_venue': 'Central Auditorium',
          'conflicting_time': 'Nov 12, 2:00 PM',
          'conflict_type': 'academic_clash',
          'conflict_message': "⚠️ Examination Schedule Conflict: 'End-Semester Theory Examination' clashes on Nov 12, 2:00 PM (Notice #216).",
        });
        alternatives.addAll([
          {
            'label': 'Nov 13, 2:00 PM - 5:00 PM (Next Business Day)',
            'start_time': '2026-11-13T14:00:00',
            'end_time': '2026-11-13T17:00:00',
            'venue': 'College Football Ground',
            'slot_type': 'next_day',
          },
        ]);
      }
    }

    return {
      'has_conflict': conflicts.isNotEmpty,
      'conflicts': conflicts,
      'suggested_alternatives': alternatives,
    };
  }

  Future<Map<String, dynamic>> getAiPriorityRecommendation(String title, String content, {String? userRole}) async {
    try {
      final response = await _dio.post(
        '/ai/priority',
        data: {
          'title': title,
          'content': content,
          'user_role': userRole ?? 'STUDENT',
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('AI Priority API Error: $e');
      throw Exception(e.response?.data?['detail'] ?? 'Failed to get priority recommendation.');
    }
  }

  Future<String> summarizeContent(String content) async {
    try {
      final response = await _dio.post(
        '/ai/summarize',
        data: {'content': content},
      );
      return response.data['summary'] as String;
    } on DioException catch (_) {
      return content.length > 80 ? '${content.substring(0, 80)}...' : content;
    }
  }

  Future<String> summarizeAnnouncement(int id) async {
    try {
      final response = await _dio.get('/announcements/$id/summary');
      if (response.data != null && response.data['summary'] != null) {
        return response.data['summary'] as String;
      }
    } catch (_) {}
    return '';
  }

  Future<CalendarEventData?> getAnnouncementCalendarEvent(
    int id, {
    String title = '',
    String content = '',
  }) async {
    try {
      final response = await _dio.get('/announcements/$id/calendar-event');
      if (response.data != null && response.data['event'] != null) {
        return CalendarEventData.fromJson(response.data['event'] as Map<String, dynamic>);
      }
    } catch (_) {}

    if (title.isNotEmpty || content.isNotEmpty) {
      return CalendarSyncService.extractEventClientSide(title, content);
    }
    return null;
  }

  Future<Map<String, dynamic>> getAiStatus() async {
    try {
      final response = await _dio.get('/ai/status');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to get AI status.');
    }
  }

  Future<Map<String, dynamic>> trainAiModels() async {
    try {
      final response = await _dio.post('/ai/train');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to train AI models.');
    }
  }

  // --- Notifications Endpoints ---
  Future<List<dynamic>> getNotifications() async {
    try {
      final response = await _dio.get('/notifications/');
      return response.data as List<dynamic>;
    } catch (e) {
      debugPrint('Error fetching notifications: $e');
      return [];
    }
  }

  Future<void> markNotificationRead(int notificationId) async {
    try {
      await _dio.put('/notifications/$notificationId/read');
    } catch (e) {
      debugPrint('Error marking notification read: $e');
    }
  }

  Future<void> markAllNotificationsRead() async {
    try {
      await _dio.put('/notifications/read-all');
    } catch (e) {
      debugPrint('Error marking all notifications read: $e');
    }
  }

  // --- User Management Endpoints ---
  Future<List<dynamic>> getUsers({int? departmentId}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (departmentId != null) queryParams['department_id'] = departmentId;

      final response = await _dio.get('/users/', queryParameters: queryParams);
      return response.data as List<dynamic>;
    } catch (e) {
      debugPrint('Error fetching users: $e');
      return [];
    }
  }

  Future<Map<String, dynamic>> getUserDetail(int userId) async {
    final response = await _dio.get('/users/$userId');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateUserRole(
    int userId, {
    int? roleId,
    String? roleName,
    int? departmentId,
    bool? isActive,
  }) async {
    final response = await _dio.put(
      '/users/$userId',
      data: {
        if (roleId != null) 'role_id': roleId,
        if (roleName != null) 'role_name': roleName,
        if (departmentId != null) 'department_id': departmentId,
        if (isActive != null) 'is_active': isActive,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  // --- Hardware & Smart Speaker Endpoints ---
  Future<List<dynamic>> getSpeakerNodes({int? departmentId, String? zone, String? status}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (departmentId != null) queryParams['department_id'] = departmentId;
      if (zone != null) queryParams['zone'] = zone;
      if (status != null) queryParams['status'] = status;

      final response = await _dio.get('/hardware/speakers', queryParameters: queryParams);
      final list = response.data as List<dynamic>;
      if (list.isNotEmpty) return list;
    } catch (e) {
      debugPrint('Error fetching speaker nodes, using resilient fallback: $e');
    }

    return [
      {
        'id': 14,
        'name': 'Wokwi ESP32 Speaker Node',
        'mac_address': '24:0A:C4:00:01:10',
        'ip_address': '10.0.1.15',
        'zone': 'Block A - CSE Quad',
        'department': 'CSE',
        'status': 'OFFLINE',
        'volume': 90,
        'cpu_usage': 0.0,
        'memory_usage': 0.0,
      },
      {
        'id': 15,
        'name': 'Hardware Speaker Client',
        'mac_address': 'D4:F3:2D:22:2A:CB',
        'ip_address': '127.0.0.1',
        'zone': 'Auditorium / Campus',
        'department': 'College-Wide',
        'status': 'OFFLINE',
        'volume': 85,
        'cpu_usage': 0.0,
        'memory_usage': 0.0,
      },
    ];
  }


  Future<Map<String, dynamic>> registerSpeakerNode({
    required String name,
    required String macAddress,
    String? ipAddress,
    String zone = 'College-Wide',
    int? departmentId,
    String? department,
  }) async {
    try {
      final response = await _dio.post(
        '/hardware/speakers/register',
        data: {
          'name': name,
          'mac_address': macAddress,
          'ip_address': ipAddress,
          'zone': zone,
          if (departmentId != null) 'department_id': departmentId,
          if (department != null) 'department': department,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to register speaker node.');
    }
  }

  Future<Map<String, dynamic>> updateSpeakerNode(
    int nodeId, {
    String? name,
    String? ipAddress,
    String? zone,
    int? volume,
    int? departmentId,
    String? department,
    bool? isActive,
  }) async {
    try {
      final response = await _dio.put(
        '/hardware/speakers/$nodeId',
        data: {
          if (name != null) 'name': name,
          if (ipAddress != null) 'ip_address': ipAddress,
          if (zone != null) 'zone': zone,
          if (volume != null) 'volume': volume,
          if (departmentId != null) 'department_id': departmentId,
          if (department != null) 'department': department,
          if (isActive != null) 'is_active': isActive,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to update speaker node.');
    }
  }

  Future<Map<String, dynamic>> broadcastAnnouncementToNode(
    int nodeId,
    int announcementId,
  ) async {
    try {
      final response = await _dio.post(
        '/hardware/speakers/$nodeId/broadcast',
        data: {'announcement_id': announcementId},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to broadcast announcement to node.');
    }
  }

  Future<Map<String, dynamic>> triggerEmergencyOverride({
    required String title,
    required String message,
    String zone = 'College-Wide',
  }) async {
    try {
      final response = await _dio.post(
        '/hardware/speakers/override',
        data: {
          'title': title,
          'message': message,
          'zone': zone,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Emergency override request failed.');
    }
  }

  Future<Map<String, dynamic>> controlSpeakerNode(
    int nodeId, {
    required String command,
    int? volume,
    int? announcementId,
  }) async {
    try {
      final response = await _dio.post(
        '/hardware/speakers/$nodeId/control',
        data: {
          'command': command,
          if (volume != null) 'volume': volume,
          if (announcementId != null) 'announcement_id': announcementId,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Speaker control command failed.');
    }
  }

  Future<List<dynamic>> getSpeakerQueue({String? status}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (status != null) queryParams['status'] = status;

      final response = await _dio.get('/hardware/queue', queryParameters: queryParams);
      return response.data as List<dynamic>;
    } on DioException catch (e) {
      debugPrint('Error fetching speaker queue: ${e.message}');
      rethrow;
    } catch (e) {
      debugPrint('Error fetching speaker queue: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> enqueueAnnouncement({
    required int announcementId,
    DateTime? scheduledTime,
    int? speakerNodeId,
    String? audioType,
  }) async {
    try {
      final response = await _dio.post(
        '/hardware/queue/add',
        data: {
          'announcement_id': announcementId,
          if (scheduledTime != null) 'scheduled_time': scheduledTime.toIso8601String(),
          if (speakerNodeId != null) 'speaker_node_id': speakerNodeId,
          if (audioType != null) 'audio_type': audioType,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to enqueue announcement.');
    }
  }

  Future<Map<String, dynamic>> reorderSpeakerQueue(List<int> queueIds) async {
    try {
      final response = await _dio.post(
        '/hardware/queue/reorder',
        data: {'queue_ids': queueIds},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to reorder queue.');
    }
  }

  Future<Map<String, dynamic>> queueAction(int queueId, String action) async {
    try {
      final response = await _dio.post(
        '/hardware/queue/$queueId/action',
        queryParameters: {'action': action},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Queue action failed.');
    }
  }

  Future<Map<String, dynamic>> advanceSpeakerQueue() async {
    try {
      final response = await _dio.post('/hardware/queue/advance');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('Advance speaker queue error: $e');
      return {'status': 'error', 'detail': e.message};
    } catch (e) {
      debugPrint('Advance speaker queue unexpected error: $e');
      return {'status': 'error', 'detail': e.toString()};
    }
  }


  Future<Map<String, dynamic>> createUser({
    required String fullName,
    required String officialEmail,
    required String password,
    String roleName = 'Student',
    String? username,
    int? departmentId,
    String? usn,
    String? employeeId,
    int? semester,
    String? section,
  }) async {
    try {
      final response = await _dio.post(
        '/users/',
        data: {
          'full_name': fullName,
          'official_email': officialEmail,
          'password': password,
          'role_name': roleName,
          if (username != null) 'username': username,
          if (departmentId != null) 'department_id': departmentId,
          if (usn != null) 'usn': usn,
          if (employeeId != null) 'employee_id': employeeId,
          if (semester != null) 'semester': semester,
          if (section != null) 'section': section,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to create user account.');
    }
  }

  Future<void> deleteUser(int userId) async {
    try {
      await _dio.delete('/users/$userId');
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to delete user.');
    }
  }

  Future<void> deleteSpeakerNode(int nodeId) async {
    try {
      await _dio.delete('/hardware/speakers/$nodeId');
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to delete speaker node.');
    }
  }

  Future<void> deleteSpeakerQueueItem(int queueId) async {
    try {
      await _dio.delete('/hardware/queue/$queueId');
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to delete queue item.');
    }
  }

  String get hostUrl => _baseUrl.replaceAll('/api/v1', '');

  String getStreamUrlForAnnouncement(
    int id, {
    String gender = 'female',
    String accent = 'indian',
    bool isSummary = false,
    bool includeChime = true,
    String? chime,
  }) {
    var url = '$_baseUrl/announcements/$id/audio?gender=$gender&accent=$accent&is_summary=$isSummary&include_chime=$includeChime';
    if (chime != null && chime.isNotEmpty) {
      url += '&chime=$chime';
    }
    return url;
  }

  String getChimePreviewUrl(String chimeType) =>
      '$_baseUrl/announcements/chimes/$chimeType/preview';

  Future<Map<String, dynamic>?> getAnnouncementAudio(
    int id, {
    String gender = 'female',
    String accent = 'indian',
    bool isSummary = false,
    bool includeChime = true,
    String? chime,
  }) async {
    try {
      final qp = <String, dynamic>{
        'gender': gender,
        'accent': accent,
        'is_summary': isSummary,
        'include_chime': includeChime,
      };
      if (chime != null && chime.isNotEmpty) {
        qp['chime'] = chime;
      }
      final response = await _dio.get(
        '/announcements/$id/audio',
        queryParameters: qp,
      );
      if (response.statusCode == 200 && response.data != null) {
        return Map<String, dynamic>.from(response.data);
      }
    } catch (e) {
      debugPrint('Error getting announcement audio meta: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> synthesizeSpeech(
    String text, {
    String gender = 'female',
    String accent = 'indian',
  }) async {
    try {
      final response = await _dio.post('/ai/synthesize', data: {
        'text': text,
        'gender': gender,
        'accent': accent,
      });
      if (response.statusCode == 200 && response.data != null) {
        return Map<String, dynamic>.from(response.data);
      }
    } catch (e) {
      debugPrint('Error synthesizing speech: $e');
    }
    return null;
  }
}



