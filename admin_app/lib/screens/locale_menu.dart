import 'package:material_ui/material_ui.dart';

import '../l10n/app_localizations.dart';
import '../session.dart';

class LocaleMenu extends StatelessWidget {
  const LocaleMenu({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final session = SessionScope.of(context);
    return PopupMenuButton<String>(
      icon: const Icon(Icons.translate),
      initialValue: session.locale.languageCode,
      onSelected: session.setLocale,
      itemBuilder: (_) => [
        PopupMenuItem(value: 'ar', child: Text(t.navLocaleArabic)),
        PopupMenuItem(value: 'en', child: Text(t.navLocaleEnglish)),
      ],
    );
  }
}
