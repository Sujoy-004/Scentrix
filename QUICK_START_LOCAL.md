# QUICK START: RUN YOUR WEBSITE LOCALLY

## 🚀 Start Your Website (< 1 minute setup)

### Step 1: Open PowerShell Terminal

```powershell
cd "C:\Users\KIIT0001\Downloads\Telegram Desktop\ScentScapeAI\ScentScape\frontend"
npm run dev
```

### Step 2: Open Your Browser

```
http://localhost:3000
```

---

## ✅ Expected Output

When you run `npm run dev`, you should see:

```
▲ Next.js 14.x.x
- Local:        http://localhost:3000
- Environments: .env.local

✓ Ready in 5.2s
```

🟢 If you see "Ready", your website is running locally!

---

## 📍 Pages to Test

| Page | URL | What to Check |
|------|-----|---------------|
| **Home** | http://localhost:3000 | Hero section, animations, buttons |
| **Fragrances** | http://localhost:3000/fragrances | List view, cards, search |
| **Quiz** | http://localhost:3000/onboarding/quiz | Rating sliders, form submission |
| **Recommendations** | http://localhost:3000/recommendations | Results display, scoring |
| **Families** | http://localhost:3000/families | Category view |
| **Login** | http://localhost:3000/auth/login | Form displays, no errors |
| **Register** | http://localhost:3000/auth/register | Form displays, no errors |
| **Profile** | http://localhost:3000/profile | User data (if logged in) |
| **Search** | http://localhost:3000/search | Search bar, results |

---

## 🔍 Check for Issues

### Open DevTools (F12)

**Console Tab:**
- ✅ No red error messages
- ✅ Any yellow warnings okay
- ✅ No "undefined" errors

**Network Tab:**
- ✅ All requests are green (200 status)
- ✅ No red failed requests
- ✅ Images loading

**Responsive:**
- ✅ Ctrl+Shift+M to test mobile (375px)
- ✅ Ctrl+Shift+M again for tablet (768px)
- ✅ Full screen for desktop (1280px)

---

## 🛑 If Something's Wrong

### Website won't load
```powershell
# Kill the server (Ctrl+C in terminal)
# Clear cache in browser (Ctrl+Shift+Delete)
# Restart: npm run dev
```

### Errors in console
```powershell
# Check terminal for error message
# Look for "[error]" or "ERR!"
# If found, restart: npm run dev
```

### Styling looks broken
```powershell
# Hard refresh: Ctrl+Shift+R
# Or: npm run dev (restart server)
```

### Missing pages
```powershell
# Verify page file exists in src/app/
# Check file naming (case-sensitive)
# Restart: npm run dev
```

---

## 📊 Performance Check

### Quick Performance Audit

1. **In DevTools:** Go to "Lighthouse" tab
2. **Click:** "Analyze page load"
3. **Check scores:**
   - Performance: ≥85? ✅
   - Accessibility: ≥90? ✅
   - Best Practices: ≥90? ✅
   - SEO: ≥90? ✅

If all ✅, you're ready for Phase 6!

---

## 🎯 Ready for Phase 6?

When you've confirmed:

- ✅ Website loads at http://localhost:3000
- ✅ All pages accessible
- ✅ No console errors
- ✅ Lighthouse scores excellent
- ✅ Responsive design working
- ✅ No broken links/images

**Then you're 100% ready for Phase 6 deployment!** 🚀

---

## 📝 Full Testing Checklist

See: `LOCAL_TESTING_CHECKLIST.md` for comprehensive testing guide

```bash
# To view the full checklist:
cat LOCAL_TESTING_CHECKLIST.md
```

---

## ⏹️ Stop the Dev Server

When done testing:

```powershell
# In the terminal running npm run dev:
Ctrl+C

# This stops the server
# You can run npm run dev again anytime
```

---

## 💡 Pro Tips

- **Hot reload:** Changes auto-reload when you save files
- **Build for production:** `npm run build` (not needed for testing)
- **Check build size:** `npm run build` shows bundle sizes
- **Clear cache:** Ctrl+Shift+Delete in browser
- **Dark mode:** Toggle in app if implemented

---

## Ready? Let's Go! 🚀

```powershell
npm run dev
# Then visit: http://localhost:3000
```

Enjoy your local website! Report back when you've tested everything and you're ready for Phase 6! ✅
