const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api';

async function handleResponse(r: Response) {
  const data = await r.json();
  if (!r.ok) {
    const errBody = data.error || {};
    const msg = typeof errBody === 'string' ? errBody : errBody.message || 'Request failed';
    const err: any = new Error(msg);
    err.status = r.status;
    err.code = errBody.code || errBody.message || msg;
    err.data = data;
    throw err;
  }
  return data;
}

function authHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function authFetch(url: string, options: RequestInit = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...authHeaders(),
    ...(options.headers || {}),
  };
  const response = await fetch(url, { ...options, headers });
  return handleResponse(response);
}

export async function login(data: any) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const result = await handleResponse(response);
  return result;
}

export const api = {
  shops: {
    getAll: () => fetch(`${API_BASE_URL}/shops`).then(handleResponse),
    getById: (id: number) => fetch(`${API_BASE_URL}/shops/${id}`).then(handleResponse),
    getCourses: (shopId: number, type?: string) => {
      const params = type ? `?type=${type}` : '';
      return fetch(`${API_BASE_URL}/shops/${shopId}/courses${params}`).then(handleResponse);
    },
    getAvailableSlots: (shopId: number, params: any) => {
      const queryString = new URLSearchParams(params).toString();
      return fetch(`${API_BASE_URL}/shops/${shopId}/available-slots?${queryString}`).then(handleResponse);
    },
    getAvailableTherapists: (shopId: number, params: any) => {
      const queryString = new URLSearchParams(params).toString();
      return fetch(`${API_BASE_URL}/shops/${shopId}/available-therapists?${queryString}`).then(handleResponse);
    }
  },

  bookings: {
    create: (data: any) => fetch(`${API_BASE_URL}/bookings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(handleResponse),

    getAll: (params?: any) => {
      const queryString = params ? new URLSearchParams(params).toString() : '';
      return fetch(`${API_BASE_URL}/bookings?${queryString}`).then(handleResponse);
    },

    getById: (id: number) => fetch(`${API_BASE_URL}/bookings/${id}`).then(handleResponse),

    update: (id: number, data: any) => fetch(`${API_BASE_URL}/bookings/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(handleResponse),

    cancel: (id: number) => fetch(`${API_BASE_URL}/bookings/${id}/cancel`, {
      method: 'PATCH'
    }).then(handleResponse),

    checkEligibility: (phoneNumber: string) => fetch(`${API_BASE_URL}/booking-eligibility-checks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phoneNumber })
    }).then(handleResponse)
  },

  auth: {
    login: (username: string, password: string) => fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    }).then(handleResponse)
  },

  admin: {
    getBookings: (params?: any) => {
      const queryString = params ? new URLSearchParams(params).toString() : '';
      return authFetch(`${API_BASE_URL}/admin/bookings?${queryString}`);
    },
    cancelBooking: (id: number) => authFetch(`${API_BASE_URL}/admin/bookings/${id}/cancel`, { method: 'PATCH' }),
    checkinBooking: (id: number) => authFetch(`${API_BASE_URL}/admin/bookings/${id}/checkin`, { method: 'PATCH' }),
    checkoutBooking: (id: number) => authFetch(`${API_BASE_URL}/admin/bookings/${id}/checkout`, { method: 'PATCH' }),

    getShops: (params?: any) => {
      const queryString = params ? new URLSearchParams(params).toString() : '';
      return authFetch(`${API_BASE_URL}/admin/shops?${queryString}`);
    },
    getShop: (id: number) => authFetch(`${API_BASE_URL}/admin/shops/${id}`),
    createShop: (data: any) => authFetch(`${API_BASE_URL}/admin/shops`, { method: 'POST', body: JSON.stringify(data) }),
    updateShop: (id: number, data: any) => authFetch(`${API_BASE_URL}/admin/shops/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

    getTherapists: (shopId: number, params?: any) => {
      const queryString = params ? new URLSearchParams(params).toString() : '';
      return authFetch(`${API_BASE_URL}/admin/shops/${shopId}/therapists?${queryString}`);
    },
    createTherapist: (shopId: number, data: any) => authFetch(`${API_BASE_URL}/admin/shops/${shopId}/therapists`, { method: 'POST', body: JSON.stringify(data) }),
    getTherapistSchedule: (therapistId: number, dateFrom: string, dateTo: string) =>
      authFetch(`${API_BASE_URL}/admin/therapists/${therapistId}/schedule?dateFrom=${dateFrom}&dateTo=${dateTo}`),

    getCourses: (shopId: number, params?: any) => {
      const queryString = params ? new URLSearchParams(params).toString() : '';
      return authFetch(`${API_BASE_URL}/admin/shops/${shopId}/courses?${queryString}`);
    },
    createCourse: (shopId: number, data: any) => authFetch(`${API_BASE_URL}/admin/shops/${shopId}/courses`, { method: 'POST', body: JSON.stringify(data) }),
    updateCourse: (shopId: number, courseId: number, data: any) => authFetch(`${API_BASE_URL}/admin/shops/${shopId}/courses/${courseId}`, { method: 'PATCH', body: JSON.stringify(data) }),
    deleteCourse: (shopId: number, courseId: number) => authFetch(`${API_BASE_URL}/admin/shops/${shopId}/courses/${courseId}`, { method: 'DELETE' }),

    getCustomers: (params?: any) => {
      const queryString = params ? new URLSearchParams(params).toString() : '';
      return authFetch(`${API_BASE_URL}/admin/customers?${queryString}`);
    },
    getCustomer: (id: number) => authFetch(`${API_BASE_URL}/admin/customers/${id}`)
  },

  therapist: {
    getProfile: () => authFetch(`${API_BASE_URL}/therapists/me/profile`),
    updateProfile: (data: any) => authFetch(`${API_BASE_URL}/therapists/me/profile`, { method: 'PATCH', body: JSON.stringify(data) }),
    getSchedule: (dateFrom: string, dateTo: string) =>
      authFetch(`${API_BASE_URL}/therapists/me/schedule?dateFrom=${dateFrom}&dateTo=${dateTo}`),
    getBookings: (params?: any) => {
      const queryString = params ? new URLSearchParams(params).toString() : '';
      return authFetch(`${API_BASE_URL}/therapists/bookings?${queryString}`);
    },
    checkinBooking: (id: number) => authFetch(`${API_BASE_URL}/therapists/bookings/${id}/checkin`, { method: 'PATCH' }),
    checkoutBooking: (id: number) => authFetch(`${API_BASE_URL}/therapists/bookings/${id}/checkout`, { method: 'PATCH' })
  }
};
