# Notices des composants tiers

NoteClaire est publié sous licence [GNU AGPL-3.0](LICENSE). Il s'appuie sur les composants ci-dessous,
distribués sous leurs propres licences, toutes compatibles avec l'AGPL-3.0 pour cet usage.

## Polices

| Police | Licence | Fichier de licence |
| --- | --- | --- |
| [Lexend](https://github.com/googlefonts/lexend) (interface et site) | SIL Open Font License 1.1 | [site/OFL-Lexend.txt](site/OFL-Lexend.txt) |
| [Caveat](https://github.com/googlefonts/caveat) (aspect manuscrit des schémas) | SIL Open Font License 1.1 | [backend/app/assets/OFL.txt](backend/app/assets/OFL.txt) |

La licence OFL autorise l'usage, la redistribution et l'intégration dans un logiciel, y compris
commercial, à condition de conserver la mention de copyright et le texte de la licence.

## Dépendances

Liste des dépendances **de production** (les outils de développement ne sont pas distribués),
générée à partir des fichiers de verrouillage (`backend/uv.lock`, `frontend/package-lock.json`).
Quelques composants sont sous MPL-2.0 (`certifi`, `dompurify` en double licence avec Apache-2.0) :
licence à copyleft limité aux fichiers eux-mêmes, sans effet sur le reste du code.

### Python (42 paquets)

- MIT : 18
- BSD-3-Clause : 13
- Apache-2.0 : 3
- MPL-2.0 : 1
- MIT-0 : 1
- Apache-2.0 OR BSD-3-Clause : 1
- ? : 1
- MIT-CMU : 1
- MIT OR Apache-2.0 : 1
- PSF-2.0 : 1
- MIT License : 1

<details>
<summary>Liste complète</summary>

| Paquet | Version | Licence |
| --- | --- | --- |
| alembic | 1.20.0 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| click | 8.5.0 | BSD-3-Clause |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| fastapi | 0.143.0 | MIT |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpcore2 | 2.13.1 | BSD-3-Clause |
| httptools | 0.9.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| httpx2 | 2.13.1 | BSD-3-Clause |
| httpx2-jsfetch | ? | ? |
| idna | 3.20 | BSD-3-Clause |
| jiter | 0.17.0 | MIT |
| mako | 1.4.3 | MIT |
| markupsafe | 3.0.4 | BSD-3-Clause |
| openai | 3.29.0 | Apache-2.0 |
| opentelemetry-api | 1.45.1 | Apache-2.0 |
| pillow | 12.3.0 | MIT-CMU |
| pycparser | 3.11 | BSD-3-Clause |
| pydantic | 2.14.1 | MIT |
| pydantic-core | 2.50.1 | MIT |
| pydantic-settings | 2.15.0 | MIT |
| pyjwt | 2.15.1 | MIT |
| pypdf | 6.20.0 | BSD-3-Clause |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| pyyaml | 6.0.3 | MIT |
| sniffio | 1.3.1 | MIT OR Apache-2.0 |
| sqlalchemy | 2.1.4 | MIT |
| starlette | 1.7.0 | BSD-3-Clause |
| truststore | 0.10.4 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| uvloop | 0.23.0 | MIT License |
| watchfiles | 1.3.0 | MIT |
| websockets | 17.2 | BSD-3-Clause |

</details>

### JavaScript (264 paquets)

- MIT : 202
- ISC : 39
- Apache-2.0 : 8
- BSD-3-Clause : 5
- BSD-2-Clause : 2
- MPL-2.0 : 2
- OFL-1.1 : 1
- PSF-2.0 : 1
- (MPL-2.0 OR Apache-2.0) : 1
- EPL-2.0 : 1
- MIT (selon le dépôt amont) : 1
- Unlicense : 1

<details>
<summary>Liste complète</summary>

| Paquet | Version | Licence |
| --- | --- | --- |
| @antfu/install-pkg | 2.1.0 | MIT |
| @babel/helper-string-parser | 7.29.7 | MIT |
| @babel/helper-string-parser | 8.0.6 | MIT |
| @babel/helper-validator-identifier | 7.29.7 | MIT |
| @babel/helper-validator-identifier | 8.0.6 | MIT |
| @babel/parser | 7.29.9 | MIT |
| @babel/parser | 8.0.7 | MIT |
| @babel/types | 7.29.8 | MIT |
| @babel/types | 8.0.6 | MIT |
| @braintree/sanitize-url | 7.1.2 | MIT |
| @chevrotain/cst-dts-gen | 13.2.0 | Apache-2.0 |
| @chevrotain/gast | 13.2.0 | Apache-2.0 |
| @chevrotain/regexp-to-ast | 13.2.0 | Apache-2.0 |
| @chevrotain/types | 13.2.0 | Apache-2.0 |
| @chevrotain/utils | 13.2.0 | Apache-2.0 |
| @floating-ui/core | 1.8.0 | MIT |
| @floating-ui/dom | 1.8.0 | MIT |
| @floating-ui/utils | 0.2.12 | MIT |
| @fontsource-variable/lexend | 5.3.0 | OFL-1.1 |
| @iconify/types | 2.0.0 | MIT |
| @iconify/utils | 3.1.7 | MIT |
| @jridgewell/gen-mapping | 0.3.13 | MIT |
| @jridgewell/remapping | 2.3.5 | MIT |
| @jridgewell/resolve-uri | 3.1.2 | MIT |
| @jridgewell/sourcemap-codec | 1.6.0 | MIT |
| @jridgewell/trace-mapping | 0.3.31 | MIT |
| @mermaid-js/parser | 2.0.1 | MIT |
| @oxc-project/types | 0.153.0 | MIT |
| @rolldown/binding-linux-x64-gnu | 1.2.13 | MIT |
| @rolldown/pluginutils | 1.0.1 | MIT |
| @tiptap/core | 3.31.4 | MIT |
| @tiptap/extension-blockquote | 3.31.4 | MIT |
| @tiptap/extension-bold | 3.31.4 | MIT |
| @tiptap/extension-bubble-menu | 3.31.4 | MIT |
| @tiptap/extension-bullet-list | 3.31.4 | MIT |
| @tiptap/extension-code | 3.31.4 | MIT |
| @tiptap/extension-code-block | 3.31.4 | MIT |
| @tiptap/extension-document | 3.31.4 | MIT |
| @tiptap/extension-dropcursor | 3.31.4 | MIT |
| @tiptap/extension-floating-menu | 3.31.4 | MIT |
| @tiptap/extension-gapcursor | 3.31.4 | MIT |
| @tiptap/extension-hard-break | 3.31.4 | MIT |
| @tiptap/extension-heading | 3.31.4 | MIT |
| @tiptap/extension-highlight | 3.31.4 | MIT |
| @tiptap/extension-horizontal-rule | 3.31.4 | MIT |
| @tiptap/extension-image | 3.31.4 | MIT |
| @tiptap/extension-italic | 3.31.4 | MIT |
| @tiptap/extension-link | 3.31.4 | MIT |
| @tiptap/extension-list | 3.31.4 | MIT |
| @tiptap/extension-list-item | 3.31.4 | MIT |
| @tiptap/extension-list-keymap | 3.31.4 | MIT |
| @tiptap/extension-ordered-list | 3.31.4 | MIT |
| @tiptap/extension-paragraph | 3.31.4 | MIT |
| @tiptap/extension-strike | 3.31.4 | MIT |
| @tiptap/extension-table | 3.31.4 | MIT |
| @tiptap/extension-text | 3.31.4 | MIT |
| @tiptap/extension-underline | 3.31.4 | MIT |
| @tiptap/extensions | 3.31.4 | MIT |
| @tiptap/markdown | 3.31.4 | MIT |
| @tiptap/pm | 3.31.4 | MIT |
| @tiptap/starter-kit | 3.31.4 | MIT |
| @tiptap/vue-3 | 3.31.4 | MIT |
| @types/d3 | 7.4.3 | MIT |
| @types/d3-array | 3.2.2 | MIT |
| @types/d3-axis | 3.0.6 | MIT |
| @types/d3-brush | 3.0.6 | MIT |
| @types/d3-chord | 3.0.6 | MIT |
| @types/d3-color | 3.1.3 | MIT |
| @types/d3-contour | 3.0.6 | MIT |
| @types/d3-delaunay | 6.0.4 | MIT |
| @types/d3-dispatch | 3.0.7 | MIT |
| @types/d3-drag | 3.0.7 | MIT |
| @types/d3-dsv | 3.0.7 | MIT |
| @types/d3-ease | 3.0.2 | MIT |
| @types/d3-fetch | 3.0.7 | MIT |
| @types/d3-force | 3.0.10 | MIT |
| @types/d3-format | 3.0.4 | MIT |
| @types/d3-geo | 3.1.1 | MIT |
| @types/d3-hierarchy | 3.1.7 | MIT |
| @types/d3-interpolate | 3.0.4 | MIT |
| @types/d3-path | 3.1.1 | MIT |
| @types/d3-polygon | 3.0.2 | MIT |
| @types/d3-quadtree | 3.0.6 | MIT |
| @types/d3-random | 3.0.4 | MIT |
| @types/d3-scale | 4.0.9 | MIT |
| @types/d3-scale-chromatic | 3.1.0 | MIT |
| @types/d3-selection | 3.0.12 | MIT |
| @types/d3-shape | 3.2.0 | MIT |
| @types/d3-time | 3.0.4 | MIT |
| @types/d3-time-format | 4.0.3 | MIT |
| @types/d3-timer | 3.0.2 | MIT |
| @types/d3-transition | 3.0.9 | MIT |
| @types/d3-zoom | 3.0.9 | MIT |
| @types/estree | 1.0.9 | MIT |
| @types/geojson | 7946.0.16 | MIT |
| @types/node | 26.6.5 | MIT |
| @types/trusted-types | 2.0.7 | MIT |
| @upsetjs/venn.js | 2.0.0 | MIT |
| @vscode/markdown-it-katex | 1.1.2 | MIT |
| @vue-macros/common | 3.1.4 | MIT |
| @vue/compiler-core | 3.5.43 | MIT |
| @vue/compiler-dom | 3.5.43 | MIT |
| @vue/compiler-sfc | 3.5.43 | MIT |
| @vue/compiler-ssr | 3.5.43 | MIT |
| @vue/devtools-api | 8.2.1 | MIT |
| @vue/devtools-kit | 8.2.1 | MIT |
| @vue/devtools-shared | 8.2.1 | MIT |
| @vue/reactivity | 3.5.43 | MIT |
| @vue/runtime-core | 3.5.43 | MIT |
| @vue/runtime-dom | 3.5.43 | MIT |
| @vue/server-renderer | 3.5.43 | MIT |
| @vue/shared | 3.5.43 | MIT |
| acorn | 8.19.0 | MIT |
| argparse | 3.0.2 | PSF-2.0 |
| ast-kit | 2.2.0 | MIT |
| ast-kit | 3.0.0 | MIT |
| ast-walker-scope | 0.10.0 | MIT |
| birpc | 2.9.0 | MIT |
| chevrotain | 13.2.0 | Apache-2.0 |
| chokidar | 5.0.0 | MIT |
| commander | 15.0.0 | MIT |
| commander | 7.2.0 | MIT |
| confbox | 0.1.8 | MIT |
| confbox | 0.3.1 | MIT |
| cose-base | 1.0.3 | MIT |
| cose-base | 2.2.0 | MIT |
| csstype | 3.2.3 | MIT |
| cytoscape | 3.34.3 | MIT |
| cytoscape-cose-bilkent | 4.1.0 | MIT |
| cytoscape-fcose | 2.2.0 | MIT |
| d3 | 7.9.0 | ISC |
| d3-array | 2.12.1 | ISC |
| d3-array | 3.2.4 | ISC |
| d3-axis | 3.0.0 | ISC |
| d3-brush | 3.0.0 | ISC |
| d3-chord | 3.0.1 | ISC |
| d3-color | 3.1.0 | ISC |
| d3-contour | 4.0.2 | ISC |
| d3-delaunay | 6.0.4 | ISC |
| d3-dispatch | 3.0.1 | ISC |
| d3-drag | 3.0.0 | ISC |
| d3-dsv | 3.0.1 | ISC |
| d3-ease | 3.0.1 | BSD-3-Clause |
| d3-fetch | 3.0.1 | ISC |
| d3-force | 3.0.0 | ISC |
| d3-format | 3.1.2 | ISC |
| d3-geo | 3.1.1 | ISC |
| d3-hierarchy | 3.1.2 | ISC |
| d3-interpolate | 3.0.1 | ISC |
| d3-path | 1.0.9 | ISC |
| d3-path | 3.1.0 | ISC |
| d3-polygon | 3.0.1 | ISC |
| d3-quadtree | 3.0.1 | ISC |
| d3-random | 3.0.1 | ISC |
| d3-sankey | 0.12.3 | BSD-3-Clause |
| d3-scale | 4.0.2 | ISC |
| d3-scale-chromatic | 3.1.0 | ISC |
| d3-selection | 3.0.0 | ISC |
| d3-shape | 1.3.7 | ISC |
| d3-shape | 3.2.0 | ISC |
| d3-time | 3.1.0 | ISC |
| d3-time-format | 4.1.0 | ISC |
| d3-timer | 3.0.1 | ISC |
| d3-transition | 3.0.1 | ISC |
| d3-zoom | 3.0.0 | ISC |
| dagre-d3-es | 7.0.14 | MIT |
| dayjs | 1.11.23 | MIT |
| delaunator | 5.1.0 | ISC |
| detect-libc | 2.1.2 | Apache-2.0 |
| diff | 9.0.0 | BSD-3-Clause |
| dompurify | 3.4.16 | (MPL-2.0 OR Apache-2.0) |
| elkjs | 0.9.3 | EPL-2.0 |
| entities | 7.0.1 | BSD-2-Clause |
| entities | 8.1.0 | BSD-2-Clause |
| es-toolkit | 1.52.0 | MIT |
| estree-walker | 2.0.2 | MIT |
| estree-walker | 3.0.3 | MIT |
| exsolve | 1.1.3 | MIT |
| fdir | 6.5.0 | MIT |
| hachure-fill | 0.5.2 | MIT |
| hookable | 5.5.3 | MIT |
| iconv-lite | 0.6.3 | MIT |
| import-meta-resolve | 4.2.0 | MIT |
| internmap | 1.0.1 | ISC |
| internmap | 2.0.3 | ISC |
| jiti | 2.7.0 | MIT |
| katex | 0.19.0 | MIT |
| khroma | 2.1.0 | MIT (selon le dépôt amont) |
| layout-base | 1.0.2 | MIT |
| layout-base | 2.0.1 | MIT |
| lightningcss | 1.33.0 | MPL-2.0 |
| lightningcss-linux-x64-gnu | 1.33.0 | MPL-2.0 |
| linkify-it | 6.1.0 | MIT |
| linkifyjs | 4.3.3 | MIT |
| local-pkg | 1.2.1 | MIT |
| lodash-es | 4.18.1 | MIT |
| lucide-vue-next | 1.0.0 | ISC |
| magic-string | 0.30.21 | MIT |
| magic-string | 1.4.3 | MIT |
| magic-string-ast | 1.0.3 | MIT |
| markdown-it | 15.0.2 | MIT |
| markdown-it-container | 4.0.0 | MIT |
| markdown-it-mark | 4.0.0 | MIT |
| marked | 16.4.2 | MIT |
| marked | 17.0.6 | MIT |
| mdurl | 2.1.0 | MIT |
| mermaid | 12.1.0 | MIT |
| mlly | 1.8.2 | MIT |
| muggle-string | 0.4.1 | MIT |
| nanoid | 3.3.20 | MIT |
| nostics | 1.3.0 | MIT |
| orderedmap | 2.1.1 | MIT |
| package-manager-detector | 1.9.0 | MIT |
| path-data-parser | 0.1.0 | MIT |
| pathe | 2.0.3 | MIT |
| perfect-debounce | 2.1.0 | MIT |
| picocolors | 1.1.1 | ISC |
| picomatch | 4.0.7 | MIT |
| pkg-types | 1.3.1 | MIT |
| pkg-types | 2.3.3 | MIT |
| points-on-curve | 0.2.0 | MIT |
| points-on-path | 0.2.1 | MIT |
| postcss | 8.5.29 | MIT |
| prosemirror-changeset | 2.4.4 | MIT |
| prosemirror-commands | 1.7.2 | MIT |
| prosemirror-dropcursor | 1.8.4 | MIT |
| prosemirror-gapcursor | 1.4.1 | MIT |
| prosemirror-history | 1.5.1 | MIT |
| prosemirror-inputrules | 1.5.1 | MIT |
| prosemirror-keymap | 1.2.3 | MIT |
| prosemirror-model | 1.25.12 | MIT |
| prosemirror-schema-list | 1.5.1 | MIT |
| prosemirror-state | 1.4.4 | MIT |
| prosemirror-tables | 1.8.5 | MIT |
| prosemirror-transform | 1.12.2 | MIT |
| prosemirror-view | 1.42.6 | MIT |
| punycode.js | 2.3.1 | MIT |
| quansync | 0.2.11 | MIT |
| readdirp | 5.1.1 | MIT |
| robust-predicates | 3.0.3 | Unlicense |
| rolldown | 1.2.13 | MIT |
| rope-sequence | 1.3.4 | MIT |
| roughjs | 4.6.6 | MIT |
| rw | 1.3.3 | BSD-3-Clause |
| safer-buffer | 2.1.2 | MIT |
| scule | 1.3.0 | MIT |
| source-map-js | 1.2.2 | BSD-3-Clause |
| stylis | 4.4.0 | MIT |
| tinyexec | 1.3.1 | MIT |
| tinyglobby | 0.2.17 | MIT |
| ts-dedent | 2.3.0 | MIT |
| typescript | 6.0.3 | Apache-2.0 |
| uc.micro | 3.0.0 | MIT |
| ufo | 1.6.4 | MIT |
| undici-types | 8.9.0 | MIT |
| unplugin | 3.4.0 | MIT |
| unplugin-utils | 0.3.2 | MIT |
| uuid | 14.0.3 | MIT |
| vite | 8.3.4 | MIT |
| vue | 3.5.43 | MIT |
| vue-router | 5.4.0 | MIT |
| w3c-keyname | 2.2.8 | MIT |
| webpack-virtual-modules | 0.6.2 | MIT |
| yaml | 2.9.1 | ISC |

</details>

## Autres éléments

- Le logo, les icônes et les captures d'écran de ce dépôt sont des œuvres du projet, publiées sous
  la même licence que le code.
- NoteClaire ne contient aucun programme officiel de l'Éducation nationale : ils sont téléchargés à la
  demande depuis les sites officiels (voir [docs/configuration.md](docs/configuration.md)).
