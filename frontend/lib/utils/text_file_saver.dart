import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

/// Saves a .txt file on every platform: a "Save as" dialog on desktop, the share sheet on
/// Android/iOS (save to Files, Drive, email...), and a download/share on the web.
/// Returns false if the user cancelled or saving failed.
Future<bool> saveTextFile(String fileName, String content) async {
  final bytes = Uint8List.fromList(utf8.encode(content));
  try {
    if (kIsWeb) {
      await SharePlus.instance.share(ShareParams(files: [XFile.fromData(bytes, mimeType: 'text/plain', name: fileName)]));
      return true;
    }
    if (Platform.isWindows || Platform.isMacOS || Platform.isLinux) {
      final path = await FilePicker.platform.saveFile(
        dialogTitle: 'Save log',
        fileName: fileName,
        type: FileType.custom,
        allowedExtensions: ['txt'],
      );
      if (path == null) return false;
      await File(path).writeAsBytes(bytes);
      return true;
    }
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/$fileName');
    await file.writeAsBytes(bytes);
    await SharePlus.instance.share(ShareParams(files: [XFile(file.path, mimeType: 'text/plain')]));
    return true;
  } catch (e) {
    debugPrint('Saving $fileName failed: $e');
    return false;
  }
}
