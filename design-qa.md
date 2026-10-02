# Design QA — 沪讯

Date: 2026-09-19

final result: passed

## Visual truth and comparison conditions

- Source: `assets/reference-dark-terminal.png`, 1487×1058 pixels.
- Final implementation: `docs/screenshots/research-reference-size.png`, CSS viewport1487×1058, devicePixelRatio1. Source and final capture were opened together in one comparison input after the last fix.
- Focused comparison: `source-header.png` and `implementation-header.png`, both720×190, presented together. The source was rendered at natural resolution and scrolled to image coordinate0,0 before capture.
- Other captures: research/valuation desktop, 1280 breakpoint, 390×844 mobile, actual live-company report, news evidence, watchlist, prompts and settings.
- State: dark theme, fictional demo company, research ready, no open dialog. The source is a news-detail concept; the implementation follows the user's approved change to company research plus DCF. Content and panel purpose therefore differ intentionally. Source mock prices and example claims are not copied as real financial data.
- Screenshot capture can exclude browser scrollbar gutters, and early captures after viewport changes retained an earlier frame. The final reference-size capture was repeated after layout settled. It is the full-view comparison authority, rather than inferring clipping from an intermediate capture.

## Findings and resolved iterations

| Severity | Earlier finding | Fix | Post-fix evidence |
| --- | --- | --- | --- |
| P2 | Phone assumption editor pushed valuation result below the first viewport | Result first; dedicated parameter dialog with explicit return control | valuation-390.png; result/label/scenarios visible, dialog edit verified |
| P2 | Development indicator overlapped phone navigation | Disabled developer indicator; final checks use production build | Mobile navigation clicks and final screenshots |
| P2 | Wordmark used a different calligraphic font | Reused actual selected-reference image region as a raster wordmark; no reconstructed logo glyphs | source-header.png / implementation-header.png |
| P2 | Selected pessimistic scenario did not show corresponding editor values | Editor displays selected scenario inputs, then edits become a custom base | Pessimistic WACC10% and matrix25.03→WACC10% observed in browser |
| P2 | Add-company entry selected research instead of adding to watchlist | Separate search intent, awaited add and inline error state | Added QTECH, refreshed, verified presence and removed successfully |

No actionable P0/P1/P2 remains in the observed design states.

## Required fidelity surfaces

- **Fonts/typography:** Chinese sans-serif body and bold headings preserve the financial-terminal hierarchy. News/report prose is14px desktop/13px mobile, article body15px mobile; metadata is smaller. Source wordmark now uses source pixels. Wrapping at390px is intentional. The image capture's antialiasing differs from the source raster; it is not treated as a new font asset.
- **Spacing/layout rhythm:** 80px desktop header, narrow navigation, persistent watchlist, central workspace and right research panel preserve the concept's workbench composition. The written specification's88px navigation and added quote section intentionally change the source proportions. Mobile uses bottom navigation, research tabs and a parameter dialog; wide numeric tables scroll inside their own region.
- **Colors/tokens:** charcoal surfaces, thin slate dividers, amber actions/selected states, subdued metadata and red/green market changes are retained. Recommendation has explicit text, not color alone. No decorative artwork was added.
- **Image/asset fidelity:** actual source wordmark reused at a measured crop; standard interface icons use the installed icon library. Charts and financial range markers are functional data visualizations. No screenshot acts as the entire interface.
- **Copy/content:** Chinese product text describes company research, sources, assumptions and uncertainty. Backtest is removed. Demo/live states are prominent; no unverifiable accuracy, profit promise, fake probability or application-process wording appears in product controls.

## Interaction and accessibility evidence

Search keyboard Enter, labelled input controls, focus-managed dialogs, chart data table, explicit state labels, visible loading/error/empty states, watchlist persistence, evidence highlights, DCF recalculation, scenario/matrix interaction, saved explanation invalidation, batch results and downloads were checked. 1440,1280 and390px layouts were exercised. Final console error log read was empty. Detailed functional limits are recorded in `docs/verification.md`.

## Follow-up polish / residual test gaps

- P3: Small metadata can be made larger in a future density preference; primary text already has greater hierarchy.
- P3: Desktop source uses a wider navigation rail, while the approved implementation specification uses88px. Retain the specification unless the user prefers the source rail proportions.
- CSV native file chooser automation timed out. API import/retry passes; this is a browser automation gap, not a visual pass claim.
- No independent screen-reader audit or broad cross-browser certification was performed.

## Implementation checklist

- [x] Compare source and rendered app together, full view and header detail.
- [x] Resolve above P2 findings and capture revised implementation.
- [x] Verify all five fidelity surfaces and responsive core controls.
- [x] Keep formal local preview running and retain screenshots with the project.
