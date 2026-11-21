/// Where the app talks to. The live site by default; point a build at the
/// develop preview (or a laptop) with
/// `--dart-define=API_BASE_URL=https://api-develop-develop-5e32.up.railway.app`.
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://janoubona.net',
);

/// Media URLs in payloads are site-relative (`/media/...`).
String absoluteUrl(String? path) {
  if (path == null || path.isEmpty) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return '$apiBaseUrl$path';
}
