# Frontend Testing Guide - AI Offer Agent

**Quick Start Guide for Local Testing**
**Last Updated**: 2025-10-06

## 🚀 Quick Start (5 Minutes)

### Step 1: Start the Frontend

```bash
# Navigate to frontend directory
cd /home/patrickjaja/development/aigentics-corp/aigentics-corp/frontend

# Install dependencies (if not already done)
npm install

# Start development server
npm run dev
```

**Expected Output**:
```
- Ready on http://localhost:3000
- ○ Compiling / ...
- ✓ Compiled successfully
```

### Step 2: Open in Browser

Navigate to: **http://localhost:3000**

You should see the main conversation page with:
- ✅ "AI Offer Agent" title
- ✅ Language selector (Deutsch, English, Français, etc.)
- ✅ Progress indicator
- ✅ Chat interface

---

## 🧪 Main Testing Scenarios (No Backend Required)

### Scenario 1: UI/UX Testing (Frontend Only)
**Duration**: 5-10 minutes
**Backend Required**: ❌ NO

#### What You Can Test:

**1.1 Layout & Responsiveness**
```bash
# Open browser DevTools (F12)
# Toggle device toolbar (Ctrl+Shift+M)
# Test different screen sizes:
- Mobile: 375x667 (iPhone SE)
- Tablet: 768x1024 (iPad)
- Desktop: 1920x1080
```

**✅ Check**:
- [ ] All elements visible at different screen sizes
- [ ] No horizontal scrolling
- [ ] Text readable without zooming
- [ ] Buttons accessible
- [ ] Chat interface responsive

**1.2 Language Selector**
```
Action: Click language dropdown
Expected: Shows 5 languages (Deutsch, English, Français, Español, Italiano)

Action: Select "Deutsch"
Expected: Interface labels might change (though full translation needs backend)

Action: Select "English"
Expected: Dropdown updates correctly
```

**✅ Check**:
- [ ] Dropdown opens/closes smoothly
- [ ] Selected language highlighted
- [ ] No JavaScript errors in console

**1.3 Input Validation**
```
Action: Type in the message textarea
Expected: Text appears, cursor blinks

Action: Press Enter (without Shift)
Expected: Attempts to send message (will fail without backend)

Action: Click "Senden" button with empty input
Expected: Button disabled (no action)

Action: Type very long text (1000+ characters)
Expected: Textarea expands, scrollbar appears
```

**✅ Check**:
- [ ] Textarea accepts input
- [ ] Character limit (if any) enforced
- [ ] Button states (enabled/disabled) work
- [ ] Keyboard shortcuts functional

**1.4 Visual Design**
```
Inspect:
- Color scheme (blue primary, gray backgrounds)
- Typography (readable fonts)
- Spacing and padding
- Border radius on elements
- Shadow effects
```

**✅ Check**:
- [ ] Professional appearance
- [ ] Consistent styling
- [ ] Good contrast ratios
- [ ] No visual glitches

---

### Scenario 2: Mock Mode Testing (With Mock Data)
**Duration**: 10-15 minutes
**Backend Required**: ❌ NO (using browser console)

You can simulate backend responses using browser DevTools:

**2.1 Mock API Responses**

Open browser console (F12) and run:

```javascript
// Mock conversation start
const mockConversation = {
  conversationId: 'mock-conv-123',
  initialQuestions: [
    'What type of project are you planning?',
    'What is your budget range?',
    'What is your timeline?'
  ]
};

// Mock message response
const mockMessageResponse = {
  aiResponse: 'Thank you for that information. Can you tell me more about your technical requirements?',
  nextQuestions: [
    'Which platforms do you need to support?',
    'Do you have any existing systems to integrate with?'
  ],
  completionPercentage: 40,
  status: 'active'
};

// You can modify the apiClient to return mock data
window.mockMode = true;
console.log('Mock mode enabled - API calls will return test data');
```

**✅ Test**:
- [ ] Message bubbles appear correctly (user on right, AI on left)
- [ ] Timestamps display properly
- [ ] Progress bar updates (0% → 40% → 100%)
- [ ] Loading indicators work

---

### Scenario 3: Component Testing (Isolated)
**Duration**: 5 minutes each component
**Backend Required**: ❌ NO

**3.1 Test Available Pages**

Navigate to each page directly:

1. **Main Conversation Page**: http://localhost:3000
   - ✅ Loads without errors
   - ✅ Shows conversation interface
   - ✅ Language selector present

2. **Offer Review Page** (mock): http://localhost:3000/offer/test-123
   - ⚠️ Will show error without backend data
   - ✅ Check error handling is graceful

3. **Admin Dashboard**: http://localhost:3000/admin
   - ⚠️ May require authentication
   - ✅ Check redirect or login prompt

4. **Admin Approval Detail**: http://localhost:3000/admin/approvals/test-456
   - ⚠️ Will show error without backend data
   - ✅ Check error handling

**3.2 Test Error States**

```
Action: Disconnect from internet (or block localhost:8000 in DevTools)
Action: Try to interact with UI
Expected: Friendly error message (not crash)
```

**✅ Check**:
- [ ] Graceful error handling
- [ ] User-friendly error messages
- [ ] No console crashes
- [ ] Option to retry

---

## 🔗 Testing With Backend (Full Integration)

### Scenario 4: Complete Conversation Flow
**Duration**: 10-15 minutes
**Backend Required**: ✅ YES

**Prerequisites**:
```bash
# Terminal 1: Start backend services
cd /home/patrickjaja/development/aigentics-corp/aigentics-corp/backend
docker-compose up -d  # Infrastructure
source venv/bin/activate
python -m src.main  # Main API (port 8000)

# Terminal 2: Start frontend
cd /home/patrickjaja/development/aigentics-corp/aigentics-corp/frontend
npm run dev  # Port 3000
```

**4.1 Start Conversation**

```
1. Open http://localhost:3000
2. Select language (English recommended for testing)
3. Wait for conversation to start automatically

Expected:
- Conversation ID displayed in DevTools console
- AI greeting message appears
- Initial questions shown (max 5)
```

**✅ Check**:
- [ ] Auto-start works (or click "Start" if button exists)
- [ ] API call succeeds (check Network tab)
- [ ] Response time < 3 seconds
- [ ] Questions in selected language

**4.2 Have Conversation**

```
Sample Conversation:

User: "We need an e-commerce platform"
AI: [Asks follow-up questions about features]

User: "Product catalog, shopping cart, payment integration, user accounts"
AI: [Asks about scale/users]

User: "About 10,000 users per month"
AI: [Asks about technical preferences]

User: "React frontend, Node.js backend preferred"
AI: [Asks about budget]

User: "50,000 to 80,000 EUR"
AI: [Summarizes and offers to create offer]
```

**✅ Check**:
- [ ] Each response appears within 3 seconds
- [ ] Max 5 questions per round
- [ ] Progress bar increases (0% → 20% → 40% → 60% → 80% → 100%)
- [ ] Conversation context maintained (no repeated questions)
- [ ] Typing indicator shows while waiting

**4.3 Generate Offer**

```
When conversation reaches 100%:
- System prompts for customer details
- GDPR consent form appears
- Fill in details:
  Company: Test GmbH
  Contact: Max Mustermann
  Email: test@example.com
  Phone: +49 30 12345678
  ✓ Consent to offer generation

- Click "Angebot erstellen" (Generate Offer)

Expected:
- Loading indicator with progress updates
- "Anforderungen werden analysiert..."
- "Arbeitspakete werden erstellt..."
- "Stunden werden geschätzt..."
- "PDF wird generiert..."
- Redirect to offer preview page
```

**✅ Check**:
- [ ] GDPR form validation works
- [ ] Cannot submit without consent
- [ ] Email/phone format validated
- [ ] Generation completes in < 30 seconds
- [ ] Progress updates visible
- [ ] Successful redirect

**4.4 Review Offer**

```
On offer preview page:
- Offer number (format: YY-NNNN)
- Customer details
- Project summary
- Work packages with:
  - Description
  - Deliverables
  - Estimated hours
  - Cost (German format: 1.234,56 €)
- Total cost
- Valid until date (30 days)
- Download PDF button
```

**✅ Check**:
- [ ] All sections display correctly
- [ ] Numbers formatted correctly (German: 1.234,56 €)
- [ ] Dates formatted correctly (DD.MM.YYYY)
- [ ] Professional layout
- [ ] Download button functional

---

### Scenario 5: Multi-Language Testing
**Duration**: 5 minutes
**Backend Required**: ✅ YES (for full testing)

**5.1 Test Language Switching**

```
1. Start conversation in German (Deutsch)
Expected: AI questions in German

2. Switch to English mid-conversation
Expected: Interface updates, but conversation continues in German

3. Start NEW conversation in French
Expected: New AI questions in French
```

**✅ Check**:
- [ ] Language selector updates
- [ ] UI labels change language
- [ ] AI responses in correct language
- [ ] No mixed languages in same message

**5.2 Test Supported Languages**

Try each language:
- ✅ Deutsch (German)
- ✅ English
- ✅ Français (French)
- ✅ Español (Spanish)
- ✅ Italiano (Italian)

**Note**: Full 24-language support requires backend translation service

---

### Scenario 6: Error Handling
**Duration**: 5 minutes
**Backend Required**: ⚠️ YES (to test failures)

**6.1 Simulate Backend Down**

```
1. Start conversation
2. Stop backend (Ctrl+C in backend terminal)
3. Try to send message

Expected:
- Loading indicator appears
- After timeout: "Service temporarily unavailable"
- Option to retry
- No crash or blank screen
```

**✅ Check**:
- [ ] Graceful error display
- [ ] User-friendly message
- [ ] Retry button works
- [ ] No data loss in conversation

**6.2 Test Invalid Input**

```
1. Leave message empty → Send
Expected: Button disabled

2. Type only whitespace → Send
Expected: Button disabled or trimmed

3. Type very long message (10,000 chars)
Expected: Accepted or length warning
```

**✅ Check**:
- [ ] Input validation works
- [ ] Clear error messages
- [ ] No JavaScript errors

---

## 🎨 Visual Testing Checklist

### Accessibility (A11Y)

**Test with Keyboard Only** (no mouse):
```
Tab through the page:
- [ ] All interactive elements reachable
- [ ] Focus indicator visible
- [ ] Can activate buttons with Enter/Space
- [ ] Can navigate dropdowns with arrows
```

**Test with Screen Reader** (if available):
```
- [ ] All text read correctly
- [ ] Images have alt text
- [ ] Form labels associated
- [ ] Buttons have descriptive labels
```

**Color Contrast**:
```
Check in DevTools > Lighthouse > Accessibility
- [ ] Text meets WCAG AA (4.5:1)
- [ ] UI elements meet WCAG AA (3:1)
- [ ] No information by color alone
```

---

## 🔍 Browser Console Checks

### Things to Monitor in DevTools

**Console Tab** (F12 → Console):
```
✅ Good signs:
- Clean console (no errors on load)
- API calls logged (if verbose)
- Component lifecycle logs (in dev)

❌ Red flags:
- JavaScript errors
- Failed API calls (without graceful handling)
- Warning about deprecated APIs
- Memory leaks (over time)
```

**Network Tab** (F12 → Network):
```
Watch API calls:
- POST /v1/conversations → 200 OK (< 2s)
- POST /v1/conversations/{id}/messages → 200 OK (< 3s)
- POST /v1/offers → 200 OK (< 30s)

Check:
- [ ] Reasonable response times
- [ ] Proper HTTP status codes
- [ ] No unnecessary calls
- [ ] Payload sizes reasonable
```

**Performance Tab** (F12 → Performance):
```
Record a session and check:
- [ ] First Contentful Paint < 1.5s
- [ ] Time to Interactive < 3s
- [ ] No long tasks (> 50ms)
- [ ] Smooth animations (60fps)
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "Cannot connect to backend"
```
Error: Failed to start conversation

Solution:
1. Check backend is running:
   curl http://localhost:8000/health

2. Check .env.local:
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

3. Check CORS in backend allows localhost:3000
```

### Issue 2: "Page won't load"
```
Error: Module not found / Build failed

Solution:
1. Delete .next folder:
   rm -rf .next

2. Reinstall dependencies:
   rm -rf node_modules package-lock.json
   npm install

3. Restart dev server:
   npm run dev
```

### Issue 3: "Styles not applying"
```
Components look unstyled

Solution:
1. Check Tailwind CSS compiled:
   npm run dev (rebuilds on changes)

2. Clear browser cache:
   Ctrl+Shift+R (hard refresh)

3. Check console for CSS errors
```

### Issue 4: "Type errors in console"
```
TypeScript errors appearing

Solution:
1. Run type check:
   npm run type-check

2. Fix type errors in code

3. Restart dev server
```

---

## 📊 Testing Checklist Summary

### Quick Test (5 minutes - No Backend)
- [ ] Page loads on http://localhost:3000
- [ ] No JavaScript errors in console
- [ ] UI elements render correctly
- [ ] Responsive on mobile/tablet/desktop
- [ ] Language selector works

### Standard Test (15 minutes - With Backend)
- [ ] Conversation starts successfully
- [ ] Can send/receive messages
- [ ] Progress indicator updates
- [ ] Offer generation works
- [ ] PDF download functional

### Comprehensive Test (30 minutes - Full Flow)
- [ ] All 5 languages work
- [ ] GDPR consent flow complete
- [ ] High-value offer triggers approval
- [ ] Error handling graceful
- [ ] Accessibility standards met
- [ ] Performance targets met

---

## 🎯 Quick Testing Commands

```bash
# Start frontend only (UI testing)
cd frontend && npm run dev

# Run frontend tests
npm test

# Run type checking
npm run type-check

# Build production version (test build)
npm run build

# Lint code
npm run lint

# Run all checks at once
npm run type-check && npm run lint && npm test
```

---

## 📝 Test Results Template

```markdown
**Test Date**: 2025-10-06
**Tester**: [Your Name]
**Browser**: Chrome 120.0
**Backend**: Running / Not Running

### Scenarios Tested
- [ ] Scenario 1: UI/UX (No Backend)
- [ ] Scenario 2: Mock Mode
- [ ] Scenario 3: Component Isolation
- [ ] Scenario 4: Complete Flow (With Backend)
- [ ] Scenario 5: Multi-Language
- [ ] Scenario 6: Error Handling

### Issues Found
1. [Issue description]
2. [Issue description]

### Screenshots
[Attach if relevant]

### Notes
[Any additional observations]

### Verdict
✅ PASS / ⚠️ PASS WITH ISSUES / ❌ FAIL
```

---

## 🚀 Next Steps After Testing

1. **If Frontend Works Without Backend**:
   - Great! The UI is solid
   - Document any UI/UX improvements
   - Test different browsers (Firefox, Safari)

2. **If Frontend Works With Backend**:
   - Test all user journeys
   - Check performance under load
   - Validate GDPR compliance flows

3. **If Issues Found**:
   - Document in GitHub Issues
   - Prioritize critical vs. nice-to-have
   - Fix and re-test

---

## 💡 Pro Tips

1. **Browser DevTools is your friend**: Keep it open (F12)
2. **Test in different browsers**: Chrome, Firefox, Safari
3. **Use incognito mode**: Avoid cached issues
4. **Check mobile first**: Most users on mobile
5. **Document everything**: Screenshots help debugging

---

**Happy Testing! 🎉**

For questions or issues, check the main project documentation or create a GitHub issue.

---
*Last Updated: 2025-10-06*
*Frontend URL: http://localhost:3000*
*Backend URL: http://localhost:8000*
