# Hyperframes Composition Brief: Scentrix

## Objective
Create a short launch-style brag video for Scentrix — an AI fragrance-discovery platform. Quiet-premium execution of its "Neural Sommelier" ritual: rate a scent, get a matched constellation.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 60.0 seconds (user requested ~1 min)

## Source Material
- Project root: `frontend/` (Next.js app) + `backend/`
- Primary files read: `frontend/src/components/HeroSection.tsx`, `frontend/src/components/StandardQuiz.tsx`, `frontend/src/components/DiscoveryNeuralLoader.tsx`, `frontend/src/lib/reason-engine.ts`, `frontend/src/app/recommendations/page.tsx`, `frontend/src/app/globals.css`, `frontend/src/styles/hero.css`/`quiz.css`/`recommendations.css`, `frontend/src/app/layout.tsx`
- Product name: **Scentrix**
- Tagline / strongest claim: `Molecular Artistry. Neural Instinct.` · `Discover the scent DNA that defines your dimension.`
- Key UI moments to recreate:
  1. Quiz rating card (`/quiz`): brand label, serif fragrance name, note capsules, 1–10 slider with live readout (`7.4 / 10`), `Confirm Dimension` button, top bar `Discovery 1 / 8` + progress bar
  2. Neural loader (`DiscoveryNeuralLoader`): `Neural Pipeline` eyebrow, cycling lore lines (`Synthesizing 2.1M Graph Relationships...`, `Decoding Animalic Musks...`, `Waking the Digital Sommelier...`), progress rail, footer `Syncing 24k Archive` / `V.PRIME_ELITE`
  3. Match cards (`/recommendations`): name, family label, match %, note chips, one short reason line, under header `Your Aromatic Constellation` with badge `PROTOCOL RESULTS COMPLETE`
  4. Landing hero (`HeroSection`): headline `Neural Sommelier Protocol v2.0-REWIRED`, tagline `Discover the scent DNA that defines your dimension.`, stats `5,130+ Elite Scents` · `91.5% Match Accuracy` · `50K+ Critics & Collectors`, CTAs `Browse Library` / `Browse Popular Picks`
- Real catalog data used verbatim: `guerlain / Shalimar Parfum` (Bergamot · Floral), `valentino / Valentino Uomo Intense` (Mandarin Orange · Nutmeg), `ysl / Opium Pour Homme` (Star Anise · Black Currant)
- Copy that must appear verbatim:
  - `Neural Sommelier Protocol`
  - `Molecular Artistry.`
  - `Neural Instinct.`
  - `91.5% Match Accuracy`
  - `Discovery 1 / 8`, `Discovery 2 / 8`
  - `How does this profile resonate?`
  - `7.4 / 10`, `8.1 / 10`
  - `Confirm Dimension`
  - `Neural Pipeline`
  - `Synthesizing 2.1M Graph Relationships...` / `Decoding Animalic Musks...` / `Waking the Digital Sommelier...`
  - `Syncing 24k Archive`, `V.PRIME_ELITE`
  - `Your Aromatic Constellation` / `PROTOCOL RESULTS COMPLETE`
  - `Start Discovery →` / `Scentrix` / `Your neural sommelier.`
  - `Neural Sommelier Protocol v2.0-REWIRED`
  - `Discover the scent DNA that defines your dimension.`
  - `5,130+` `Elite Scents` · `91.5%` `Match Accuracy` · `50K+` `Critics & Collectors`
  - `Browse Library` / `Browse Popular Picks`

## Creative Direction
- Tone preset: `polished`
- Creative direction: quiet premium product film — the ritual, played straight
- Interpretation: 8 scenes, longer holds, slow crossfades (0.6–0.8s); Cormorant-shaped light italic serif with generous letter-spacing; the amber glow on near-black does the drama; restraint, no flashy transitions
- Angle: the working ritual is the show — viewer rates one scent, three named matches land on the beat
- Hook: `Molecular Artistry.` typing itself in under `Neural Sommelier Protocol`
- Outro / punchline: `Scentrix` wordmark + `Your neural sommelier.`, music fading under it
- Avoid:
  - Generic SaaS language ("streamline", "personalized experience")
  - Abstract filler / waveform / equalizer visuals or generic particle systems
  - Bullet lists, feature callouts, or marketing slides elsewhere than the final landing-proof scene
  - Deviating from the amber (`#f4bb92`) / near-black palette

## Visual Identity
- Background: #050505 → #12131a ambient (`constellation-bg` feel)
- Text: #ffffff (headline), rgba(255,255,255,0.6) (secondary), on-amber ink #4a280a
- Accent: #f4bb92 (amber/rose-gold) with gradient #f4bb92 → #e4c285
- Display/body font: Cormorant Garamond (light italic serif; 300–700); match % and labels may use monospace per the app
- Visual references from the project: quiz card (serif name + note capsules + slider), match-card grid, amber glow on dark, tracked-caps eyebrow labels

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Hook — 3.5s — eyebrow `Neural Sommelier Protocol` + typed `Molecular Artistry.`
2. Reveal — 4.5s — `Neural Instinct.` (locked 3.52s) + chip `91.5% Match Accuracy` (5.03s)
3. Rate #1 — 8.0s — working quiz card: `Discovery 1 / 8`, Shalimar Parfum, note capsules, `5.0 → 7.4` rating count-up, `Confirm Dimension`
4. Neural Pipeline loader — 8.5s — `Neural Pipeline` eyebrow, cycling lore lines on beats (16.02/18.02/20.02/22.02), progress rail, `Syncing 24k Archive` / `V.PRIME_ELITE`
5. Rate #2 — 8.5s — `Discovery 2 / 8` (25% rail), Valentino Uomo Intense, `5.0 → 8.1` count-up, `Confirm Dimension`
6. Constellation — 9.5s — header `Your Aromatic Constellation` (32.02s), three match cards (34.02/35.52/37.02), `Start Discovery →` (38.52s)
7. Landing proof — 8.5s — `Neural Sommelier Protocol v2.0-REWIRED`, tagline, stats 5,130+/91.5%/50K+, CTAs `Browse Library` / `Browse Popular Picks`
8. Outro — 11.5s — `Scentrix` wordmark (49.02s), `Your neural sommelier.`, `Start Discovery →` (51.52s), music fade

## Audio
- Audio role: warm upbeat ambient bed with sparse professional accents
- Audio arc: warm intro → slight lift at reveal → steady pulse through the two rate beats and loader → natural build peaking at the match cascade (34.02s) → settle through landing proof → close + fade under the wordmark
- Music: `happy-beats-business-moves-vol-1-by-ende-dot-app.mp3` (copied to `brag-output/composition/assets/music/`; 120.19 BPM; 60s region = uniform 0.5s beat grid)
- Music treatment: fade-in ≈0.5s; volume ≈0.32 (steady warm bed); build toward the match cascade key; fade out ≈1.0s after the outro wordmark settles (music element spans full 60s)
- Music cue guidance: bundled preset `assets/music/cues/happy-beats-business-moves-vol-1-by-ende-dot-app.music-cues.json` (strongCues + beats arrays; planning window 0–25s). Anchors within window: 3.52s (reveal), 8.02s (quiz header), 16.02s (peak — repurposed to loader tail). Beat-grid hints: 5.03s stat chip, 8.52s card body #1, 10.02s rating count #1, 11.02s confirm #1, 16.02/18.02/20.02/22.02 loader lore swaps. Beyond 25s: uniform 0.5s grid — 24.02 topbar #2, 24.52 card body #2, 26.52 count #2, 27.52 confirm #2, 32.02 constellation header, 34.02/35.52/37.02 match cards, 38.52 CTA, 40.5–46.5 landing proof, 49.02 wordmark, 51.52 CTA
- Audio-reactive treatment: subtle — RMS/bass energy may breathe the amber glow intensity and card presence; no waveforms, no strobing
- Audio-coupled moments:
  - Hook typed text → key ticks
  - Reveal slam → one soft whoosh
  - Rating count-up → subtle tick (both rate beats)
  - Loader lore swap → one quiet key tick each
  - Match card cascade → one low-risk card sound per arrival
  - Wordmark → dry low-impact hit with a short ring into the music fade
- SFX selection guidance: motion-matched; card-like sounds for card arrivals; short announcing cue for the wordmark; keep repeated/polished sounds low on high-frequency risk (use `assets/sfx/sfx-analysis.md`)
- SFX analysis guidance: `C:\Users\KIIT0001\.agents\skills\brag\assets\sfx\sfx-analysis.md`
- Exact SFX choice: Hyperframes chooses filenames, timestamps, density, volume after the visual animation exists; copy chosen files into `brag-output/composition/assets/sfx/`
- Audio files: music already at `brag-output/composition/assets/music/`

## Hyperframes Instructions
Load the Hyperframes domain skills — `hyperframes-core` (composition contract + `data-*` timing), `hyperframes-animation` (motion), `hyperframes-creative` (design spec, beats, audio-reactive), `hyperframes-keyframes` (seek-safe keyframes), and `hyperframes-cli` (lint/check/render). /brag is its own workflow: do NOT enter the `hyperframes` entry-point intent interview and do NOT route into its generic promo / launch-video workflow. Prefer native Hyperframes conventions.

Requirements:
- Show real UI/copy from the source project in every scene (quiz card, loader, match cards, landing hero, verbatim copy).
- Keep all text readable in the final render; honor the reading-time floors set in `brag-plan.md`.
- Keep the video at 60.0s (± a frame or two).
- Include the music + SFX layer (music present at `assets/music/`).
- Treat `/brag` audio notes as guidance, not a fixed cue sheet. Choose SFX after the visual animation exists. Ignore any cue that would hurt readability (e.g. if a beat lands too close for a text line to read, use natural timing).
- Major reveals may move toward strong cues within ±0.15s — that's what the anchors above already are. Mark them `// beat-locked`. Smaller sequential items snap to beats within ±0.10s — mark `// beat-grid`. Keep to the 1–3 locks listed plus the quiz card (centerpiece, so it clearly benefits). Beats past 25s are the uniform 0.5s grid of the 120.19 BPM table (extrapolated).
- Wire at least one visual element subtly to the music's RMS/bass (audio-reactive), per `hyperframes-creative`.
- Use local assets for audio.
- Run `npx hyperframes check` before render — it is /brag's single gate.