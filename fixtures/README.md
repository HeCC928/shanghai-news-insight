# Fictional demo fixtures

The authoritative deterministic fixture generator is `backend/app/adapters/demo.py`. It is imported directly in demo mode and makes no external request. Prices are reproducible synthetic paths; companies, news and financial values are fictional.

`scripts/export_demo_fixtures.py` writes a portable JSON snapshot generated from that same module, so documentation fixtures cannot drift into a separate implementation. Regenerate after changing the demo source.

Cases: DEMO:HCM undervalued; DEMO:YHE overvalued; DEMO:LXC fair value; DEMO:QTECH insufficient data; DEMO:HBANK unsupported sector. Recommendations are computed by the real valuation engine rather than hardcoded verdicts.
