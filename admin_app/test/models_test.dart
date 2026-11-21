import 'package:flutter_test/flutter_test.dart';
import 'package:janoubona_admin/api/models.dart';
import 'package:janoubona_admin/config.dart';

void main() {
  test('a shop review payload reads into a Listing', () {
    final listing = Listing.business({
      'id': 'b1',
      'name': 'Shop',
      'status': 'PENDING_REVIEW',
      'category': {'name_ar': 'Category'},
      'location': {'name_ar': 'Town'},
      'logo_url': '/media/logo.jpg',
      'logo_thumb_url': null,
      'owner_display_name': 'Owner',
      'owner_phone': '+96103123456',
      'submitted_at': '2026-11-20T10:00:00Z',
      'images': [
        {'url': '/media/a.jpg'},
      ],
      'items': [{}, {}],
    });
    expect(listing.kind, ListingKind.business);
    expect(listing.subtitle, 'Category');
    expect(listing.place, 'Town');
    expect(listing.imageUrl, '/media/logo.jpg');
    expect(listing.gallery, ['/media/a.jpg']);
    expect(listing.itemCount, 2);
    expect(listing.submittedAt, isNotNull);
  });

  test("the owner's own words win over the literal Other category", () {
    final listing = Listing.business({
      'id': 'b1',
      'name': 'Shop',
      'status': 'APPROVED',
      'category': {'name_ar': 'Other'},
      'custom_category_text': 'Own words',
    });
    expect(listing.subtitle, 'Own words');
  });

  test('a services profile reads into a Listing', () {
    final listing = Listing.talent({
      'id': 't1',
      'display_name': 'Person',
      'status': 'SUSPENDED',
      'skill': {'name_ar': 'Skill'},
      'photo_url': null,
    });
    expect(listing.kind, ListingKind.talent);
    expect(listing.subtitle, 'Skill');
  });

  test('a ticket detail carries its comments and reporter', () {
    final ticket = TicketDetail.fromJson({
      'id': 'x',
      'title': 'T',
      'status': 'TODO',
      'priority': 'HIGH',
      'assignee': {'display_name': null, 'email': 'a@b.c'},
      'comment_count': 1,
      'reporter_contact': {'name': 'N', 'phone': '03123456'},
      'comments': [
        {'body': 'hi', 'author_display_name': 'A', 'created_at': '2026-11-20T10:00:00Z'},
      ],
    });
    expect(ticket.assignee, 'a@b.c');
    expect(ticket.reporterPhone, '03123456');
    expect(ticket.comments.single.body, 'hi');
  });

  test('media paths are made absolute against the API, full URLs kept', () {
    expect(absoluteUrl('/media/x.jpg'), '$apiBaseUrl/media/x.jpg');
    expect(absoluteUrl('https://cdn.example/x.jpg'), 'https://cdn.example/x.jpg');
    expect(absoluteUrl(null), '');
  });
}
