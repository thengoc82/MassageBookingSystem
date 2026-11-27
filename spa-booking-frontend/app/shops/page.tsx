'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { bookableCourses, bookableOptions } from '@/lib/course-options';
import type { Course, Shop } from '@/types';

export default function ShopsPage() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [coursesByShop, setCoursesByShop] = useState<Record<number, Course[]>>({});
  const [courseErrors, setCourseErrors] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadShops();
  }, []);

  const loadShops = async () => {
    try {
      const response = await api.shops.getAll();
      if (response.success) {
        const openShops = response.data as Shop[];
        setShops(openShops);
        const results = await Promise.allSettled(openShops.map(shop => api.shops.getCourses(shop.shopId)));
        const catalog: Record<number, Course[]> = {};
        const errors: number[] = [];
        results.forEach((result, index) => {
          const id = openShops[index].shopId;
          if (result.status === 'fulfilled') catalog[id] = bookableCourses(result.value.data || result.value);
          else errors.push(id);
        });
        setCoursesByShop(catalog);
        setCourseErrors(errors);
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
              <div className="mt-5 border-t pt-4">
                <h3 className="font-semibold">Services and add-ons</h3>
                {courseErrors.includes(shop.shopId) && <p role="alert" className="mt-2 text-sm text-red-700">Services could not be loaded.</p>}
                {!courseErrors.includes(shop.shopId) && (coursesByShop[shop.shopId] || []).length === 0 && <p className="mt-2 text-sm">No bookable services are available.</p>}
                {(['main', 'addon'] as const).map(type => {
                  const entries = (coursesByShop[shop.shopId] || []).filter(course => course.courseType === type);
                  return entries.length ? <div key={type} className="mt-3">
                    <h4 className="text-sm font-medium">{type === 'main' ? 'Main courses' : 'Optional add-ons'}</h4>
                    <ul className="mt-1 space-y-1 text-sm">{entries.map(course => <li key={course.courseId}>
                      <span className="font-medium">{course.courseName}</span>: {bookableOptions(course).map(option => `${option.duration} min · ${option.price.toLocaleString('en-US')} VND`).join(', ')}
                    </li>)}</ul>
                  </div> : null;
                })}
                <p className="mt-3 text-xs">Time availability is checked after you choose a date and duration.</p>
              </div>
              {(coursesByShop[shop.shopId] || []).some(course => course.courseType === 'main') && <a
                href={`/dashboard?shopId=${shop.shopId}`}
                className="mt-4 block text-center bg-celadon text-white py-2 rounded-lg hover:bg-celadon-deep"
              >
                Choose a time
              </a>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
