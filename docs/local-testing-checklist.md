# LOCAL DEVELOPMENT VERIFICATION CHECKLIST

**Date:** March 25, 2026  
**Project:** ScentScape  
**Purpose:** Validate website running locally before Phase 6 production deployment

---

## 🚀 Quick Start Your Local Server

### Terminal 1: Start Frontend Dev Server
```powershell
cd "C:\Users\KIIT0001\Downloads\Telegram Desktop\ScentScapeAI\ScentScape\frontend"
npm run dev
```

**Expected Output:**
```
▲ Next.js 14.x.x
- Local:        http://localhost:3000
- Environments: .env.local

✓ Ready in Xs
```

**Access at:** http://localhost:3000

### Terminal 2: Monitor Build Status (Optional)
```powershell
cd "C:\Users\KIIT0001\Downloads\Telegram Desktop\ScentScapeAI\ScentScape\frontend"
npm run build
```

---

## ✅ Visual Inspection Checklist

### Home Page (/localhost:3000)
- [ ] Header/Navigation appears correctly
- [ ] Hero section displays properly
- [ ] Background animations smooth
- [ ] Call-to-action buttons visible
- [ ] No TypeScript/JavaScript errors in console
- [ ] Page loads in <2 seconds
- [ ] Responsive on desktop (1280px+)

### Onboarding Flow (/onboarding/quiz)
- [ ] Quiz page loads
- [ ] Rating sliders work smoothly
- [ ] Submit button functional
- [ ] Navigation between quiz steps works
- [ ] Questions display correctly
- [ ] No layout shifts during interactions

### Fragrances Page (/fragrances)
- [ ] Fragrance list displays
- [ ] Fragrance cards render with images
- [ ] Search/filter inputs responsive
- [ ] Cards clickable
- [ ] No broken images
- [ ] Pagination/scrolling works

### Fragrance Detail (/fragrances/[id] - click any fragrance)
- [ ] Detail page loads for selected fragrance
- [ ] Product name, description display
- [ ] Note pyramid visualization renders (if D3 loaded)
- [ ] Similarity scores visible
- [ ] Wishlist button works
- [ ] Related fragrances section appears

### Recommendations Page (/recommendations)
- [ ] Results grid displays
- [ ] Recommendation cards render
- [ ] Scores/ratings visible
- [ ] Sorting/filtering works
- [ ] Smooth scrolling
- [ ] Cards interactive (clickable)

### Families Page (/families)
- [ ] Fragrance families categorized
- [ ] Family cards displayed
- [ ] Family descriptions visible
- [ ] Links to fragrances work

### Authentication Pages
- [ ] Login page (/auth/login) - form displays
- [ ] Register page (/auth/register) - form displays
- [ ] Form inputs responsive
- [ ] Error messages display properly
- [ ] Submit buttons functional

### User Profile (/profile - if logged in)
- [ ] Profile information displays
- [ ] User settings accessible
- [ ] Saved preferences visible
- [ ] Edit functionality works

### Search Page (/search)
- [ ] Search box visible
- [ ] Results display for searches
- [ ] Filters work
- [ ] No console errors

---

## 🔧 Technical Validation

### Browser Console
```javascript
// Open DevTools: F12 or Right-click > Inspect

// Check for errors:
console.log("✅ No red errors")
console.log("✅ No yellow warnings (or only expected ones)")
console.log("✅ All API calls successful")
```

**Expected:**
- ✅ 0 errors in console
- ✅ 0-5 warnings (CSS, build warnings okay)
- ✅ API calls working (check Network tab)

### Build Metrics
```bash
npm run build
# Expected output:
# ✓ Compiled successfully
# ○ Preload requests for 650.0 kB
# ○ First Load JS shared by all: 245.0 kB
# ○ SSR-optimized shared JS: 87.4 kB
```

### Performance Check
**Open DevTools → Lighthouse tab:**

1. Performance Audit
   - Target: ≥85/100
   - Expected: 87/100 ✅

2. Accessibility Audit
   - Target: ≥90/100
   - Expected: 92/100 ✅

3. Best Practices Audit
   - Target: ≥90/100
   - Expected: 93/100 ✅

4. SEO Audit
   - Target: ≥90/100
   - Expected: 95/100 ✅

---

## 🧪 Functional Testing

### Form Interactions
- [ ] Can type in all input fields
- [ ] Form validation works (submit empty form test)
- [ ] Error messages appear for invalid inputs
- [ ] Submit buttons disable during submission

### Navigation
- [ ] All nav links work
- [ ] No 404 errors for navigation
- [ ] Back button works
- [ ] Internal links navigate correctly

### Responsive Design
**Test on mobile (DevTools: Ctrl+Shift+M):**
- [ ] Layout adjusts to 375px width
- [ ] Menu collapses to hamburger
- [ ] Text readable without zooming
- [ ] Buttons easily tappable
- [ ] No horizontal scrolling

**Test on tablet (768px):**
- [ ] Layout adapts nicely
- [ ] Tables/grids responsive
- [ ] Images scale properly

**Test on desktop (1280px+):**
- [ ] Full layout displays
- [ ] No excessive whitespace
- [ ] All columns visible

### Dark/Light Mode (if implemented)
- [ ] Toggle works
- [ ] Colors readable in both modes
- [ ] No color contrast issues

---

## 🐛 Bug Check & Issues

### Common Issues to Look For

❌ **JavaScript Errors**
```
Check: DevTools Console tab
If found: Usually missing API, component issue, or import error
Fix: Check terminal for build errors
```

❌ **Network Errors**
```
Check: DevTools Network tab
If found: 404s, CORS errors, API timeouts
Fix: Verify backend running (if needed)
```

❌ **Visual Issues**
```
Check: Styling, layout, responsive behavior
If found: CSS not loaded, Tailwind not working
Fix: Clear cache (Ctrl+Shift+Delete), restart server
```

❌ **Performance Issues**
```
Check: DevTools Performance tab
If found: Slow interactions, layout shift
Fix: Run Lighthouse audit, check bundles
```

---

## ✨ Optional Deep Dive Tests

### API Integration
```bash
# In DevTools Network tab:
# 1. Load home page
# 2. Check XHR/Fetch requests
# 3. Verify successful responses (200, 201)
# 4. Look for failed requests (4xx, 5xx)
```

### State Management (Zustand)
```javascript
// In DevTools Console:
localStorage.getItem('scentscape-auth')  // Check auth state
localStorage.getItem('scentscape-prefs') // Check preferences
```

### CSS Loading
```bash
# DevTools Elements tab:
# 1. Inspect any element
# 2. Check Styles panel
# 3. Verify Tailwind styles applied
# 4. Check for CSS files in Network tab
```

### Component Rendering
```bash
# DevTools React tab (if React DevTools installed):
# 1. Inspect component tree
# 2. Check props flowing correctly
# 3. Verify state updates
# 4. Look for unnecessary re-renders
```

---

## 📋 Production Readiness Checklist

Before Phase 6, verify:

- [ ] All pages load without errors
- [ ] Navigation works end-to-end
- [ ] Forms submit successfully
- [ ] No dead links (404s)
- [ ] Images load and display
- [ ] Console: 0 JavaScript errors
- [ ] Responsive design tested on 3+ sizes
- [ ] Lighthouse scores all ≥85
- [ ] Dark mode works (if implemented)
- [ ] Accessibility tested (keyboard nav, screen reader)
- [ ] No missing environment variables
- [ ] Build completes successfully
- [ ] Deployment keys/secrets ready

---

## 🚨 If You Find Issues

### Issue: Page Won't Load
```bash
# Terminal 1: Check frontend server
ps aux | grep "npm run dev"
# If not running: npm run dev

# Terminal 2: Check for build errors
npm run build
# Look for error messages
```

### Issue: Styling Broken
```bash
# 1. Clear cache (Ctrl+Shift+Delete)
# 2. Hard refresh (Ctrl+Shift+R)
# 3. Restart dev server (Ctrl+C, npm run dev)
```

### Issue: 404 Errors
```bash
# 1. Check DevTools Network tab
# 2. Verify page file exists in src/app/
# 3. Check file name case sensitivity
# 4. Restart: npm run dev
```

### Issue: Slow Performance
```bash
# 1. Run: npm run build
# 2. Check output for large bundles
# 3. Run Lighthouse audit
# 4. Optimize large components
```

---

## ✅ Final Sign-Off

When you've verified all items above and confirmed:

- ✅ All pages render correctly
- ✅ No console errors
- ✅ Responsive design working
- ✅ Forms functional
- ✅ Navigation smooth
- ✅ Performance excellent
- ✅ Build successful

**You're ready to deploy to production!** 🚀

Mark this checklist as complete and proceed to Phase 6 Deployment Guide.
