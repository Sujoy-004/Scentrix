# Brag Plan: Scentrix

## What is this app?
Scentrix is an AI fragrance-discovery platform: rate a few scents one-by-one in its adaptive "Neural Sommelier" quiz, and a graph/neural engine returns a ranked, explained aroma constellation of matches (5,130+ scents).

## The angle
The app already dresses itself as an elegant science ritual — "Molecular Artistry. Neural Instinct.", a purple-prose eyebrow ("Neural Sommelier Protocol v2.0-REWIRED"), amber glows on near-black, italic Cormorant serif. Play it 100% straight and quiet-premium: the *working ritual* is the show. Viewer watches a scent get rated and immediately sees three named matches land on the beat — proof of the promise, no marketing slides.

## Hook (first 2-3 seconds)
Nearly-black frame. A small amber eyebrow fades in — `Neural Sommelier Protocol`. Then `Molecular Artistry.` types itself in across the screen in light italic Cormorant with soft key ticks. Elegant, specific, on-brand. The next ~58 seconds answer "…okay, where's the neural instinct?"

## Key moments (the middle)
- **The characterize step:** the working quiz screen (`Discovery 1 / 8` + progress bar) arrives; the Shalimar card enters with real note capsules (Bergamot · Floral); the rating readout counts `5.0 → 7.4` as the slider fills; `Confirm Dimension` prompts.
- **The neural core:** real loader moment from the app — `Neural Pipeline` eyebrow, the lore lines cycling (`Synthesizing 2.1M Graph Relationships...`, `Decoding Animalic Musks...`, `Waking the Digital Sommelier...`), the progress rail filling, restrained orbital rings. The science ritual made visible.
- **The second rate:** a second quiz beat (`Discovery 2 / 8`, 25% rail) — Valentino Uomo Intense (Mandarin Orange · Nutmeg) rated `5.0 → 8.1`, confirming the pattern.
- **The payoff:** header `Your Aromatic Constellation` / badge `Protocol Results Complete`; three named match cards (Shalimar Parfum, Valentino Uomo Intense, Opium Pour Homme) cascade onto consecutive beats, each with match %, note chips and one short reason line.
- **The landing frame:** real hero proof — `Neural Sommelier Protocol v2.0-REWIRED`, `Discover the scent DNA that defines your dimension.`, stat row `5,130+ Elite Scents · 91.5% Match Accuracy · 50K+ Critics & Collectors`, CTA pills `Browse Library` / `Browse Popular Picks`.

## Outro / punchline
The logo moment: `Scentrix` wordmark lands on a beat with tagline `Your neural sommelier.` and a quiet `Start Discovery →` pill. Music fades out under the settled wordmark.

## User flow worth showing
entry → key action → result, from the real routes:
1. **Quiz** (`/quiz`): scent card slides in, user rates it on the 1–10 slider, hits Confirm Dimension; the neural loader runs between ratings.
2. **Recommendations** (`/recommendations`): personalized match grid with per-card match score, note chips, and server-side explanation — "Your Aromatic Constellation."
3. **Landing** (`/`): hero proof — headline, tagline, the three stats, the two CTAs.

The ritual is the centerpiece (Scenes 3–6). Hero hook and landing proof are the frame.

## Tone
- Preset: `polished`
- Creative direction: quiet premium product film — the ritual, played straight
- Interpretation: 8 scenes, longer holds, slow crossfades; typography light weight with generous letter-spacing; restraint over flash. Landing stats appear once, near the end. The product's own amber/dark palette and Cormorant italic carry all the personality.

## Format: landscape — 1920x1080
## Duration: 60.0s (user requested ~1 min; beat grid extended past 25s as the 0.5s interpolation of the 120.19 BPM cue table)

## Visual identity (from the project)
- Background: #050505 → #12131a ambient (near-black; `constellation-bg`)
- Accent: #f4bb92 (amber/rose-gold; gradient #f4bb92 → #e4c285)
- Accent-hi: #ffdcc5 · secondary amber #f6ede6 off-white text
- Text: #ffffff / rgba(255,255,255,0.6); on-amber ink #4a280a
- Display font: Cormorant Garamond (slab serif + italic; weights 300–700)
- Body font: Cormorant Garamond (same variable font serves body in the app)
- Monospace accent (match scores): monospace
- Strongest visual element: the quiz rating card (serif fragrance name, note capsules, 1–10 slider, "Confirm Dimension") and the match-card grid.

## Share copy (draft)
"Rate three scents. Scentrix returns your aroma constellation — 5,130+ fragrances, one neural sommelier. ✨"

## Audio direction
- Role: warm, upbeat ambient bed — professional, not ballroom
- Music: `happy-beats-business-moves-vol-1-by-ende-dot-app.mp3` (bundled, 120.19 BPM, precomputed cue preset exists)
- Music treatment: fade in ~0.5s; warm full bed (~0.32 level) through the middle; natural build into the match cascade; fade out over the final 1.0s once the outro wordmark settles (music element spans the full 60s)
- Music cue guidance: preset `assets/music/cues/happy-beats-business-moves-vol-1-by-ende-dot-app.music-cues.json` read. strongCue anchors within its 25s planning window: **3.52s** (reveal, i≈0.82), **8.02s** (quiz card, i≈0.89), **16.02s** (loader peak — but repurposed: match cascade/lore here), **20.02s** (wordmark of the 20.5s cut — now the loader tail). Beyond 25s, beats extend at the uniform 0.5s grid of the 120.19 BPM table.
- Audio-reactive treatment: subtle — RMS/bass breathes the amber glow and card presence; no waveforms, no strobing
- SFX posture: moderate, motion-matched, low high-frequency risk (per sfx-analysis.md): key ticks for the typed hook, one soft announcement whoosh for the reveal, card chips for card arrivals (incl. match cards), subtle key ticks for loader lore-line swaps, a gentle chime on each Confirm, one dry low-impact hit for the closing wordmark
- Audio-coupled moments: typed hook → key ticks; reveal slam → whoosh; rating count-up → tick; loader lore swaps → quiet key tick each; match card cascade → card-sound per arrival; wordmark → low hit ringing into the music fade
- Restraint rule: nothing pops louder than the copy; SFX density drops in the payoff and landing scenes except per-arrival hits

## Storyboard

### Scene 1 — Hook — 3.5s (0.0–3.5)
Nearly-black canvas. Amber glow breathes in the corner. Label `NEURAL SOMMELIER PROTOCOL` (eyebrow, tracked caps, small) fades in 0.4–1.0s. `Molecular Artistry.` types out character-by-character in light italic Cormorant (0.8–2.4s), amber cursor blinks, holds settled to 3.3s.
Sequential/interaction: yes — the headline types itself.
Audio intent: quiet, precise, confident. No tension.
Audio-coupled idea: typed text with delicate key ticks.
Music: warm ambient enters and frames the type.
Transition mood: soft crossfade → Scene 2

### Scene 2 — Reveal — 4.5s (3.5–8.0)
`Neural Instinct.` slams in at **3.52s strongCue (beat-locked)** in heavier Cormorant italic; thin amber gradient sweep crosses behind it (0.6s). Holds in full. Small stat chip `91.5% Match Accuracy` slides up onto beat **5.03s** (beat-grid) and reads (floor ≈0.8s+). Whole frame settles to 7.5s.
Sequential/interaction: no.
Audio intent: the payoff of the hook — understated but deliberate.
Audio-coupled idea: beat-locked entrance with one soft whoosh; stat chip on the 5.03 beat.
Music: slight warmth lift for the slam, then holds.
Transition mood: soft crossfade → Scene 3

### Scene 3 — Rate #1 (the characterization) — 8.0s (7.5–15.5)
Working quiz screen. Top bar `Discovery 1 / 8` + thin progress bar enter at **8.02s strongCue (beat-locked)**. Fragrance card body (brand `guerlain`, name `Shalimar Parfum`, note capsules `Bergamot · Floral`, prompt `How does this profile resonate?`) slides in onto **8.52s beat** (beat-grid). At **10.02s** the rating readout counts `5.0 → 7.4` as the slider sweeps (beat-grid), `7.4 / 10` reads. `Confirm Dimension` button warms at **11.02s** (beat-grid), amber glint crosses at ~11.3s. Warm frame holds to the crossfade.
Sequential/interaction: yes — simulated slider interaction + confirm button.
Audio intent: alive but unhurried — the interaction is the demonstration.
Audio-coupled idea: card arrival chip; count-up tick during the rating animation; gentle chime on Confirm.
Music: steady pulse; RMS subtle glow breathing on the card.
Transition mood: soft crossfade → Scene 4

### Scene 4 — Neural Pipeline loader — 8.5s (15.0–23.5)
Real loader from the app. Centered glass panel: eyebrow `Neural Pipeline`, the lore line cycling through `Synthesizing 2.1M Graph Relationships...`, `Decoding Animalic Musks...`, `Waking the Digital Sommelier...` with blur-fade swaps on the beat grid (16.02 / 18.02 / 20.02 / 22.02), two faint orbital rings rotating in opposite directions, the progress rail filling to ~90%, footer `Syncing 24k Archive` / `V.PRIME_ELITE`. This is the science ritual made visible.
Sequential/interaction: yes — lore lines progress one by one.
Audio intent: quiet machinery — precise, back-of-the-house.
Audio-coupled idea: one quiet key tick per lore-line swap.
Music: steady pulse under the loader.
Transition mood: soft crossfade → Scene 5

### Scene 5 — Rate #2 — 8.5s (23.0–31.5)
Second quiz beat. Top bar `Discovery 2 / 8` + progress bar at **24.02s** (beat-grid: 25% for 2/8). Card (brand `valentino`, name `Valentino Uomo Intense`, note capsules `Mandarin Orange · Nutmeg`, same prompt) slides in at **24.52s** (beat-grid). Rating readout counts `5.0 → 8.1` at **26.52s**, slider sweeps to 81%, `Confirm Dimension` warms at **27.52s**, glint crosses at ~28.0s. Holds.
Sequential/interaction: yes — second slider interaction.
Audio intent: the pattern is now established — confident repetition.
Audio-coupled idea: card arrival chip, count tick, gentle chime on Confirm.
Music: steady pulse, slight lift into the build.
Transition mood: soft crossfade → Scene 6

### Scene 6 — Constellation — 9.5s (31.0–40.5)
Header `Your Aromatic Constellation` + badge `PROTOCOL RESULTS COMPLETE` fade in at **32.02s** (beat-grid). Three match cards cascade onto beats — **34.02s, 35.52s, 37.02s** (beat-grid) — each: name, family label, match %, note chips; card 3 carries the short reason line `Warm spice + green freshness, like the notes you rated.` CTA pill `Start Discovery →` rises at **38.52s** (beat-grid). Amber glow pulses on the beat. Holds.
Sequential/interaction: yes — three cards arrive one by one.
Audio intent: the peak — the promise is delivered.
Audio-coupled idea: per-card card sounds locked to each arrival; CTA on grid.
Music: natural build feeding the cascade.
Transition mood: soft crossfade → Scene 7

### Scene 7 — Landing proof — 8.5s (40.0–48.5)
Real hero copy, quiet-premium. Eyebrow `Neural Sommelier Protocol v2.0-REWIRED` (40.5s), headline `Discover the scent DNA that defines your dimension.` (41.0s), the stat row `5,130+ Elite Scents · 91.5% Match Accuracy · 50K+ Critics & Collectors` staggered (42.5 / 43.5 / 44.5s), then the two real CTA pills `Browse Library` / `Browse Popular Picks` (46.5s). Proof, not marketing slides.
Sequential/interaction: yes — stats resolve one by one.
Audio intent: quiet confidence.
Audio-coupled idea: one light tick per stat.
Music: settles under the proof.
Transition mood: soft crossfade → Scene 8

### Scene 8 — Outro — 11.5s (48.5–60.0)
`Scentrix` wordmark lands at **49.02s** (beat-grid), tagline `Your neural sommelier.` below, quiet `Start Discovery →` pill at **51.52s**. Music fades out over the final ~1s (58.5s). Hold the settled closing frame to 60.0s.
Sequential/interaction: no.
Audio intent: resolution and close.
Audio-coupled idea: dry low-impact wordmark hit ringing into the music fade.
Music: fade to silence under the wordmark.
Transition mood: fade to black (end).

**Music mood for this video:** upbeat ambient warmth — professional, calm.
**Audio summary:** warm ambient bed breathes through the hook, lifts at the reveal and match cascade (card sounds + one wordmark hit), then fades out under the closing wordmark.