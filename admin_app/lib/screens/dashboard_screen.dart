import 'package:material_ui/material_ui.dart';

import '../api/models.dart';
import '../l10n/app_localizations.dart';
import '../session.dart';
import '../widgets/common.dart';
import 'listing_detail_screen.dart';

/// The platform's counts and, below them, what is waiting for review.
class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final api = SessionScope.of(context).api;
    return AsyncView<(Stats, Paged<Listing>, Paged<Listing>)>(
      load: () async => (
        await api.stats(),
        await api.listings(ListingKind.business, status: 'PENDING_REVIEW'),
        await api.listings(ListingKind.talent, status: 'PENDING_REVIEW'),
      ),
      builder: (context, data, reload) {
        final (stats, shops, talent) = data;
        final t = AppLocalizations.of(context);
        final tiles = [
          (t.adminPendingLabel, stats['pending_businesses'], true),
          (t.adminPendingTalentLabel, stats['pending_talents'], true),
          (t.adminPendingTestimonialsLabel, stats['pending_testimonials'], true),
          (t.adminStatTotal, stats['total_businesses'], false),
          (t.adminStatApproved, stats['approved_businesses'], false),
          (t.adminStatRejected, stats['rejected_businesses'], false),
          (t.adminStatSuspended, stats['suspended_businesses'], false),
          (t.adminStatDrafts, stats['draft_businesses'], false),
          (t.adminStatItems, stats['total_items'], false),
          (t.adminStatUsers, stats['total_users'], false),
        ];
        final queue = [...shops.items, ...talent.items]
          ..sort((a, b) => (b.submittedAt ?? DateTime(0)).compareTo(a.submittedAt ?? DateTime(0)));
        return RefreshIndicator(
          onRefresh: () async => reload(),
          child: ListView(padding: const EdgeInsets.all(16), children: [
            GridView.count(
              crossAxisCount: MediaQuery.sizeOf(context).width > 600 ? 4 : 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              childAspectRatio: 1.6,
              children: [
                for (final (label, value, highlight) in tiles)
                  Card(
                    color: highlight && value > 0
                        ? Theme.of(context).colorScheme.tertiaryContainer
                        : null,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(label,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context).textTheme.bodySmall),
                          Text('$value', style: Theme.of(context).textTheme.headlineSmall),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 24),
            Text(t.adminReviewRequests, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if (queue.isEmpty)
              EmptyState(title: t.adminQueueEmpty, description: t.adminQueueEmptyDescription)
            else
              for (final listing in queue)
                ListingTile(listing: listing, onChanged: reload),
          ]),
        );
      },
    );
  }
}

class ListingTile extends StatelessWidget {
  const ListingTile({super.key, required this.listing, required this.onChanged});

  final Listing listing;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    final subtitle = [listing.subtitle, listing.place].whereType<String>().join(' · ');
    return Card(
      child: ListTile(
        leading: ListingAvatar(url: listing.imageUrl),
        title: Text(listing.name, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: subtitle.isEmpty ? null : Text(subtitle, maxLines: 1),
        trailing: StatusChip(status: listing.status),
        onTap: () async {
          final changed = await Navigator.of(context).push<bool>(MaterialPageRoute(
            builder: (_) => ListingDetailScreen(kind: listing.kind, id: listing.id),
          ));
          if (changed == true) onChanged();
        },
      ),
    );
  }
}
