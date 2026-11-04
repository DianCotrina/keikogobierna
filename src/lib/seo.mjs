// Vercel redirects every page to its trailing-slash URL, so the canonical has to
// name that same URL. Files such as /api/plan.json keep their exact path.
export function canonicalUrl(pathname, site) {
  const last = pathname.split('/').at(-1);
  const path = pathname.endsWith('/') || last.includes('.') ? pathname : `${pathname}/`;
  return new URL(path, site).href;
}
