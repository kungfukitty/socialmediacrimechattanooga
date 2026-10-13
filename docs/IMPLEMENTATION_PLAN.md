# Chattanooga Public Safety Feed — Implementation Plan

**Goal:** a monetized short-form public-safety news channel for Chattanooga / Hamilton County on TikTok and YouTube Shorts. The channel is powered by an automated data pipeline and has a human host.
**Start date:** Tue Oct 13, 2026 · **Plan horizon:** 6 months (to Apr 2027)
**Status:** Week 1. The repo is empty, and this is the first commit.

---

## 1. Key decisions (read first)

Research into current platform rules changed the original concept in four ways.

| # | Original idea | Problem | Decision |
|---|---|---|---|
| 1 | Auto-generate one templated video per incident with no human involved | YouTube's **inauthentic content** policy, enforced since Jul 15, 2025, bars templated, mass-produced and minimal-value AI content from monetization. TikTok's Creator Rewards pays only for **original** videos. A fully automated card farm fails both rules, so it can grow but not earn. | **Automation drafts and a human publishes.** The pipeline finds incidents, drafts scripts and renders visuals. A host records voiceover and adds context, and approves every post. |
| 2 | 15–30 second per-incident clips | TikTok Creator Rewards pays only on videos **longer than 1 minute**. | Two formats: short **incident clips** build reach, and a **60–90 second daily recap** earns Creator Rewards. |
| 3 | Live scanner audio + AI transcription | Rebroadcasting scanner feeds such as Broadcastify for profit carries terms-of-service and federal radio-law risk. Transcription errors have caused false "active shooter" reports for competitors. | **Phase 1 uses public CAD data only** and no scanner audio. Audio is reconsidered in Phase 5 after a legal review. |
| 4 | Poll the county site every 60 seconds | The Hamilton County 911 page limits sessions to 15 minutes, fills its table with JavaScript, and carries an "All Rights Reserved" notice. | Poll every **3–5 minutes** with a headless browser and an identifying User-Agent. **Ask the 911 district for permission or a data feed** in Week 1. |

**Main earner:** platform payouts are small at local scale. **Local sponsorships** are the realistic primary revenue, and they can be sold before platform thresholds are met (see §2).

---

## 2. Monetization model

Revenue streams are listed in the order they become available.

| Stream | Unlock condition | Realistic timing | Notes |
|---|---|---|---|
| **Local sponsorship** ("Safety Recap presented by …") | About 3–5k engaged local followers and a media kit | Months 2–3 | Target security and alarm installers, locksmiths, personal-injury and defense attorneys, insurance agents, towing and auto-glass companies, and self-defense gyms. A planning assumption is **$150–500 per sponsor slot per month**; validate with the first 3 pitches. Disclose sponsorships with the platform's paid-partnership tools. |
| **Affiliate** (home cameras, dashcams, safety gear) | Link in bio or link page | Month 1 onward | Low effort, low yield. Use only products the host would recommend. |
| **TikTok Creator Rewards** | 18+, personal account, **10k followers, 100k views in the last 30 days**, videos over 1 minute, original content | Months 3–5 if growth holds | Creator-reported US RPM is about **$0.50–$2.00 per 1,000 qualified views**. At 1M qualified views a month, that is roughly $500–2,000 a month. |
| **YouTube Partner Program** | **1,000 subscribers + 10M Shorts views in the last 90 days** (or 4,000 long-form watch hours in 12 months) | Months 4–6+ | Shorts ad revenue per view is low. Check in YouTube Studio whether the lower fan-funding tier is available. Shorts views do not count toward watch hours. |
| **Web map + newsletter** (owned audience) | Phase 3 site live | Month 2 onward | This protects against platform bans. Monetize with display ads and newsletter sponsors. |
| **Data and clip licensing** to local media | Clean archive of 90+ days | Month 6+ | Sell trend summaries, such as "incidents by neighborhood," to local outlets and real-estate or insurance researchers. |

**Brand-safety note:** advertisers avoid graphic crime content. The editorial tone should be "informative, calm, neighborhood-useful" and never sensational. This applies to the sponsor pitch as much as to platform policy.

---

## 3. System architecture

```
[Hamilton Co. 911 CAD page]
        │  poll every 3–5 min (Playwright, Render cron)
        ▼
[ingest/]  scrape → normalize → dedupe on Master Incident # → status history
        │
        ▼
[db/]  Postgres + PostGIS (Render)  — incidents, status_events, geocodes, posts, sponsors
        │
        ├──► [geocode/]  US Census Geocoder (free) → fallback Nominatim; store block-level only
        │
        ├──► [content/]  rules filter (exclude EMS/medical, domestic, juveniles)
        │                → LLM drafts script + caption + hashtags (facts only from CAD fields)
        │
        ├──► [render/]   Remotion (Node) 1080×1920 template: map + text + host VO slot → .mp4
        │
        ├──► [review/]   Review queue web app (Vercel): approve / edit / reject, upload VO
        │                → human approval is REQUIRED before anything is posted
        │
        ├──► [publish/]  Phase 3a: manual upload from queue export
        │                Phase 3b: YouTube Data API + TikTok Content Posting API (after audits)
        │
        └──► [web/]      Public map + daily recap archive + newsletter signup (Vercel)
```

**Stack choices**

- **Python 3.12** for ingest, with Playwright because the table is rendered by JavaScript.
- **Postgres + PostGIS on Render**, with **Render cron jobs** for the poller. The Render connector is already linked to this account.
- **Next.js on Vercel** for the review queue and the public site. The Vercel connector is already linked.
- **Remotion** for rendering. It is free for individuals and companies of up to 3 people; check the license if the team grows.
- **Map tiles:** MapLibre with an OpenStreetMap-based style, or Mapbox, each with on-screen attribution. Do not use Google Maps static images, because its terms restrict this use.
- **LLM drafting:** Claude API. The model gets only structured CAD fields and is told never to invent facts.

**API publishing caveat:** YouTube API uploads from an unverified project are forced to *private* until the project passes Google's audit. TikTok's Content Posting API also needs an app audit before public posts. Phase 3 therefore starts with manual posting, and the audits are filed in Week 4.

---

## 4. Phased plan

### Phase 0 — Foundation (W1–W2: Oct 13 – Oct 25)

1. Lock the brand name and handle, and register them on TikTok, YouTube, Instagram and a domain.
2. Use **personal** TikTok and YouTube accounts. TikTok business accounts are ineligible for Creator Rewards.
3. Write `docs/CONTENT_POLICY.md` (D3): the exclusion list, language rules ("reported," "dispatched," never "confirmed"), no names, block-level locations only, and a corrections process.
4. Email the Hamilton County 911 district's public-information contact. Describe the project and ask about reuse and whether a data feed exists (D4).
5. Find the data endpoint: inspect the page's network calls (XHR/JSON) and document the fields, values and refresh behavior (D5).
6. Set up the repo: monorepo layout, CI, `.env.example`, and issue templates (D2).
7. Post 5–10 **manual** test videos by hand to learn the format before automating it. Engagement data from these videos guides Phase 2.

### Phase 1 — Data pipeline (W2–W4: Oct 19 – Nov 8)

1. `ingest/`: a Playwright scraper with polite polling, retry with backoff, and an alert if parsing breaks (D6).
2. `db/`: schema migrations for `incidents`, `status_events`, `geocodes`, `posts`, `sponsors` and `metrics` (D7).
3. Deduplicate on Master Incident number, and track status changes (R→E→OS→T→H) as events.
4. `geocode/`: Census Geocoder first and Nominatim as fallback, with a cache table. Snap locations to the block centroid; never store or show house-level points for display (D8).
5. A rules filter that excludes EMS and medical calls, domestic calls, calls involving juveniles, and calls at schools and hospitals (D9).
6. Deploy the poller as a Render cron job and Postgres on Render. Run for 14 days to collect baseline volume (D10).

**Exit gate:** 7 days of uninterrupted capture with less than 1% parse failures and at least 90% geocode success.

### Phase 2 — Content engine (W4–W6: Nov 2 – Nov 22)

1. Define formats (D11):
   - **Incident clip** (20–40 s): built for growth on major road closures, structure fires and large police responses.
   - **Daily Recap** (60–90 s): the core earning format, posted every evening.
   - **Weekly Top 5 / neighborhood trends** (60–120 s): evergreen and suited to sponsors.
2. `content/`: LLM script and caption drafter with fact-locking. Every claim must map to a CAD field (D12).
3. `render/`: Remotion templates for all three formats, with a map animation, lower-thirds, a disclaimer bar, a sponsor slot and a voiceover track (D13).
4. `review/`: a review queue on Vercel for the day's candidates. It supports approve, edit, reject and voiceover upload, and exports .mp4 files with captions (D14).
5. Create the host's voice and style guide, with recording settings and a 3-step script structure (hook → facts → useful takeaway) (D15).

**Exit gate:** one person can produce the Daily Recap in **20 minutes or less** from opening the queue to an exported file.

### Phase 3 — Publishing & growth (W6–W9: Nov 16 – Dec 13)

1. Set a cadence: 1 Daily Recap every day, plus 1–2 incident clips a day when warranted. Post to both platforms (D16).
2. Phase 3a: manual posting. File the YouTube API audit and the TikTok Content Posting API audit in Week 6 (D17).
3. Build a metrics loop: pull views, retention, followers and comments into the `metrics` table, and send a weekly report (D18).
4. Launch the public web map and recap archive, with newsletter signup, on Vercel and a custom domain (D19).
5. Community: pin a corrections and "how this works" video, and answer comments every day.

**Exit gate:** 30 consecutive days of posting, at least 3k followers on the leading platform, and the recap's average watch time at 50% or more.

### Phase 4 — Monetization (W8–W16: Nov 30 – Jan 31)

1. Build the media kit: audience geography, reach, engagement, the sponsor slot format and the rate card (D20).
2. Make a list of 40 local sponsor prospects and pitch 10 a week. Aim to **close the first sponsor by W12** (D21).
3. Set up an affiliate link page with 5–8 vetted products (D22).
4. Watch the platform thresholds weekly. Apply for TikTok Creator Rewards and YPP as soon as each is eligible (D23).
5. Track revenue in the `sponsors` table and on a monthly P&L sheet (D24).

**Exit gate:** at least $500 a month in recurring revenue from any mix of streams by Jan 31, 2027.

### Phase 5 — Scale (Feb – Apr 2027)

1. Turn on API auto-publishing once the audits pass. A human still approves every post.
2. Expand to a second area, such as Walker or Catoosa County in Georgia or Bradley County, by reusing the pipeline (D25).
3. Reconsider scanner audio only after a written legal review (D26).
4. Build a data and clip licensing offer for local media (D27).

---

## 5. Deliverables register

| ID | Deliverable | Repo path / location | Acceptance criteria |
|---|---|---|---|
| D1 | Implementation plan + crosswalk (this file) | `docs/` | Committed and reviewed by the owner |
| D2 | Repo scaffold + CI | `/`, `.github/workflows/` | Lint and tests run on every PR |
| D3 | Content & safety policy | `docs/CONTENT_POLICY.md` | Exclusions, language rules and corrections process written |
| D4 | 911 district outreach record | `docs/legal/911_outreach.md` | Email sent; reply logged |
| D5 | Data source spec | `docs/DATA_SOURCE.md` | Endpoint, fields, values and refresh behavior documented with samples |
| D6 | CAD scraper | `ingest/` | Parses all columns; unit tests run against saved HTML fixtures |
| D7 | Database schema | `db/migrations/` | Migrations apply cleanly on Render Postgres |
| D8 | Geocoder + cache | `geocode/` | At least 90% match rate; outputs block-level points |
| D9 | Exclusion filter | `content/filters.py` | 100% of EMS, domestic and juvenile test cases excluded |
| D10 | Production poller on Render | Render cron | 7 days at 99% or better uptime |
| D11 | Format spec (3 formats) | `docs/FORMATS.md` | Length, structure and visual layout per format |
| D12 | Script drafter | `content/` | No claims beyond CAD fields in a 50-sample audit |
| D13 | Render templates | `render/` | 1080×1920 30fps .mp4 with captions, attribution and disclaimer |
| D14 | Review queue app | `review/` (Vercel) | Approve, edit, reject, VO upload and export work end to end |
| D15 | Host voice & style guide | `docs/HOST_GUIDE.md` | Script template and recording checklist |
| D16 | Posting calendar | `docs/CALENDAR.md` | 30 days of consecutive posts logged |
| D17 | API audit applications | `docs/legal/api_audits.md` | YouTube and TikTok submissions filed |
| D18 | Metrics collector + weekly report | `metrics/` | Automated weekly report generated |
| D19 | Public web map + newsletter | `web/` (Vercel) | Live on custom domain; signup works |
| D20 | Media kit + rate card | `sales/media_kit` | PDF and one-page web version |
| D21 | Sponsor pipeline (40 prospects) | `sales/pipeline.csv` | 40 prospects, at least 10 pitched, first close |
| D22 | Affiliate link page | `web/` | Live with disclosures |
| D23 | Platform monetization applications | `docs/MONETIZATION_LOG.md` | Applied on reaching eligibility |
| D24 | Revenue tracker / P&L | `sales/` | Monthly P&L for Dec and Jan |
| D25 | Second-area expansion | `ingest/sources/` | Second source live in prod |
| D26 | Scanner-audio legal memo | `docs/legal/` | Written opinion before any audio use |
| D27 | Licensing offer | `sales/` | One-page offer sent to 5 outlets |

---

## 6. Crosswalk — deliverables × phase × timeframe × monetization lever

*Weeks start Monday. W1 is the partial week of Oct 13–18, 2026.*

| ID | Phase | Weeks | Dates | Owner | Depends on | Monetization lever it unlocks |
|---|---|---|---|---|---|---|
| D1 | 0 | W1 | Oct 13 – 18 | Claude | — | All (roadmap) |
| D2 | 0 | W1 | Oct 13 – 18 | Claude | — | All (build base) |
| D3 | 0 | W1–W2 | Oct 13 – 25 | You + Claude | — | Brand safety → sponsors; platform good standing |
| D4 | 0 | W1 | Oct 13 – 18 | You | — | Risk reduction (data access) |
| D5 | 0 | W1–W2 | Oct 14 – 22 | Claude | — | Pipeline |
| D6 | 1 | W2–W3 | Oct 19 – Nov 1 | Claude | D5 | Pipeline |
| D7 | 1 | W2 | Oct 19 – 25 | Claude | D5 | Pipeline; sponsor/revenue tracking |
| D8 | 1 | W3 | Oct 26 – Nov 1 | Claude | D6, D7 | Map visuals; web map |
| D9 | 1 | W3 | Oct 26 – Nov 1 | Claude | D3, D6 | Brand safety → sponsors |
| D10 | 1 | W3–W4 | Oct 29 – Nov 8 | Claude + You (Render) | D6–D9 | Data archive → licensing (D27) |
| D11 | 2 | W4 | Nov 2 – 8 | You + Claude | Manual test posts | **Daily Recap over 1 min → TikTok Creator Rewards** |
| D12 | 2 | W4–W5 | Nov 2 – 15 | Claude | D10, D11 | Originality (host + facts) → YPP/TikTok eligibility |
| D13 | 2 | W4–W6 | Nov 2 – 22 | Claude | D11 | Sponsor slot built into template |
| D14 | 2 | W5–W6 | Nov 9 – 22 | Claude | D12, D13 | Human review → passes inauthentic-content policy |
| D15 | 2 | W5 | Nov 9 – 15 | You | D11 | Originality; host trust → sponsors |
| D16 | 3 | W6–W9 | Nov 16 – Dec 13 | You | D14 | Audience growth toward 10k / 1k-sub thresholds |
| D17 | 3 | W6 | Nov 16 – 22 | You + Claude | D14 | Automation at scale (Phase 5) |
| D18 | 3 | W7 | Nov 23 – 29 | Claude | D16 | Media-kit stats; threshold tracking |
| D19 | 3 | W7–W9 | Nov 23 – Dec 13 | Claude | D8, D10 | Owned audience: newsletter + display ads |
| D20 | 4 | W8–W9 | Nov 30 – Dec 13 | You + Claude | D18 | **Sponsorship (primary revenue)** |
| D21 | 4 | W9–W12 | Dec 7 – Jan 3 | You | D20 | **Sponsorship: first close by W12** |
| D22 | 4 | W8 | Nov 30 – Dec 6 | You + Claude | D19 | Affiliate |
| D23 | 4 | W10–W16 | Dec 14 – Jan 31 | You | D16, D18 | **TikTok Creator Rewards; YPP** |
| D24 | 4 | W10, W14 | Dec 14 + Jan 11 | You + Claude | D21 | Revenue visibility |
| D25 | 5 | Feb – Mar 2027 | — | Claude | D10 stable | Larger audience → higher sponsor rates |
| D26 | 5 | Feb 2027 | — | You (attorney) | — | Richer content (audio), if cleared |
| D27 | 5 | Mar – Apr 2027 | — | You + Claude | D10 (90+ days of data) | Data licensing |

### Milestone timeline

| Milestone | Target date |
|---|---|
| Data endpoint documented; 911 email sent | Oct 22, 2026 |
| Poller live in production | Nov 1, 2026 |
| First automated-draft Daily Recap posted | Nov 16, 2026 |
| Public web map live | Dec 13, 2026 |
| Media kit ready; sponsor outreach begins | Dec 13, 2026 |
| First paid sponsor | Jan 3, 2027 |
| At least $500/month recurring revenue | Jan 31, 2027 |
| Second area live | Mar 31, 2027 |

---

## 7. KPIs & go/no-go gates

| Metric | Week 8 target | Week 16 target |
|---|---|---|
| Followers (best platform) | 3,000 | 10,000 |
| 30-day views (TikTok) | 50,000 | 100,000+ (Creator Rewards threshold) |
| Daily Recap avg. watch % | 45% | 55% |
| Posts published on schedule | 90% | 95% |
| Corrections issued / posts | < 2% | < 1% |
| Recurring revenue | $0–150 | $500+ |

**Week 9 review:** if recap retention is below 35% after 30 days, rework the format, hook and host delivery before scaling volume. More posts will not fix weak retention.

---

## 8. Risks & guardrails

| Risk | Mitigation |
|---|---|
| Demonetization for templated or AI content | Host voiceover and commentary on every earning video, human approval, varied formats and a clear channel About section |
| Defamation / false reports | Facts come only from CAD fields, with "reported/dispatched" language, no names, a corrections pin and a 24-hour takedown SLA |
| Privacy (victims, medical calls) | Exclude EMS, domestic and juvenile calls; show block-level locations only; never show residences |
| County blocks scraping or changes the page | Permission request (D4), polite polling, parser alerts, fixture-based tests and a manual fallback |
| Platform crime-content restrictions | No graphic imagery, calm tone and community-safety framing |
| Copyright / ToS for map tiles and music | Licensed tiles with attribution; platform-library music only |
| Burnout from a daily cadence | The 20-minute production gate (Phase 2) and batch-recorded weekly segments |

*This plan is not legal advice. Have a Tennessee media attorney review D3 and D26 before monetization begins.*

---

## 9. This week's checklist (W1: Oct 13 – 18)

- [ ] **You:** pick the brand name and handles; register personal TikTok and YouTube accounts
- [ ] **You:** send the email to the Hamilton County 911 district (Claude can draft it)
- [ ] **You:** record 3 manual test recaps from today's incident list
- [ ] **Claude:** scaffold the repo (D2), draft CONTENT_POLICY.md (D3), and investigate the CAD endpoint (D5)

## 10. Open questions for the owner

1. Brand name / handle?
2. Will you be the on-camera or voice host, or will someone else?
3. Budget for tools: Render, Vercel, domain, LLM API, and possibly Mapbox. The planning estimate is under $75 a month in Phases 1–3.
4. Are you operating as an individual or forming an LLC? Sponsorship contracts and liability affect this choice.
