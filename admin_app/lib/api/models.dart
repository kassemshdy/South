/// The parts of the admin payloads the app reads. Field names follow the
/// API's own schemas (`backend/app/schemas/`), so a rename there is a rename
/// here.
library;

DateTime? _date(Object? v) => v is String ? DateTime.tryParse(v)?.toLocal() : null;
String? _nameAr(Object? v) => v is Map ? v['name_ar'] as String? : null;

class Me {
  Me({required this.id, required this.role, this.staffRole, this.displayName, this.email});

  factory Me.fromJson(Map<String, dynamic> j) => Me(
        id: j['id'] as String,
        role: j['role'] as String,
        staffRole: j['staff_role'] as String?,
        displayName: j['display_name'] as String?,
        email: j['email'] as String?,
      );

  final String id;
  final String role;
  final String? staffRole;
  final String? displayName;
  final String? email;

  bool get isAdmin => role == 'ADMIN';
}

class Paged<T> {
  Paged(this.items, this.total, this.hasNext);

  factory Paged.fromJson(Map<String, dynamic> j, T Function(Map<String, dynamic>) item) {
    final meta = j['meta'] as Map<String, dynamic>;
    return Paged(
      (j['items'] as List).cast<Map<String, dynamic>>().map(item).toList(),
      meta['total'] as int,
      meta['has_next'] as bool,
    );
  }

  final List<T> items;
  final int total;
  final bool hasNext;
}

/// What the review screens need from a shop or a services profile; the two
/// payloads share their moderation fields, so one class reads both.
class Listing {
  Listing({
    required this.kind,
    required this.id,
    required this.name,
    required this.status,
    this.subtitle,
    this.place,
    this.imageUrl,
    this.shortDescription,
    this.description,
    this.phone,
    this.whatsapp,
    this.ownerName,
    this.ownerPhone,
    this.ownerPersonalPhone,
    this.submittedAt,
    this.rejectionReason,
    this.approvedByName,
    this.gallery = const [],
    this.itemCount = 0,
  });

  factory Listing.business(Map<String, dynamic> j) => Listing(
        kind: ListingKind.business,
        id: j['id'] as String,
        name: j['name'] as String,
        status: j['status'] as String,
        subtitle: (j['custom_category_text'] as String?) ?? _nameAr(j['category']),
        place: _nameAr(j['location']),
        imageUrl: (j['logo_thumb_url'] ?? j['logo_url']) as String?,
        shortDescription: j['short_description'] as String?,
        description: j['description'] as String?,
        phone: j['phone'] as String?,
        whatsapp: j['whatsapp'] as String?,
        ownerName: j['owner_display_name'] as String?,
        ownerPhone: j['owner_phone'] as String?,
        ownerPersonalPhone: j['owner_personal_phone'] as String?,
        submittedAt: _date(j['submitted_at']),
        rejectionReason: j['rejection_reason'] as String?,
        approvedByName: j['approved_by_name'] as String?,
        gallery: [
          for (final img in (j['images'] as List? ?? const []).cast<Map<String, dynamic>>())
            img['url'] as String,
        ],
        itemCount: (j['items'] as List? ?? const []).length,
      );

  factory Listing.talent(Map<String, dynamic> j) => Listing(
        kind: ListingKind.talent,
        id: j['id'] as String,
        name: j['display_name'] as String,
        status: j['status'] as String,
        subtitle: (j['custom_skill_text'] as String?) ?? _nameAr(j['skill']),
        place: _nameAr(j['location']),
        imageUrl: j['photo_url'] as String?,
        shortDescription: j['skill_specialty'] as String?,
        description: j['bio'] as String?,
        phone: j['phone'] as String?,
        whatsapp: j['whatsapp'] as String?,
        ownerName: j['owner_display_name'] as String?,
        ownerPhone: j['owner_phone'] as String?,
        ownerPersonalPhone: j['owner_personal_phone'] as String?,
        submittedAt: _date(j['submitted_at']),
        rejectionReason: j['rejection_reason'] as String?,
        approvedByName: j['approved_by_name'] as String?,
        gallery: [
          for (final img in (j['images'] as List? ?? const []).cast<Map<String, dynamic>>())
            img['url'] as String,
        ],
      );

  final ListingKind kind;
  final String id;
  final String name;
  final String status;
  final String? subtitle;
  final String? place;
  final String? imageUrl;
  final String? shortDescription;
  final String? description;
  final String? phone;
  final String? whatsapp;
  final String? ownerName;
  final String? ownerPhone;
  final String? ownerPersonalPhone;
  final DateTime? submittedAt;
  final String? rejectionReason;
  final String? approvedByName;
  final List<String> gallery;
  final int itemCount;
}

enum ListingKind {
  business('businesses'),
  talent('talent');

  const ListingKind(this.path);

  /// The segment under `/api/admin/`.
  final String path;
}

class Stats {
  Stats(this.raw);

  final Map<String, dynamic> raw;

  int operator [](String key) => (raw[key] as num?)?.toInt() ?? 0;
}

const ticketStatuses = [
  'BACKLOG',
  'TODO',
  'IN_PROGRESS',
  'NEEDS_FEEDBACK',
  'NEEDS_APPROVAL',
  'APPROVED',
  'DONE',
];

class TicketSummary {
  TicketSummary.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        title = j['title'] as String,
        status = j['status'] as String,
        priority = j['priority'] as String,
        assignee = _person(j['assignee']),
        commentCount = j['comment_count'] as int? ?? 0,
        attachmentCount = j['attachment_count'] as int? ?? 0,
        updatedAt = _date(j['updated_at']);

  final String id;
  final String title;
  final String status;
  final String priority;
  final String? assignee;
  final int commentCount;
  final int attachmentCount;
  final DateTime? updatedAt;
}

String? _person(Object? v) =>
    v is Map ? (v['display_name'] as String?) ?? (v['email'] as String?) : null;

class TicketComment {
  TicketComment.fromJson(Map<String, dynamic> j)
      : body = j['body'] as String,
        author = j['author_display_name'] as String?,
        createdAt = _date(j['created_at']);

  final String body;
  final String? author;
  final DateTime? createdAt;
}

class TicketDetail extends TicketSummary {
  TicketDetail.fromJson(super.j)
      : description = j['description'] as String?,
        pagePath = j['page_path'] as String?,
        reporterName = (j['reporter_contact'] as Map?)?['name'] as String?,
        reporterPhone = (j['reporter_contact'] as Map?)?['phone'] as String?,
        comments = (j['comments'] as List? ?? const [])
            .cast<Map<String, dynamic>>()
            .map(TicketComment.fromJson)
            .toList(),
        super.fromJson();

  final String? description;
  final String? pagePath;
  final String? reporterName;
  final String? reporterPhone;
  final List<TicketComment> comments;
}
