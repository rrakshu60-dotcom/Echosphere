import 'package:echosphere/controllers/announcement_controller.dart';
import 'package:echosphere/widgets/non_widgets/snackbar.dart';
import 'package:url_launcher/url_launcher.dart';

/// Opens a notice attachment (the uploaded file) in the browser or the device's viewer.
Future<void> openNoticeAttachment(NoticeAttachment file) async {
  if (!file.isUploaded) {
    errorSnackBar('"${file.name}" was never uploaded, so it can\'t be opened.');
    return;
  }
  final ok = await launchUrl(Uri.parse(file.url), mode: LaunchMode.externalApplication);
  if (!ok) errorSnackBar('Could not open "${file.name}".');
}
