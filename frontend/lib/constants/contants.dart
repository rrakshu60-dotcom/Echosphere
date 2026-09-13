import 'package:flutter/material.dart';

Map<String, Color> colorMap = {
  "Violet": const Color(0xFF6B26D9),
  "ElectricViolet": const Color(0xFF945AF2),
  "LightViolet": const Color(0xFFC084FC),
  "PastelViolet": const Color(0xFFD1B8F9),
  "DeepViolet": const Color(0xFF401782),
  "DarkViolet": const Color(0xFF231736),
  "Plum": const Color(0xFF7C1E55),
};
List<Color> colorList = colorMap.values.toList();
List<String> colorKeys = colorMap.keys.toList();

Map<String, BoxFit> resizeModes = {
  for (var e in BoxFit.values)
    if (e != BoxFit.none)
      capitalize(e.name) +
          (e == BoxFit.contain ? ' (default)' : '') +
          (e == BoxFit.fill ? ' (Stretch) ' : ''): e,
};
List<String> resizeModeList = resizeModes.keys.toList()..sort();

Map<String, DynamicSchemeVariant> dynamicSchemeVariantMap = {
  for (var variant in DynamicSchemeVariant.values)
    capitalize(variant.name): variant,
};

List<DynamicSchemeVariant> dynamicSchemeVariantList =
    dynamicSchemeVariantMap.values.toList();
List<String> dynamicSchemeVariantKeys = dynamicSchemeVariantMap.keys.toList();

String capitalize(String word) {
  String firstLetter = (word[0]).toUpperCase();
  String truncatedWord = firstLetter + word.substring(1, word.length);
  return truncatedWord;
}

const maxMobileWidth = 600;

final Map<String, Color> colorOptions = {
  'None': Colors.transparent,
  'White': Colors.white,
  'Black': Colors.black,
  'Violet': const Color(0xFF6B26D9),
  'ElectricViolet': const Color(0xFF945AF2),
  'PastelViolet': const Color(0xFFD1B8F9),
};

final Map<String, Color> fontColorOptions = {
  'Default': Colors.white70,
  'White': Colors.white,
  'Black': Colors.black,
  'Violet': const Color(0xFF6B26D9),
  'ElectricViolet': const Color(0xFF945AF2),
  'PastelViolet': const Color(0xFFD1B8F9),
};

final cursedSpeed = [
  0.25,
  0.50,
  0.75,
  1.00,
  1.25,
  1.50,
  1.75,
  2.00,
  3.00,
  5.00,
  10.00,
  ...[25.0, 50.0, 75.0, 100.0],
];

final List<String> extensions = [
  'srt',
  'vtt',
  'ssa',
  'ass',
  'sub',
  'idx',
  'txt',
  'dfxp',
  'ttml',
  'lrc',
  'stl',
  'sbv',
  'xml',
  'cap',
  'mks',
  'sup',
];
