import { api, clearCustomerBookingAccess, saveCustomerBookingAccess } from './api';

const response = { ok: true, json: async () => ({ success: true, data: {} }) };

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  global.fetch = jest.fn().mockResolvedValue(response);
});

test('customer lookup, edit, and cancellation send only the phone-scoped token', async () => {
  localStorage.setItem('access_token', 'staff-token');
  saveCustomerBookingAccess('0901234567', 'customer-token');

  await api.bookings.getAll({ phone: '0901234567' });
  await api.bookings.update(42, { startTime: '11:00' }, true);
  await api.bookings.cancel(42);

  expect(global.fetch).toHaveBeenNthCalledWith(1,
    expect.stringContaining('/bookings?phone=0901234567'),
    { headers: { Authorization: 'Bearer customer-token' } },
  );
  expect(global.fetch).toHaveBeenNthCalledWith(2,
    expect.stringContaining('/bookings/42'),
    { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer customer-token' }, body: JSON.stringify({ startTime: '11:00' }) },
  );
  expect(global.fetch).toHaveBeenNthCalledWith(3,
    expect.stringContaining('/bookings/42/cancel'),
    { method: 'PATCH', headers: { Authorization: 'Bearer customer-token' } },
  );
});

test('staff detail uses staff token and clearing customer token removes its access', async () => {
  localStorage.setItem('access_token', 'staff-token');
  saveCustomerBookingAccess('0901234567', 'customer-token');
  await api.bookings.getById(42);
  expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/bookings/42'),
    { headers: { Authorization: 'Bearer staff-token' } });

  await api.bookings.getById(42, true);
  expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining('/bookings/42'),
    { headers: { Authorization: 'Bearer customer-token' } });

  clearCustomerBookingAccess();
  await api.bookings.getAll({ phone: '0901234567' });
  expect(global.fetch).toHaveBeenLastCalledWith(expect.stringContaining('/bookings?phone=0901234567'),
    { headers: {} });
});
