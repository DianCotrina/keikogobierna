# Workflow — writing a minister's ficha

**Objective.** Give every minister in `src/data/cabinet/people.json` a
`profession` and a `bio`, so their card and dossier say who they are rather than
*"falta confirmar de qué persona se trata"*.

**The tool gathers; you write.** Nothing here produces publishable prose. The
facts in a news profile are public and yours to use; the sentences belong to the
outlet. Copying them into `bio` would reproduce their writing, which this site
tells its readers it does not do.

## Why the JNE is not enough

`jne_scraper.py` drafts a ficha from the Declaración Jurada de Hoja de Vida —
the strongest source available, because it is the person's own sworn statement
to the state. But it exists only for people who **stood for election**. Ministers
brought in from outside politics have none, and the tool says so:

    Marco Vinelli: sin hoja de vida en el padrón (no fue candidato)

Try the JNE first anyway. When it comes back empty, come here.

## Steps

### 1. Gather the press material

```bash
python3 -m tools.scrapers.infobae_profiles
python3 -m tools.scrapers.infobae_profiles --portfolio m-vivienda   # one cartera
```

Prints, per cartera: the minister, every matched Infobae item (headline,
summary, link, date), and a `people.json` skeleton with `profession` and `bio`
blank. It writes nothing.

Carteras with no profile in today's feed are listed by name at the end rather
than silently skipped — an empty ficha is a correct outcome, a guessed one is
not.

**Only feed metadata is read.** The summaries shown come from the RSS
`<description>`, the same field `/ultimitas/` already displays. The feed also
carries `content:encoded`, the full article body; no tool here reads it.

### 2. Write `profession`

Usually stated outright in the summary — *"El economista y docente
universitario"*, *"El ingeniero"*, *"La administradora piurana"*, *"exjefe del
Comando Conjunto de las FF.AA."*. Record the qualification, not the job:
`Economista`, not `Ministro de Desarrollo Agrario`.

If two sources disagree, or the summary only describes a role rather than a
qualification, leave it empty. An empty field is honest; a wrong one is not.

### 3. Write `bio`

Two or three neutral sentences in your own words, covering what the person did
before this post. Say where each claim comes from — *"según su hoja de vida ante
el JNE"*, *"según Infobae"* — the way Galarreta's ficha does.

Do not paste the outlet's sentence. Do not editorialise. Do not include anything
judicial here; that belongs in `judicial[]` with its own stage and source, and
`workflows/judicial_record.md` governs it.

### 4. Cite and link

Add the note as a `press` source on the person:

```json
"sources": [{"label": "Infobae", "url": "https://www.infobae.com/peru/…", "kind": "press"}]
```

Then link the ficha to its announcement by adding the slug to the matching entry
in `announcements.json`:

```json
{"portfolio": "m-vivienda", "person_name": "Mauricio Arnillas Gonzales",
 "person": "mauricio-arnillas-gonzales", …}
```

Until that `person` key exists the card shows the raw reported name and no
ficha — deliberately, because a name in a headline is not an identification.

### 5. Validate

```bash
npm run validate
python3 -m unittest discover -s tools/tests -t . -q
```

`npm run validate` fails on a non-https source, an unknown `kind`, an unknown
`person` slug, or a judicial entry without a stage.

## If the run surfaces something judicial

The same command's sibling, `cabinet_scraper.py --press`, reports judicial
coverage of people on the roster. That is how Infobae's report of Mauricio
Arnillas' *prisión suspendida* and declared *condena por lesiones culposas*
reached us.

A signal is a prompt, never a finding. Do not put it in `bio`, and do not stage
it from a headline — follow `workflows/judicial_record.md`.

## Edge cases

- **No profile in the feed.** Feeds are a rolling window; a profile published
  last week may be gone. Re-run later, or find the note by hand and cite it.
- **Two ministers share a surname.** Matching requires surname *and* cartera, so
  this resolves itself — but check the note really is about your minister before
  citing it.
- **A minister with no coverage at all.** Leave the ficha empty. The card already
  explains the gap honestly, and that is better than filling it with guesswork.
