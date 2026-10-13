# socialmediacrimechattanooga

This is a short-form public-safety news channel for Chattanooga and Hamilton County, published on TikTok and YouTube Shorts. A data pipeline drafts each video from the county's public CAD active-incident list, and a human host reviews, narrates and publishes it.

- **7-day sprint plan, skills review, deliverables and crosswalk:** [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- **Crosswalk (spreadsheet-ready):** [docs/crosswalk.csv](docs/crosswalk.csv)

## Planned layout

```
ingest/    CAD scraper (Node/TypeScript + Playwright)
db/        Postgres/PostGIS migrations
geocode/   address → block-level coordinates
content/   filters + script/caption drafting
render/    Remotion vertical video templates
review/    human approval queue (Vite + React on Vercel)
metrics/   platform analytics collector
web/       public map, recap archive, newsletter
sales/     media kit, sponsor pipeline, revenue
docs/      plan, policies, legal records
```

Videos describe dispatched and reported incidents only. They are not official statements from any agency.

## Development

Requires Node 20+.

```
npm install
npm run check    # typecheck + lint + tests (same as CI)
```

Copy `.env.example` to `.env` for local secrets. Policies: [docs/CONTENT_POLICY.md](docs/CONTENT_POLICY.md) · Data source: [docs/DATA_SOURCE.md](docs/DATA_SOURCE.md)
