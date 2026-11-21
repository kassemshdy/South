import 'dart:async';

import 'package:material_ui/material_ui.dart';

import '../api/models.dart';
import '../l10n/app_localizations.dart';
import '../session.dart';
import '../widgets/common.dart';
import 'dashboard_screen.dart';

/// Every shop (or services profile), filtered by status and searched by
/// name, a page at a time.
class ListingsScreen extends StatefulWidget {
  const ListingsScreen({super.key, required this.kind});

  final ListingKind kind;

  @override
  State<ListingsScreen> createState() => _ListingsScreenState();
}

class _ListingsScreenState extends State<ListingsScreen> {
  String? _status = 'PENDING_REVIEW';
  String _query = '';
  Timer? _debounce;
  final _items = <Listing>[];
  int _page = 1;
  bool _hasNext = false;
  bool _loading = false;
  Object? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load(reset: true));
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _load({bool reset = false}) async {
    if (_loading) return;
    final api = SessionScope.of(context).api;
    setState(() {
      _loading = true;
      _error = null;
      if (reset) {
        _items.clear();
        _page = 1;
      }
    });
    try {
      final page = await api.listings(widget.kind, status: _status, q: _query, page: _page);
      if (!mounted) return;
      setState(() {
        _items.addAll(page.items);
        _hasNext = page.hasNext;
        _page += 1;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final filters = [
      (null, t.adminFilterAll),
      ('PENDING_REVIEW', t.adminFilterPending),
      ('APPROVED', t.adminFilterApproved),
      ('REJECTED', t.adminFilterRejected),
      ('SUSPENDED', t.adminFilterSuspended),
      ('DRAFT', t.adminFilterDrafts),
    ];
    final statusLabel = filters.firstWhere((f) => f.$1 == _status).$2;
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
        child: TextField(
          decoration: InputDecoration(
            prefixIcon: const Icon(Icons.search),
            hintText: widget.kind == ListingKind.business
                ? t.adminSearchPlaceholder
                : t.adminTalentSearchPlaceholder,
            border: const OutlineInputBorder(),
            isDense: true,
          ),
          onChanged: (value) {
            _debounce?.cancel();
            _debounce = Timer(const Duration(milliseconds: 400), () {
              _query = value.trim();
              _load(reset: true);
            });
          },
        ),
      ),
      SizedBox(
        height: 48,
        child: ListView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          children: [
            for (final (value, label) in filters)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: ChoiceChip(
                  label: Text(label),
                  selected: _status == value,
                  onSelected: (_) {
                    setState(() => _status = value);
                    _load(reset: true);
                  },
                ),
              ),
          ],
        ),
      ),
      Expanded(child: _body(t, statusLabel)),
    ]);
  }

  Widget _body(AppLocalizations t, String statusLabel) {
    if (_error != null && _items.isEmpty) {
      return ErrorState(error: _error, onRetry: () => _load(reset: true));
    }
    if (_items.isEmpty && _loading) return const Center(child: CircularProgressIndicator());
    if (_items.isEmpty) {
      return EmptyState(
        title: widget.kind == ListingKind.business
            ? t.adminListEmptyTitle(statusLabel)
            : t.adminTalentListEmptyTitle(statusLabel),
        description: t.adminListEmptyDescription,
      );
    }
    return RefreshIndicator(
      onRefresh: () => _load(reset: true),
      child: NotificationListener<ScrollNotification>(
        onNotification: (n) {
          if (_hasNext && n.metrics.extentAfter < 400) _load();
          return false;
        },
        child: ListView.builder(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          itemCount: _items.length + (_hasNext ? 1 : 0),
          itemBuilder: (context, i) => i == _items.length
              ? const Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator()),
                )
              : ListingTile(listing: _items[i], onChanged: () => _load(reset: true)),
        ),
      ),
    );
  }
}
