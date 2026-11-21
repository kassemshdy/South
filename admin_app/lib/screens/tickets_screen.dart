import 'package:material_ui/material_ui.dart';

import '../api/models.dart';
import '../l10n/app_localizations.dart';
import '../session.dart';
import '../widgets/common.dart';
import 'ticket_detail_screen.dart';

/// The support board, one column at a time: a phone has no room for seven
/// columns side by side, so the column is a chip and the cards are a list.
class TicketsScreen extends StatefulWidget {
  const TicketsScreen({super.key});

  @override
  State<TicketsScreen> createState() => _TicketsScreenState();
}

class _TicketsScreenState extends State<TicketsScreen> {
  String _status = 'TODO';
  String _query = '';

  Future<List<TicketSummary>> _fetch() => SessionScope.of(context).api.tickets();

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return AsyncView<List<TicketSummary>>(
      load: _fetch,
      builder: (context, tickets, reload) {
        final counts = <String, int>{};
        for (final ticket in tickets) {
          counts[ticket.status] = (counts[ticket.status] ?? 0) + 1;
        }
        final shown = tickets
            .where((x) => x.status == _status)
            .where((x) => _query.isEmpty || x.title.toLowerCase().contains(_query))
            .toList();
        return Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: TextField(
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                hintText: t.feedbackBoardSearch,
                border: const OutlineInputBorder(),
                isDense: true,
              ),
              onChanged: (v) => setState(() => _query = v.trim().toLowerCase()),
            ),
          ),
          SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                for (final status in ticketStatuses)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: ChoiceChip(
                      label: Text('${ticketStatusLabel(t, status)} (${counts[status] ?? 0})'),
                      selected: _status == status,
                      onSelected: (_) => setState(() => _status = status),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () async => reload(),
              child: shown.isEmpty
                  ? ListView(children: [
                      const SizedBox(height: 80),
                      EmptyState(title: t.feedbackBoardTotal('0')),
                    ])
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      itemCount: shown.length,
                      itemBuilder: (context, i) => _TicketCard(
                        ticket: shown[i],
                        onChanged: reload,
                      ),
                    ),
            ),
          ),
        ]);
      },
    );
  }
}

class _TicketCard extends StatelessWidget {
  const _TicketCard({required this.ticket, required this.onChanged});

  final TicketSummary ticket;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final urgent = ticket.priority == 'URGENT' || ticket.priority == 'HIGH';
    return Card(
      child: ListTile(
        title: Text(ticket.title, maxLines: 2, overflow: TextOverflow.ellipsis),
        subtitle: Text([
          priorityLabel(t, ticket.priority),
          ticket.assignee ?? t.feedbackUnassigned,
        ].join(' · ')),
        leading: Icon(
          urgent ? Icons.priority_high : Icons.confirmation_number_outlined,
          color: urgent ? Theme.of(context).colorScheme.error : null,
        ),
        trailing: ticket.commentCount > 0
            ? Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.chat_bubble_outline, size: 16),
                const SizedBox(width: 4),
                Text('${ticket.commentCount}'),
              ])
            : null,
        onTap: () async {
          final changed = await Navigator.of(context).push<bool>(
            MaterialPageRoute(builder: (_) => TicketDetailScreen(id: ticket.id)),
          );
          if (changed == true) onChanged();
        },
      ),
    );
  }
}
