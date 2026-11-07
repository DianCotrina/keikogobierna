---
name: elperuano-review
description: Review El Peruano "Norma candidata" issues (label evidencia-candidata) and decide, from the raw norma, whether it certifies a plan commitment as in progress or fulfilled, is context, is counter-evidence, or is discarded. Use for the daily "status checker", for re-reviewing a closed candidate, or when certifying evidence in src/data/tracking.json.
---

# El Peruano candidate review

The scraper's match only says a norma *mentions* the words of a commitment. This skill decides whether it *moves* the commitment. Be strict: a wrong certification on a political tracker costs more trust than a missed one.

**Non-negotiables**
- A human certifies. You gather, read and propose; status changes go through a PR the user approves, and issues close only on the user's go-ahead.
- No AI inside the pipeline. The tools below are deterministic; judgment happens here, in review.
- Closing comments and evidence notes are in Spanish (Peru); everything else in English.
- Read [precedents.md](precedents.md) before deciding. Same facts, same verdict.

## 1. Gather raw material (never decide from the issue excerpt)

```bash
python3 -m tools.review.fetch_norma <op> --out <scratch>     # page.txt, norma.pdf, pdf.txt, meta.json
python3 -m tools.review.plan_context <id> [<neighbour id>…]  # the promise on its plan page
python3 -m tools.review.plan_context --grep "<regex>"         # every commitment, any topic, whose text matches
git fetch origin normas-archive
python3 -m tools.review.archive_search "<norma it modifies>" "<program name>"
```

Read, in this order:
1. **The considerandos**, not only the articles. The reasons, the program's origin and the reports cited (VISTOS) are where the real change is stated. #650 looked like a cut; the considerandos showed a transfer.
2. **The articles and every complementary provision** (finales, transitorias, modificatorias, derogatorias), with numbers you can cite. Extensions often carry their substance there: D.S. 143-2026-PCM "only" extends an emergency in article 1 and creates the Comando Unificado PNP-FFAA in its modificatoria.
3. **Every norma it modifies or extends**, back to the creating act. Date the creating act from its own number and date, or from how later normas describe it. Absence from the archive is only a hint: the archive starts 2026-07-14, misses 2026-10-12 entirely and holds partial captures of some days.
4. **The right commitment, not the matcher's.** Read the promise on its plan page with the neighbouring bullets, then `--grep` the whole plan for the act's object: the right commitment is often in another topic (D.S. 121-2026-PCM matched `t2-9.C03`; it moves `t2-2.C03`). Every commitment with the same promise gets the same verdict.
5. **Annexes** when the verdict depends on them (project lists, procedure lists). They are usually on gob.pe or the entity's site, not in the gazette PDF. If you cannot reach one, or it is a scanned image you can only partly read, say so in the verdict and lower the confidence instead of assuming its content.

`archive_search` matches numero and sumilla only, not the body of each norma.

## 2. Write the bar before judging

For each commitment in play, write these lines first, from the plan text alone:

```
<id>: <promise in one line>
  started  = <the specific act that would show it began: creation, launch, approval of the instrument, first execution>
  kept     = <what has to exist for the plan's wording to be true: scope, coverage, permanence, actors>
  counter  = <what would move it backwards: dissolution, cut in scope, reversal>
  actor    = <who must act: national Executive (ministry, PCM, Presidency)>
```

Then compare the norma to the bar, element by element. Name each element the norma meets and each it misses; "queda en progreso" notes come from the misses.

## 3. Credit test

Answer all four; any "no" usually ends in discard or context:
- **Actor**: issued by the national Executive of this government (from 2026-07-28)? Congress, BCRP, autonomous regulators, subnational governments and the judiciary don't execute this plan (see `regulator-acts-not-evidence`).
- **Origin**: did this government create the program or instrument, or is it continuing one from before? Continuation counts only if it changes scope, design or reach in the promise's direction.
- **Discretion**: is the act a decision, or routine machinery? Routine: budget transfers and transfers of partidas, VAT-recovery qualifications for one company, delegation of powers, extensions of an existing body's term, legal transfer of already-built assets, procedure-list compilations.
- **Substance**: does it create, launch, approve or execute something, or only plan, study or convene?

**Temporary or partial** lowers the verdict only when the promise itself asks for permanence, a set composition or national scope. A temporary command in one critical zone *starts* "creación de comandos mixtos en zonas críticas"; it does not start a "Comando Unificado **Permanente**" with named members. Crisis-only promises (credit "para MYPEs afectadas por crisis") are met by temporary measures.

**States of emergency.** A declaration or extension is routine when it only sets the usual template (PNP in control with Armed Forces support, coordination committees). It is evidence when it creates or changes a body or measure that meets a commitment's `started`, and only for that commitment. Judge each extension on its own provisions, not as "same as before".

## 4. Outcome

| Outcome | When | Effect today |
|---|---|---|
| `fulfilled` | The norma meets every element of `kept` | Certify (status + evidence + log) |
| `in_progress` | Meets `started` and passes the credit test; misses part of `kept` | Certify; the note says what is missing |
| `context` | Real, related act by this government that is below `started` (one season, pilot, convening, a related neighbour promise) | Discard the issue; comment starts **Contexto:** |
| `counter` | Meets `counter` (cuts, dissolves or reverses what was promised) | Discard the issue; comment starts **Contraevidencia:**; tell the user |
| `discard` | Fails the credit test or has no relation | Close with the reason class |

Discard reason classes (keep these exact phrases): «no acredita avance», «no tiene relación», «actor equivocado». Spending is «no acredita avance», never «no tiene relación».

**Context or discard?** Context when this government's act concerns exactly the object of a commitment and stops below `started` (a diagnosis, a draft, one season of it, an inherited reform it finishes). Discard when no commitment covers the act, the actor is wrong, or it is routine machinery.

**100-day commitments.** Day 100 doesn't move the bar. Approving the exact instrument a "lanzamiento/implementación" commitment names counts as `started`; the note says whether it came inside the 100 days.

`context` and `counter` are not tracker states yet (a schema change waits on the user). Until then they live only in the closing comment, so write them so a later reader can reuse them.

**Confidence**: alta (raw text decisive), media (depends on an annex or judgment you could not fully verify), baja (ask the user before closing).

## 5. Execution, when money or projects are named

A norma is intent. If it names projects, codes or amounts, check what followed: MEF Consulta Amigable (spending), Invierte.pe banco de inversiones (project codes), INFOBRAS (works). These sites block or rate-limit automated access often; when they do, record "no verificado" rather than skipping silently. Execution can upgrade `in_progress` to `fulfilled`; it never certifies a norma that fails the credit test.

## 6. Write it up

Closing comment (Spanish):

```
Descartada: **<clase>**.            (or) Contexto: … / Contraevidencia: …

<What the norma does, with article numbers.> <Why it does or doesn't meet the bar, element by element.> <Origin and credit, if it decided the case.>

Confianza: <alta|media|baja>. <What would change the verdict: the act that would be evidence.>

**Compromisos del match:** `<id>`; …
```

Certification: one evidence entry per commitment id with the same promise (duplicates across topics included), one log line per norma, then `npm run validate` and a PR. The note states what the norma does and, for `in_progress`, "Queda en progreso, no cumplida: …".

**Open policy questions** (ask the user; don't settle them by habit):
- Does a working group created to diagnose and reform a named program start "promoción y fortalecimiento" of that program? (R.M. 00273-2026-PRODUCE was certified; the blind back-test called it context.)
- Does a permanent supervisory commission without operational command start a "Comando Unificado Permanente" with named members? (D.S. 141-2026-PCM was certified; the blind back-test called it context.)

After deciding, add a precedent to [precedents.md](precedents.md) when the case was close, new in kind, or overturned an earlier call.

## Recall

The queue only shows what the matcher caught. While tracing history you will find related normas that never became issues (the August and October changes to the MIDAGRI group were missed). Note them in the verdict and, if one would be evidence, raise it with the user.
