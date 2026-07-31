# Project Context

## Product

AVScout is a local, bilingual scouting workspace for explainable historical
player recommendations. It helps analysts find players with similar or desired
profiles using reproducible sporting evidence rather than unsupported generated
claims.

The MVP covers the 2017/18 seasons of the Premier League, La Liga, Bundesliga,
Serie A, and Ligue 1. Historical context matters: age, club, minutes, position,
market value, and statistics must be interpreted for that season rather than for
the present day.

## Architecture

- `backend/` contains the FastAPI API and Python data/model services.
- `frontend/` contains the Next.js App Router application written in TypeScript.
- DuckDB is the intended local analytical database.
- The primary recommendation model is a function-specific weighted nearest-neighbor
  model. PCA is an experimental comparison model and must not silently replace the
  primary model.
- The frontend consumes calculated API results and does not calculate or reorder
  recommendations.

## Recommendation Rules

- Objective filters are applied before similarity ranking.
- Filters must never be relaxed silently to fill the top five.
- The default minimum playing-time threshold is 900 minutes and is adjustable.
- Budget-constrained rankings include only players with known historical market
  value at or below the budget.
- Unknown market values may be shown separately as financially unverifiable
  honorable mentions, never as guessed values.
- Comparisons are made within the relevant player function.
- Compatibility is relative profile similarity, not transfer-success probability.
- Results must include enough evidence to explain favorable similarities and
  relevant divergences.

## LLM Boundary

- The ranking engine must work when OpenAI is unavailable.
- The LLM may translate natural-language requests into validated structured
  filters, preferences, and weights.
- The LLM may turn already-calculated evidence into grounded Portuguese or English
  explanations.
- The LLM must never calculate similarity, change result ordering, fill missing
  values, or invent football facts.

## Data And Provenance

- Wyscout public event data is the sporting-action source.
- Transfermarkt public datasets provide historical metadata, positions, and market
  values where available.
- Identity matches must retain confidence and matching evidence.
- Ambiguous matches remain isolated for review instead of being silently accepted.
- Every external source must retain attribution and documented provenance.
- Raw downloads and generated analytical datasets are not source-controlled.

## Testing Boundaries

- The primary test seam is the public recommendation API.
- API tests should use a small deterministic historical fixture and a fake LLM
  provider while exercising real filtering, ranking, evidence, and fallback paths.
- Data-build tests should validate the reproducible build command at its public
  boundary.
- Browser tests should cover only minimal user journeys such as synchronized
  filters/chat and rendering a recommendation; ranking behavior belongs in API
  tests.
