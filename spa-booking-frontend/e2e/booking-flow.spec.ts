import { expect, test } from '@playwright/test';

test('slot context leads to one-page course selection and one booking request', async ({ page }) => {
  const base = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
  const payloads: unknown[] = [];
  await page.route('**/api/shops/7', route => route.fulfill({ json: { data: { shopId: 7, shopName: 'Shinjuku Store' } } }));
  await page.route('**/api/shops/7/courses', route => route.fulfill({ json: { data: [
    { courseId: 11, courseName: 'Full Body Massage', courseType: 'main', durations: [{ duration: 30, price: 3000 }] },
    { courseId: 12, courseName: 'Dry Head Spa', courseType: 'main', durations: [{ duration: 30, price: 3000 }] },
    { courseId: 13, courseName: 'Aromatherapy', courseType: 'main', durations: [{ duration: 15, price: 3500 }] },
  ] } }));
  await page.route('**/api/shops/7/available-slots?**', route => route.fulfill({ json: { data: [
    { startTime: '10:00', endTime: '11:00', availableCapacity: 1 },
  ] } }));
  await page.route('**/api/bookings', async route => {
    payloads.push(route.request().postDataJSON());
    await route.fulfill({ status: 201, json: { data: { bookingCode: 'BK123' } } });
  });

  await page.goto(`${base}/reservation?shopId=7&date=2026-12-10&time=10%3A00&duration=60&people=1`);
  await expect(page.getByRole('heading', { name: 'Booking Summary', exact: true })).toBeVisible();
  await expect(page.getByText('Shinjuku Store')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Select Courses' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Customer Information' })).toBeVisible();
  const confirm = page.getByRole('button', { name: 'Confirm Booking' });
  await expect(confirm).toBeDisabled();
  await page.getByRole('button', { name: 'Full Body Massage, 30 minutes, 3,000 VND' }).click();
  await page.getByRole('button', { name: 'Dry Head Spa, 30 minutes, 3,000 VND' }).click();
  await page.getByLabel('Phone Number *').fill('0901234567');
  await expect(confirm).toBeEnabled();
  await confirm.click();
  await expect(page.getByText('BK123')).toBeVisible();
  expect(payloads).toHaveLength(1);
  expect(payloads[0]).toEqual(expect.objectContaining({
    duration: 60,
    services: [{ personIndex: 1, courseId: 11 }, { personIndex: 1, courseId: 12 }],
  }));
});
