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
  }
};
