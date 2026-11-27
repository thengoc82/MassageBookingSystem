import { expect, test } from '@playwright/test';

test('slot context preserves main and add-on options in one booking request', async ({ page }) => {
  const base = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
  const payloads: unknown[] = [];
  await page.route('**/api/shops/7', route => route.fulfill({ json: { data: { shopId: 7, shopName: 'Shinjuku Store', status: 'Open' } } }));
  await page.route('**/api/shops/7/courses', route => route.fulfill({ json: { data: [
    { courseId: 11, courseName: 'Full Body Massage', courseType: 'main', durations: [{ duration: 30, price: 3000 }] },
    { courseId: 12, courseName: 'Head Extra', courseType: 'addon', durations: [{ duration: 15, price: 1000 }] },
  ] } }));
  await page.route('**/api/shops/7/available-slots?**', route => route.fulfill({ json: { data: [
    { startTime: '10:00', endTime: '10:45', availableCapacity: 2 },
  ] } }));
  await page.route('**/api/bookings', async route => {
    payloads.push(route.request().postDataJSON());
    await route.fulfill({ status: 201, json: { data: { bookingCode: 'BK123' } } });
  });

  await page.goto(`${base}/reservation?shopId=7&date=2026-12-10&time=10%3A00&duration=45&people=2`);
  await expect(page.getByRole('heading', { name: 'Booking Summary', exact: true })).toBeVisible();
  await expect(page.getByText('Shinjuku Store')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Select Courses' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Customer Information' })).toBeVisible();
  const confirm = page.getByRole('button', { name: 'Confirm Booking' });
  await expect(confirm).toBeDisabled();
  await page.getByRole('button', { name: 'Full Body Massage, 30 minutes, 3,000 VND' }).click();
  await page.getByRole('button', { name: 'Head Extra, 15 minutes, 1,000 VND' }).click();
  await page.getByLabel('Phone Number *').fill('0901234567');
  await expect(confirm).toBeEnabled();
  await confirm.click();
  await expect(page.getByText('BK123')).toBeVisible();
  expect(payloads).toHaveLength(1);
  expect(payloads[0]).toEqual(expect.objectContaining({
    duration: 45,
    numberOfPeople: 2,
    services: [{ personIndex: 1, courseId: 11 }, { personIndex: 2, courseId: 11 }],
    addOns: [{ personIndex: 1, courseId: 12 }, { personIndex: 2, courseId: 12 }],
    selectedCourses: [{ courseId: 11, duration: 30, price: 3000 }, { courseId: 12, duration: 15, price: 1000 }],
  }));
});

test('recovers from a POST slot loss while keeping courses and contact details', async ({ page }) => {
  const base = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
  const payloads: Record<string, unknown>[] = [];
  await page.route('**/api/shops/7', route => route.fulfill({ json: { data: { shopId: 7, shopName: 'Shinjuku Store', status: 'Open' } } }));
  await page.route('**/api/shops/7/courses', route => route.fulfill({ json: { data: [
    { courseId: 11, courseName: 'Full Body Massage', courseType: 'main', durations: [{ duration: 30, price: 3000 }] },
    { courseId: 12, courseName: 'Head Extra', courseType: 'addon', durations: [{ duration: 15, price: 1000 }] },
  ] } }));
  await page.route('**/api/shops/7/available-slots?**', route => route.fulfill({ json: { data: [
    { startTime: '10:00', endTime: '10:45', availableCapacity: 2 },
    { startTime: '10:30', endTime: '11:15', availableCapacity: 2 },
  ] } }));
  await page.route('**/api/bookings', async route => {
    payloads.push(route.request().postDataJSON());
    if (payloads.length === 1) {
      await route.fulfill({ status: 422, json: { success: false, error: { code: 'INSUFFICIENT_THERAPISTS', message: 'Taken' } } });
    } else {
      await route.fulfill({ status: 201, json: { data: { bookingCode: 'BK456' } } });
    }
  });

  await page.goto(`${base}/reservation?shopId=7&date=2026-12-10&time=10%3A00&duration=45&people=2`);
  await page.getByRole('button', { name: 'Full Body Massage, 30 minutes, 3,000 VND' }).click();
  await page.getByRole('button', { name: 'Head Extra, 15 minutes, 1,000 VND' }).click();
  await page.getByLabel('Phone Number *').fill('0901234567');
  await page.getByLabel(/Special Requests/).fill('Quiet room');
  await page.getByRole('button', { name: 'Confirm Booking' }).click();
  await page.getByRole('button', { name: '10:30–11:15' }).click();
  await expect(page.getByLabel('Phone Number *')).toHaveValue('0901234567');
  await expect(page.getByLabel(/Special Requests/)).toHaveValue('Quiet room');
  await page.getByRole('button', { name: 'Confirm Booking' }).click();
  await expect(page.getByText('BK456')).toBeVisible();
  expect(payloads.map(payload => payload.startTime)).toEqual(['10:00', '10:30']);
  expect(payloads[1]).toEqual(expect.objectContaining({
    numberOfPeople: 2, notes: 'Quiet room',
    services: [{ personIndex: 1, courseId: 11 }, { personIndex: 2, courseId: 11 }],
    addOns: [{ personIndex: 1, courseId: 12 }, { personIndex: 2, courseId: 12 }],
  }));
});
