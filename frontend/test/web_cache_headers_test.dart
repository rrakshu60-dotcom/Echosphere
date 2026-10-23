import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Flutter's web build rewrites assets such as the icon font on every deploy (only the icons in use are
/// kept) but keeps the same file names. If browsers cache them without re-checking, new code is paired
/// with an old font and newly used icons render blank until the cache expires.
void main() {
  test('web assets are re-checked on every load, never served stale', () {
    final rules = _parseHeaders(File('web/_headers').readAsStringSync());
    final assets = rules['/assets/*'];
    expect(assets, isNotNull, reason: 'web/_headers must set Cache-Control for /assets/*');
    final cache = assets!['cache-control']!.toLowerCase();
    expect(cache.contains('no-cache') || RegExp(r'max-age=0\b').hasMatch(cache), isTrue,
        reason: '/assets/* is cached without revalidation: "$cache"');
  });
}

Map<String, Map<String, String>> _parseHeaders(String text) {
  final rules = <String, Map<String, String>>{};
  String? path;
  for (final line in text.split(RegExp(r'\r?\n'))) {
    if (line.trim().isEmpty) continue;
    if (!line.startsWith(' ') && !line.startsWith('\t')) {
      path = line.trim();
      rules[path] = {};
    } else if (path != null && line.contains(':')) {
      final i = line.indexOf(':');
      rules[path]![line.substring(0, i).trim().toLowerCase()] = line.substring(i + 1).trim();
    }
  }
  return rules;
}
