/// Utility to intelligently detect academic department from a VTU/University USN string.
/// Format example:
/// - 1DB23CI079 -> CI -> AIML
/// - 1DB23AD012 -> AD -> AIDS
/// - 1DB23IS045 -> IS -> ISE
/// - 1DB23CS101 -> CS -> CSE
/// - 1DB23EC088 -> EC -> ECE
/// - 1DB23EE030 -> EE -> EEE
/// - 1DB23ME015 -> ME -> ME
/// - 1DB23CV022 -> CV -> CIVIL
String detectDepartmentFromUsn(String? usn) {
  if (usn == null || usn.trim().isEmpty) {
    return 'AIML';
  }

  final clean = usn.trim().toUpperCase();

  if (clean.contains('CI') || clean.contains('AI')) {
    return 'AIML';
  } else if (clean.contains('AD')) {
    return 'AIDS';
  } else if (clean.contains('IS')) {
    return 'ISE';
  } else if (clean.contains('CS')) {
    return 'CSE';
  } else if (clean.contains('EC')) {
    return 'ECE';
  } else if (clean.contains('EE')) {
    return 'EEE';
  } else if (clean.contains('ME')) {
    return 'ME';
  } else if (clean.contains('CV')) {
    return 'CIVIL';
  }

  return 'AIML';
}
