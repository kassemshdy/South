import 'package:material_ui/material_ui.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/client.dart';
import '../config.dart';
import '../l10n/app_localizations.dart';

/// Loads [load] once and renders [builder], with the web admin's loading,
/// error and retry states. Refresh through the `reload` the builder is
/// given; a new [load] passed in later is not called.
class AsyncView<T> extends StatefulWidget {
  const AsyncView({super.key, required this.load, required this.builder});

  final Future<T> Function() load;
  final Widget Function(BuildContext context, T data, VoidCallback reload) builder;

  @override
  State<AsyncView<T>> createState() => _AsyncViewState<T>();
}

class _AsyncViewState<T> extends State<AsyncView<T>> {
  late Future<T> _future = widget.load();

  void _reload() => setState(() => _future = widget.load());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return ErrorState(error: snapshot.error, onRetry: _reload);
        }
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        return builder(context, snapshot.data as T);
      },
    );
  }

  Widget builder(BuildContext context, T data) => widget.builder(context, data, _reload);
}

class ErrorState extends StatelessWidget {
  const ErrorState({super.key, required this.error, required this.onRetry});

  final Object? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.cloud_off, size: 48, color: Theme.of(context).colorScheme.error),
          const SizedBox(height: 12),
          Text(t.statesErrorTitle, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(errorMessage(context, error), textAlign: TextAlign.center),
          const SizedBox(height: 16),
          FilledButton.tonal(onPressed: onRetry, child: Text(t.statesRetry)),
        ]),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.title, this.description});

  final String title;
  final String? description;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.inbox_outlined, size: 48),
          const SizedBox(height: 12),
          Text(title, style: Theme.of(context).textTheme.titleMedium, textAlign: TextAlign.center),
          if (description != null) ...[
            const SizedBox(height: 4),
            Text(description!, textAlign: TextAlign.center),
          ],
        ]),
      ),
    );
  }
}

/// The API's own message when it sent one, else the generic sentence.
String errorMessage(BuildContext context, Object? error) {
  if (error is ApiException && error.message != null) return error.message!;
  return AppLocalizations.of(context).statesErrorFallback;
}

void showError(BuildContext context, Object error) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(errorMessage(context, error))));
}

String formatDate(BuildContext context, DateTime? date) {
  if (date == null) return AppLocalizations.of(context).commonNotSet;
  final locale = Localizations.localeOf(context).languageCode;
  return DateFormat.yMMMd(locale).add_Hm().format(date);
}

String listingStatusLabel(AppLocalizations t, String status) => switch (status) {
      'DRAFT' => t.statusDRAFT,
      'PENDING_REVIEW' => t.statusPENDING_REVIEW,
      'APPROVED' => t.statusAPPROVED,
      'REJECTED' => t.statusREJECTED,
      'SUSPENDED' => t.statusSUSPENDED,
      _ => status,
    };

String ticketStatusLabel(AppLocalizations t, String status) => switch (status) {
      'BACKLOG' => t.feedbackStatusBACKLOG,
      'TODO' => t.feedbackStatusTODO,
      'IN_PROGRESS' => t.feedbackStatusIN_PROGRESS,
      'NEEDS_FEEDBACK' => t.feedbackStatusNEEDS_FEEDBACK,
      'NEEDS_APPROVAL' => t.feedbackStatusNEEDS_APPROVAL,
      'APPROVED' => t.feedbackStatusAPPROVED,
      'DONE' => t.feedbackStatusDONE,
      _ => status,
    };

String priorityLabel(AppLocalizations t, String priority) => switch (priority) {
      'LOW' => t.feedbackPriorityLOW,
      'MEDIUM' => t.feedbackPriorityMEDIUM,
      'HIGH' => t.feedbackPriorityHIGH,
      'URGENT' => t.feedbackPriorityURGENT,
      _ => priority,
    };

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final (bg, fg) = switch (status) {
      'APPROVED' => (scheme.primaryContainer, scheme.onPrimaryContainer),
      'PENDING_REVIEW' => (scheme.tertiaryContainer, scheme.onTertiaryContainer),
      'REJECTED' || 'SUSPENDED' => (scheme.errorContainer, scheme.onErrorContainer),
      _ => (scheme.surfaceContainerHighest, scheme.onSurfaceVariant),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12)),
      child: Text(listingStatusLabel(AppLocalizations.of(context), status),
          style: Theme.of(context).textTheme.labelSmall?.copyWith(color: fg)),
    );
  }
}

class ListingAvatar extends StatelessWidget {
  const ListingAvatar({super.key, required this.url, this.radius = 24});

  final String? url;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final src = absoluteUrl(url);
    return CircleAvatar(
      radius: radius,
      backgroundImage: src.isEmpty ? null : NetworkImage(src),
      child: src.isEmpty ? const Icon(Icons.storefront_outlined) : null,
    );
  }
}

/// Opens the phone's dialler; nothing is sent from the app.
Future<void> callNumber(String number) =>
    launchUrl(Uri(scheme: 'tel', path: number.replaceAll(RegExp(r'[^\d+]'), '')));
