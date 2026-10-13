# socialmediacrimechattanooga

This is a short-form public-safety news channel for Chattanooga and Hamilton County, published on TikTok and YouTube Shorts. A data pipeline drafts each video from the county's public CAD active-incident list, and a human host reviews, narrates and publishes it.

- **Plan, deliverables and crosswalk:** [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- **Crosswalk (spreadsheet-ready):** [docs/crosswalk.csv](docs/crosswalk.csv)

## Planned layout

```
ingest/    CAD scraper (Python + Playwright)
db/        Postgres/PostGIS migrations
geocode/   address → block-level coordinates
content/   filters + script/caption drafting
render/    Remotion vertical video templates
review/    human approval queue (Next.js on Vercel)
metrics/   platform analytics collector
web/       public map, recap archive, newsletter
sales/     media kit, sponsor pipeline, revenue
docs/      plan, policies, legal records
```

Videos describe dispatched and reported incidents only. They are not official statements from any agency.
