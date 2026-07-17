# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e/booking-flow.spec.ts >> Booking Flow >> full booking flow - slot click navigates to booking page and shows confirm form
- Location: e2e/booking-flow.spec.ts:4:7

# Error details

```
Error: expect(received).toContain(expected) // indexOf

Expected substring: "/booking"
Received string:    "http://localhost:3000/"
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - navigation [ref=e2]:
    - generic [ref=e4]:
      - link "AI Massage Booking" [ref=e5] [cursor=pointer]:
        - /url: /
      - generic [ref=e6]:
        - link "Book" [ref=e7] [cursor=pointer]:
          - /url: /
        - link "My Bookings" [ref=e8] [cursor=pointer]:
          - /url: /my-bookings
  - generic [ref=e10]:
    - generic [ref=e12]:
      - generic [ref=e13]:
        - generic [ref=e14]: Shop
        - combobox [ref=e15]:
          - option "Shinjuku Store" [selected]
          - option "Shibuya Store"
      - generic [ref=e16]:
        - generic [ref=e17]: Date
        - generic [ref=e18]:
          - button "←" [ref=e19]
          - button "Today, Jul 16" [ref=e20]
          - button "→" [ref=e21]
    - generic [ref=e23]:
      - generic [ref=e24]:
        - generic [ref=e25]: Guests
        - combobox [ref=e26]:
          - option "1" [selected]
          - option "2"
          - option "3"
      - generic [ref=e27]:
        - generic [ref=e28]: Duration
        - combobox [ref=e29]:
          - option "15 min"
          - option "30 min"
          - option "45 min"
          - option "60 min" [selected]
          - option "75 min"
          - option "90 min"
          - option "105 min"
          - option "120 min"
          - option "135 min"
          - option "150 min"
          - option "165 min"
          - option "180 min"
          - option "195 min"
          - option "210 min"
          - option "225 min"
          - option "240 min"
          - option "255 min"
          - option "270 min"
          - option "285 min"
          - option "300 min"
    - generic [ref=e30]:
      - heading "Main Course" [level=3] [ref=e31]
      - generic [ref=e32]:
        - button "Full Body Massage" [ref=e33]
        - button "Dry Head Spa" [ref=e34]
        - button "Aromatherapy" [ref=e35]
    - generic [ref=e36]:
      - heading "Add-ons (Optional)" [level=3] [ref=e37]
      - generic [ref=e38]:
        - button "Premium Mattress · 1,500 VND" [ref=e39]
        - button "Foot Reflexology · 2,000 VND" [ref=e40]
    - button "🔍 Find Slots" [ref=e41]
  - contentinfo [ref=e42]:
    - paragraph [ref=e44]: © 2026 AI Massage Booking. All rights reserved.
  - button "Open Next.js Dev Tools" [ref=e50] [cursor=pointer]:
    - img [ref=e51]
  - alert [ref=e54]
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe.serial('Booking Flow', () => {
  4   |   test('full booking flow - slot click navigates to booking page and shows confirm form', async ({ page }) => {
  5   |     const consoleErrors: string[] = [];
  6   |     const pageErrors: Error[] = [];
  7   |     page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  8   |     page.on('pageerror', err => pageErrors.push(err));
  9   | 
  10  |     await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
  11  |     await page.waitForTimeout(2000);
  12  | 
  13  |     // Wait for the shop select to be populated
  14  |     const shopSelect = page.locator('select').first();
  15  |     await expect(shopSelect).not.toBeEmpty({ timeout: 15000 });
  16  | 
  17  |     // Click "Find Slots"
  18  |     const findBtn = page.getByRole('button', { name: /find slots/i });
  19  |     await expect(findBtn).toBeVisible({ timeout: 3000 });
  20  | 
  21  |     // First try to find slots without any date navigation
  22  |     await findBtn.click();
  23  |     await page.waitForTimeout(2000);
  24  | 
  25  |     // Check for available slot buttons
  26  |     let clickedSlot = false;
  27  |     for (let attempt = 0; attempt < 6 && !clickedSlot; attempt++) {
  28  |       // Wait for loading to finish
  29  |       await page.waitForTimeout(1500);
  30  | 
  31  |       // Look for visible, enabled buttons with time format
  32  |       const slotButtons = page.locator('button').filter({ hasText: /^\d{2}:\d{2}$/ });
  33  |       const count = await slotButtons.count();
  34  | 
  35  |       if (count > 0) {
  36  |         // Check if any are enabled/clickable
  37  |         for (let i = 0; i < count; i++) {
  38  |           const btn = slotButtons.nth(i);
  39  |           const disabled = await btn.isDisabled();
  40  |           if (!disabled) {
  41  |             const text = await btn.textContent();
  42  |             console.log(`Clicking slot: ${text} (button ${i})`);
  43  |             await btn.click();
  44  |             clickedSlot = true;
  45  |             break;
  46  |           }
  47  |         }
  48  |       }
  49  | 
  50  |       if (!clickedSlot) {
  51  |         // Navigate to next day and try again
  52  |         console.log(`Attempt ${attempt}: No clickable slots found, trying next day`);
  53  |         const nextBtn = page.locator('button').filter({ hasText: '→' });
  54  |         if (await nextBtn.isVisible()) {
  55  |           await nextBtn.click();
  56  |           await page.waitForTimeout(300);
  57  |           await findBtn.click();
  58  |         }
  59  |       }
  60  |     }
  61  | 
  62  |     expect(clickedSlot).toBe(true);
  63  | 
  64  |     // Wait for navigation or re-render
  65  |     await page.waitForTimeout(3000);
  66  | 
  67  |     const url = page.url();
  68  |     console.log('URL after slot click:', url);
  69  |     console.log('Page errors:', pageErrors);
  70  |     console.log('Console errors:', consoleErrors);
  71  | 
  72  |     // Should be on booking page
> 73  |     expect(url).toContain('/booking');
      |                 ^ Error: expect(received).toContain(expected) // indexOf
  74  | 
  75  |     // Wait for client-side hydration
  76  |     await page.waitForTimeout(3000);
  77  | 
  78  |     const body = await page.textContent('body');
  79  |     console.log('=== Page content ===');
  80  |     console.log('Has "Confirm Booking":', body.includes('Confirm Booking'));
  81  |     console.log('Has "Loading...":', body.includes('Loading...'));
  82  |     console.log('Has "Expired":', body.includes('Expired'));
  83  |     console.log('Has "Reservation Expired":', body.includes('Reservation Expired'));
  84  |     console.log('Has "Find New Slots":', body.includes('Find New Slots'));
  85  | 
  86  |     // The page should eventually show the confirm form OR expired state OR find new slots
  87  |     // The key is it shouldn't redirect to home
  88  |     expect(url).toContain('/booking');
  89  |   });
  90  | 
  91  |   test('booking page renders confirm form when localStorage has valid data', async ({ page }) => {
  92  |     // Pre-set localStorage with a valid reservation (5 min from now)
  93  |     const validData = {
  94  |       reservationId: 9999,
  95  |       sessionId: 'test-session-valid',
  96  |       shopId: 1,
  97  |       date: '2026-07-20',
  98  |       startTime: '10:00',
  99  |       endTime: '11:00',
  100 |       duration: 60,
  101 |       numberOfPeople: 1,
  102 |       courseId: 1,
  103 |       isActive: true,
  104 |       reservedUntil: new Date(Date.now() + 300000).toISOString(),
  105 |       remainingSeconds: 300
  106 |     };
  107 | 
  108 |     await page.goto('http://localhost:3000/booking');
  109 |     await page.evaluate((data) => {
  110 |       localStorage.setItem('active_reservation', JSON.stringify(data));
  111 |     }, validData);
  112 | 
  113 |     // Reload to pick up localStorage
  114 |     await page.reload({ waitUntil: 'networkidle' });
  115 |     await page.waitForTimeout(3000);
  116 | 
  117 |     const body = await page.textContent('body');
  118 |     console.log('=== Valid reservation page content ===');
  119 |     console.log('Has "Confirm Booking":', body.includes('Confirm Booking'));
  120 |     console.log('Has "Loading...":', body.includes('Loading...'));
  121 |     console.log('Has "Expired":', body.includes('Expired'));
  122 |     console.log('URL:', page.url());
  123 | 
  124 |     // Should see the confirm form
  125 |     expect(body.includes('Confirm Booking')).toBe(true);
  126 |     expect(page.url()).toContain('/booking');
  127 |   });
  128 | 
  129 |   test('booking page shows expired when localStorage has expired reservation', async ({ page }) => {
  130 |     // Pre-set localStorage with an expired reservation
  131 |     const expiredData = {
  132 |       reservationId: 9998,
  133 |       sessionId: 'test-session-expired',
  134 |       shopId: 1,
  135 |       date: '2026-07-20',
  136 |       startTime: '10:00',
  137 |       endTime: '11:00',
  138 |       duration: 60,
  139 |       numberOfPeople: 1,
  140 |       courseId: 1,
  141 |       isActive: false,
  142 |       reservedUntil: new Date(Date.now() - 60000).toISOString(),
  143 |       remainingSeconds: 0
  144 |     };
  145 | 
  146 |     await page.goto('http://localhost:3000/booking');
  147 |     await page.evaluate((data) => {
  148 |       localStorage.setItem('active_reservation', JSON.stringify(data));
  149 |     }, expiredData);
  150 | 
  151 |     await page.reload({ waitUntil: 'networkidle' });
  152 |     await page.waitForTimeout(3000);
  153 | 
  154 |     const body = await page.textContent('body');
  155 |     console.log('=== Expired reservation page content ===');
  156 |     console.log('Has "Expired":', body.includes('Expired'));
  157 |     console.log('Has "Reservation Expired":', body.includes('Reservation Expired'));
  158 |     console.log('Has "Confirm Booking":', body.includes('Confirm Booking'));
  159 |     console.log('URL:', page.url());
  160 |   });
  161 | 
  162 |   test('simulates API response format for booking page', async ({ page }) => {
  163 |     // This test uses the EXACT format the API returns (without isActive, no Z in ISO)
  164 |     const apiFormatData = {
  165 |       reservationId: 7777,
  166 |       sessionId: 'test-session-api-format',
  167 |       shopId: 1,
  168 |       date: '2026-07-20',
  169 |       startTime: '10:00',
  170 |       endTime: '11:00',
  171 |       duration: 60,
  172 |       numberOfPeople: 1,
  173 |       courseId: 1,
```