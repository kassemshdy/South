import 'package:material_ui/material_ui.dart';

import '../api/models.dart';
import '../l10n/app_localizations.dart';
import '../session.dart';
import 'dashboard_screen.dart';
import 'listings_screen.dart';
import 'locale_menu.dart';
import 'tickets_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final session = SessionScope.of(context);
    final tabs = [
      (Icons.dashboard_outlined, t.adminNavDashboard, const DashboardScreen()),
      (Icons.storefront_outlined, t.adminNavBusinesses,
          const ListingsScreen(kind: ListingKind.business, key: ValueKey('b'))),
      (Icons.handyman_outlined, t.adminNavTalent,
          const ListingsScreen(kind: ListingKind.talent, key: ValueKey('t'))),
      (Icons.view_kanban_outlined, t.adminNavFeedback, const TicketsScreen()),
    ];
    return Scaffold(
      appBar: AppBar(
        title: Text(tabs[_tab].$2),
        actions: [
          const LocaleMenu(),
          IconButton(
            tooltip: t.navSignOut,
            icon: const Icon(Icons.logout),
            onPressed: session.signOut,
          ),
        ],
      ),
      body: IndexedStack(index: _tab, children: [for (final tab in tabs) tab.$3]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: [
          for (final tab in tabs) NavigationDestination(icon: Icon(tab.$1), label: tab.$2),
        ],
      ),
    );
  }
}
