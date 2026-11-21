import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import 'models.dart';

/// A failed call, carrying the API's own message — already in the caller's
/// language, because every request sends `Accept-Language`.
class ApiException implements Exception {
  ApiException(this.statusCode, this.message);

  final int statusCode;
  final String? message;

  bool get unauthorized => statusCode == 401;

  @override
  String toString() => message ?? 'HTTP $statusCode';
}

class ApiClient {
  ApiClient({http.Client? httpClient}) : _http = httpClient ?? http.Client();

  final http.Client _http;
  String? token;
  String locale = 'ar';

  /// Called on a 401 so the app can drop the session and show sign-in.
  void Function()? onUnauthorized;

  Map<String, String> get _headers => {
        'Accept': 'application/json',
        'Accept-Language': locale,
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Uri _uri(String path, [Map<String, String?>? query]) {
    final q = {
      for (final e in (query ?? const <String, String?>{}).entries)
        if (e.value != null && e.value!.isNotEmpty) e.key: e.value!,
    };
    return Uri.parse('$apiBaseUrl/api$path').replace(queryParameters: q.isEmpty ? null : q);
  }

  Future<dynamic> _send(String method, String path,
      {Map<String, String?>? query, Object? body}) async {
    final request = http.Request(method, _uri(path, query))..headers.addAll(_headers);
    if (body != null) request.body = jsonEncode(body);
    final response = await http.Response.fromStream(await _http.send(request));
    final text = utf8.decode(response.bodyBytes);
    final decoded = text.isEmpty ? null : jsonDecode(text);
    if (response.statusCode >= 400) {
      if (response.statusCode == 401 && token != null) onUnauthorized?.call();
      throw ApiException(
        response.statusCode,
        decoded is Map ? decoded['message'] as String? : null,
      );
    }
    return decoded;
  }

  // --- Session ------------------------------------------------------------

  /// The one sign-in route: an administrator types their email address.
  Future<(String, Me)> login(String identifier, String password) async {
    final j = await _send('POST', '/auth/login',
        body: {'identifier': identifier, 'password': password}) as Map<String, dynamic>;
    return (j['access_token'] as String, Me.fromJson(j['user'] as Map<String, dynamic>));
  }

  Future<Me> me() async => Me.fromJson(await _send('GET', '/me') as Map<String, dynamic>);

  // --- Dashboard ----------------------------------------------------------

  Future<Stats> stats() async => Stats(await _send('GET', '/admin/stats') as Map<String, dynamic>);

  // --- Listings -----------------------------------------------------------

  Listing _listing(ListingKind kind, Map<String, dynamic> j) =>
      kind == ListingKind.business ? Listing.business(j) : Listing.talent(j);

  Future<Paged<Listing>> listings(ListingKind kind,
      {String? status, String? q, int page = 1}) async {
    final j = await _send('GET', '/admin/${kind.path}', query: {
      'status': status,
      'q': q,
      'page': '$page',
      'page_size': '30',
    }) as Map<String, dynamic>;
    return Paged.fromJson(j, (item) => _listing(kind, item));
  }

  Future<Listing> listing(ListingKind kind, String id) async =>
      _listing(kind, await _send('GET', '/admin/${kind.path}/$id') as Map<String, dynamic>);

  /// approve / reactivate take no body; reject needs a reason (5+ chars),
  /// suspend takes an optional one.
  Future<Listing> moderate(ListingKind kind, String id, String action, {String? reason}) async {
    final body = switch (action) {
      'reject' => {'reason': reason},
      'suspend' => {'reason': reason},
      _ => null,
    };
    final j = await _send('POST', '/admin/${kind.path}/$id/$action', body: body);
    return _listing(kind, j as Map<String, dynamic>);
  }

  // --- Tickets ------------------------------------------------------------

  Future<List<TicketSummary>> tickets() async => (await _send('GET', '/admin/feedback/tickets')
          as List)
      .cast<Map<String, dynamic>>()
      .map(TicketSummary.fromJson)
      .toList();

  Future<TicketDetail> ticket(String id) async => TicketDetail.fromJson(
      await _send('GET', '/admin/feedback/tickets/$id') as Map<String, dynamic>);

  /// To the top of [status]'s column; the server re-derives every order.
  Future<void> moveTicket(String id, String status) =>
      _send('POST', '/admin/feedback/tickets/$id/move', body: {'status': status, 'index': 0});

  Future<TicketDetail> comment(String id, String body) async => TicketDetail.fromJson(
      await _send('POST', '/admin/feedback/tickets/$id/comments', body: {'body': body})
          as Map<String, dynamic>);
}
