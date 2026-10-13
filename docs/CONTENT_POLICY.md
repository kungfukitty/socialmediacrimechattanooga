# Content & Safety Policy (D3)

**Status:** DRAFT. The owner must approve it. Have a Tennessee media attorney review it before taking paid sponsors.
**Applies to:** every video, caption, comment reply, link page and newsletter we publish.

This policy exists for three reasons:

- to avoid harming people who are having the worst day of their lives
- to avoid publishing anything false
- to keep the channel eligible for platform monetization and safe for sponsors

The pipeline enforces the rules marked **[auto]** in `content/filters.ts` (D9). The host enforces the rest at review.

---

## 1. What we publish

- Incidents that appear on the Hamilton County 9-1-1 public Active Incidents list, described **only** with facts shown there: type, event, status, agency, time, block-level location and area.
- Road closures and traffic-impacting incidents.
- Aggregates and trends, such as "burglaries reported in East Ridge this week."
- Official agency statements, quoted and linked, when available.

## 2. What we never publish

| Rule | Why | Enforcement |
|---|---|---|
| **No EMS or medical calls** (type `EMS`, or events naming medical conditions, overdoses or deaths) | Health privacy, and the family's dignity | [auto] |
| **No domestic, sexual-assault or child-related calls** (events containing domestic, DV, sex, rape, juvenile, child, CPS) | Victim safety; these can identify survivors | [auto] |
| **No suicide, self-harm or mental-health calls** (suicid*, self harm, mental, welfare check, 10-96, crisis) | Contagion risk; platform rules | [auto] |
| **No names, faces, license plates or house numbers** of victims, suspects or bystanders | Privacy and defamation risk | [auto] for text; host for visuals |
| **No exact addresses.** Show the street block only ("1200 block of Boynton Dr"). Map pins snap to the block, not the parcel. | Locations of homes | [auto] |
| **No speculation** about cause, motive, suspects, injuries or outcome | Defamation and accuracy | Host + drafter prompt |
| **No incidents at schools, shelters, hospitals or places of worship** unless an agency has issued a public statement | Sensitive locations | Host |
| **No calls still at status `R` (Reported) in single-incident clips.** Only use them in recap counts. | Many reported calls turn out to be nothing | [auto] |
| **No scanner audio** until a legal review is done | Federal and state law limits; Broadcastify terms | Policy |

## 3. Language rules

- Always use "**reported**", "**dispatched**" or "**responded to**". Never write "a burglary happened" or "a shooting occurred."
- Use the event wording from the county list. Don't escalate it: "Shots Fired Call" never becomes "shooting."
- No fear-bait hooks. "Is your street safe?" is fine; "Chattanooga is a war zone" is not.
- Times are stated as "around 2 p.m.", with the dispatch time, not the time of the crime.
- Every video carries the on-screen line: **"Based on public 9-1-1 dispatch data. Not an official statement. Details may change."**
- The AI-assisted script is reviewed and voiced by a human. Turn on the platform's AI-content label whenever synthetic visuals or voice are used.

## 4. Accuracy & corrections

- **Every sentence must trace to a CAD field or a linked official source.** The drafter (D12) outputs a source field next to each line, and the host deletes any line without one.
- **Corrections SLA:** a reported error gets a pinned correction comment within **2 hours** during waking hours. If the error is material, the video is deleted and re-posted corrected within **24 hours**.
- A pinned "How this channel works / corrections" video, plus a link-page form, gives people a way to report errors.
- Log every correction in `docs/legal/corrections_log.md`: the date, video, what was wrong and the action taken.

## 5. Takedown requests

People named or shown (by mistake), property owners, and agencies can request removal through the link-page form or by email.

- **Agency requests** are honored immediately. No argument.
- **Individual requests** about their own home or identity: remove within **24 hours**.
- Log every request, as in §4.

## 6. Comments

- Hide or delete comments that name suspects or victims, make threats, or give exact addresses.
- Use keyword filters on both platforms: names of slurs, "address is", "lives at", phone-number patterns.
- Don't argue with comments. Pin the facts.

## 7. Sponsors

- Sponsor segments are visually separate and labeled "**Sponsored**." Turn on the platform's paid-partnership toggle every time.
- **Sponsors never appear inside a single-incident clip.** They appear only in recaps and trend videos, so no business is shown next to a specific victim's incident.
- We don't accept sponsors whose pitch exploits fear, such as "buy a gun before it's too late." Security, insurance, locksmith and similar offers are fine when framed around prevention.
- Affiliate links carry an FTC disclosure on the link page and in the caption ("#ad / affiliate links").

## 8. Data source conduct

- Poll the county page **no more than once every 3–5 minutes**, from one IP, with a descriptive User-Agent that includes a contact email.
- Stop immediately and email the district if asked to.
- Keep the archive for analysis. Don't republish the raw feed as a product until the district answers the D4 email.
