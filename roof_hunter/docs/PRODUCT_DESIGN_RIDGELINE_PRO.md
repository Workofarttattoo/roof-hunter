# Ridgeline — Product & Experience Design

This document merges the **Roof Hunter Pro** vision (storm intelligence, maps, lead gen) with the **Alexandria** editorial system (hierarchy, typography, surfaces) and aligns with code already branded **Ridgeline** / **RoofMap AI** in this repository.

## Naming (recommended)

| Layer | Name | Use |
|--------|------|-----|
| **Platform** | **Ridgeline** | APIs, voice, dashboard chrome, B2B comms (`dashboard_api.py`, ElevenLabs, SMS copy). |
| **Map / intelligence UI** | **Ridgeline AI · RoofMap** | App shell title, map product (matches `roofmap_ai/frontend`). |
| **Campaign / tier** | **Roof Hunter Pro** | Optional commercial tier or landing hero: *“Roof Hunter Pro, powered by Ridgeline”* — keeps SEO and existing “roof hunter” equity without splitting engineering brands. |

**Do not** introduce a third engineering name (e.g. separate repos or APIs called “Roof Hunter Pro”). Public tech face: **Ridgeline**; commercial packaging can still say **Pro**.

## North stars (from merged inputs)

1. **Product:** Real-time NOAA + MRMS/SPC context, historical date search, hail/wind layers, lead density — competitive with HailTrace/Nearmap on **clarity**, not clutter.
2. **Marketing:** Premium, “property intelligence” trust — Nearmap-grade restraint.
3. **System (Alexandria rules applied):** Hierarchy via **surface tiers**, not 1px borders; serif authority for narrative; **one primary action per view**; rounded geometry; glass for floating panels on the map.

## Dual theme: Editorial vs Command

Alexandria’s palette is light/editorial; the storm plan calls for ultra-dark + cyan. **Resolve by context**, not by picking one:

### A — Editorial (landing, pricing, property-intel story)

- **Intent:** “Digital curator” — dense facts, calm confidence.
- **Surfaces:** Light stack per Alexandria — `surface-container-lowest` → `surface-dim` steps; **no hard borders**; ghost outlines at ~15% if needed.
- **Accent:** Primary `#094cb2` for links and primary CTAs; **tertiary / archival gold** `#6d5e00` for badges (“MRMS verified”, “24h swath”).
- **Type:** **Noto Serif** headlines, **Inter** body, **Public Sans** labels/meta.
- **CTAs:** Gradient primary → primary-container; glass nav at 80% opacity + ~20px blur.

### B — Command (Storm Intelligence Dashboard)

- **Intent:** Long-session ops — low glare, high signal, map-first.
- **Surfaces:** Ultra-dark bases (`#0a0e14` → `#121a22` tiers) — same *rule* as Alexandria (tiered backgrounds, not borders), different hue.
- **Accent:** **Cyan** `#22d3ee` or `#06b6d4` for live data, playheads, and “now” indicators; reserve Alexandria **blue** for primary buttons that leave the map (upgrade, export, billing).
- **Gold:** Same tertiary gold for **severity badges** and verified radar layers — ties marketing and product.
- **Type:** **Inter** primary UI; **Noto Serif** only in empty states, insights, or report exports — keeps dashboard legible at small sizes.
- **Map panels:** Glass sidebar (Alexandria glass rule) over dark basemap; storm polygons use semantic greens/yellows/reds with **WCAG-checked** contrast on dark.

**Rule:** Editorial sells trust; Command sells throughput. Shared tokens: gold badge, Inter body, gradient primary on CTAs, no sharp corners.

## Information architecture (site / app map)

Maps the reimagined plan to concrete surfaces:

| Plan section | Delivery |
|----------------|----------|
| **Landing hook** | Marketing site + optional Cesium/MapLibre hero with **lightweight** overlay (MRMS or tile stub); value prop; logo ticker; “storms last 24h” = embedded iframe or shared **RoofMap** read-only view. |
| **Storm Intelligence Dashboard** | **`roofmap_ai` frontend** + backend: layers — hail severity polygons, wind (if/when layered), NWS watches/warnings (GeoJSON), historical date picker tied to ingest DB or API. |
| **Property intelligence / lead gen** | Story page (Editorial) + in-app property drawer (already in RoofMap direction); explain scoring, MRMS/SPC provenance, automation (CRM/SMS) as diagrams. |
| **Pricing / ROI** | Editorial pricing cards; interactive calculator (job size → qualified lead estimate) — static formula v1, API later. |

## Data & trust copy (differentiators)

Surface in UI and footnotes:

- **SPC / LSR** — spotter and reports (existing ingest).
- **MRMS MESH** — radar-estimated hail max (see `mrms_mesh_ingest.py`); label as *model estimate*, not ground truth.
- **Satellite / CV** — damage signals where `ROOF_YOLO_WEIGHTS` or heuristic runs; disclosure when confidence is heuristic-only.

## Engineering alignment (this repo)

| Capability | Where it lives |
|------------|----------------|
| Map + property API | `roofmap_ai/backend` |
| Storm ingest, MRMS | `live_hail_ingest.py`, `mrms_mesh_ingest.py` |
| Forensic / credits / ops API | `src/dashboard_api.py` (“Ridgeline Forensic Dashboard API”) |
| Legacy dashboard | `web_dashboard/` |

**Next build steps (non-binding):** unify auth and env naming under `RIDGE_*`, share a small **design tokens** package (CSS variables) for Editorial vs Command, and expose layer toggles in RoofMap that match the Command theme.

## One-line positioning

**Ridgeline** — *Forensic storm intelligence for roofers: live MRMS and SPC context, scored leads, and proof you can show the homeowner.*

**Roof Hunter Pro** (optional sleeve) — *The full Ridgeline stack for teams that want national scale and API access.*

---

*Sources internalized: `project_plan_roof_hunter_pro_reimagined.md`, `DESIGN.md` (Alexandria).*
