# 90-second walkthrough

Use fictional demo mode for reliable presentation. Begin on Hua Chen Manufacturing (华辰制造 / DEMO:HCM), with no dialog open.

**0–15 seconds — Research context**

“Shanghai News Insight brings company news, market context and valuation into one research workspace. I can search a company, add it to a watchlist and inspect its price history. This walkthrough uses clearly labelled fictional data.”

Search 华辰 with Ctrl/Cmd+K. Show the company and news list.

**15–30 seconds — Evidence**

“A negative headline is not automatically a negative valuation recommendation. The article panel separates news sentiment from the cash-flow model and highlights the source passage behind an extracted claim.”

Open the order-delay article and analyse it. Point to highlighted evidence.

**30–50 seconds — Research and valuation**

“The research report combines evidence with a deterministic five-year FCFF calculation. The language model explains the result; it does not invent the price or decide the numeric recommendation.”

Return to research, generate the demo report and open DCF.

**50–70 seconds — Interactive assumptions**

“Here I can inspect growth, margins, discount rates and terminal assumptions. Raising WACC reduces the value in this example. Scenarios and sensitivity expose how dependent the conclusion is on those assumptions.”

Change WACC from 9% to 15%. Show the label change. Restore the baseline.

**70–90 seconds — Reproducibility**

“Saving creates a version rather than overwriting the prior analysis. Explanations are linked to that version and become stale when assumptions change. Reports and calculation tables can be exported with their sources and assumptions.”

Save, explain and show the export control. Mention that a separate live pipeline has been tested with public sources and DeepSeek; manual financial adjustments remain explicitly labelled.

## Interview talking points

- Why deterministic finance and generated language are separate responsibilities.
- Why cumulative financial statements require TTM normalization.
- Why terminal growth must be accompanied by reinvestment.
- Why source provenance, failed attempts and missing-data states matter more than unsupported accuracy claims.
- How a versioned report stays consistent when a fresh market quote arrives.

Only quote completed checks from verification.md. Do not claim a return forecast, alpha, classification benchmark or all-market automated DCF coverage.
