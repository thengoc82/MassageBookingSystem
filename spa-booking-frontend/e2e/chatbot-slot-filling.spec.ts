import { test, expect } from '@playwright/test';

test.describe('Chatbot slot filling', () => {
  test('spec transcript produces clean user-facing messages', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (m) => {
      if (m.type() === 'error') consoleErrors.push(m.text());
    });

    await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Open the chat widget
    await page.getByRole('button', { name: /open chat/i }).click();
    await page.waitForTimeout(500);

    const chatInput = page.locator('#chat-input');
    await expect(chatInput).toBeVisible();

    const LEAK_PATTERNS = [
      'Please select',
      'Missing context',
      'Missing:',
      'ValidationError',
      'shop_id required',
      'course_id required',
      'phone_number required',
      'stack trace',
      'Traceback',
      'error_message',
      'Invalid state',
      'shopId is required',
      'BKYYYYMMDDXXXX',
    ];

    async function sendAndCheck(text: string, mustContain: RegExp | null) {
      await chatInput.fill(text);
      await page.keyboard.press('Enter');
      // Wait for the response message to appear (loading → response).
      await page.waitForTimeout(2500);
      const messages = await page.locator('.message, [class*="message"]').allTextContents();
      const lastAssistant = [...messages].reverse().find((m) => !m.startsWith(text));
      // Read all visible text in the chat region
      const allText = await page
        .locator('body')
        .innerText();
      for (const p of LEAK_PATTERNS) {
        expect(allText.toLowerCase(), `turn "${text}" leaked: ${p}`).not.toContain(p.toLowerCase());
      }
      if (mustContain) {
        expect(allText.toLowerCase(), `turn "${text}" missing: ${mustContain}`).toMatch(mustContain);
      }
    }

    await sendAndCheck('I want a massage', /which shop|choose a shop/i);
    await sendAndCheck('Shinjuku', /which.*course|choose a course/i);
    await sendAndCheck('Full Body Massage', /date/i);
    await sendAndCheck('Tomorrow', /guests|people/i);
    await sendAndCheck('2', /appointment times|available slots/i);

    // Console clean
    expect(consoleErrors.filter((e) => !e.includes('Download the React DevTools'))).toEqual([]);
  });
});