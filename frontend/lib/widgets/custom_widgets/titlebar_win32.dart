import 'dart:ffi';
import 'package:ffi/ffi.dart';
import 'package:win32/win32.dart';
import 'package:anymex/widgets/custom_widgets/echosphere_titlebar.dart';

void listenToWin32Impl() {
  final hwnd = GetForegroundWindow();

  final placement = calloc<WINDOWPLACEMENT>();
  GetWindowPlacement(hwnd, placement);

  final isMaximized = placement.ref.showCmd == SW_SHOWMAXIMIZED;
  EchoSphereTitleBar.isMaximized.value = isMaximized;

  calloc.free(placement);
}
