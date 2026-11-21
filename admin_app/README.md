# Janoubona Admin (Flutter)

The staff app for Janoubona, for Android and iOS: the review queue, the shop
and services-profile lists, and the support ticket board, on a phone. It is a
client of the same API the web admin uses (`/api/auth/login`, `/api/admin/*`),
so every rule in `backend/app/core/permissions.py` applies to it unchanged.

## What it does

| Tab | What a staff member can do |
|---|---|
| Dashboard | The platform's counts, and everything awaiting review (shops and profiles together, newest first) |
| Businesses / Talent | Filter by status, search, open one; **approve**, **reject** (with a reason), **suspend**, **reactivate** |
| Feedback | The ticket board one column at a time; open a ticket, move it to another column, add a comment, call the reporter |

Buttons a staff role cannot use are hidden (`lib/permissions.dart`, a mirror
of `frontend/src/features/admin/staffAccess.ts`); the API refuses them
regardless. Only an `ADMIN` account can sign in: an owner's phone and
password get the same "could not sign you in" as a wrong password.

Not in the app, on purpose for a first version: ID scans, CVs and business
papers, the owner's identity card, issuing passwords, view-as, deleting
anything, and every editorial and settings page. They stay on the web admin.

## Run it

```bash
cd admin_app
flutter pub get
flutter run                                   # talks to https://janoubona.net
flutter run --dart-define=API_BASE_URL=https://api-develop-develop-5e32.up.railway.app
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000   # local API from the Android emulator
```

Release builds: `flutter build apk --release` / `flutter build ipa`. Signing
keys and store listings are not set up in this repository.

## Strings

The app has **no copy of its own**. Every string is a key from the web
catalogs (`frontend/src/i18n/locales/{ar,en}.json`), copied into
`lib/l10n/app_{ar,en}.arb` by:

```bash
python3 admin_app/tool/sync_strings.py
```

To use another string, add its web key to `KEYS` in that script and re-run
it. `backend/tests/test_i18n.py` fails when the ARB files and the web
catalogs disagree, and when a `.dart` file outside `lib/l10n/` contains
Arabic.

## Security notes

- The session token is kept in the Keychain / Android Keystore
  (`flutter_secure_storage`), never in plain preferences, and dropped on any
  401.
- The app sends nothing anywhere but the API. Calling a number opens the
  phone's dialler.

## Checks

```bash
flutter analyze
flutter test
```
