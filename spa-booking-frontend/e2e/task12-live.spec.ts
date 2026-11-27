import { expect, test } from '@playwright/test';
import { readFileSync } from 'fs';

const frontend = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const api = process.env.TASK12_API_URL || 'http://127.0.0.1:5001/api';
const logPath = process.env.TASK12_FLASK_LOG || '/private/tmp/task12_flask.log';
const phone = `090${String(Date.now()).slice(-7)}`;

test.skip(!process.env.TASK12_LIVE, 'requires isolated Flask and the existing Next.js server');
test.setTimeout(60_000);

test('customer books through the site, verifies phone, edits, and cancels', async ({ page, request }) => {
  // The already-running Next dev server has its original API URL compiled in.
  // Forward browser API requests to the isolated live Flask process; responses
  // still come from the real API and its separate migrated database.
  await page.route(/https?:\/\/(?:localhost|127\.0\.0\.1):5000\/api\//, async route => {
    const target = route.request().url().replace(/https?:\/\/(?:localhost|127\.0\.0\.1):5000\/api/, api);
    const response = await route.fetch({ url: target });
    await route.fulfill({ response });
  });
  page.on('dialog', dialog => void dialog.accept());

  await page.goto(`${frontend}/shops`);
  await expect(page.getByRole('heading', { name: 'Our Locations' })).toBeVisible();
  await expect(page.getByText('Full Body Massage').first()).toBeVisible();
  await page.getByRole('link', { name: 'Choose a time' }).first().click();
  await expect(page.getByRole('combobox', { name: 'Shop' })).toHaveValue('1');
  const nextDay = page.getByRole('button', { name: 'Choose booking date' }).locator('xpath=../following-sibling::button');
  await nextDay.click();
  await nextDay.click();
  await page.getByRole('combobox', { name: 'Guests' }).selectOption('2');
  await page.getByRole('button', { name: 'Book 13:00' }).click();

  await expect(page.getByRole('heading', { name: 'Booking Summary', exact: true })).toBeVisible();
  await expect(page.getByText('2', { exact: true }).first()).toBeVisible();
  await page.getByRole('button', { name: 'Full Body Massage, 60 minutes, 6,000 VND' }).click();
  await page.getByLabel('Phone Number *').fill(phone);
  await page.getByLabel(/Special Requests/).fill('Task 12 browser journey');
  await page.getByRole('button', { name: 'Confirm Booking' }).click();
  await expect(page.getByRole('heading', { name: 'Booking confirmed' })).toBeVisible();
  const code = (await page.locator('body').innerText()).match(/BK\d{8}\d{4}/)?.[0];
  expect(code).toBeTruthy();

  await page.goto(`${frontend}/my-bookings`);
  await page.getByPlaceholder('0123456789').fill(phone);
  const start = readFileSync(logPath, 'utf8').length;
  await page.getByRole('button', { name: 'Get code' }).click();
  await expect(page.getByText('For local development, find the code')).toBeVisible();
  let verificationCode: string | undefined;
  for (let i = 0; i < 30 && !verificationCode; i++) {
    verificationCode = readFileSync(logPath, 'utf8').slice(start)
      .match(new RegExp(`Booking access code for ${phone}: (\\d{6})`))?.[1];
    if (!verificationCode) await page.waitForTimeout(100);
  }
  expect(verificationCode).toMatch(/^\d{6}$/);
  await page.locator('input[inputmode="numeric"]').fill(verificationCode!);
  await page.getByRole('button', { name: 'Verify and search' }).click();
  await expect(page.getByRole('heading', { name: `Booking #${code}` })).toBeVisible();
  await page.getByRole('button', { name: 'Edit booking' }).click();
  await expect(page.getByRole('heading', { name: code })).toBeVisible();
  await page.getByLabel('Start time').fill('14:30');
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByRole('status')).toContainText('Booking updated');
  await page.getByRole('button', { name: 'Cancel booking' }).click();
  await expect(page.getByRole('status')).toContainText('Booking cancelled');
  await expect(page.getByRole('button', { name: 'Edit booking' })).toHaveCount(0);

  const login = await request.post(`${api}/auth/login`, {
    data: { username: 'admin', password: 'admin123' },
  });
  expect(login.ok()).toBeTruthy();
  const token = (await login.json()).data.access_token;
  const saved = await request.get(`${api}/admin/bookings`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(saved.ok()).toBeTruthy();
  expect((await saved.json()).data).toEqual(expect.arrayContaining([
    expect.objectContaining({ bookingCode: code, startTime: '14:30', status: 'Cancelled', numberOfPeople: 2 }),
  ]));
});

test('admin and assigned therapist manage a booking through their pages', async ({ page, request }) => {
  await page.route(/https?:\/\/(?:localhost|127\.0\.0\.1):5000\/api\//, async route => {
    const target = route.request().url().replace(/https?:\/\/(?:localhost|127\.0\.0\.1):5000\/api/, api);
    const response = await route.fetch({ url: target });
    await route.fulfill({ response });
  });
  const catalog = await request.get(`${api}/shops/1/courses`);
  const main = (await catalog.json()).data.find((entry: { courseType: string }) => entry.courseType === 'main');
  const bookingDate = new Date(Date.now() + 4 * 86400000).toISOString().slice(0, 10);
  const createdResponse = await request.post(`${api}/bookings`, { data: {
    phoneNumber: `090${String(Date.now()).slice(-7)}`, shopId: 1,
    bookingDate, startTime: '16:30', duration: 60, numberOfPeople: 1,
    courseId: main.courseId, therapistPreferenceType: 'specific', therapistPreferenceValue: 1,
  } });
  expect(createdResponse.status()).toBe(201);
  const created = (await createdResponse.json()).data;

  await page.goto(`${frontend}/login`);
  await page.getByPlaceholder('Enter username').fill('admin');
  await page.getByPlaceholder('Enter password').fill('admin123');
  await page.getByRole('button', { name: 'Login' }).click();
  await page.waitForURL('**/admin');
  await page.goto(`${frontend}/admin/bookings`);
  await page.getByRole('button', { name: 'All dates' }).click();
  await page.getByPlaceholder('Find by phone or code').fill(created.bookingCode);
  const card = page.locator('article').filter({ hasText: created.bookingCode });
  await expect(card).toBeVisible();
  await card.getByRole('button', { name: 'Check in' }).click();
  await expect(card.getByText('In session')).toBeVisible();
  const adminToken = await page.evaluate(() => localStorage.getItem('access_token'));

  await page.evaluate(() => localStorage.clear());
  await page.goto(`${frontend}/login`);
  await page.getByPlaceholder('Enter username').fill('tanaka');
  await page.getByPlaceholder('Enter password').fill('tanaka123');
  await page.getByRole('button', { name: 'Login' }).click();
  await page.waitForURL('**/therapist');
  await page.goto(`${frontend}/therapist/bookings`);
  const therapistCard = page.getByText(`#${created.bookingCode}`, { exact: true }).locator('xpath=../..');
  await expect(therapistCard).toBeVisible();
  await therapistCard.getByRole('button', { name: 'Complete' }).click();
  await expect(therapistCard.getByText('CheckedOut')).toBeVisible();
  await page.goto(`${frontend}/admin/schedules`);
  await expect(page.getByRole('heading', { name: '403 Forbidden' })).toBeVisible();

  const saved = await request.get(`${api}/bookings/${created.bookingId}`, {
    headers: { Authorization: `Bearer ${adminToken}` },
  });
  expect(saved.status()).toBe(200);
  expect((await saved.json()).data.status).toBe('CheckedOut');
});
