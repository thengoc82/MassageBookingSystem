import { api } from './api';

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem('access_token', 'admin-token');
  global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ success: true, data: [] }) });
});

test('customer restriction requests use admin authentication and private routes', async () => {
  await api.admin.getCustomerRestrictions({ phone: '0987', status: 'inactive', page: 2, size: 10 });
  await api.admin.getCustomerRestriction(7);
  await api.admin.createCustomerRestriction({ phoneNumber: '0987654321', reason: 'No show' });
  await api.admin.updateCustomerRestriction(7, { reason: 'Repeated no show' });
  await api.admin.deleteCustomerRestriction(7);

  const headers = { 'Content-Type': 'application/json', Authorization: 'Bearer admin-token' };
  expect(global.fetch).toHaveBeenNthCalledWith(1,
    expect.stringContaining('/admin/customer-restrictions?phone=0987&status=inactive&page=2&size=10'),
    { headers });
  expect(global.fetch).toHaveBeenNthCalledWith(2, expect.stringContaining('/admin/customer-restrictions/7'), { headers });
  expect(global.fetch).toHaveBeenNthCalledWith(3, expect.stringContaining('/admin/customer-restrictions'),
    { method: 'POST', body: JSON.stringify({ phoneNumber: '0987654321', reason: 'No show' }), headers });
  expect(global.fetch).toHaveBeenNthCalledWith(4, expect.stringContaining('/admin/customer-restrictions/7'),
    { method: 'PATCH', body: JSON.stringify({ reason: 'Repeated no show' }), headers });
  expect(global.fetch).toHaveBeenNthCalledWith(5, expect.stringContaining('/admin/customer-restrictions/7'),
    { method: 'DELETE', headers });
});
