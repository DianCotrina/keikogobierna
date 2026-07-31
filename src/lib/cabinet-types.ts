/**
 * The cabinet data shapes, named once.
 *
 * `src/data/cabinet/*.json` arrives through static ESM imports, so TypeScript
 * infers `never` for every field while a file is still empty (ministers.json has
 * one entry; tenures.json has none). These declarations are what the pages and
 * cards type against instead — and having one home for them means adding a
 * field to a dossier is a single edit rather than a hunt through the cards.
 */

export interface Source {
  label: string;
  url: string;
  kind?: string;
}

export interface JudicialEntry {
  id: string;
  case: string;
  expediente?: string | null;
  stage: string;
  crime: string;
  body?: string;
  date: string;
  summary: string;
  sources: Source[];
}

export interface Person {
  slug: string;
  name: string;
  profession?: string;
  bio?: string;
  sources?: Source[];
  judicial?: JudicialEntry[];
}

export interface Norma {
  numero: string;
  url: string;
  date?: string;
}

export interface Portfolio {
  id: string;
  name: string;
  short: string;
  slug?: string;
  topics?: string[];
}

export interface Tenure {
  person: string;
  portfolio: string;
  start: string;
  end: string | null;
  appointment_norma?: Norma | null;
  exit_norma?: Norma | null;
  exit_reason?: string | null;
}

/**
 * A portfolio whose holder was named in public but not yet appointed by norma.
 * `person` is the raw slug in the JSON; `currentCabinet()` replaces it with the
 * resolved dossier (or null) before handing the announcement to a card.
 */
export interface Announcement {
  portfolio: string;
  person_name: string;
  person?: string | null;
  announced: string;
  sources: Source[];
}

export interface ResolvedAnnouncement extends Omit<Announcement, 'person'> {
  person: Person | null;
}
