import 'package:flutter/foundation.dart';
import 'package:package_info_plus/package_info_plus.dart';

/// Which app this is, as the backend's sign-in and access logs record it.
String clientPlatform() {
  if (kIsWeb) return 'web';
  switch (defaultTargetPlatform) {
    case TargetPlatform.android:
      return 'android';
    case TargetPlatform.iOS:
      return 'ios';
    case TargetPlatform.windows:
      return 'windows';
    case TargetPlatform.macOS:
      return 'macos';
    case TargetPlatform.linux:
      return 'linux';
    case TargetPlatform.fuchsia:
      return 'other';
  }
}

String? _version;

/// The installed app version, e.g. "1.1.0+2". Null if it cannot be read.
Future<String?> clientAppVersion() async {
  if (_version != null) return _version;
  try {
    final info = await PackageInfo.fromPlatform();
    _version = '${info.version}+${info.buildNumber}';
  } catch (_) {}
  return _version;
}
