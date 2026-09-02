import 'package:anymex/controllers/settings/settings.dart';
import 'package:get/get.dart';

extension UIMultiplierExtension on num {
  double multiplyRadius() {
    if (!Get.isRegistered<Settings>()) return toDouble();
    final settings = Get.find<Settings>();
    return toDouble() * settings.glowMultiplier.value;
  }

  double multiplyGlow() {
    if (!Get.isRegistered<Settings>()) return toDouble();
    final settings = Get.find<Settings>();
    return toDouble() * settings.glowMultiplier.value;
  }

  double multiplyRoundness() {
    if (!Get.isRegistered<Settings>()) return toDouble();
    final settings = Get.find<Settings>();
    return toDouble() * settings.glowMultiplier.value;
  }

  double multiplyBlur() {
    if (!Get.isRegistered<Settings>()) return toDouble();
    final settings = Get.find<Settings>();
    return toDouble() * settings.glowMultiplier.value;
  }
}

int getAnimationDuration() {
  return 200;
}

