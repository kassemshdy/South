import 'package:material_ui/material_ui.dart';

import '../api/models.dart';
import '../l10n/app_localizations.dart';
import '../permissions.dart';
import '../session.dart';
import '../widgets/common.dart';

class TicketDetailScreen extends StatefulWidget {
  const TicketDetailScreen({super.key, required this.id});

  final String id;

  @override
  State<TicketDetailScreen> createState() => _TicketDetailScreenState();
}

class _TicketDetailScreenState extends State<TicketDetailScreen> {
  TicketDetail? _ticket;
  Object? _error;
  bool _busy = false;
  bool _changed = false;
  final _comment = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final ticket = await SessionScope.of(context).api.ticket(widget.id);
      if (mounted) setState(() => _ticket = ticket);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  Future<void> _move(String status) async {
    final t = AppLocalizations.of(context);
    setState(() => _busy = true);
    try {
      final api = SessionScope.of(context).api;
      await api.moveTicket(widget.id, status);
      final ticket = await api.ticket(widget.id);
      if (!mounted) return;
      setState(() {
        _ticket = ticket;
        _changed = true;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t.feedbackMoveFailed)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addComment() async {
    final body = _comment.text.trim();
    if (body.isEmpty) return;
    setState(() => _busy = true);
    try {
      final ticket = await SessionScope.of(context).api.comment(widget.id, body);
      if (!mounted) return;
      _comment.clear();
      setState(() {
        _ticket = ticket;
        _changed = true;
      });
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final ticket = _ticket;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) Navigator.of(context).pop(_changed);
      },
      child: Scaffold(
        appBar: AppBar(title: Text(t.feedbackTicketDetails)),
        body: _error != null
            ? ErrorState(error: _error, onRetry: _load)
            : ticket == null
                ? const Center(child: CircularProgressIndicator())
                : _body(context, t, ticket),
      ),
    );
  }

  Widget _body(BuildContext context, AppLocalizations t, TicketDetail ticket) {
    final text = Theme.of(context).textTheme;
    final canWrite = staffCan(SessionScope.of(context).me?.staffRole, StaffAction.support);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Text(ticket.title, style: text.titleLarge),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          key: ValueKey(ticket.status),
          initialValue: ticket.status,
          decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
          items: [
            for (final status in ticketStatuses)
              DropdownMenuItem(value: status, child: Text(ticketStatusLabel(t, status))),
          ],
          onChanged: !canWrite || _busy
              ? null
              : (status) {
                  if (status != null && status != ticket.status) _move(status);
                },
        ),
        const SizedBox(height: 12),
        Wrap(spacing: 16, runSpacing: 4, children: [
          Text('${t.feedbackPriorityLabel}: ${priorityLabel(t, ticket.priority)}'),
          Text('${t.feedbackAssigneeLabel}: ${ticket.assignee ?? t.feedbackUnassigned}'),
        ]),
        if (ticket.reporterName != null || ticket.reporterPhone != null) ...[
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              child: Text(
                '${t.feedbackSentBy}: ${[ticket.reporterName, ticket.reporterPhone].whereType<String>().join(' · ')}',
              ),
            ),
            if (ticket.reporterPhone != null)
              IconButton(
                icon: const Icon(Icons.call_outlined),
                tooltip: t.adminShopsCall,
                onPressed: () => callNumber(ticket.reporterPhone!),
              ),
          ]),
        ],
        if (ticket.pagePath != null)
          Text('${t.feedbackReportedFrom}: ${ticket.pagePath}', style: text.bodySmall),
        const Divider(height: 32),
        Text(t.feedbackDescriptionLabel, style: text.titleMedium),
        const SizedBox(height: 4),
        SelectableText(ticket.description ?? t.commonNotSet),
        const Divider(height: 32),
        Text(t.feedbackCommentsLabel, style: text.titleMedium),
        if (ticket.comments.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(t.feedbackNoComments),
          ),
        for (final c in ticket.comments)
          Card(
            child: ListTile(
              title: SelectableText(c.body),
              subtitle: Text([c.author, formatDate(context, c.createdAt)]
                  .whereType<String>()
                  .join(' · ')),
            ),
          ),
        if (canWrite) ...[
          const SizedBox(height: 12),
          TextField(
            controller: _comment,
            minLines: 2,
            maxLines: 6,
            maxLength: 4000,
            decoration: InputDecoration(
              labelText: t.feedbackAddCommentLabel,
              hintText: t.feedbackAddCommentPlaceholder,
              border: const OutlineInputBorder(),
            ),
          ),
          Align(
            alignment: AlignmentDirectional.centerEnd,
            child: FilledButton(
              onPressed: _busy ? null : _addComment,
              child: Text(t.feedbackAddCommentAction),
            ),
          ),
        ],
      ]),
    );
  }
}
