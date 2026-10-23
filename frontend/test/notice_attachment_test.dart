import 'package:flutter_test/flutter_test.dart';
import 'package:echosphere/controllers/announcement_controller.dart';

void main() {
  test('attachments are read with their cloud link; old name-only entries have no link', () {
    final a = NoticeAttachment.fromJson({'name': 'circular.pdf', 'url': 'https://cdn.example/circular.pdf', 'size': 1200, 'mime': 'application/pdf'});
    expect(a.name, 'circular.pdf');
    expect(a.url, 'https://cdn.example/circular.pdf');
    expect(a.isUploaded, isTrue);
    final old = NoticeAttachment.fromJson('scan.jpg');
    expect(old.name, 'scan.jpg');
    expect(old.isUploaded, isFalse);
  });

  test('a notice keeps its attachments through JSON', () {
    final n = AnnouncementModel.fromJson({
      'id': 1, 'title': 'T', 'description': 'D', 'priority': 'NORMAL', 'status': 'PUBLISHED',
      'created_at': '2026-10-23T04:00:00',
      'attachments': [
        {'name': 'circular.pdf', 'url': 'https://cdn.example/circular.pdf', 'size': 1200, 'mime': 'application/pdf'}
      ],
    });
    expect(n.attachments.single.url, 'https://cdn.example/circular.pdf');
    final again = AnnouncementModel.fromJson(n.toJson());
    expect(again.attachments.single.name, 'circular.pdf');
    expect(again.attachments.single.url, 'https://cdn.example/circular.pdf');
  });
}
