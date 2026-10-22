/// Backend-shaped speaker queue items, matching GET /api/v1/hardware/queue.
/// Speaker queue tests feed these to SpeakerQueueController.applyServerSnapshot,
/// because the backend (not the app) decides what is queued, playing or held.
Map<String, dynamic> serverQueueItem({
  required int id,
  required int announcementId,
  required String title,
  String status = 'Queued',
  int queuePosition = 1,
  int durationSeconds = 15,
  bool speakerConfirmed = false,
  double? speakerElapsedSeconds,
  String priority = 'NORMAL',
  bool hasRepeat = false,
  int maxRepeats = 1,
  int totalPlayedCount = 0,
}) {
  return {
    'id': id,
    'announcement_id': announcementId,
    'title': title,
    'description': '$title (details)',
    'content': '$title (details)',
    'department': 'College-Wide',
    'priority': priority,
    'type': 'AI Speech',
    'status': status,
    'queue_position': queuePosition,
    'scheduled_time': null,
    'played_at': null,
    'duration_seconds': durationSeconds,
    'speaker_confirmed': speakerConfirmed,
    'speaker_elapsed_seconds': speakerElapsedSeconds,
    'audio_url': 'https://example.invalid/api/v1/announcements/$announcementId/audio/stream',
    'speaker_node_id': 13,
    'speaker_node_mac': 'D4:F3:2D:22:2A:CD',
    'speaker_node_name': 'ESP32 Smart Speaker & Live Display',
    'speaker_node_status': 'ONLINE',
    'speaker_node_zone': 'Main Corridor',
    'repeat_schedule': hasRepeat
        ? {'is_active': true, 'repeat_mode': 'INTERVAL', 'interval_minutes': 15, 'max_repeats': maxRepeats, 'total_played_count': totalPlayedCount}
        : null,
    'has_repeat': hasRepeat,
    'is_repeat': hasRepeat && totalPlayedCount > 0,
    'repeat_mode': hasRepeat ? 'INTERVAL' : null,
    'repeat_round': totalPlayedCount + 1,
    'current_round': totalPlayedCount,
    'max_repeats': maxRepeats,
    'interval_minutes': hasRepeat ? 15 : null,
    'next_repeat_at': null,
  };
}

final List<Map<String, dynamic>> serverSpeakerNodes = [
  {
    'id': 13,
    'name': 'ESP32 Smart Speaker & Live Display',
    'mac_address': 'D4:F3:2D:22:2A:CD',
    'zone': 'Main Corridor',
    'status': 'ONLINE',
    'volume': 80,
    'is_active': true,
  },
];
