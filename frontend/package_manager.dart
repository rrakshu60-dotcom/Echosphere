#!/usr/bin/env dart
// ignore_for_file: avoid_print

import 'dart:io';
import 'dart:convert';

class AppNamePackageManager {
  static const String configBackupPath = 'app_config_backup.json';
  static const String basePackageName = 'com.roxy.echosphere';
  static const String baseAppName = 'EchoSphere';

  void run() async {
    try {
      print('🚀 EchoSphere App Name & Package Manager\n');

      final currentConfig = await getCurrentConfig();

      print('📋 Current Status:');
      print('   App Name: ${currentConfig['appName']}');
      print('   Package Name: ${currentConfig['packageName']}\n');

      print('🔧 What would you like to do?');
      print('   1. Switch to Alpha ($baseAppName α, $basePackageName.alpha)');
      print('   2. Switch to Beta ($baseAppName β, $basePackageName.beta)');
      print('   3. Switch to Production ($baseAppName, $basePackageName)');
      print('   4. Custom configuration');
      print('   5. Revert to saved production config');
      print('   6. Show current backup');
      print('   7. Exit\n');

      stdout.write('Enter your choice (1-7): ');
      final choice = stdin.readLineSync()?.trim();

      String? newAppName;
      String? newPackageName;

      switch (choice) {
        case '1':
          newAppName = '$baseAppName ALpha';
          newPackageName = '$basePackageName.alpha';
          break;
        case '2':
          newAppName = '$baseAppName Beta';
          newPackageName = '$basePackageName.beta';
          break;
        case '3':
          newAppName = baseAppName;
          newPackageName = basePackageName;
          break;
        case '4':
          final customConfig = await getCustomConfiguration();
          if (customConfig == null) return;
          newAppName = customConfig['appName'];
          newPackageName = customConfig['packageName'];
          break;
        case '5':
          await revertToProductionConfig();
          return;
        case '6':
          await showCurrentBackup();
          return;
        case '7':
          print('👋 Goodbye!');
          return;
        default:
          print('❌ Invalid choice');
          return;
      }

      if (newAppName == null || newPackageName == null) return;

      // Save current config as backup if it's the production version
      if (currentConfig['packageName'] == basePackageName) {
        await saveProductionConfig(currentConfig);
      }

      print('\n📝 Proposed Changes:');
      print('   Current App Name: ${currentConfig['appName']}');
      print('   New App Name: $newAppName');
      print('   Current Package: ${currentConfig['packageName']}');
      print('   New Package: $newPackageName');

      stdout.write('\n✅ Proceed with this update? (y/N): ');
      final confirm = stdin.readLineSync()?.trim().toLowerCase();

      if (confirm != 'y' && confirm != 'yes') {
        print('❌ Update cancelled');
        return;
      }

      await updateAppConfiguration(newAppName, newPackageName);

      print('\n🎉 App configuration updated successfully!');
      print('📝 Remember to run: dart pub get');

      if (newPackageName != basePackageName) {
        print(
            '💡 Your production config has been backed up and can be restored with option 5');
      }
    } catch (e) {
      print('❌ Error: $e');
    }
  }

  Future<Map<String, String>> getCurrentConfig() async {
    try {
      String appName = baseAppName;
      String packageName = basePackageName;

      // Get app name from Android manifest
      const androidManifestPath = 'android/app/src/main/AndroidManifest.xml';
      if (await File(androidManifestPath).exists()) {
        final manifestContent = await File(androidManifestPath).readAsString();

        // Extract package name from manifest
        final packageMatch =
            RegExp(r'package="([^"]+)"').firstMatch(manifestContent);
        if (packageMatch != null) {
          packageName = packageMatch.group(1)!;
        }

        // Extract app name from application label
        final labelMatch =
            RegExp(r'android:label="([^"]+)"').firstMatch(manifestContent);
        if (labelMatch != null) {
          appName = labelMatch.group(1)!;
        }
      }

      // Fallback: try to get app name from strings.xml
      const stringsPath = 'android/app/src/main/res/values/strings.xml';
      if (await File(stringsPath).exists()) {
        final stringsContent = await File(stringsPath).readAsString();
        final appNameMatch = RegExp(r'<string name="app_name">([^<]+)</string>')
            .firstMatch(stringsContent);
        if (appNameMatch != null) {
          appName = appNameMatch.group(1)!;
        }
      }

      // Alternative fallback: check iOS Info.plist for app name
      const infoPlistPath = 'ios/Runner/Info.plist';
      if (await File(infoPlistPath).exists()) {
        final plistContent = await File(infoPlistPath).readAsString();

        // Look for CFBundleDisplayName or CFBundleName
        final displayNameMatch =
            RegExp(r'<key>CFBundleDisplayName</key>\s*<string>([^<]+)</string>')
                .firstMatch(plistContent);
        if (displayNameMatch != null) {
          appName = displayNameMatch.group(1)!;
        } else {
          final bundleNameMatch =
              RegExp(r'<key>CFBundleName</key>\s*<string>([^<]+)</string>')
                  .firstMatch(plistContent);
          if (bundleNameMatch != null) {
            appName = bundleNameMatch.group(1)!;
          }
        }

        // Get bundle identifier (iOS package name equivalent)
        final bundleIdMatch =
            RegExp(r'<key>CFBundleIdentifier</key>\s*<string>([^<]+)</string>')
                .firstMatch(plistContent);
        if (bundleIdMatch != null) {
          // Use iOS bundle ID if it's different from Android package name
          // This helps verify consistency across platforms
          final iosBundleId = bundleIdMatch.group(1)!;
          if (iosBundleId != packageName) {
            print(
                '⚠️  Warning: iOS bundle ID ($iosBundleId) differs from Android package name ($packageName)');
          }
        }
      }

      return {
        'appName': appName,
        'packageName': packageName,
      };
    } catch (e) {
      print('⚠️  Warning: Could not read current config, using defaults: $e');
      return {
        'appName': baseAppName,
        'packageName': basePackageName,
      };
    }
  }

  Future<Map<String, String>?> getCustomConfiguration() async {
    stdout.write('\n📝 Enter custom app name: ');
    final appName = stdin.readLineSync()?.trim();

    stdout
        .write('📝 Enter custom package name (e.g., com.ryan.echosphere.custom): ');
    final packageName = stdin.readLineSync()?.trim();

    if (appName == null ||
        appName.isEmpty ||
        packageName == null ||
        packageName.isEmpty) {
      print('❌ Invalid configuration');
      return null;
    }

    if (!RegExp(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$')
        .hasMatch(packageName)) {
      print('❌ Invalid package name format');
      return null;
    }

    return {
      'appName': appName,
      'packageName': packageName,
    };
  }

  Future<void> saveProductionConfig(Map<String, String> config) async {
    try {
      final backupData = {
        'appName': config['appName'],
        'packageName': config['packageName'],
        'timestamp': DateTime.now().toIso8601String(),
      };

      await File(configBackupPath).writeAsString(
          const JsonEncoder.withIndent('  ').convert(backupData));
      print('💾 Production config backed up');
    } catch (e) {
      print('⚠️  Warning: Could not backup production config: $e');
    }
  }

  Future<void> revertToProductionConfig() async {
    try {
      if (!await File(configBackupPath).exists()) {
        print('❌ No production config backup found');
        return;
      }

      final backupContent = await File(configBackupPath).readAsString();
      final backupData = jsonDecode(backupContent) as Map<String, dynamic>;

      print('📋 Backup found:');
      print('   App Name: ${backupData['appName']}');
      print('   Package Name: ${backupData['packageName']}');
      print('   Saved: ${backupData['timestamp']}');

      stdout.write('\n✅ Restore this configuration? (y/N): ');
      final confirm = stdin.readLineSync()?.trim().toLowerCase();

      if (confirm != 'y' && confirm != 'yes') {
        print('❌ Restore cancelled');
        return;
      }

      await updateAppConfiguration(
        backupData['appName'] as String,
        backupData['packageName'] as String,
      );

      print('\n🎉 Configuration restored successfully!');
    } catch (e) {
      print('❌ Failed to revert configuration: $e');
    }
  }

  Future<void> showCurrentBackup() async {
    try {
      if (!await File(configBackupPath).exists()) {
        print('📋 No production config backup found');
        return;
      }

      final backupContent = await File(configBackupPath).readAsString();
      final backupData = jsonDecode(backupContent) as Map<String, dynamic>;

      print('📋 Current Backup:');
      print('   App Name: ${backupData['appName']}');
      print('   Package Name: ${backupData['packageName']}');
      print('   Saved: ${backupData['timestamp']}');
    } catch (e) {
      print('❌ Failed to read backup: $e');
    }
  }

  Future<void> updateAppConfiguration(
      String appName, String packageName) async {
    await changePackageName(packageName);
    await changeAppName(appName);
    print('✅ App configuration updated');
  }

  Future<void> changePackageName(String packageName) async {
    try {
      print('🔄 Changing package name...');

      final result = await Process.run(
        'dart',
        ['run', 'change_app_package_name:main', packageName],
        runInShell: true,
      );

      if (result.exitCode == 0) {
        print('✅ Package name changed successfully');
        if (result.stdout.toString().isNotEmpty) {
          print('📝 Output: ${result.stdout}');
        }
      } else {
        print('❌ Package name change failed: ${result.stderr}');
        if (result.stdout.toString().isNotEmpty) {
          print('📝 Output: ${result.stdout}');
        }
      }
    } catch (e) {
      print('❌ Failed to change package name: $e');
      print(
          '💡 Make sure change_app_package_name package is added to dev_dependencies');
    }
  }

  Future<void> changeAppName(String appName) async {
    try {
      print('🔄 Changing app name...');

      final result = await Process.run(
        'dart',
        ['run', 'rename_app:main', 'all="$appName"'],
        runInShell: true,
      );

      if (result.exitCode == 0) {
        print('✅ App name changed successfully');
        if (result.stdout.toString().isNotEmpty) {
          print('📝 Output: ${result.stdout}');
        }
      } else {
        print('❌ App name change failed: ${result.stderr}');
        if (result.stdout.toString().isNotEmpty) {
          print('📝 Output: ${result.stdout}');
        }
      }
    } catch (e) {
      print('❌ Failed to change app name: $e');
      print('💡 Make sure rename_app package is added to dev_dependencies');
    }
  }
}

void main() {
  final manager = AppNamePackageManager();
  manager.run();
}
