import { test } from '@playwright/test';
import path from 'path';

test('debug booking page', async ({ page }) => {
  await page.goto('http://localhost:3000/');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // Take screenshot
  await page.screenshot({ path: 'e2e/screenshot-home.png', fullPage: true });
  console.log('=== Page HTML ===');
  console.log(await page.content());

  // Check what's visible
  const selects = await page.locator('select').count();
  console.log('Select count:', selects);

  // Try clicking Find Slots first to see what happens
  const findSlotsBtn = page.locator('button:has-text("Find Slots")');
  console.log('Find slots visible:', await findSlotsBtn.isVisible());
  console.log('Find slots disabled:', await findSlotsBtn.isDisabled());

  // Check course buttons
  const courseBtns = page.locator('button:has-text("Full Body Massage")');
  console.log('Course buttons count:', await courseBtns.count());

  // Check slots
  for (let i = 0; i < 3; i++) {
    const dateBtn = page.locator('button:has-text("Today")');
    console.log(`Date button (attempt ${i}):`, await dateBtn.isVisible({ timeout: 2000 }).catch(() => false));
    await page.waitForTimeout(500);
  }
});
