import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:echosphere/controllers/auth_controller.dart';
import 'package:echosphere/controllers/echosphere_ai_controller.dart';
import 'package:echosphere/controllers/settings/settings.dart';

/// When the server can't be reached the chatbot must not make up campus facts (it used to answer with a
/// 9:00 PM hostel curfew, "CGPA >= 7.0" and a list of recruiters that came from no notice).
void main() {
  late EchosphereAiController ai;

  setUp(() {
    Get.reset();
    Get.testMode = true; // network calls fail in test mode, like an unreachable server
    SharedPreferences.setMockInitialValues({});
    Get.put(Settings());
    final auth = Get.put(AuthController());
    auth.currentUser.value = EchosphereUser(
      id: 7, fullName: 'Asha K', officialEmail: 'asha@echosphere.edu', role: 'Student', department: 'CSE');
    ai = Get.put(EchosphereAiController());
  });

  tearDown(Get.reset);

  Future<String> ask(String q) async {
    await ai.sendQuery(q);
    return ai.messages.last.text;
  }

  test('campus questions get an honest "cannot reach notices" answer offline', () async {
    final invented = ['9:00 PM', '9:30 PM', 'CGPA', 'Google', 'Microsoft', 'TCS', 'Infosys', '15 minutes', '7:30'];
    for (final q in [
      'What is the hostel curfew time?',
      'Which companies come for placements?',
      'When are the mid-sem exams?',
      'What are the library timings?',
    ]) {
      final answer = await ask(q);
      for (final fact in invented) {
        expect(answer, isNot(contains(fact)), reason: '$q -> $answer');
      }
      expect(answer.toLowerCase(), contains("can't reach the campus notices"), reason: q);
    }
  });

  test('greetings and app help still work offline', () async {
    expect(await ask('hi'), contains('Asha'));
    expect((await ask('how do I switch to dark mode?')).toLowerCase(), contains('dark'));
  });
}
