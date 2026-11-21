import 'package:material_ui/material_ui.dart';

import '../api/models.dart';
import '../config.dart';
import '../l10n/app_localizations.dart';
import '../permissions.dart';
import '../session.dart';
import '../widgets/common.dart';

/// One shop or services profile, as a reviewer reads it, with the
/// moderation actions its status allows.
class ListingDetailScreen extends StatefulWidget {
  const ListingDetailScreen({super.key, required this.kind, required this.id});

  final ListingKind kind;
  final String id;

  @override
  State<ListingDetailScreen> createState() => _ListingDetailScreenState();
}

class _ListingDetailScreenState extends State<ListingDetailScreen> {
  Listing? _listing;
  Object? _error;
  bool _busy = false;
  bool _changed = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final listing = await SessionScope.of(context).api.listing(widget.kind, widget.id);
      if (mounted) setState(() => _listing = listing);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  Future<void> _act(String action) async {
    final t = AppLocalizations.of(context);
    String? reason;
    if (action == 'reject') {
      reason = await _askReason(context);
      if (reason == null) return;
    } else if (!await _confirm(context, _actionLabel(t, action))) {
      return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    try {
      final updated = await SessionScope.of(context)
          .api
          .moderate(widget.kind, widget.id, action, reason: reason);
      if (!mounted) return;
      setState(() {
        _listing = updated;
        _changed = true;
      });
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(t.adminStatusUpdated(listingStatusLabel(t, updated.status))),
      ));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _actionLabel(AppLocalizations t, String action) => switch (action) {
        'approve' => t.adminApprove,
        'reject' => t.adminReject,
        'suspend' => t.adminSuspend,
        _ => t.adminReactivate,
      };

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final listing = _listing;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) Navigator.of(context).pop(_changed);
      },
      child: Scaffold(
        appBar: AppBar(title: Text(listing?.name ?? '')),
        body: _error != null
            ? ErrorState(error: _error, onRetry: _load)
            : listing == null
                ? const Center(child: CircularProgressIndicator())
                : _details(context, t, listing),
        bottomNavigationBar: listing == null ? null : _actions(context, t, listing),
      ),
    );
  }

  Widget? _actions(BuildContext context, AppLocalizations t, Listing listing) {
    final role = SessionScope.of(context).me?.staffRole;
    if (!staffCan(role, StaffAction.moderate)) return null;
    final actions = switch (listing.status) {
      'PENDING_REVIEW' => ['reject', 'approve'],
      'APPROVED' => ['suspend'],
      'SUSPENDED' => ['reactivate'],
      _ => <String>[],
    };
    if (actions.isEmpty) return null;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(children: [
          for (final action in actions)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: action == 'approve' || action == 'reactivate'
                    ? FilledButton(
                        onPressed: _busy ? null : () => _act(action),
                        child: Text(_actionLabel(t, action)),
                      )
                    : OutlinedButton(
                        style: OutlinedButton.styleFrom(
                            foregroundColor: Theme.of(context).colorScheme.error),
                        onPressed: _busy ? null : () => _act(action),
                        child: Text(_actionLabel(t, action)),
                      ),
              ),
            ),
        ]),
      ),
    );
  }

  Widget _details(BuildContext context, AppLocalizations t, Listing listing) {
    final text = Theme.of(context).textTheme;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Row(children: [
          ListingAvatar(url: listing.imageUrl, radius: 32),
          const SizedBox(width: 16),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(listing.name, style: text.titleLarge),
              if (listing.subtitle != null) Text(listing.subtitle!),
              if (listing.place != null) Text(listing.place!, style: text.bodySmall),
              const SizedBox(height: 4),
              StatusChip(status: listing.status),
            ]),
          ),
        ]),
        const SizedBox(height: 12),
        Text(t.adminSubmittedAt(formatDate(context, listing.submittedAt)), style: text.bodySmall),
        if (listing.approvedByName != null)
          Text(t.adminApprovedByStaff(listing.approvedByName!), style: text.bodySmall),
        if (listing.rejectionReason != null) ...[
          const SizedBox(height: 12),
          Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: ListTile(
              title: Text(t.adminRejectionReasonTitle),
              subtitle: Text(listing.rejectionReason!),
            ),
          ),
        ],
        if (listing.shortDescription != null) ...[
          const SizedBox(height: 16),
          Text(listing.shortDescription!, style: text.titleSmall),
        ],
        if (listing.description != null) ...[
          const SizedBox(height: 8),
          Text(listing.description!),
        ],
        if (listing.gallery.isNotEmpty) ...[
          const SizedBox(height: 16),
          SizedBox(
            height: 120,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: listing.gallery.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) => ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(absoluteUrl(listing.gallery[i]),
                    width: 160, fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const SizedBox(
                        width: 160, child: Icon(Icons.broken_image_outlined))),
              ),
            ),
          ),
        ],
        const SizedBox(height: 16),
        for (final number in {listing.phone, listing.whatsapp}.whereType<String>())
          _PhoneRow(label: t.adminShopsCall, number: number),
        const Divider(height: 32),
        Text(t.adminOwnerTitle, style: text.titleMedium),
        _Field(label: t.adminOwnerName, value: listing.ownerName),
        _PhoneRow(label: t.adminOwnerAccount, number: listing.ownerPhone),
        _PhoneRow(label: t.adminOwnerPersonalPhone, number: listing.ownerPersonalPhone),
      ]),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.value});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) => ListTile(
        contentPadding: EdgeInsets.zero,
        dense: true,
        title: Text(label, style: Theme.of(context).textTheme.bodySmall),
        subtitle: Text(value ?? AppLocalizations.of(context).commonNotSet,
            style: Theme.of(context).textTheme.bodyLarge),
      );
}

class _PhoneRow extends StatelessWidget {
  const _PhoneRow({required this.label, required this.number});

  final String label;
  final String? number;

  @override
  Widget build(BuildContext context) {
    if (number == null || number!.isEmpty) return _Field(label: label, value: null);
    return ListTile(
      contentPadding: EdgeInsets.zero,
      dense: true,
      title: Text(label, style: Theme.of(context).textTheme.bodySmall),
      // Phone numbers read left to right in either language.
      subtitle: Text(number!,
          textDirection: TextDirection.ltr, style: Theme.of(context).textTheme.bodyLarge),
      trailing: IconButton(
        icon: const Icon(Icons.call_outlined),
        tooltip: AppLocalizations.of(context).adminShopsCall,
        onPressed: () => callNumber(number!),
      ),
    );
  }
}

Future<bool> _confirm(BuildContext context, String action) async {
  final t = AppLocalizations.of(context);
  final ok = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(action),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(t.commonCancel)),
        FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(t.commonConfirm)),
      ],
    ),
  );
  return ok ?? false;
}

/// The reason is sent to the owner, so it is required (five characters at
/// least, as the API's `RejectIn` says).
Future<String?> _askReason(BuildContext context) {
  final t = AppLocalizations.of(context);
  final controller = TextEditingController();
  return showDialog<String>(
    context: context,
    builder: (context) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: Text(t.adminReject),
        content: TextField(
          controller: controller,
          autofocus: true,
          minLines: 3,
          maxLines: 6,
          maxLength: 1000,
          onChanged: (_) => setState(() {}),
          decoration: InputDecoration(
            labelText: t.adminRejectReasonLabel,
            hintText: t.adminRejectReasonPlaceholder,
            border: const OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: Text(t.commonCancel)),
          FilledButton(
            onPressed: controller.text.trim().length < 5
                ? null
                : () => Navigator.pop(context, controller.text.trim()),
            child: Text(t.adminReject),
          ),
        ],
      ),
    ),
  );
}
