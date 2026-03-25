# 🧭 Navigation Guide — What Each Button & Link Does

## Quick Legend

| Button/Link | Routes To | What You See | When to Use |
|-------------|-----------|--------------|------------|
| **Logo** (top-left) | `/` | Homepage | Return home |
| **Browse** (navbar) | `/fragrances` | All fragrances list | Find specific fragrance |
| **"Start Discovery"** (hero) | `/onboarding/quiz` | Quiz format | Rate fragrances |
| **"Learn More"** (hero, green) | `/fragrances` | All fragrances list | Same as Browse |
| **Log In** (navbar, not auth) | `/auth/login` | Login form | Create account |
| **Sign Up** (navbar, not auth) | `/auth/register` | Registration form | Create account |
| **Explore Families** (NEW) | `/families` | All family categories | Browse by scent type |

---

## Full Navigation Map with Details

### 🏠 **HOMEPAGE** — `/`
**What it shows:**
- Hero banner with "Discover Your Perfect Scent" title
- "Start Discovery" button (green)
- "Learn More" button (green outline)
- Trust indicators (98% satisfaction, 1000+ fragrances, etc.)
- Testimonials from users

**Where you can go from here:**
- Click "Start Discovery" → `/onboarding/quiz` (Take the quiz)
- Click "Learn More" → `/fragrances` (Browse all fragrances)
- Click Logo → Stay on `/` (refresh homepage)
- Click "Browse" → `/fragrances` (Same as Learn More)
- Click "Log In" → `/auth/login` (Sign in if you have account)
- Click "Sign Up" → `/auth/register` (Create new account)

---

### 📚 **BROWSE ALL FRAGRANCES** — `/fragrances`
**What it shows:**
- Grid of all 8 fragrances:
  1. Sauvage (Dior)
  2. Bleu de Chanel (Chanel)
  3. Acqua di Parma
  4. Creed Aventus
  5. Oud Wood (Tom Ford)
  6. Maison Francis Kurkdjian
  7. La Nuit de l'Homme (YSL)
  8. L'Artisan Parfumeur Timbuktu

- Each card shows:
  - Fragrance emoji (🧴)
  - Name and brand
  - Top notes preview
  - Rating (★★★★★)
  - Match percentage
  - "View" button to see details

**Where you can go from here:**
- Click any "View" button → `/fragrances/[id]` (See detailed info)
- Click Logo → `/` (Return to homepage)
- Click "Browse" → Stays on `/fragrances` (Refresh)
- Click "Log In" → `/auth/login`

---

### 🎯 **QUIZ PAGE** — `/onboarding/quiz`

#### If You're NOT Logged In:
**Standard Quiz (Rating Slider Format)**
- Shows one fragrance at a time
- Rate on a scale of 1-10
- See top notes for each fragrance
- "Skip" button to skip rating
- "Next Fragrance" button to continue

8 fragrances to rate:
1. Sauvage 2. Bleu de Chanel
3. Acqua di Parma
4. Creed Aventus
5. Oud Wood
6. Maison Francis Kurkdjian
7. La Nuit de l'Homme
8. L'Artisan Parfumeur

After you rate all 8: → `/recommendations` (See your matches)

#### If You're Logged In:
**Flashcard Quiz (Flip Card Format)**
- Front of card: Fragrance brand and name
- Click card to flip → See back with:
  - Description
  - Top, middle, base notes
  - Accord/family tags
  - 5-star rating system
- Click a star to rate → Auto-advances to next
- "Previous" and "Skip" buttons
- Progress bar shows "3 of 8"

Same 8 fragrances, better format for authenticated users!

**Where you can go from here:**
- Complete quiz → `/recommendations` (See results)
- Click Logo → `/` (Abandon quiz, return home)

---

### ✨ **ALL FRAGRANCE FAMILIES** — `/families` (✅ NEW)
**What it shows:**
Grid of 8 fragrance family cards. Each card displays:

1. **🌲 Woody Family**
   - Description: "Rich, warm, and grounding..."
   - Click → `/families/woody`

2. **🍊 Citrus Family**
   - Description: "Bright, fresh, and energizing..."
   - Click → `/families/citrus`

3. **🌿 Aromatic Family**
   - Description: "Fresh, herbal, and invigorating..."
   - Click → `/families/aromatic`

4. **🌶 Spicy Family**
   - Description: "Warm, exotic, and sensual..."
   - Click → `/families/spicy`

5. **🌸 Floral Family**
   - Description: "Delicate, romantic, and elegant..."
   - Click → `/families/floral`

6. **💧 Fresh Family**
   - Description: "Light, airy, and refreshing..."
   - Click → `/families/fresh`

7. **🍓 Fruity Family**
   - Description: "Juicy, playful, and vibrant..."
   - Click → `/families/fruity`

8. **✨ Oriental Family**
   - Description: "Sweet, sensual, and warm..."
   - Click → `/families/oriental`

**Where you can go from here:**
- Click any family card → `/families/[family]` (See fragrances in that family)
- Click Logo → `/` (Return home)

---

### 🍊 **SPECIFIC FAMILY PAGE** — `/families/citrus` (Example)
**What it shows:**
- Family name: "🍊 Citrus Fragrances"
- Family description
- All fragrances in this family (may be 1-8 depending on family)
- Sort options:
  - "Highest Rated" (default)
  - "Best Match"
  - "Alphabetical"
- Result count: "Showing 3 fragrances"
- Grid of fragrance cards (same as `/fragrances`)

**Example: What's in Citrus Family?**
Some fragrances that have "Citrus" as an accord:
- Bleu de Chanel (Citrus, Woody, Aromatic)
- Acqua di Parma (Citrus, Woody, Fresh)

**Where you can go from here:**
- Click any fragrance "View" button → `/fragrances/[id]` (Details)
- Click "← All Fragrances" button → `/fragrances` (Back to all)
- Click "[family] Fragrances" button → `/families` (Back to families list)
- Click Logo → `/` (Home)

---

### 🧴 **FRAGRANCE DETAIL PAGE** — `/fragrances/bleu-de-chanel` (Example)
**What it shows:**
- Large fragrance name and brand
- Year released
- Concentration (EDT, EDP, etc.)
- Full description
- Top notes, middle notes, base notes breakdown
- Accords/families (Citrus, Woody, Aromatic, etc.)
- Rating and match score
- Add to wishlist button
- Rate this fragrance button

**Where you can go from here:**
- Click "← Back to Fragrances" → `/fragrances`
- Click "Back to Family" → `/families/[family]`
- Click Logo → `/`

---

### 🔐 **AUTHENTICATION PAGES**

#### Login — `/auth/login`
**What it shows:**
- Email input field
- Password input field
- "Log In" button
- "Create an account" link

**After successful login:**
- Redirects to → `/` (or `/onboarding/quiz` if coming from quiz)
- Navbar now shows authenticated ui (Profile, Logout instead of Log In/Sign Up)
- Quiz page now shows Flashcard format instead of Standard format

#### Register — `/auth/register`
**What it shows:**
- Email input field
- Password input field
- Password confirmation field
- "Sign Up" button
- "Already have an account?" link to Login

**After successful registration:**
- Creates new user account
- Redirects to → `/` (or requests email verification)
- You can now Log In

---

## Common User Journeys

### 🎯 Journey 1: First-Time User (No Account)
```
1. Lands on /                (Homepage)
2. Clicks "Start Discovery"  (Intrigued, wants to try)
3. Goes to /onboarding/quiz  (Takes standard quiz - rating 8 fragrances)
4. Completes quiz            (Tries to see results)
5. Sees /recommendations     (Gets recommended fragrances)
   → Result: See personalized matches!
```

### 🎯 Journey 2: Browse-First User (No Account)
```
1. Lands on /                (Homepage)
2. Clicks "Learn More"       (Wants to see fragrances first)
3. Goes to /fragrances       (Sees all 8 fragrances)
4. Clicks "View" on Sauvage  (Interested in one fragrance)
5. Sees /fragrances/sauvage  (Reads detailed info)
   → Result: Learns about specific fragrance
```

### 🎯 Journey 3: Family-Focused User (No Account)
```
1. Lands on /                      (Homepage)
2. Opens sidebar, scrolls to see   (Looking for navigation)
3. Types /families in address bar  (Directly visits families)
4. Sees /families                  (All 8 families displayed)
5. Clicks "Woody" family card      (Interested in woody scents)
6. Sees /families/woody            (All woody fragrances)
   → Result: Browses fragrances by category!
```

### 🎯 Journey 4: Registered User
```
1. Logs in at /auth/login          (Existing user)
2. Redirects to /                  (Homepage, now authenticated)
3. Clicks "Start Discovery"        (Takes flashcard variant!)
4. Goes to /onboarding/quiz        (Flashcard format, flip animation)
5. Rates 8 fragrances              (Better UI for authenticated users)
6. Completes quiz                  (Gets personalized results)
   → Result: Premium quiz experience!
```

---

## Summary: What Each Thing Does

| You Want To... | Click... | Get... |
|---|---|---|
| Rate fragrances | "Start Discovery" button | Quiz (8 fragrances) |
| See all fragrances | "Browse" link or "Learn More" | `/fragrances` list |
| Browse by scent type | "Explore Families" or `/families` | All 8 family categories |
| See one family's fragrances | Click family card | `/families/[family]` |
| Read about one fragrance | Click "View" on fragrance card | `/fragrances/[id]` detail |
| Create an account | "Sign Up" link | Registration form |
| Sign into account | "Log In" link | Login form |
| Return home | Click Logo (top-left 🌿) | `/` Homepage |

---

## Navigation Summary

✅ **Everything is now connected**
- Buttons route correctly
- No missing pages
- "Browse" = "Learn More" = All fragrances list
- "Explore Families" = New families landing page
- Quiz works for both authenticated and unauthenticated users

🧪 **Ready for testing!**

