# Changelog

## [2.12.2](https://github.com/DianCotrina/keikogobierna/compare/v2.12.1...v2.12.2) (2026-08-19)


### Bug Fixes

* certify Compras MyPerú as in progress ([515f7c5](https://github.com/DianCotrina/keikogobierna/commit/515f7c58ae7adde38a054914139cec87e2154eee))

## [2.12.1](https://github.com/DianCotrina/keikogobierna/compare/v2.12.0...v2.12.1) (2026-08-19)


### Bug Fixes

* gate the construction and canon index series ([a578be1](https://github.com/DianCotrina/keikogobierna/commit/a578be136e846c2822edc2f7bd59dd2c091b61c4))

## [2.12.0](https://github.com/DianCotrina/keikogobierna/compare/v2.11.1...v2.12.0) (2026-08-17)


### Features

* audit the first 100 days against the archive, and say what we cannot see ([3d0bed6](https://github.com/DianCotrina/keikogobierna/commit/3d0bed6403ec6bfca420e06e9fd0961d4d4743a3))


### Bug Fixes

* stop a multi-word boost from leaking its individual words ([1b5e403](https://github.com/DianCotrina/keikogobierna/commit/1b5e403f9e8af81741437c278c4712b6ff13c625))
* stop queueing drafts, statutory declarations and hazard emergencies ([0405d0d](https://github.com/DianCotrina/keikogobierna/commit/0405d0d59159a2268769c6e80d45d61d218e925d))

## [2.11.1](https://github.com/DianCotrina/keikogobierna/compare/v2.11.0...v2.11.1) (2026-08-12)


### Bug Fixes

* gate the whole personnel verb family, not one verb at a time ([26b4b93](https://github.com/DianCotrina/keikogobierna/commit/26b4b9306dcc8e3b6d1ed55ac2477724be935edc))

## [2.11.0](https://github.com/DianCotrina/keikogobierna/compare/v2.10.0...v2.11.0) (2026-08-12)


### Features

* link each update card to its commitment on the tema page ([daded90](https://github.com/DianCotrina/keikogobierna/commit/daded901e89207c22fcc553cd5e0baa29f4fa4d3))

## [2.10.0](https://github.com/DianCotrina/keikogobierna/compare/v2.9.0...v2.10.0) (2026-08-10)


### Features

* certify the first commitment as in progress ([632ebb1](https://github.com/DianCotrina/keikogobierna/commit/632ebb104b27363bd528f4dd9f114aa806a1c343))


### Bug Fixes

* gate the personnel forms and name collisions the queue kept surfacing ([77d5d0b](https://github.com/DianCotrina/keikogobierna/commit/77d5d0bdbf9c3b26229d0491ded5b0799bd70191))

## [2.9.0](https://github.com/DianCotrina/keikogobierna/compare/v2.8.5...v2.9.0) (2026-08-06)


### Features

* record quantitative commitments as a measurement series ([45ab92e](https://github.com/DianCotrina/keikogobierna/commit/45ab92e4a11fec5ccd84f929fbbba4edf498165f))


### Bug Fixes

* close the residual gaps the act gate exposed in the queue ([90b1cc0](https://github.com/DianCotrina/keikogobierna/commit/90b1cc0fccf4075a48c191925f3a3763a8e8e8cf))

## [2.8.5](https://github.com/DianCotrina/keikogobierna/compare/v2.8.4...v2.8.5) (2026-08-05)


### Bug Fixes

* routine acts no longer reach the evidencia-candidata queue ([bf37f4e](https://github.com/DianCotrina/keikogobierna/commit/bf37f4edfb0a856d315968fdf7a7b6a753bf1fe8))

## [2.8.4](https://github.com/DianCotrina/keikogobierna/compare/v2.8.3...v2.8.4) (2026-08-04)


### Bug Fixes

* the search overlay was clipped to the header on mobile ([02a51ac](https://github.com/DianCotrina/keikogobierna/commit/02a51ac8425919a75389f9e53dbb69dc119c656b))

## [2.8.3](https://github.com/DianCotrina/keikogobierna/compare/v2.8.2...v2.8.3) (2026-08-03)


### Bug Fixes

* mobile navigation was unreachable below md ([c012ce2](https://github.com/DianCotrina/keikogobierna/commit/c012ce23e7f876b3626e4bdafcaddc1e6d35754c))

## [2.8.2](https://github.com/DianCotrina/keikogobierna/compare/v2.8.1...v2.8.2) (2026-08-02)


### Performance Improvements

* check each tema label against GitHub once per run, not per issue ([ee062cc](https://github.com/DianCotrina/keikogobierna/commit/ee062cc7981b6f4694e18317d2c0bcce43cf3dfa))

## [2.8.1](https://github.com/DianCotrina/keikogobierna/compare/v2.8.0...v2.8.1) (2026-08-02)


### Bug Fixes

* drop control and judicial own-acts from the evidence queue ([4e1da4f](https://github.com/DianCotrina/keikogobierna/commit/4e1da4f3f68296f6614b355b32a4c69e0da4f4b6))
* split matcher tokens on punctuation ([41f3ddc](https://github.com/DianCotrina/keikogobierna/commit/41f3ddc1201007c59aacb9fee264399db86d9fee))
* suppress the boilerplate bigrams that flooded the evidence queue ([489ef9f](https://github.com/DianCotrina/keikogobierna/commit/489ef9f220a259834b8590128161972bd4e7d5e4))

## [2.8.0](https://github.com/DianCotrina/keikogobierna/compare/v2.7.2...v2.8.0) (2026-08-02)


### Features

* per-minister coverage index, keyed by slug and windowed ([f1bce2a](https://github.com/DianCotrina/keikogobierna/commit/f1bce2a578bdb67dcced63e1513d02b9d214766d))
* show a minister's press coverage on their dossier ([aac854c](https://github.com/DianCotrina/keikogobierna/commit/aac854ca6651c3a41f004396cfb2589fc13df3e7))
* write the per-minister coverage index each run ([995b490](https://github.com/DianCotrina/keikogobierna/commit/995b4900d0f7dc5751988b0f21d802a2e7a79dbd))


### Bug Fixes

* base matched_in on the apellido alone, not the full two-key rule ([4305e14](https://github.com/DianCotrina/keikogobierna/commit/4305e1404016df6e3289bd31f7c368323e124931))
* distinguish load failure from genuine no-coverage, drop only malformed entries ([cb880fd](https://github.com/DianCotrina/keikogobierna/commit/cb880fd14a97be24244931e3d10f23244907374c))
* examine every ministro/ministerio mention independently ([2ef1248](https://github.com/DianCotrina/keikogobierna/commit/2ef124822cc132df46a1339b11e716ad1456b30c))
* guard the ministros.json write on the built index, not the fetch ([e3f1724](https://github.com/DianCotrina/keikogobierna/commit/e3f1724f479bacfd3b3f3d49ff32d9b59891349e))
* hide press coverage on a former minister's dossier ([434d539](https://github.com/DianCotrina/keikogobierna/commit/434d539c533aabd839c9aa6b8b66c986da35224d))
* keep writing ministros.json when only ultimitas.json's two outlets are down ([501d332](https://github.com/DianCotrina/keikogobierna/commit/501d33211e80ea1a67ca1d6ff07773418cb16f0a))
* make ministros.json write survivable and its ordering test real ([d9a8bba](https://github.com/DianCotrina/keikogobierna/commit/d9a8bbada80d45eae1239ba54c3b783fbea0faf3))
* reject stale minister-news payloads and centralize the render decision ([0987960](https://github.com/DianCotrina/keikogobierna/commit/0987960f3047089bd49487cf7648e72404f18979))
* say when a minister was named only in the article summary ([145f4ed](https://github.com/DianCotrina/keikogobierna/commit/145f4edcc65c19b4086f30dba5a302bbbe0d0a3f))
* sort minister coverage by parsed instant, not raw ISO string ([c963312](https://github.com/DianCotrina/keikogobierna/commit/c963312dd1390566cbf4910ead27125e56efcac8))
* widen matched_in to apellido OR cartera in the headline ([0c152b8](https://github.com/DianCotrina/keikogobierna/commit/0c152b8a215da0b43bd32e19f9274e19f7b6b97d))

## [2.7.2](https://github.com/DianCotrina/keikogobierna/compare/v2.7.1...v2.7.2) (2026-08-01)


### Bug Fixes

* publish /ultimitas/ from El Comercio and La República only ([ab95a54](https://github.com/DianCotrina/keikogobierna/commit/ab95a5404f12c19900c2843e897cad0358c9a4b0))

## [2.7.1](https://github.com/DianCotrina/keikogobierna/compare/v2.7.0...v2.7.1) (2026-08-01)


### Bug Fixes

* the profile reader broke when the cabinet was sworn in ([351caa0](https://github.com/DianCotrina/keikogobierna/commit/351caa0bd577b797079aeb8fef150e904537d6bb))

## [2.7.0](https://github.com/DianCotrina/keikogobierna/compare/v2.6.1...v2.7.0) (2026-07-31)


### Features

* add Infobae to the shared press sources ([72998cd](https://github.com/DianCotrina/keikogobierna/commit/72998cdbf6ebc1e72104318e3ca1f5397752a30a))
* add RPP and Gestión to the press sources ([59bbe62](https://github.com/DianCotrina/keikogobierna/commit/59bbe6209a959c798b1ea1d8a9555546782e15ca))
* announcement cards lead with public record, not with who reported it ([68960ab](https://github.com/DianCotrina/keikogobierna/commit/68960ab4d111abb65c6a0e5f30996643ee19122b))
* cabinet data model, library and validator ([39f1191](https://github.com/DianCotrina/keikogobierna/commit/39f1191d12d2cab9eda8878822babb86198765e1))
* detect cabinet changes in El Peruano ([34224ed](https://github.com/DianCotrina/keikogobierna/commit/34224edf134c48d04954e09357b8b6637661537e))
* document Arnillas' declared record, marked as press-sourced ([b2e3115](https://github.com/DianCotrina/keikogobierna/commit/b2e31152adb2390f73e07d9e0452a096669b258d))
* document the two investigations reported as active ([1d5d684](https://github.com/DianCotrina/keikogobierna/commit/1d5d6847fbbf992b9046bcf5a39f8263e141e9c7))
* draft minister dossiers from the JNE hoja de vida ([4a2086e](https://github.com/DianCotrina/keikogobierna/commit/4a2086efb9e12ae38043f01decb5d808178da06f))
* gabinete roster and per-minister judicial dossiers ([fe5e71a](https://github.com/DianCotrina/keikogobierna/commit/fe5e71a889c837cb3acdb0d04043f332eafca803))
* Infobae joins the outlets shown on ultimitas and fuentes ([54bb3a8](https://github.com/DianCotrina/keikogobierna/commit/54bb3a8db6eeebf2967697be4b1cbfb8b0920df0))
* judicial stage ladder with exculpatory outcomes ranked zero ([25ff8bf](https://github.com/DianCotrina/keikogobierna/commit/25ff8bfc7af715f9d7bc54a5af243c6600d56f7f))
* match press items to the minister they profile ([3888c52](https://github.com/DianCotrina/keikogobierna/commit/3888c525553929668ba8f7f88311b1dc05f5bf06))
* print a per-minister press review packet for writing fichas ([89ca56a](https://github.com/DianCotrina/keikogobierna/commit/89ca56a374229f353cddd11fc4ce8a58274b19bf))
* provisional "anunciado" state from press announcements ([7b12412](https://github.com/DianCotrina/keikogobierna/commit/7b124127a0482ce692bfab70ed25f926fa45758a))
* qualify an imputed crime as presunto until a sentence is firm ([f36f02e](https://github.com/DianCotrina/keikogobierna/commit/f36f02ee1c10aeb06bbe9c45e903f69c638b733a))
* read the whole cabinet from El Peruano's news note ([25456e7](https://github.com/DianCotrina/keikogobierna/commit/25456e767b6e8a848a53babf81973dc839cecc48))
* record Marco Vinelli's announcement for Desarrollo Agrario ([663cee3](https://github.com/DianCotrina/keikogobierna/commit/663cee3d73cb58019ad77ae4249a66d4319420c1))
* resolve ministries by the acronyms the press actually prints ([ce6d46e](https://github.com/DianCotrina/keikogobierna/commit/ce6d46e8f92c339281086697770d0d68bce8dd56))
* seat the cabinet from the gazette instead of the press ([a8e1ace](https://github.com/DianCotrina/keikogobierna/commit/a8e1ace29a4f142d9c067973dd6b022452e7b9b8))


### Bug Fixes

* Arnillas' entry omitted the absolución he says followed ([adc9a24](https://github.com/DianCotrina/keikogobierna/commit/adc9a24172bae2fa72df4fb717b86e25e8301a14))
* judicial signals missed a minister whose roster name outruns the headline ([a1be3b7](https://github.com/DianCotrina/keikogobierna/commit/a1be3b79f3ce523b7b686df8bd5fca676f80a655))
* parse cabinet normas against the gazette's real grammar ([91672eb](https://github.com/DianCotrina/keikogobierna/commit/91672eb5dd97076a3b198ee7345c8e42fb629be4))
* read the Edición Extraordinaria, where a new cabinet is published ([1da6858](https://github.com/DianCotrina/keikogobierna/commit/1da685850e96f836475e8aa29f81d35689bec88d))
* resolve ministries when a headline runs past the office ([056e126](https://github.com/DianCotrina/keikogobierna/commit/056e12679499fe3065501a273c1e6ad74040cbb3))
* restore the transport imports the evidence reader lost ([d7407e3](https://github.com/DianCotrina/keikogobierna/commit/d7407e388409a73ec1c145d747d50fff423d70d8))
* run the El Peruano scraper the way the package requires ([a0f0b35](https://github.com/DianCotrina/keikogobierna/commit/a0f0b3544ad3b4f297608adba7802ad4a11d147a))

## [2.6.1](https://github.com/DianCotrina/keikogobierna/compare/v2.6.0...v2.6.1) (2026-07-31)


### Bug Fixes

* drop subnational and generic-bigram noise from the review queue ([53efa5d](https://github.com/DianCotrina/keikogobierna/commit/53efa5dd18df776daeb9d5f7f0873b99e50a3337))

## [2.6.0](https://github.com/DianCotrina/keikogobierna/compare/v2.5.4...v2.6.0) (2026-07-31)


### Features

* seed the evidence note with a draft instead of leaving it blank ([1498c54](https://github.com/DianCotrina/keikogobierna/commit/1498c540a38fa94c357e8470b46116ea78579b90))

## [2.5.4](https://github.com/DianCotrina/keikogobierna/compare/v2.5.3...v2.5.4) (2026-07-31)


### Bug Fixes

* retry transient errors in the El Peruano fetch ([cf5d0df](https://github.com/DianCotrina/keikogobierna/commit/cf5d0dff68438c7e5c38dd8a3a0a376ea8a19cf1))

## [2.5.3](https://github.com/DianCotrina/keikogobierna/compare/v2.5.2...v2.5.3) (2026-07-31)


### Bug Fixes

* repoint the El Peruano reader at the new search page ([92e3610](https://github.com/DianCotrina/keikogobierna/commit/92e361098b90e1e37ecdd1b212b31a5ced295ea5))

## [2.5.2](https://github.com/DianCotrina/keikogobierna/compare/v2.5.1...v2.5.2) (2026-07-29)


### Bug Fixes

* donation dialogs were invisible on iOS Safari ([29ccaa2](https://github.com/DianCotrina/keikogobierna/commit/29ccaa287612470a1f323339927ef783c5d7d134))

## [2.5.1](https://github.com/DianCotrina/keikogobierna/compare/v2.5.0...v2.5.1) (2026-07-28)


### Bug Fixes

* stop the donate widget covering the mobile screen ([e955b37](https://github.com/DianCotrina/keikogobierna/commit/e955b372c16b413aacd09623b437772fed9c84d9))

## [2.5.0](https://github.com/DianCotrina/keikogobierna/compare/v2.4.0...v2.5.0) (2026-07-28)


### Features

* accent folding that keeps a map back to source offsets ([a29d7ee](https://github.com/DianCotrina/keikogobierna/commit/a29d7ee7628fc4bf772844f46080c6a7e37fdfca))
* emit the search corpus at build time ([37387f3](https://github.com/DianCotrina/keikogobierna/commit/37387f38bf818d2688636b3ca120fdc74a0436b3))
* flatten the plan into a searchable corpus ([f5504bc](https://github.com/DianCotrina/keikogobierna/commit/f5504bccd3475935a687061516cc850175012fe4))
* give every commitment an anchor and an arrival highlight ([ab829fb](https://github.com/DianCotrina/keikogobierna/commit/ab829fb8270b45aa173a89e4155d386ab1d47a62))
* strict multi-term matching grouped by tema ([a6a9375](https://github.com/DianCotrina/keikogobierna/commit/a6a937541d9e00f319dac608159883add3e102bf))
* the buscador overlay, reachable from every page ([1427105](https://github.com/DianCotrina/keikogobierna/commit/1427105261af816c9d109777b25b1077ee3f4e77))

## [2.4.0](https://github.com/DianCotrina/keikogobierna/compare/v2.3.0...v2.4.0) (2026-07-21)


### Features

* Change text for donations ([21f353f](https://github.com/DianCotrina/keikogobierna/commit/21f353fd1d4fc334c53b6173dfb7b3aa6e95e799))

## [2.3.0](https://github.com/DianCotrina/keikogobierna/compare/v2.2.0...v2.3.0) (2026-07-20)


### Features

* La República card in fuentes automáticas ([e06e585](https://github.com/DianCotrina/keikogobierna/commit/e06e5859374ad9f850eb0a85f4be1986b451e0d5))
* La República joins the ultimitas scraper ([eb8f4da](https://github.com/DianCotrina/keikogobierna/commit/eb8f4da8dc5cd26042cc0c210f327c869c6aa0bb))
* source chips and filters on the ultimitas page ([e033f20](https://github.com/DianCotrina/keikogobierna/commit/e033f203d9b8342099a1559cf91a4bb9c2e99226))
* ultimitas scraper carries a source on every article ([f56aa18](https://github.com/DianCotrina/keikogobierna/commit/f56aa188c3719a198a7bb69e9cfa9d5688f405f3))

## [2.2.0](https://github.com/DianCotrina/keikogobierna/compare/v2.1.0...v2.2.0) (2026-07-20)


### Features

* methodology notes the assistive RAG under evaluation ([071b412](https://github.com/DianCotrina/keikogobierna/commit/071b4123508a17e80d0a6b462f742106a00faa75))


### Bug Fixes

* call the dashboard "resumen" everywhere ([b4b2701](https://github.com/DianCotrina/keikogobierna/commit/b4b2701e38589f56acc352e458e0fcfa1eca114a))
* remove the dead alerts form and its header CTA ([f3aa3e0](https://github.com/DianCotrina/keikogobierna/commit/f3aa3e0c52319d4d9e388847864ce85b59c6e780))

## [2.1.0](https://github.com/DianCotrina/keikogobierna/compare/v2.0.0...v2.1.0) (2026-07-20)


### Features

* group fuentes by automated pipelines vs human review ([5cfed67](https://github.com/DianCotrina/keikogobierna/commit/5cfed67042ea1e633e839da36b46879666199b3b))

## [2.0.0](https://github.com/DianCotrina/keikogobierna/compare/v1.1.0...v2.0.0) (2026-07-20)


### ⚠ BREAKING CHANGES

* candidate issues no longer contain AI verdicts; the ANTHROPIC_API_KEY secret is ignored.

### Features

* add El Peruano reader (GraphQL primary-source evidence pipeline) ([dceeeb5](https://github.com/DianCotrina/keikogobierna/commit/dceeeb5ea1ddf3c5014bb1c4c64479306142bf54))
* add Palacio de Gobierno banner to the Resumen hero ([0448108](https://github.com/DianCotrina/keikogobierna/commit/0448108ed22a4892017ecbad4e05c054fed31b18))
* add Redes footer section with LinkedIn and GitHub ([b167509](https://github.com/DianCotrina/keikogobierna/commit/b16750912bb297fb71699d302486112308ec90fc))
* bigram-only matching + generic-phrase stoplist for precision ([e71430c](https://github.com/DianCotrina/keikogobierna/commit/e71430ca14365271fc9661f5a5493e9879829dc3))
* distinctive-phrase index builder from plan commitments ([6ad30b7](https://github.com/DianCotrina/keikogobierna/commit/6ad30b7af38b42639b9326f7c99c1d2fb9b09edb))
* El Comercio RSS fetch and parse stage ([c0440d5](https://github.com/DianCotrina/keikogobierna/commit/c0440d59614ebdb558c4df11e93080eee5776d64))
* El Peruano scraper matches plan commitments; tema-labeled issues ([b226cb7](https://github.com/DianCotrina/keikogobierna/commit/b226cb720ac5fe9cfab8b8f3a05e39f10d06ec0f))
* footer contact/legal links and Fuentes + Privacidad pages ([32f2143](https://github.com/DianCotrina/keikogobierna/commit/32f2143d7ffada56e0d5e8ddde522864fbf8562d))
* give Privacidad its own footer section ([ee93156](https://github.com/DianCotrina/keikogobierna/commit/ee93156c7b5f424ff01ba09445c84915fafc9260))
* history merge, Lima today selection and scraper CLI ([a3a3173](https://github.com/DianCotrina/keikogobierna/commit/a3a3173d97464933a03dd97ceee102add5dda607))
* keyword filter for Keiko/Fuerza Popular coverage ([5fb4564](https://github.com/DianCotrina/keikogobierna/commit/5fb45643288c966f296409f34e1bb87356b1baab))
* Las ultimitas page fed from the ultimitas-data branch ([d0ce189](https://github.com/DianCotrina/keikogobierna/commit/d0ce1897359403f604cca918b1fbe73e7606dfec))
* move disclaimer below footer columns, add Twain epigraph ([92fad06](https://github.com/DianCotrina/keikogobierna/commit/92fad0655e074bdfddfbdbbc22589460a85dab6b))
* parameterize ensure_label/create_issue for extra labels ([12410af](https://github.com/DianCotrina/keikogobierna/commit/12410aff3cb018b38f3ef3c994d6c7da9c18ecc4))
* publish plan and tracking as static JSON API endpoints ([c9f1da8](https://github.com/DianCotrina/keikogobierna/commit/c9f1da82f2f058718cd8fb5983c830f092e73938))
* read norma text from El Peruano's HTML rendition ([c957252](https://github.com/DianCotrina/keikogobierna/commit/c9572527c434ff6c8e32efd912c5cbf235038d7d))
* remove the Claude judge — deterministic pipeline only ([3a4c552](https://github.com/DianCotrina/keikogobierna/commit/3a4c552834630b16042cd48fe051a0b826fc3176))
* shared commitment matcher with overlay and tema-level mute ([edd95cd](https://github.com/DianCotrina/keikogobierna/commit/edd95cdb46ab608aab426c0c7b04ae9c1fe23617))
* shared tokenization primitives in watcher_common ([3ce5528](https://github.com/DianCotrina/keikogobierna/commit/3ce552874948b66746ea67283cf383309678aaeb))


### Bug Fixes

* adapt Yape dialog to the new official QR export ([9d09cf1](https://github.com/DianCotrina/keikogobierna/commit/9d09cf112ab80be7748d2a944ce09926c80fc69c))
* make the landing page reflect the real pipeline ([07046a0](https://github.com/DianCotrina/keikogobierna/commit/07046a063c83b6609f51aaaa920a07aea3fe8915))
* only link http(s) URLs from the ultimitas feed ([8b50730](https://github.com/DianCotrina/keikogobierna/commit/8b507304fe2a88465d8a53568009558c28d54259))

## [1.1.0](https://github.com/DianCotrina/keikogobierna/compare/v1.0.0...v1.1.0) (2026-07-10)


### Features

* link Plan inmediato section to the 100 días page ([12bfd03](https://github.com/DianCotrina/keikogobierna/commit/12bfd03441149a00ea93c9a6b63c378841f54b8c))

## 1.0.0 (2026-07-10)


### Features

* add 23 topic detail pages with goals and proposals ([b3a373f](https://github.com/DianCotrina/keikogobierna/commit/b3a373fb2c7ae10988ed01f3d172da5ee4446bd4))
* add base layout and shared components ([aa98bb6](https://github.com/DianCotrina/keikogobierna/commit/aa98bb6710a4105e17a83a6f22afd4509f3e116c))
* add build-time plan data library with tests ([5388919](https://github.com/DianCotrina/keikogobierna/commit/5388919c601c4b5f4f389ac9048f211b6531b617))
* add curation overrides fixing t3-7 merge and t2-6 group header ([71f3879](https://github.com/DianCotrina/keikogobierna/commit/71f38792dc1801870de5a46ef5cf8fdc656980b2))
* add dedicated Primeros 100 días page ([8c62c8e](https://github.com/DianCotrina/keikogobierna/commit/8c62c8e7688264a07a5d43bddff8ad841e002e7d))
* add dom helpers (esc, ESTADOS, stamp) ([e55a7dd](https://github.com/DianCotrina/keikogobierna/commit/e55a7dd289071a0b8a3bcf67b3c8d26485fc70c9))
* add formatDateEs helper, reuse in home page ([0299c1c](https://github.com/DianCotrina/keikogobierna/commit/0299c1c41579bc54640285d4f5a452b6488be4e6))
* add fulfilledItems() for the registro de cumplidas ([ceb2eea](https://github.com/DianCotrina/keikogobierna/commit/ceb2eea92cf926ccdbfa52f0dc9f86a0b9e397d6))
* add IndexRail floating tree navigation ([fd69496](https://github.com/DianCotrina/keikogobierna/commit/fd69496d02a0968d9b0b21d899455e94e8f1ee32))
* add índice to primeros 100 días page ([111c9ee](https://github.com/DianCotrina/keikogobierna/commit/111c9eec74a6a78b621edf738c01872a0037c994))
* add plan.json data layer and validation tool ([7dddbeb](https://github.com/DianCotrina/keikogobierna/commit/7dddbeb8ecd0f22c318f4b86f28ef7d0f0a94aef))
* add PlanIndex índice block to topic pages ([b0d648b](https://github.com/DianCotrina/keikogobierna/commit/b0d648bbd65a793e5817c2e25f41ab513a678517))
* add registro de cumplidas section to home ([4f26de3](https://github.com/DianCotrina/keikogobierna/commit/4f26de36aeefd3a92d3b3fca827824265878f1b5))
* add render modules for tracker card, ejes, registro ([b2b7a11](https://github.com/DianCotrina/keikogobierna/commit/b2b7a113f63df84fbbcdef93aac21ac745847885))
* add reveal and donate behavior modules ([d187efa](https://github.com/DianCotrina/keikogobierna/commit/d187efa6adb2025022c03bef4a7cc746fa22f901))
* add tracking layer and extend validator to full plan tree ([01dde68](https://github.com/DianCotrina/keikogobierna/commit/01dde686ca445867aa71112835a2597abcdef24d))
* add Yape and PayPal donation modals with QR codes ([ec29dc0](https://github.com/DianCotrina/keikogobierna/commit/ec29dc0d7e6f62f1d754342ec94fd573fa7f0ef0))
* curate metas al 2031 goals with indicators for all 23 topics ([e997b84](https://github.com/DianCotrina/keikogobierna/commit/e997b84e51195f8ccf3899183d43629e75fd8bb2))
* extract ProposalRow with certified evidence treatment ([e6ed328](https://github.com/DianCotrina/keikogobierna/commit/e6ed3289c6f2f6029184f6252c7649de15773d73))
* extract real plan data (23 topics, 635 proposals) from official PDF ([c1974a1](https://github.com/DianCotrina/keikogobierna/commit/c1974a1e8076112736e0dc541f3911b3857bf431))
* nav chip highlight for 100 días; revert blackletter titles ([d3c06b2](https://github.com/DianCotrina/keikogobierna/commit/d3c06b2af1d08e24fcbfc9c3ba69a52a9f301db0))
* rebuild landing on Astro with real plan data ([98feb9a](https://github.com/DianCotrina/keikogobierna/commit/98feb9acc172ae5b9c53bdd292bdd7ba5487c3af))
* refine índice UX and add blackletter titles ([f715921](https://github.com/DianCotrina/keikogobierna/commit/f715921bd0a36aefbe13d7be493f28ff258c339b))
* restyle donation modals as two-tone tickets ([614011d](https://github.com/DianCotrina/keikogobierna/commit/614011dba10d6e52b13be131003d473cbf05d085))
* scaffold Astro 5 with Tailwind v4 and ported design tokens ([9bdc87d](https://github.com/DianCotrina/keikogobierna/commit/9bdc87da26382a41f8ebe45f474c7cd862fdbfc4))
* semantic versioning with release-please, CI gate, footer version ([2126cc5](https://github.com/DianCotrina/keikogobierna/commit/2126cc5d9804724fddfff189129d465a398ed9ba))
* single-file landing page baseline ([456f7dc](https://github.com/DianCotrina/keikogobierna/commit/456f7dc6fdaa5c67c498c7e18fca9a80f0f1343c))
* validate evidence schema; fulfilled requires evidence ([f694c32](https://github.com/DianCotrina/keikogobierna/commit/f694c32b7268b105e832bb41a9b2e47a6443cfb3))
* wire landing page to modular renderers via main.js ([b937512](https://github.com/DianCotrina/keikogobierna/commit/b9375122ee2babc3787c56744bf665c7ee597bc8))


### Bug Fixes

* apply final-review polish (noscript reveal, stamp color safelist, doc accuracy) ([635af7c](https://github.com/DianCotrina/keikogobierna/commit/635af7c66de369062a5988701da7be1a6ac1eca5))
* detect quote-prefixed group titles in extractor ([63b6925](https://github.com/DianCotrina/keikogobierna/commit/63b6925a5ae62df1ad56558a2462c33f626fc7ef))
* guard validator against malformed list entries ([e7c1f6b](https://github.com/DianCotrina/keikogobierna/commit/e7c1f6b543c8b3f3435c7c1dbdf50165cd90ad0f))
* reveal static sections on boot failure; harden validator and helpers ([1b500c8](https://github.com/DianCotrina/keikogobierna/commit/1b500c81a14f0923ca788e907b0a45aeceff3cb5))
* validate goal indicator and table_topic non-emptiness ([094c119](https://github.com/DianCotrina/keikogobierna/commit/094c119d3ca21de0dff98cd7f60484510459c2e4))
