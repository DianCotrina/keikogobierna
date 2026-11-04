// Vercel redirects every page to its trailing-slash URL, so the canonical has to
// name that same URL. Files such as /api/plan.json keep their exact path.
export function canonicalUrl(pathname, site) {
  const last = pathname.split('/').at(-1);
  const path = pathname.endsWith('/') || last.includes('.') ? pathname : `${pathname}/`;
  return new URL(path, site).href;
}

// A `</script>` inside a string would end the block early, so `<` never appears raw.
export function jsonLd(data) {
  return JSON.stringify(data).replace(/</g, '\\u003c');
}

/** `crumbs` is [name, path] pairs, from the homepage down to the current page. */
export function breadcrumbs(crumbs, site) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: crumbs.map(([name, path], index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name,
      item: canonicalUrl(path, site),
    })),
  };
}

export function organization(site) {
  return {
    '@type': 'Organization',
    '@id': new URL('/#organizacion', site).href,
    name: 'keikogobierna',
    url: new URL('/', site).href,
    logo: new URL('/apple-touch-icon.png', site).href,
    email: 'dian.cs183@gmail.com',
    sameAs: ['https://github.com/DianCotrina/keikogobierna'],
  };
}
