# Scentrix UX Audit — First-Time User Walkthrough

**Audit date:** 2026-06-02
**Status snapshot:** All issues remain present. P0/P1 items from the Recommended Implementation Plan (below) have NOT been implemented. The `/catalog` route still returns 404 but nav links pointing to it have been removed (partial mitigation).

## Page Status Summary

| Page | URL | Status | Render |
| ---- | --- | ------ | ------ |
| Landing | `/` | 200 OK | SSR with client hydration |
| Quiz | `/onboarding/quiz` → `/quiz` | 308 → 200 OK | Client-only |
| Recommendations | `/recommendations` | 200 OK | Client-only |
| Login | `/auth/login` | 200 OK | SSR with client hydration |
| Register | `/auth/register` | 200 OK | SSR with client hydration |
| Profile | `/profile` | 200 OK | Client-only |
| Families | `/families` | 200 OK | SSR with client hydration |
| Collection | `/collection` | 200 OK | Client-only |
| Catalog | `/catalog` | **404** | N/A |

---

## Per-Page Audit

### 1. Landing Page (`/`)

| # | Issue | Severity | Source |
| - | ----- | -------- | ------ |
| 1 | **"Neural Sommelier Protocol v2.0-REWIRED"** — zero value for a first-time user. Does not explain what the product does. Reads like a tech demo badge. | **High** | Hero section |
| 2 | **Both CTAs are `<button>` elements** — "Start Discovery" and "Browse Library" are not `<a>` links. No `href` visible in HTML. If JS fails, user is stranded. | **High** | Hero section |
| 3 | **"Browse Library"** — what library? No explanation. "Fragrance library" is never defined anywhere on the page. | **Medium** | Hero CTA |
| 4 | **"Architectural Process" section** — "Archetypal Discovery", "Neural Graph Mapping", "Elite Curation". The copy is poetic but impenetrable. Does not actually explain how the product works. | **Medium** | Steps section |
| 5 | **"Manifest Your Presence" / "Start Your Protocol"** — final CTA. The word "Protocol" is used 4+ times on the page. This is never explained. Reads as exclusive/clubby rather than welcoming. | **Medium** | Final CTA section |
| 6 | **Family cards "Explore Collection" is a `<span>`** — not a link or button. Visually looks clickable, is not. User taps/clicks and nothing happens. | **High** | Family cards |
| 7 | **Testimonials appear stock** — Sarah M., James L., Emma R. Generic first-name-only quotes with no photos. "Finally found a fragrance that matches my personality perfectly" reads like a template. | **Medium** | Social proof section |
| 8 | **Stats mismatch**: Hero says "5,130+ Elite Scents", social proof says "5,130 Elite Members" for same number — inconsistent noun. | **Low** | Stats sections |
| 9 | **"91.5% Match Accuracy"** — unsubstantiated metric. No methodology or source. | **Medium** | Hero/social proof |
| 10 | **Final CTA also has "Start Your Protocol" button** — same button but different text from "Start Discovery" at top. User may be confused about what each does. | **Low** | Final CTA |

### 2. Quiz (`/onboarding/quiz` → `/quiz`)

| # | Issue | Severity | Source |
| - | ----- | -------- | ------ |
| 1 | **URL changes during redirect** — navigating to `/onboarding/quiz` silently redirects to `/quiz`. User may notice the URL change and feel uncertain. | **Low** | Router |
| 2 | **Quiz is fully client-rendered** — zero HTML content in page source. If JS fails, user sees a white screen with no error message. | **High** | Quiz page |
| 3 | **No progress indicator visible in HTML** — quiz lives entirely in client JS, so no crawlable/accessible step info. | **Medium** | Quiz page |

### 3. Recommendations (`/recommendations`)

| # | Issue | Severity | Source |
| - | ----- | -------- | ------ |
| 1 | **Fully client-rendered** — empty `<div>` in HTML. No loading skeleton visible in server output. Users with slow connections see blank page. | **High** | Recommendations page |
| 2 | **No cache/restore mechanism visible** — recommendations are ephemeral. No way to bookmark/share a recommendation set. | **Medium** | Architecture |
| 3 | **"Why Recommended" text** — computed client-side from `quizResponses` array. The explanation is tied to session data that can be lost on refresh (guest mode). | **Medium** | `reason-engine.ts` |

### 4. Auth Pages (Login/Register)

| # | Issue | Severity | Source |
| - | ----- | -------- | ------ |
| 1 | **No "Forgot password?"** — already removed (Wave 1). User who forgets password has no recovery path visible. | **High** | Login page |
| 2 | **"← Back to Home" is a `<button>`** — not a link. If JS fails, user cannot navigate. | **Medium** | Login/Register |
| 3 | **Register: "100% privacy guaranteed"** — bold claim in sidebar. No explanation of what this means. If data is stored on Upstash Redis, this is misleading. | **Medium** | Register page |
| 4 | **Register: Terms/Privacy are plain text** — user checks "I agree to the Terms of Service and Privacy Policy" but cannot read them. No links. | **High** | Register page |

### 5. Profile (`/profile`)

| # | Issue | Severity | Source |
| - | ----- | -------- | ------ |
| 1 | **Fully client-rendered** — no server HTML visible. | **Medium** | Profile page |
| 2 | **No Edit/Delete options** — already removed (Wave 1). User cannot edit their account or delete data after registration. | **High** | Profile page |

### 6. Families (`/families`)

| # | Issue | Severity | Source |
| - | ----- | -------- | ------ |
| 1 | **Family mismatch with landing page** — families page lists 8 families (Floral, Woody, Citrus, Amber, Aromatic, Fruity, Chypre, Aquatic). Landing page lists 10 (Floral, Woody, Citrus, Oriental, Amber, Smoky, Fruity, Gourmand, Leather, Spicy). Only 5 overlap. User wonders which is correct. | **High** | `/families` vs `/` |
| 2 | **"Explore" buttons** — are actual `<button>` elements. Their destination is unknown without JS inspection. | **Medium** | Families page |

### 7. Collection (`/collection`)

| # | Issue | Severity | Source |
| - | ----- | -------- | ------ |
| 1 | **Fully client-rendered** — empty `<div>`. If user has no collection yet, they see a blank page. No empty state is visible in HTML. | **High** | Collection page |

### 8. Catalog (`/catalog`)

| # | Issue | Severity | Source |
| - | ----- | -------- | ------ |
| 1 | **404 — page does not exist.** Any nav link pointing to `/catalog` is dead. | **Critical** | Routing |

---

## Top 10 UX Issues

1. **`/catalog` returns 404** — dead end in navigation. Blocking. *(Partial fix: nav links removed, but direct access still 404)*
2. **Family cards "Explore Collection" on landing are `<span>` not `<a>`** — looks clickable, does nothing.
3. **Families page shows different families than landing page** — undermines data consistency trust.
4. **Register has no accessible Terms/Privacy links** — user checks "I agree" to invisible documents.
5. **Login has no password recovery** — forgotten password = account loss.
6. **Profile has no account management** — user cannot edit or delete their account post-registration.
7. **Client-only pages with no loading state in HTML** — Quiz, Recommendations, Collection, Profile all render empty shells server-side.
8. **"Browse Library" CTA on landing** — the destination ("library") is never explained or linked.
9. **Stock testimonials** — generic quotes with first-name-only attribution erode social proof.
10. **Esoteric copy throughout** — "Protocol", "Sommelier", "Archetypal", "Elite Curation" — the brand voice is exclusive rather than welcoming.

---

## Top 5 Trust Issues

1. **`/catalog` 404** — user clicks a nav link and hits a dead page. Immediate trust loss.
2. **Family inconsistency** — landing page and families page describe different taxonomies. User notices and wonders which data is real.
3. **"91.5% Match Accuracy" with no methodology** — unsubstantiated metrics are worse than no metrics.
4. **"100% privacy guaranteed" with no privacy policy link** — contradictory. User cannot verify.
5. **No account deletion** — user cannot delete their data. In some jurisdictions this is a legal issue (GDPR).

---

## Top 5 Opportunities to Make Recommendation Intelligence More Obvious

1. **Show loading state that explains what's happening** — e.g., "Scanning 5,130 fragrances through your taste profile..." instead of a blank loading screen.
2. **Show the rationale for each recommendation inline** — the "Why Recommended" section is a good start, but it's buried in the card. Surface the top 3 reasons prominently.
3. **After user rates a recommendation, show how the model updated** — e.g., "Thanks! We now know you prefer woody over floral. Your next batch will be adjusted."
4. **Add a confidence indicator** — "This match is 87% confident based on 12 fragrance ratings". Makes the AI feel transparent.
5. **Show the family distribution of recommendations** — a small pie/donut showing "Your profile: 60% Woody, 20% Citrus, 20% Amber" gives users a mental model of what the AI thinks they like.

---

## Recommended Wave 2 Implementation Plan

### P0 — Blocking (must fix)
1. **Create `/catalog` page** or remove all nav links pointing to it — *Partial mitigation: nav links removed, but the route itself still returns 404 if accessed directly*
2. **Make family "Explore Collection" interactive** — wire `<span>` to button/link in landing page
3. **Align family data** — decide on one taxonomy (10 from landing or 8 from families) and make both pages consistent

### P1 — Trust-critical
4. **Add Terms & Privacy links to register page** — users must be able to read what they agree to
5. **Add password reset flow** — even a simple "Contact support" message is better than nothing
6. **Add account deletion** — Profile needs a delete option (or at minimum a clear statement about how to request deletion)

### P2 — Polish
7. **Rewrite hero copy** — replace "Neural Sommelier Protocol v2.0-REWIRED" with plain-language value proposition
8. **Add loading skeletons** — for Quiz, Recommendations, Collection, Profile pages
9. **Add empty states** — Collection page should show "Your collection is empty. Take the quiz to get started!"
10. **Fire real testimonials or remove** — stock testimonials hurt more than they help

### P3 — Differentiation
11. **Surface recommendation rationale** — show why each fragrance was selected (family match, note similarity, community ratings)
12. **Add feedback confirmation** — after rating, show how the model adapted ("Noted! Steering toward warmer scents.")
13. **Show profile composition** — "Your scent profile: 60% Woody, 25% Amber, 15% Citrus"
