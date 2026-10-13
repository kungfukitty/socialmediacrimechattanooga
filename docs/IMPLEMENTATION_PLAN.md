# Chattanooga Public Safety Feed — 7-Day Full-Time Sprint

**Sprint:** Tue Oct 13 → Mon Oct 19, 2026 · full-time, about 9–10 hours a day, about 65 hours in total
**Goal:** a revenue-ready short-form channel on TikTok and YouTube Shorts by the end of Day 7: a working data-to-video pipeline, daily posting, and every monetization channel set up and pitched.
**Builders:** You (owner, host, seller) and Claude (pair-programmer, drafting, research)

> **What "done in 1 week" means.** The **product, the channel and the sales machinery** can be fully done in 7 days. **Revenue itself cannot.** TikTok Creator Rewards needs 10k followers and 100k views in 30 days. YouTube needs 1,000 subscribers and 10M Shorts views in 90 days. Sponsors want to see a few weeks of posting. The sprint therefore ends with everything that produces money **switched on and pitched**: affiliate links live and 15+ sponsor pitches sent. The first sponsor close is realistic in weeks 2–4.

---

## 1. Skills review

The review is based on the 50 repos on your GitHub, judged by repo names and organization only. Correct anything I got wrong.

| Area | Evidence in your repos | Rating | How the sprint uses it |
|---|---|---|---|
| **React / Vite frontends** | `yoh-underground-frontend*` (×6), `angelkfrontend*`, `euphoria_frontend`, `vite-react`, `gatsby-starter-portfolio-cara` | **Strong** | The **Remotion video templates are written in React**, so you design videos the way you build pages. The review queue app is plain Vite + React. |
| **Node / Express + Firebase backends** | `YOHbackend`, `YOH-API-Express-Firebase-Admin-`, `angelkbackend`, `yoh-underground-server`, `southafricaback` | **Strong** | The **whole pipeline is Node/TypeScript**: scraper, drafter, render worker and API. That means one language, no Python, and no context switching. |
| **SQL / data analysis** | `SQL_Work`, `DA_Builds`, Snowflake pipelines fork | **Strong** | Postgres schema, dedupe logic, and the "incidents by neighborhood" trend videos and sponsor stats |
| **Bots, schedulers and polling APIs** | `solana-signal-bot`, `crypto-fvg-fib-bot`, `trading2026` | **Strong** | The scraper is a signal bot: it polls a source, detects new events and fires an action. Reuse that pattern. |
| **Healthcare data / HL7 / EHR** | `HL7-INTERFACE-ANALYST-PORTFOLIO`, `HL7_DB_EHR` | **Strong (transferable)** | You already think in feeds, field mapping and privacy (PHI). Apply it to CAD fields and to excluding medical calls. |
| **Deploying to cloud hosts** | Many frontend/backend pairs; Render and Vercel are connected to this account | **Medium** | Render cron + Postgres; Vercel for the review app |
| **Video production / on-camera hosting** | None visible | **Gap** | Remotion covers the visuals. Your voiceover is the human element that keeps the channel monetizable. Day 1 includes 2 manual practice videos. |
| **Audience growth / short-form strategy** | None visible | **Gap** | Use the format and hook templates (D11). Study 3 competitor channels on Day 1. |
| **Local sales / sponsorship** | None visible | **Gap** | Day 6–7 scripts: media kit, rate card, pitch email and call script (D20–D21) |
| **Finishing one version** | 6 versions of `yoh-underground-*`, 6 of `angel*`, 4 of `ForeverDocs` | **Risk** | **Sprint rule:** one repo, one `main` branch and a deploy every day. Fix forward and never start a "v2" repo this week. |

**Net:** the build is squarely within your skills. The real risks this week are the non-code work: hosting, posting consistently and selling. The schedule gives those real hours instead of leaving them for "after."

---

## 2. Scope for 7 days

**In scope:** CAD scraper, Postgres, geocoding, exclusion filters, AI script drafts, Remotion templates for two formats, a review queue, daily posting, the content policy, the 911 outreach email, a media kit, a link page with affiliate links, a 40-prospect sponsor list, 15+ pitches, and API audit applications.

**Cut or deferred:**

- Public web map: replaced by a simple link page
- Automated metrics collection: replaced by a manual tracking sheet
- API auto-posting: waits for platform audits, so posting stays manual for now
- Scanner audio: needs a legal review first
- Second county

**Stack (matched to your skills):** Node 20 + TypeScript · Playwright (Node) · Postgres on Render (cron job for the poller) · Census Geocoder · Claude API for drafts · Remotion (React) · Vite + React review app on Vercel · MapLibre/OSM tiles with attribution.

**Key rules carried over from research:**

- A human voiceover and approval on every video. YouTube's inauthentic-content policy demonetizes templated AI output.
- The Daily Recap runs **over 60 seconds**, because TikTok Creator Rewards pays only on videos over one minute.
- Poll the county page every 3–5 minutes. It limits sessions to 15 minutes and carries an "All Rights Reserved" notice. Email the 911 district on Day 1.
- No EMS or medical, domestic, or juvenile calls. Show block-level locations only, never names, and use "reported/dispatched" wording.

---

## 3. Day-by-day plan

### Day 1 — Tue Oct 13 · Foundation (about 6 hours, afternoon)

| Time | Task | Who | Deliverable |
|---|---|---|---|
| 12:00–1:00 | Pick the brand name and handles. Create **personal** TikTok and YouTube accounts, a Gmail and a domain. | You | D1 |
| 1:00–1:30 | Send the email to the Hamilton County 911 district: describe the project and ask about reuse and data-feed access. | You (Claude drafts) | D4 |
| 1:30–3:00 | Inspect the network calls on the CAD page. Document the fields and status codes and save 3 HTML/JSON fixtures. | You + Claude | D5 |
| 3:00–4:00 | Repo scaffold: TS monorepo (`ingest/`, `db/`, `content/`, `render/`, `review/`), ESLint, Vitest, CI | Claude | D2 |
| 4:00–5:00 | Write `CONTENT_POLICY.md`: exclusions, language rules, corrections and takedown process | Claude drafts, you approve | D3 |
| 5:00–6:00 | Study 3 competitor channels, then **record and post 2 manual recaps** from today's incident list | You | D11 (input) |

**End of day:** accounts live, data source understood, first 2 posts up.

### Day 2 — Wed Oct 14 · Data pipeline (about 10 hours)

| Time | Task | Who | Deliverable |
|---|---|---|---|
| 8:00–12:00 | `ingest/`: Playwright scraper. Parse all columns, use polite polling with backoff, alert on parse errors, and test against fixtures. | You + Claude | D6 |
| 12:30–2:30 | `db/`: migrations for `incidents`, `status_events`, `geocodes`, `posts` and `sponsors`. Upsert on Master Incident number and record each status change as an event. | You (your SQL strength) | D7 |
| 2:30–5:00 | Deploy Postgres and the poller as a Render cron job running every 4 minutes. Confirm rows arrive. | You + Claude | D10 |
| 5:00–6:00 | Daily post: a manual recap | You | D16 |

**End of day:** live incidents are flowing into Postgres in production.

### Day 3 — Thu Oct 15 · Enrichment + script drafting (about 10 hours)

| Time | Task | Who | Deliverable |
|---|---|---|---|
| 8:00–10:30 | `geocode/`: Census Geocoder with a Nominatim fallback, a cache table, and points snapped to the block | Claude + you | D8 |
| 10:30–12:00 | `content/filters.ts`: exclusion rules with a test suite | Claude | D9 |
| 12:30–3:30 | `content/draft.ts`: a Claude API prompt that turns the day's eligible incidents into a recap script, caption and hashtags. **Fact-locked:** every sentence must map to a CAD field. Audit 20 samples. | You + Claude | D12 |
| 3:30–5:00 | Format spec: Incident Clip (20–40 s) and Daily Recap (60–90 s). Each uses a hook → facts → takeaway structure, plus sponsor slot rules. | You | D11 |
| 5:00–6:00 | Daily post | You | D16 |

**End of day:** the pipeline outputs a ready-to-read recap script every evening.

### Day 4 — Fri Oct 16 · Video templates (about 10 hours)

| Time | Task | Who | Deliverable |
|---|---|---|---|
| 8:00–12:00 | `render/`: Remotion project at 1080×1920 and 30fps. **Daily Recap** template: animated map pins, incident cards, lower-thirds, disclaimer bar, sponsor card slot and voiceover track. | You (React) + Claude | D13 |
| 12:30–3:00 | **Incident Clip** template, and captions burned in from the voiceover via auto-transcribe | You + Claude | D13 |
| 3:00–4:30 | Render script: pull the day's data and voiceover file, then output an .mp4 | Claude | D13 |
| 4:30–5:00 | Host guide: recording setup (phone + lav mic), script template, delivery notes | Claude | D15 |
| 5:00–6:00 | Record a voiceover and render the **first pipeline-made recap**. Post it. | You | D16 |

**End of day:** a real recap built by the pipeline is published.

### Day 5 — Sat Oct 17 · Review queue + end-to-end (about 9 hours)

| Time | Task | Who | Deliverable |
|---|---|---|---|
| 8:00–12:30 | `review/`: a Vite + React app on Vercel. It lists today's draft, lets you edit the script, upload a voiceover, approve to trigger a render, and download the .mp4 and caption. It is protected by a password. | You + Claude | D14 |
| 1:00–3:00 | End-to-end test: data → draft → edit → voiceover → render → download → post. **Time it, with a target of 20 minutes or less.** | You | D14 gate |
| 3:00–4:00 | Fix whatever made the run slow | You + Claude | — |
| 4:00–5:00 | Post a recap and 1 incident clip | You | D16 |

**End of day:** the daily routine is repeatable in about 20 minutes.

### Day 6 — Sun Oct 18 · Monetization assets (about 9 hours)

| Time | Task | Who | Deliverable |
|---|---|---|---|
| 8:00–10:00 | Link page (a Vercel static page) with affiliate links for 5–8 vetted products: cameras, dashcams, doorbells. Include disclosures. | You + Claude | D22 |
| 10:00–12:30 | Media kit and rate card: the concept, audience geography, posting cadence, sponsor slot formats and launch-sponsor pricing. Use launch rates, since the channel has no stats yet. | Claude drafts, you finalize | D20 |
| 1:00–3:30 | Sponsor prospect list of 40 local businesses: security and alarm, locksmiths, PI and defense attorneys, insurance agents, towing, auto glass, self-defense gyms. Collect names, contacts and a personalized hook for each. | You + Claude research | D21 |
| 3:30–4:30 | Pitch email, DM and call script with a follow-up sequence | Claude | D21 |
| 4:30–5:30 | Posting calendar for the next 30 days, and a manual metrics sheet | Claude | D16, D18 |
| 5:30–6:30 | Post a recap and a "how this channel works / corrections" pinned video | You | D16 |

**End of day:** everything needed to sell is ready.

### Day 7 — Mon Oct 19 · Sell + harden + hand off (about 10 hours)

| Time | Task | Who | Deliverable |
|---|---|---|---|
| 8:30–12:00 | **Send 15+ sponsor pitches** by email and DM, and make 5 calls during business hours. Offer a **free first week** to the first 2 sponsors to get a case study. | You | D21 |
| 12:30–1:30 | File the YouTube API audit and TikTok Content Posting API application | You + Claude | D17 |
| 1:30–3:30 | Hardening: parser-failure alerts, Render log checks, database backup, README run-book | Claude | D10, D2 |
| 3:30–4:30 | Log the monetization thresholds you're tracking. Note whether YouTube's lower tier is available in Studio. | You | D23 |
| 4:30–5:30 | Sprint retro, and lock in the steady-state routine (§6) | You + Claude | D24 |
| 5:30–6:30 | Post a recap and an incident clip | You | D16 |

**End of day:** the system is live, 8–10 videos are published, 15+ pitches are out and affiliate links are live.

---

## 4. Deliverables register

| ID | Deliverable | Location | Acceptance criteria |
|---|---|---|---|
| D1 | Brand + accounts | TikTok, YouTube, domain | Personal accounts with bios, links and profile art |
| D2 | Repo scaffold + CI + run-book | `/`, `.github/` | CI green; README explains deploy and daily routine |
| D3 | Content & safety policy | `docs/CONTENT_POLICY.md` | Exclusions, language rules and takedown SLA |
| D4 | 911 district outreach | `docs/legal/911_outreach.md` | Sent; reply logged |
| D5 | Data source spec + fixtures | `docs/DATA_SOURCE.md`, `ingest/fixtures/` | Fields and status codes documented; 3 fixtures |
| D6 | CAD scraper | `ingest/` | All columns parsed; fixture tests pass |
| D7 | DB schema | `db/migrations/` | Applies on Render; upsert + status history work |
| D8 | Geocoder | `geocode/` | At least 90% match; block-level output |
| D9 | Exclusion filter | `content/filters.ts` | 100% of excluded test cases blocked |
| D10 | Production poller | Render cron | Running every 4 minutes with alerts |
| D11 | Format spec | `docs/FORMATS.md` | Two formats, recap over 60 seconds |
| D12 | Script drafter | `content/draft.ts` | 20-sample audit shows no invented facts |
| D13 | Remotion templates + render script | `render/` | 1080×1920 .mp4 with captions, attribution, disclaimer |
| D14 | Review queue app | `review/` on Vercel | Full run in 20 minutes or less |
| D15 | Host guide | `docs/HOST_GUIDE.md` | Setup + script template |
| D16 | Posts + 30-day calendar | `docs/CALENDAR.md` | 8–10 videos posted during the sprint |
| D17 | API audit applications | `docs/legal/api_audits.md` | Both filed |
| D18 | Metrics sheet | `sales/metrics.csv` | Daily views and followers logged |
| D20 | Media kit + rate card | `sales/` | PDF + one-pager |
| D21 | Sponsor pipeline + scripts | `sales/pipeline.csv`, `sales/scripts.md` | 40 prospects, 15+ pitched |
| D22 | Link page + affiliate | `web/` on Vercel | Live with disclosures |
| D23 | Monetization threshold log | `docs/MONETIZATION_LOG.md` | Thresholds and current status logged |
| D24 | Retro + steady-state routine | `docs/OPERATIONS.md` | Daily and weekly routine defined |

*D19 (the public web map) moved to post-sprint.*

---

## 5. Crosswalk — deliverable × day × hours × skill fit × revenue lever

| ID | Day | Date | Hours | Owner | Your skill fit | Depends on | Monetization lever |
|---|---|---|---|---|---|---|---|
| D1 | 1 | Tue Oct 13 | 1 | You | — | — | Accounts are prerequisite for all payouts |
| D4 | 1 | Tue Oct 13 | 0.5 | You | — | — | Protects data access, and so the business |
| D5 | 1 | Tue Oct 13 | 1.5 | You + Claude | HL7 field mapping (strong) | — | Pipeline |
| D2 | 1 | Tue Oct 13 | 1 | Claude | Node (strong) | — | Pipeline |
| D3 | 1 | Tue Oct 13 | 1 | Claude → You | PHI privacy (strong) | — | Brand safety → sponsors; platform standing |
| D6 | 2 | Wed Oct 14 | 4 | You + Claude | Bots/polling (strong) | D5 | Pipeline |
| D7 | 2 | Wed Oct 14 | 2 | You | SQL (strong) | D5 | Sponsor stats; trend videos |
| D10 | 2 | Wed Oct 14 | 2.5 | You + Claude | Deploys (medium) | D6, D7 | Data archive → future licensing |
| D8 | 3 | Thu Oct 15 | 2.5 | Claude + You | APIs (strong) | D7 | Map visuals |
| D9 | 3 | Thu Oct 15 | 1.5 | Claude | — | D3 | Brand safety → sponsors |
| D12 | 3 | Thu Oct 15 | 3 | You + Claude | — | D9 | Original content → TikTok and YouTube eligibility |
| D11 | 3 | Thu Oct 15 | 1.5 | You | Short-form (gap) | Day 1 posts | **Recap over 60 seconds → TikTok Creator Rewards** |
| D13 | 4 | Fri Oct 16 | 6.5 | You + Claude | React (strong) | D11, D12 | Sponsor card slot built in |
| D15 | 4 | Fri Oct 16 | 0.5 | Claude | On-camera (gap) | D11 | Human voice → passes inauthentic-content policy |
| D14 | 5 | Sat Oct 17 | 7.5 | You + Claude | React/Vite (strong) | D12, D13 | 20-minute routine → sustainable daily output |
| D22 | 6 | Sun Oct 18 | 2 | You + Claude | Frontend (strong) | D1 | **Affiliate: first possible revenue** |
| D20 | 6 | Sun Oct 18 | 2.5 | Claude → You | Sales (gap) | D16 | **Sponsorship** |
| D21 | 6–7 | Oct 18–19 | 7.5 | You + Claude | Sales (gap) | D20 | **Sponsorship: 15+ pitches** |
| D16 | 1–7 | Daily | about 7 | You | Hosting (gap) | — | Audience growth toward payout thresholds |
| D18 | 6 | Sun Oct 18 | 0.5 | Claude | Data analysis (strong) | D16 | Media-kit stats |
| D17 | 7 | Mon Oct 19 | 1 | You + Claude | — | D14 | Future automation at scale |
| D23 | 7 | Mon Oct 19 | 1 | You | — | D16 | **TikTok Creator Rewards; YouTube Partner Program** |
| D24 | 7 | Mon Oct 19 | 1 | You + Claude | — | All | Keeps revenue work going after the sprint |

**Hours:** about 65 total. About 40 are build hours, mostly in your strong skills. About 25 are posting, hosting and selling, which are your gaps and the work that actually produces revenue.

---

## 6. After the sprint — steady state (2–3 hours a day)

| Cadence | Task |
|---|---|
| Daily (about 45 min) | Review queue → record voiceover → post the recap and 1 clip → reply to comments |
| Daily (about 30 min) | 3–5 sponsor follow-ups or new pitches |
| Weekly | Weekly Top 5 trend video, metrics review and pipeline health check |

**Revenue milestones after the sprint**

| Target | Date |
|---|---|
| First 2 sponsors running, on the free first week | by Nov 2 |
| First paid sponsor | by Nov 16 |
| $500/month recurring revenue | by Dec 31 |
| Check TikTok Creator Rewards eligibility weekly | Ongoing |

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Restarting instead of finishing (your repo history) | One repo, deploy every day, cut scope rather than slip it |
| Demonetization for templated AI content | Your voice and approval on every video |
| False reports or defamation | Fact-locked drafts, "reported" wording, no names, pinned corrections video |
| County blocks scraping or changes the page | Day 1 email, polite polling, parse alerts, manual fallback |
| Selling feels uncomfortable | Scripts written for you, and a free first week lowers the bar |

*This plan is not legal advice. Have a Tennessee media attorney review CONTENT_POLICY.md before taking paid sponsors.*
