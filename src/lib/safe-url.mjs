/**
 * Only http(s) may reach an href.
 *
 * Feed data is external and `canonical_url()` upstream preserves whatever
 * scheme it was given, including `javascript:` and `data:`. Shared rather than
 * copied: two renderers show third-party links, and a guard that exists twice
 * is a guard that will eventually differ.
 */
export function safeHttpUrl(raw) {
  try {
    const url = new URL(raw);
    if (url.protocol === 'https:' || url.protocol === 'http:') return url.href;
  } catch {
    // unparseable — fall through to ''
  }
  return '';
}
