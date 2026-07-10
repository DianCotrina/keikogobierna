# Changelog

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
