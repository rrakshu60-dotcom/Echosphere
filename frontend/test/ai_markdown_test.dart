import 'package:flutter_test/flutter_test.dart';
import 'package:anymex/controllers/echosphere_ai_controller.dart';

void main() {
  test('EchosphereAiController.sanitizeClientMarkdown eliminates raw formatting artifacts', () {
    final controller = EchosphereAiController();

    // 1. Dollar-prefixed headings
    const rawHeading = '##\$Academics\nExamination Circular';
    final cleanH = controller.sanitizeClientMarkdown(rawHeading);
    expect(cleanH, contains('## Academics'));
    expect(cleanH, isNot(contains('##\$')));

    // 2. Raw dividers & asterisk clutter
    const rawDividers = 'Heading\n---\n***\n****Bold Clutter****\n___';
    final cleanD = controller.sanitizeClientMarkdown(rawDividers);
    expect(cleanD, isNot(contains('---')));
    expect(cleanD, isNot(contains('***')));
    expect(cleanD, contains('**Bold Clutter**'));

    // 3. Bullet list spacing and space after bold colons
    const rawBullets = 'Guidelines:\n- **Item 1:**A requirement\n- **Item 2:** Another';
    final cleanB = controller.sanitizeClientMarkdown(rawBullets);
    expect(cleanB, contains('Guidelines:\n\n- **Item 1:** A requirement'));
    expect(cleanB, contains('- **Item 2:** Another'));

    // 4. Action tags stripped from user bubble
    const rawAction = 'Directing you now.\n\n[[ACTION:navigate:{"screen":"notices"}]]';
    final cleanA = controller.sanitizeClientMarkdown(rawAction);
    expect(cleanA, equals('Directing you now.'));
    expect(cleanA, isNot(contains('[[ACTION:')));
  });
}
