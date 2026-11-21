import 'package:flutter/widgets.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api/client.dart';
import 'api/models.dart';

/// Who is signed in, and in which language. One instance for the app,
/// reached through [SessionScope.of].
class Session extends ChangeNotifier {
  Session(this.api, {FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage() {
    api.onUnauthorized = signOut;
  }

  static const _tokenKey = 'session_token';
  static const _localeKey = 'locale';

  final ApiClient api;
  final FlutterSecureStorage _storage;

  Me? me;
  bool restoring = true;
  Locale locale = const Locale('ar');

  bool get signedIn => me != null;

  /// Reopens the last session if its token still works.
  Future<void> restore() async {
    final savedLocale = await _storage.read(key: _localeKey);
    if (savedLocale != null) _applyLocale(savedLocale);
    final token = await _storage.read(key: _tokenKey);
    if (token != null) {
      api.token = token;
      try {
        final user = await api.me();
        if (user.isAdmin) {
          me = user;
        } else {
          await _forget();
        }
      } on ApiException {
        await _forget();
      } catch (_) {
        // Offline: keep the token and try again on the next start.
        api.token = null;
      }
    }
    restoring = false;
    notifyListeners();
  }

  /// Signs in; an owner's account is refused here, with the same sentence
  /// as a wrong password, because this app is for staff only.
  Future<bool> signIn(String identifier, String password) async {
    final (token, user) = await api.login(identifier, password);
    if (!user.isAdmin) return false;
    api.token = token;
    me = user;
    await _storage.write(key: _tokenKey, value: token);
    notifyListeners();
    return true;
  }

  Future<void> signOut() async {
    me = null;
    await _forget();
    notifyListeners();
  }

  Future<void> _forget() async {
    api.token = null;
    await _storage.delete(key: _tokenKey);
  }

  void _applyLocale(String code) {
    locale = Locale(code);
    api.locale = code;
  }

  Future<void> setLocale(String code) async {
    _applyLocale(code);
    await _storage.write(key: _localeKey, value: code);
    notifyListeners();
  }
}

class SessionScope extends InheritedNotifier<Session> {
  const SessionScope({super.key, required Session session, required super.child})
      : super(notifier: session);

  static Session of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<SessionScope>()!.notifier!;
}
