import 'package:material_ui/material_ui.dart';
import 'package:flutter_localizations/flutter_localizations.dart' show GlobalWidgetsLocalizations;

import 'api/client.dart';
import 'l10n/app_localizations.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'session.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final session = Session(ApiClient())..restore();
  runApp(SessionScope(session: session, child: const JanoubonaAdminApp()));
}

class JanoubonaAdminApp extends StatelessWidget {
  const JanoubonaAdminApp({super.key});

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    return MaterialApp(
      onGenerateTitle: (context) => AppLocalizations.of(context).navAdminPanel,
      debugShowCheckedModeBanner: false,
      locale: session.locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ],
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF1F6F50),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: const Color(0xFF1F6F50),
        brightness: Brightness.dark,
        useMaterial3: true,
      ),
      home: session.restoring
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : session.signedIn
              ? const HomeScreen()
              : const LoginScreen(),
    );
  }
}
