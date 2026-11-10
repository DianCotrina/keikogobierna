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

/** Schema.org nodes sharing one `@context`, for pages that describe several things. */
export function graph(...nodes) {
  return {
    '@context': 'https://schema.org',
    '@graph': nodes.map(({ '@context': _context, ...node }) => node),
  };
}

export function website(site) {
  return {
    '@type': 'WebSite',
    '@id': new URL('/#sitio', site).href,
    name: 'keikogobierna',
    url: new URL('/', site).href,
    inLanguage: 'es-PE',
    publisher: { '@id': new URL('/#organizacion', site).href },
  };
}

/**
 * A page of the site. `dateModified` is left out rather than guessed when no
 * dated record backs it.
 * @param {{ type?: string, path: string, name: string, description?: string,
 *   dateModified?: string | null, about?: object, mainEntity?: object }} page
 * @param {string | URL | undefined} site
 */
export function webPage({ type = 'WebPage', path, name, description, dateModified, about, mainEntity }, site) {
  const url = canonicalUrl(path, site);
  return {
    '@type': type,
    '@id': `${url}#pagina`,
    url,
    name,
    description,
    inLanguage: 'es-PE',
    isPartOf: { '@id': new URL('/#sitio', site).href },
    ...(dateModified && { dateModified }),
    ...(about && { about }),
    ...(mainEntity && { mainEntity }),
  };
}

/**
 * A cabinet member. Only a sitting minister gets `jobTitle` and `worksFor`:
 * for someone announced or out of office the markup would assert a post they
 * do not hold.
 * @param {{ name: string, slug: string, portfolioName?: string, serving: boolean }} person
 * @param {string | URL | undefined} site
 */
export function minister({ name, slug, portfolioName, serving }, site) {
  return {
    '@type': 'Person',
    '@id': `${canonicalUrl(`/gabinete/${slug}/`, site)}#persona`,
    name,
    ...(serving && portfolioName && {
      jobTitle: 'Ministro de Estado',
      worksFor: { '@type': 'GovernmentOrganization', name: portfolioName },
    }),
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
