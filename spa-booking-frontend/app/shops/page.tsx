'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import type { Shop } from '@/types';

export default function ShopsPage() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadShops();
  }, []);

  const loadShops = async () => {
    try {
      const response = await api.shops.getAll();
      if (response.success) {
        setShops(response.data);
      }
    } catch (error) {
      console.error('Failed to load shops:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="container mx-auto px-4">
          <div className="text-center">Loading shops...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        <h1 className="text-4xl font-bold mb-8">Our Locations</h1>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {shops.map((shop) => (
            <div key={shop.shopId} className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-semibold mb-3">{shop.shopName}</h2>
              <div className="space-y-2 text-gray-600">
                <div className="flex items-start">
                  <span className="mr-2">📍</span>
                  <span>{shop.address}</span>
                </div>
                <div className="flex items-center">
                  <span className="mr-2">📞</span>
                  <span>{shop.phoneNumber}</span>
                </div>
                <div className="flex items-center">
                  <span className="mr-2">🕐</span>
                  <span>{shop.openTime} - {shop.closeTime}</span>
                </div>
                <div className="mt-4">
                  <span className={`inline-block px-3 py-1 rounded-full text-sm ${
                    shop.status === 'Open' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {shop.status}
                  </span>
                </div>
              </div>
              <a
                href="/booking"
                className="mt-4 block text-center bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700"
              >
                Book Now
              </a>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
