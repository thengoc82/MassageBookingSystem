import { test, expect } from '@playwright/test';

test.describe('Chatbot Selection Flow', () => {
  test('package and therapist selections should collapse and allow changes', async ({ page }) => {
    page.on('console', msg => console.log(msg.text()));
    
    await page.goto('http://localhost:3000/');
    await page.getByRole('button', { name: /open chat/i }).click();

    const chatContainer = page.locator('div[class*="overflow-y-auto"]');

    // Start conversation and select shop
    await page.waitForSelector('#chat-input');
    await page.locator('#chat-input').fill('I want a massage');
    await page.keyboard.press('Enter');
    await expect(chatContainer.last()).toContainText('Which shop');
    await page.locator('#chat-input').fill('Shinjuku');
    await page.keyboard.press('Enter');

    // Select course/package
    await expect(chatContainer.last()).toContainText('package', { timeout: 10000 });
    const firstPackage = page.locator('button:has-text("Full Body Massage")').first();
    await firstPackage.click();
    await page.getByRole('button', { name: 'Confirm' }).click();
    await expect(page.getByText('Package', { exact: false })).toBeVisible();
    await expect(page.getByText('Full Body Massage', { exact: false })).toBeVisible();

    // Change package
    await page.getByRole('button', { name: 'Change' }).click();
    await expect(chatContainer.last()).toContainText('package');
    const secondPackage = page.locator('button:has-text("Hot Stone")').first();
    await secondPackage.click();
    await page.getByRole('button', { name: 'Confirm' }).click();
    await expect(page.getByText('Hot Stone', { exact: false })).toBeVisible();

    // Continue to therapist selection
    await page.locator('#chat-input').fill('Tomorrow');
    await page.keyboard.press('Enter');
    await page.locator('#chat-input').fill('2');
    await page.keyboard.press('Enter');
    await expect(chatContainer.last()).toContainText('therapist', { timeout: 10000 });
    
    // Select a therapist
    const firstTherapist = page.getByRole('button', { name: 'Tanaka Yuki' });
    await firstTherapist.click();
    await page.getByRole('button', { name: 'Confirm' }).click();
    await expect(page.getByText('Therapist', { exact: false })).toBeVisible();
    await expect(page.getByText('Tanaka Yuki', { exact: false })).toBeVisible();

    // Change therapist
    await page.getByRole('button', { name: 'Change' }).click();
    const secondTherapist = page.getByRole('button', { name: 'Suzuki Kenji' });
    await secondTherapist.click();
    await page.getByRole('button', { name: 'Confirm' }).click();
    await expect(page.getByText('Suzuki Kenji', { exact: false })).toBeVisible();

    // Skip therapist
    await page.getByRole('button', { name: 'Change' }).click();
    await page.getByRole('button', { name: 'No preference' }).click();
    await expect(page.getByText('No preference', { exact: false })).toBeVisible();
  });
});
