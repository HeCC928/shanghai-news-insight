# Source release validation — 2026-10-02

This record covers the GitHub source package, not a public deployment.

| Check | Result |
| --- | --- |
| Backend tests in working project | 54 passed |
| Backend tests in staged source package | 54 passed, using the existing installed Python environment and a temporary test database |
| Frontend type checking | Passed on the source-matching working project |
| Frontend production build | Passed on the source-matching working project |
| Fresh dependency installation | Not repeated; locked Python and npm dependencies are included |
| README screenshots | Four new screenshots captured from the actual running build; existing desktop/mobile validation images retained |
| README image and relative document references | Checked during packaging |
| Secrets and generated files | `.env`, database, runtime state, dependency directories and build outputs excluded; archive content checked before delivery |

The tests emitted two deprecation warnings from Starlette/httpx/anyio integration; no tests failed. The dependency warnings remain maintenance work.

## Evidence dates

- New screenshots: October 2, 2026.
- Maotai preparation: September 27, 2026; quote September 24; statement period June 30.
- Historical desktop/mobile PNGs and earlier benchmark record: September 19, 2026.

The prepared Maotai workflow completed a research report, valuation explanation and suggestions, nine article analyses, a nine-article batch and three follow-up answers. No new paid model call was made solely to create this release package. The author's SQLite database and live source cache are not distributed.

## Reproduction boundaries

The repository starts with fictional demo fixtures. Live research depends on network access, data availability, a configured DeepSeek account and sufficiently reviewed financial inputs. The prepared presentation page requires a locally prepared snapshot. A fresh checkout does not automatically reproduce the historical screenshot values.

Earlier measurements are recorded in [verification.md](verification.md); they are dated observations rather than current service guarantees. No classification-accuracy, return-forecasting or investment-performance benchmark is claimed.
