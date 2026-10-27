import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/echosphere_ai_controller.dart';
import 'package:echosphere/controllers/settings/settings.dart';

/// The create-notice dialog guesses priority and category while staff type. It used to match parts of
/// words, so "training" (contains "rain") and "closed" made a notice an emergency, and a fire or a gas
/// leak was not one.
void main() {
  late EchosphereAiController ai;

  setUp(() {
    Get.reset();
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    Get.put(Settings());
    Get.put(AuthController());
    ai = Get.put(EchosphereAiController());
  });

  tearDown(Get.reset);

  Map<String, String> guess(String title, String body, {String role = 'HOD'}) =>
      ai.recommendPriorityAndCategory(title, body, userRole: role);

  test('real emergencies are flagged', () {
    for (final text in [
      'Fire in Block B, evacuate the building now',
      'Gas leak near the chemistry lab, leave the area immediately',
      'Earthquake tremors felt, assemble on the main ground',
      'College closed today due to heavy rain red alert',
      'Medical emergency in the library, ambulance on the way',
    ]) {
      final rec = guess('Alert', text);
      expect(rec['category'], 'Emergency', reason: text);
      expect(rec['priority'], 'EMERGENCY', reason: text);
    }
  });

  test('ordinary notices are not emergencies', () {
    for (final text in [
      'Placement training session on Monday in Seminar Hall',
      'Fire safety awareness workshop next Friday',
      'Mock fire drill scheduled for 25 November at 11 AM',
      'Latest brain-teaser contest results are out',
      'Cultural fest registrations are closed',
      'Library will remain closed on Sunday for maintenance',
    ]) {
      expect(guess('Notice', text)['category'], isNot('Emergency'), reason: text);
    }
  });

  test('only HoDs and admins get EMERGENCY; a teacher gets HIGH for the same text', () {
    final rec = guess('Alert', 'Fire in Block B, evacuate now', role: 'Teacher');
    expect(rec['category'], 'Emergency');
    expect(rec['priority'], 'HIGH');
  });

  test('"latest" is not an exam and "foundation" is not lost-and-found', () {
    expect(guess('Update', 'Latest results of the coding contest')['category'], isNot('Examinations'));
    expect(guess('Foundation day', 'Foundation day celebrations in the auditorium')['category'], isNot('General'));
  });
}
