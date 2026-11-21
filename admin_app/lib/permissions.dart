/// What a staff role may do, mirroring `backend/app/core/permissions.py`
/// and `frontend/src/features/admin/staffAccess.ts`.
///
/// Only for what the app *shows*: a button the person cannot use is hidden
/// rather than left to fail. The API enforces the same table whatever this
/// says, so a mismatch costs a 403, never access.
enum StaffAction { moderate, support }

const Map<StaffAction, Set<String>> _allowed = {
  StaffAction.moderate: {'MANAGER', 'REVIEWER'},
  StaffAction.support: {'MANAGER', 'SUPPORT'},
};

bool staffCan(String? role, StaffAction action) =>
    // An administrator with no role recorded is a viewer, as on the server.
    _allowed[action]!.contains(role ?? 'VIEWER');
