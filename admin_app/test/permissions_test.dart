import 'package:flutter_test/flutter_test.dart';
import 'package:janoubona_admin/permissions.dart';

void main() {
  test('moderation is the manager and reviewers only, as on the server', () {
    expect(staffCan('MANAGER', StaffAction.moderate), isTrue);
    expect(staffCan('REVIEWER', StaffAction.moderate), isTrue);
    for (final role in ['SUPPORT', 'EDITOR', 'ACTIVITIES', 'REELS', 'VIEWER']) {
      expect(staffCan(role, StaffAction.moderate), isFalse, reason: role);
    }
  });

  test('the ticket board is written by the manager and support', () {
    expect(staffCan('MANAGER', StaffAction.support), isTrue);
    expect(staffCan('SUPPORT', StaffAction.support), isTrue);
    expect(staffCan('REVIEWER', StaffAction.support), isFalse);
  });

  test('an administrator with no role recorded is a viewer', () {
    expect(staffCan(null, StaffAction.moderate), isFalse);
    expect(staffCan(null, StaffAction.support), isFalse);
  });
}
