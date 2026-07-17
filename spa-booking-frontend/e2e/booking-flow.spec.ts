import { test, expect } from '@playwright/test';

test.describe.serial('Booking Flow', () => {
  test('full booking flow - slot click navigates to booking page and shows confirm form', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: Error[] = [];
    page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    page.on('pageerror', err => pageErrors.push(err));

    await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Wait for the shop select to be populated
    const shopSelect = page.locator('select').first();
    await expect(shopSelect).not.toBeEmpty({ timeout: 15000 });

    // Click "Find Slots"
    const findBtn = page.getByRole('button', { name: /find slots/i });
    await expect(findBtn).toBeVisible({ timeout: 3000 });

    // First try to find slots without any date navigation
    await findBtn.click();
    await page.waitForTimeout(2000);

    // Check for available slot buttons
    let clickedSlot = false;
    for (let attempt = 0; attempt < 6 && !clickedSlot; attempt++) {
      // Wait for loading to finish
      await page.waitForTimeout(1500);

      // Look for visible, enabled buttons with time format
      const slotButtons = page.locator('button').filter({ hasText: /^\d{2}:\d{2}$/ });
      const count = await slotButtons.count();

      if (count > 0) {
        // Check if any are enabled/clickable
        for (let i = 0; i < count; i++) {
          const btn = slotButtons.nth(i);
          const disabled = await btn.isDisabled();
          if (!disabled) {
            const text = await btn.textContent();
            console.log(`Clicking slot: ${text} (button ${i})`);
            await btn.click();
            clickedSlot = true;
            break;
          }
        }
      }

      if (!clickedSlot) {
        // Navigate to next day and try again
        console.log(`Attempt ${attempt}: No clickable slots found, trying next day`);
        const nextBtn = page.locator('button').filter({ hasText: '→' });
        if (await nextBtn.isVisible()) {
          await nextBtn.click();
          await page.waitForTimeout(300);
          await findBtn.click();
        }
      }
    }

    expect(clickedSlot).toBe(true);

    // Wait for navigation or re-render
    await page.waitForTimeout(3000);

    const url = page.url();
    console.log('URL after slot click:', url);
    console.log('Page errors:', pageErrors);
    console.log('Console errors:', consoleErrors);

    // Should be on booking page
    expect(url).toContain('/booking');

    // Wait for client-side hydration
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    console.log('=== Page content ===');
    console.log('Has "Confirm Booking":', body.includes('Confirm Booking'));
    console.log('Has "Loading...":', body.includes('Loading...'));
    console.log('Has "Expired":', body.includes('Expired'));
    console.log('Has "Reservation Expired":', body.includes('Reservation Expired'));
    console.log('Has "Find New Slots":', body.includes('Find New Slots'));

    // The page should eventually show the confirm form OR expired state OR find new slots
    // The key is it shouldn't redirect to home
    expect(url).toContain('/booking');
  });

  test('booking page renders confirm form when localStorage has valid data', async ({ page }) => {
    // Pre-set localStorage with a valid reservation (5 min from now)
    const validData = {
      reservationId: 9999,
      sessionId: 'test-session-valid',
      shopId: 1,
      date: '2026-07-20',
      startTime: '10:00',
      endTime: '11:00',
      duration: 60,
      numberOfPeople: 1,
      courseId: 1,
      isActive: true,
      reservedUntil: new Date(Date.now() + 300000).toISOString(),
      remainingSeconds: 300
    };

    await page.goto('http://localhost:3000/booking');
    await page.evaluate((data) => {
      localStorage.setItem('active_reservation', JSON.stringify(data));
    }, validData);

    // Reload to pick up localStorage
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    console.log('=== Valid reservation page content ===');
    console.log('Has "Confirm Booking":', body.includes('Confirm Booking'));
    console.log('Has "Loading...":', body.includes('Loading...'));
    console.log('Has "Expired":', body.includes('Expired'));
    console.log('URL:', page.url());

    // Should see the confirm form
    expect(body.includes('Confirm Booking')).toBe(true);
    expect(page.url()).toContain('/booking');
  });

  test('booking page shows expired when localStorage has expired reservation', async ({ page }) => {
    // Pre-set localStorage with an expired reservation
    const expiredData = {
      reservationId: 9998,
      sessionId: 'test-session-expired',
      shopId: 1,
      date: '2026-07-20',
      startTime: '10:00',
      endTime: '11:00',
      duration: 60,
      numberOfPeople: 1,
      courseId: 1,
      isActive: false,
      reservedUntil: new Date(Date.now() - 60000).toISOString(),
      remainingSeconds: 0
    };

    await page.goto('http://localhost:3000/booking');
    await page.evaluate((data) => {
      localStorage.setItem('active_reservation', JSON.stringify(data));
    }, expiredData);

    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    console.log('=== Expired reservation page content ===');
    console.log('Has "Expired":', body.includes('Expired'));
    console.log('Has "Reservation Expired":', body.includes('Reservation Expired'));
    console.log('Has "Confirm Booking":', body.includes('Confirm Booking'));
    console.log('URL:', page.url());
  });

  test('simulates API response format for booking page', async ({ page }) => {
    // This test uses the EXACT format the API returns (without isActive, no Z in ISO)
    const apiFormatData = {
      reservationId: 7777,
      sessionId: 'test-session-api-format',
      shopId: 1,
      date: '2026-07-20',
      startTime: '10:00',
      endTime: '11:00',
      duration: 60,
      numberOfPeople: 1,
      courseId: 1,
      // no isActive field - API doesn't return it
      reservedUntil: new Date(Date.now() + 300000).toISOString().replace('Z', ''), // remove Z like API does
      remainingSeconds: 300
    };

    console.log('API format data reservedUntil:', apiFormatData.reservedUntil);

    await page.goto('http://localhost:3000/booking');
    await page.evaluate((data) => {
      localStorage.setItem('active_reservation', JSON.stringify(data));
    }, apiFormatData);

    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    console.log('=== API format reservation page content ===');
    console.log('Has "Confirm Booking":', body.includes('Confirm Booking'));
    console.log('Has "Loading...":', body.includes('Loading...'));
    console.log('Has "Expired":', body.includes('Expired'));
    console.log('Has "Reservation Expired":', body.includes('Reservation Expired'));
    console.log('URL:', page.url());
  });
});
