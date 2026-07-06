# Dependabot-Alert-Bereinigung (Juli 2026)

Dokumentation der systematischen Bereinigung aller 58 zum Zeitpunkt der
Arbeit offenen Dependabot-Alerts in `Hereliesviolet/NotebookLMC`. Alle 58
Alerts sind inzwischen im Status `fixed` (verifiziert über die GitHub
Dependabot-Alerts-API, keine wurden per `dismiss` weggeklickt).

## Vorgehen

Risikobasiert in Batches, je ein Commit pro Paket (oder eng zusammengehöriger
Gruppe), damit im Fehlerfall ein einzelner `git revert` reicht:

1. Inventur: alle Alerts nach Paket gruppiert, sichere Zielversionen über die
   GHSA-Advisories (nicht nur den Alert-Text) verifiziert.
2. Dev-only/transitive Build-Zeit-Abhängigkeiten (`glob`, `postcss`) per
   `npm install`/`overrides`, getestet mit `npm run build` + `npm run lint`.
3. Isolierte Backend-Bibliotheken (`python-multipart`, `cairosvg`) mit
   gezieltem End-to-End-Test der jeweils betroffenen Funktion.
4. Restliche Backend-Pakete (`pytest`, `Markdown`, `pypdf`).
5. Next.js (+ notwendiger React-19-Begleitbump).
6. Verifikation + diese Dokumentation + CI-Workflow.

## Batches im Detail

| # | Paket(e) | Alerts | Alt → Neu | Risiko/Testtiefe |
|---|---|---|---|---|
| 1 | `glob` (npm, dev, transitiv über `@next/eslint-plugin-next`) | 1 | 10.3.10 → 10.5.0 | Minimal (nie zur Laufzeit erreichbar) - `npm run build` + `npm run lint` |
| 1 | `postcss` (npm, devDependency; Next bündelt zusätzlich eine eigene Kopie) | 1 | 8.4.47 (+ 8.4.31 in next) → 8.5.10 | Minimal (reine Build-Zeit-Abhängigkeit für Tailwind) - `npm run build` + `npm run lint`, Docker-Rebuild + Smoke-Test |
| 2 | `python-multipart` (pip, api, Upload-Endpoint) | 8 | 0.0.9 → 0.0.31 | Mittel - api-pytest (6/6) + manueller Upload-Test TXT/DOCX/PDF über den echten Upload-Endpoint |
| 2 | `cairosvg` (pip, api, Mindmap-PNG-Export) | 1 | 2.7.1 → 2.9.0 | Mittel - api-pytest (6/6) + manuelle Mindmap-Generierung + PNG-Export, visuell verifiziert |
| 3 | `pytest` (pip, api + worker, nur Test-Dependency) | 2 | 8.3.3 → 9.0.3 | Minimal (kein Laufzeit-Code) - beide Testsuiten unverändert grün nach dem Major-Bump |
| 3 | `Markdown` (pip, worker) | 1 | 3.7 → 3.8.1 | Minimal - Paket wird aktuell nirgends importiert (`parse_markdown()` nutzt einen eigenen Regex-Splitter, nicht die `markdown`-Lib); worker-pytest (15/15) + manueller `.md`-Upload |
| 3 | `pypdf` (pip, worker, PDF-Parsing inkl. OCR-Fallback) | 30 | 4.3.1 → 6.13.3 | Hoch von der Versionsdifferenz her (2 Major-Versionen), aber niedrig vom tatsächlichen Risiko: `apps/worker/app/parsing/pdf.py` nutzt nur die seit Jahren stabile Kern-API (`PdfReader`, `reader.pages`, `page.extract_text()`), keine der zwischen 4.x/5.x/6.x entfernten Legacy-Klassen. worker-pytest (15/15) + manueller Upload eines normalen Text-Layer-PDFs UND eines gescannten/bildbasierten PDFs (Vision-OCR-Fallback in den Worker-Logs bestätigt: `page 1 has no usable text layer (0 chars) - falling back to Vision OCR`) |
| 5 | `next` (+ `react`/`react-dom`/Types als notwendiger Begleitbump) | 14 | next 14.2.35 → 15.5.20, react/react-dom 18.3.1 → 19.2.7 | Hoch (Major-Version-Migration) - siehe eigener Abschnitt unten |

## Next.js 14 → 15: warum ein Major-Bump nötig war

Alle 14 ursprünglichen Next.js-Alerts wurden geprüft nicht nur über den
Alert-Text, sondern direkt über die GHSA-Advisory-Daten
(`gh api /advisories/<id>`). Ergebnis: **keine einzige Advisory hat eine
Fix-Version innerhalb der 14.x-Reihe** - jede listet als frühestmögliche
`first_patched_version` einen 15.5.x- oder 16.x-Stand. Next.js hat diese
Sicherheitsfixes nicht auf den 14.x-Branch zurückportiert. Ein Verbleib auf
14.x hätte alle 14 Alerts (11 davon High/Medium) dauerhaft offen gelassen.

Zusätzlich wurde beim finalen `npm audit` nach dem Bump auf `15.5.16`
(die zum Zeitpunkt der Alert-Inventur aktuellste sichere Version) eine
weitere, zu diesem Zeitpunkt noch nicht als Dependabot-Alert erfasste CVE
gefunden (`GHSA-26hh-7cqf-hhc6`, Middleware/Proxy-Bypass via
Segment-Prefetch-Routen), die erst ab `15.5.20` behoben ist - daher direkt
auf `15.5.20` gebumpt statt auf die ursprünglich ermittelte Minimalversion.

Next.js 15 zwingt den App Router auf React 19 (siehe
[Next.js-15-Upgrade-Guide](https://nextjs.org/docs/app/guides/upgrading/version-15)),
daher wurden `react`/`react-dom` (+ `@types/react`/`@types/react-dom`) im
selben Commit mitgezogen. Alle direkten Laufzeit-Abhängigkeiten
(`@xyflow/react`, `react-markdown`, `lucide-react`) deklarieren React-19-
kompatible Peer-Ranges.

Code-Anpassungen durch das Breaking Change "Async Request APIs" (`params`
ist jetzt ein `Promise`, auch in Client-Component-`page.tsx`-Dateien):

- `apps/frontend/app/api/[...path]/route.ts` (Route Handler, der lang
  laufende Studio-/Chat-Requests proxied) - `params` wird jetzt awaited.
- `apps/frontend/app/notebooks/[id]/page.tsx` (Client Component) - `params`
  wird über React's `use()` aufgelöst.

Keine weiteren Next.js-15-Migrationsflächen vorhanden: kein `next/image`,
kein `next/font`, kein `middleware.ts`, kein `generateMetadata` im Projekt.

Verifiziert: `npm audit` meldet `0 vulnerabilities`; Lint + Build grün;
Docker-Image neu gebaut; browser-gesteuerter Regressionstest (Notebook-
Liste, Erstellen/Öffnen/Löschen, Quellen-/Notizen-Tabs, 0 Konsolen-/
Hydration-Fehler); manueller End-to-End-Test durch den neu gebauten Proxy
(GET/POST/Multipart-Upload/Chat, alle 2xx mit korrekten Antworten).

## Nicht betroffene Pakete

Zu Beginn der Aufräumarbeit gab es die Vermutung, dass auch `weasyprint`,
`jinja2`, `qdrant-client`, `anthropic`, `openai`, `python-docx`, `pandas`,
`openpyxl`, `@xyflow/react` und `react-markdown` betroffen sein könnten -
die tatsächliche Alert-Inventur (Phase 0) hat das nicht bestätigt: keine
dieser Pakete hatte zu diesem Zeitpunkt offene Alerts.

## Kontinuierliche Absicherung

`.github/workflows/pytest.yml` baut die `api`- und `worker`-Docker-Images
1:1 wie in Produktion (`docker-compose.yml`) und führt die jeweilige
`pytest`-Suite darin aus - bei jedem Push/PR, der `apps/api/**` oder
`apps/worker/**` verändert. Das stellt sicher, dass künftige Dependency-
Bumps (Dependabot-PRs oder manuell) nicht unbemerkt Kern-Funktionalität wie
PDF-Parsing, RAG-Retrieval oder die Vision-OCR-Fallback-Logik brechen,
bevor sie gemerged werden.

## Empfehlung für die Zukunft

- Dependabot-PRs für Patch-Versionen (kein Major-Bump) können nach grünem
  CI-Lauf im Regelfall zügig gemerged werden.
- Bei Major-Version-Bumps (wie hier bei Next.js/React) immer zuerst die
  GHSA-Advisory-Daten direkt prüfen (nicht nur den Dependabot-Alert-Text),
  da die "erste sichere Version" je nach Branch-Backport-Politik des
  Projekts stark variieren kann.
