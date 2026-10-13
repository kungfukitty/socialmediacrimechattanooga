# Data Source Spec (D5)

**Source:** Hamilton County 9-1-1 Emergency Communications District, Active Incidents
**URL:** https://www.hamiltontn911.gov/active-incidents.php
**Last reviewed:** Tue Oct 13, 2026

## What the page shows

| Item | Detail |
|---|---|
| Columns | `Type` · `Status` · `Master Incident` · `Time Created` · `Agency` · `Event` · `Location (Click Buttons to Locate on Map)` · `Area` |
| Status codes | `R` Reported · `E` Enroute · `OS` On Scene · `T` Transporting · `H` At Hospital |
| Types | Law · Fire · EMS · Road Closure |
| Areas | Collegedale · Chattanooga · East Ridge · Hamilton County · Red Bank · Signal Mountain · Soddy-Daisy |
| Agencies | 15 in the filter: police, fire, EMS and sheriff's office entries. List them from a fixture. |
| Counters | Current active, daily total and yearly total incidents |
| Map | "OPEN MAP" view with a per-row locate button. The rows probably carry coordinates, which would let us skip most geocoding. **Check this.** |
| Notes on page | "Not all incident types are displayed." "Session time is limited to 15 minutes," with a Continue Viewing button. |
| Rights | "© 2025-2026 Hamilton County 9-1-1 Emergency Communications District. All Rights Reserved." See D4. |

**Important:** the rows load with JavaScript after the page opens; a plain HTML fetch returns an empty table. Before writing the scraper, we need to find the request that delivers the rows. If it's a JSON endpoint, the scraper can call it directly, which is lighter for their server than running a browser. If it isn't, use Playwright.

Note: the dev container can't reach this site (its network allowlist blocks it). Captures have to come from your own browser. The production poller on Render will reach it normally.

## Capture checklist (you, about 20 min, Day 1)

Do this in Chrome on your computer:

1. Open the page and press **F12** → **Network** tab. Tick **Preserve log**. Filter by **Fetch/XHR**.
2. Reload. Wait for the table to fill.
3. Find the request whose **Response** contains incident rows (search the Network panel with Ctrl+F for a Master Incident number you can see in the table).
4. For that request, write down the following in the table below:
   - the **URL**
   - the **method** (GET or POST)
   - the **request payload or query string**, if any
   - any **cookies or tokens** it needs (Headers tab)
5. Right-click the request → **Copy → Copy response**. Paste it into `ingest/fixtures/rows-1.json` (or `.html` if it's HTML).
6. Click one row's **locate** button and see whether coordinates appear in the response or in a new request. Note it.
7. Repeat steps 5–6 at **two other times of day** to get `rows-2` and `rows-3`. Aim for one busy evening capture.
8. Also save the full page: **Ctrl+S → Webpage, HTML only** → `ingest/fixtures/page.html`.
9. Commit the fixtures, or attach them in chat and I'll commit them.

| Finding | Value |
|---|---|
| Data request URL | |
| Method / payload | |
| Needs cookie or token? | |
| Response format (JSON or HTML) | |
| Coordinates present? | |
| Refresh interval the page uses | |
| Time Created format (example) | |
| Master Incident format (example) | |

## How the scraper will behave (D6)

- Poll every **4 minutes** (240 s), from one IP, with the User-Agent `ChattanoogaSafetyFeed/0.1 (+contact: [email])`.
- On HTTP errors, back off: 4 → 8 → 16 → 30 min. Alert if there's no successful fetch in 30 min.
- **Parse-error alert:** if a non-empty response produces 0 rows, or a column disappears, send an alert and save the raw response for debugging.
- Upsert on `Master Incident`. Each status change becomes a row in `status_events`, so the archive records how calls progress. An incident that drops off the list is marked `cleared_at`.
- Normalizer: `ingest/src/normalize.ts` (tests in `normalize.test.ts`). Confirm its date parsing against the fixtures.
