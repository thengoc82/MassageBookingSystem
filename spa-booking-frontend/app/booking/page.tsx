'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import type { Course, TimeSlot, BookingFormData } from '@/types';

function formatPrice(price: number): string {
  return price.toLocaleString() + ' VND';
}

const STEPS = [
  { num: 1, label: 'Date & Time' },
  { num: 2, label: 'Your Info' },
  { num: 3, label: 'Services' },
  { num: 4, label: 'Preferences' },
  { num: 5, label: 'Review' },
];

const bodyParts = [
  'Neck', 'Shoulders', 'Back', 'Lower Back', 'Arms', 'Legs', 'Feet'
];

export default function BookingConfirmPage() {
  const router = useRouter();
  const [bookingData, setBookingData] = useState<BookingFormData | null>(null);
  const [shopName, setShopName] = useState('');
  const [courseName, setCourseName] = useState('');
  const [coursePrice, setCoursePrice] = useState(0);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bookingCode, setBookingCode] = useState('');
  const [assignedTherapistName, setAssignedTherapistName] = useState('');
  const [showAlternatives, setShowAlternatives] = useState(false);
  const [alternativeSlots, setAlternativeSlots] = useState<TimeSlot[]>([]);
  const [shopOpenTime, setShopOpenTime] = useState('09:00');
  const [shopCloseTime, setShopCloseTime] = useState('21:00');

  const [currentStep, setCurrentStep] = useState(0);

  const [guestPhone, setGuestPhone] = useState('');
  const [customerFound, setCustomerFound] = useState<'pending' | 'found' | 'new'>('pending');
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerDOB, setCustomerDOB] = useState('');
  const [customerGender, setCustomerGender] = useState('');

  const [bodyMassageDuration, setBodyMassageDuration] = useState(0);
  const [selectedAddons, setSelectedAddons] = useState<string[]>([]);
  const [optionalExtras, setOptionalExtras] = useState<string[]>([]);

  const [therapistPref, setTherapistPref] = useState('no_preference');
  const [massageStrength, setMassageStrength] = useState('normal');
  const [chatPref, setChatPref] = useState('');
  const [focusAreas, setFocusAreas] = useState<string[]>([]);
  const [avoidAreas, setAvoidAreas] = useState<string[]>([]);
  const [notes, setNotes] = useState('');

  const bodyMassageOptions = [30, 45, 60, 90, 120];
  const addonOptions = ['Foot Reflexology', 'Dry Head Spa', 'Hand Reflexology', 'Neck Care', 'Calf Care'];
  const extraOptions = [
    'Premium Mattress', 'Cooling Mattress', 'Premium Face Pillow',
    'Recovery Wear', 'Back Care Course'
  ];

  const toggleAddon = (item: string) =>
    setSelectedAddons(prev => prev.includes(item) ? prev.filter(s => s !== item) : [...prev, item]);

  const toggleExtra = (item: string) =>
    setOptionalExtras(prev => prev.includes(item) ? prev.filter(s => s !== item) : [...prev, item]);

  const toggleFocus = (area: string) =>
    setFocusAreas(prev => prev.includes(area) ? prev.filter(s => s !== area) : [...prev, area]);

  const toggleAvoid = (area: string) =>
    setAvoidAreas(prev => prev.includes(area) ? prev.filter(s => s !== area) : [...prev, area]);

  const addonMinutes = selectedAddons.reduce((sum, name) => {
    if (name === 'Foot Reflexology' || name === 'Dry Head Spa' || name === 'Hand Reflexology') return sum + 30;
    if (name === 'Neck Care' || name === 'Calf Care') return sum + 15;
    return sum;
  }, 0);

  const totalMinutes = bodyMassageDuration + addonMinutes;

  const loadDetails = async (data: BookingFormData) => {
    try {
      const [shopRes, courseRes] = await Promise.all([
        api.shops.getById(data.shopId),
        api.shops.getCourses(data.shopId, 'main')
      ]);
      const shop: { shopName?: string; openTime?: string; closeTime?: string } = shopRes?.data || shopRes;
      setShopName(shop?.shopName || '');
      if (shop?.openTime) setShopOpenTime(shop.openTime);
      if (shop?.closeTime) setShopCloseTime(shop.closeTime);

      const courses: Course[] = Array.isArray(courseRes) ? courseRes : courseRes?.data || [];
      const course = courses.find(c => c.courseId === data.courseId);
      if (course) {
        setCourseName(course.courseName);
        setCoursePrice(course.price);
      }
    } catch {}
  };

  useEffect(() => {
    const stored = localStorage.getItem('pending_booking');
    if (!stored) {
      router.push('/');
      return;
    }
    try {
      const data: BookingFormData = JSON.parse(stored);
      setBookingData(data);
      loadDetails(data);
    } catch {
      localStorage.removeItem('pending_booking');
      router.push('/');
    }
  }, []);

  const refreshSlots = async () => {
    if (!bookingData) return;
    try {
      const data = await api.shops.getAvailableSlots(bookingData.shopId, {
        date: bookingData.bookingDate,
        duration: bookingData.duration,
        numberOfPeople: bookingData.numberOfPeople
      });
      const slotList: TimeSlot[] = Array.isArray(data) ? data : data.data || [];
      setAlternativeSlots(slotList);
      setShowAlternatives(true);
    } catch {
      setAlternativeSlots([]);
      setShowAlternatives(true);
    }
  };

  const handleReselectSlot = (startTime: string) => {
    if (!bookingData) return;
    const startMinutes = parseInt(startTime.split(':')[0]) * 60 + parseInt(startTime.split(':')[1]);
    const endMinutes = startMinutes + bookingData.duration;
    const endHour = Math.floor(endMinutes / 60);
    const endMin = endMinutes % 60;
    const endTime = `${String(endHour).padStart(2, '0')}:${String(endMin).padStart(2, '0')}`;

    const updated: BookingFormData = {
      ...bookingData,
      startTime,
      endTime,
      services: Array.from({ length: bookingData.numberOfPeople }, (_, i) => ({
        personIndex: i + 1,
        courseId: bookingData.courseId
      })),
    };

    localStorage.setItem('pending_booking', JSON.stringify(updated));
    setBookingData(updated);
    setShowAlternatives(false);
    setAlternativeSlots([]);
    setError(null);
    loadDetails(updated);
  };

  const findNearestSlots = (slots: TimeSlot[], originalStart: string): TimeSlot[] => {
    const origMinutes = parseInt(originalStart.split(':')[0]) * 60 + parseInt(originalStart.split(':')[1]);
    const sorted = [...slots].sort((a, b) => {
      const aMin = parseInt(a.startTime.split(':')[0]) * 60 + parseInt(a.startTime.split(':')[1]);
      const bMin = parseInt(b.startTime.split(':')[0]) * 60 + parseInt(b.startTime.split(':')[1]);
      return Math.abs(aMin - origMinutes) - Math.abs(bMin - origMinutes);
    });
    return sorted.slice(0, 5);
  };

  const handleFindCustomer = async () => {
    if (!guestPhone) return;
    try {
      await api.bookings.checkEligibility(guestPhone);
      setCustomerFound('found');
    } catch {
      setCustomerFound('new');
    }
  };

  const handleConfirm = async () => {
    if (!bookingData || !guestPhone) return;
    setIsConfirming(true);
    setError(null);
    setShowAlternatives(false);

    try {
      const payload: Record<string, unknown> = {
        phoneNumber: guestPhone,
        shopId: bookingData.shopId,
        bookingDate: bookingData.bookingDate,
        startTime: bookingData.startTime,
        duration: totalMinutes || bookingData.duration,
        numberOfPeople: bookingData.numberOfPeople,
        courseId: bookingData.courseId,
        services: bookingData.services,
        addOns: bookingData.addOns || [],
        customerName,
        customerEmail: customerEmail || undefined,
        bodyMassageDuration,
        selectedAddons,
        optionalExtras,
        massageStrength,
        chatPref,
        focusAreas,
        avoidAreas,
        notes: notes || undefined,
      };

      if (therapistPref !== 'no_preference') {
        payload.therapistPreferenceType = therapistPref;
        payload.therapistPreferenceValue = therapistPref === 'specific' ? 'specific' : therapistPref;
      }

      const result = await api.bookings.create(payload) as { data?: { bookingCode?: string; therapistName?: string }; bookingCode?: string; therapistName?: string };
      const code = result.data?.bookingCode || result.bookingCode || '';
      const therapistName = result.data?.therapistName || result.therapistName || '';

      setBookingCode(code);
      if (therapistName) setAssignedTherapistName(therapistName);
      localStorage.removeItem('pending_booking');
    } catch (err: any) {
      if (err.code === 'SLOT_UNAVAILABLE' || err.code === 'INSUFFICIENT_THERAPISTS') {
        setError('This time slot is no longer available. Checking nearby slots...');
        await refreshSlots();
      } else if (err.code === 'CUSTOMER_BLOCKED') {
        setError('Your account has a restriction. Please contact support.');
        localStorage.removeItem('pending_booking');
      } else {
        setError(err.message || 'Booking failed. Please try again.');
      }
    } finally {
      setIsConfirming(false);
    }
  };

  if (!bookingData) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-white/60">Loading...</div>
      </div>
    );
  }

  if (bookingCode) {
    return (
      <div className="min-h-screen bg-[#031050] py-8">
        <div className="container mx-auto px-4 max-w-2xl">
          <div className="bg-white rounded-xl shadow-lg p-8 text-center">
            <div className="text-6xl mb-4 text-green-500">✓</div>
            <h2 className="text-2xl font-semibold mb-2 text-black">Booking Confirmed!</h2>

            <div className="bg-gray-900 text-white p-6 rounded-lg mb-6">
              <div className="text-sm text-gray-400 mb-1">Booking Code</div>
              <div className="text-2xl font-mono font-bold tracking-wider">{bookingCode}</div>
            </div>

            <div className="border rounded-lg p-4 mb-6 space-y-2 text-left text-sm">
              <div className="flex justify-between"><span className="text-black">Shop</span><span className="font-medium text-black">{shopName}</span></div>
              <div className="flex justify-between"><span className="text-black">Date</span><span className="font-medium text-black">{bookingData.bookingDate}</span></div>
              <div className="flex justify-between"><span className="text-black">Time</span><span className="font-medium text-black">{bookingData.startTime}</span></div>
              <div className="flex justify-between"><span className="text-black">Duration</span><span className="font-medium text-black">{totalMinutes || bookingData.duration} min</span></div>
              <div className="flex justify-between"><span className="text-black">Course</span><span className="font-medium text-black">{courseName}</span></div>
              <div className="flex justify-between"><span className="text-black">Price</span><span className="font-medium text-black">{formatPrice(coursePrice)}</span></div>
              {assignedTherapistName && (
                <div className="flex justify-between"><span className="text-black">Therapist</span><span className="font-medium text-black">{assignedTherapistName}</span></div>
              )}
            </div>

            <div className="bg-yellow-50 border border-yellow-200 p-3 rounded-lg mb-6 text-sm text-yellow-800">
              Please arrive <strong>10 minutes</strong> before your appointment.
            </div>

            <div className="flex gap-3">
              <button onClick={() => router.push('/')}
                className="flex-1 px-4 py-3 border-2 rounded-lg hover:bg-gray-50 text-sm font-medium text-black">
                Book Another
              </button>
              <button onClick={() => router.push('/my-bookings')}
                className="flex-1 bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 text-sm font-medium">
                My Bookings
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (showAlternatives) {
    const nearest = findNearestSlots(alternativeSlots, bookingData.startTime);
    return (
      <div className="min-h-screen bg-white py-8">
        <div className="container mx-auto px-4 max-w-2xl">
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="text-center mb-6">
              <div className="text-4xl mb-2">⏰</div>
              <h2 className="text-xl font-semibold mb-2 text-black">Slot No Longer Available</h2>
              <p className="text-black text-sm">Here are nearby available slots:</p>
            </div>

            {nearest.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-black mb-4">No nearby slots available.</p>
                <button onClick={() => { localStorage.removeItem('pending_booking'); router.push('/'); }}
                  className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700">
                  Try a Different Date
                </button>
              </div>
            ) : (
              <>
                <div className="space-y-2 mb-6">
                  {nearest.map(slot => (
                    <button key={slot.startTime}
                      onClick={() => handleReselectSlot(slot.startTime)}
                      className="w-full flex items-center justify-between p-4 border rounded-lg hover:bg-blue-50 transition text-left">
                      <div>
                        <span className="font-mono font-semibold text-lg text-black">{slot.startTime}</span>
                        <span className="text-black mx-2">-</span>
                        <span className="font-mono text-black">{slot.endTime}</span>
                      </div>
                      <span className="text-sm text-green-600">{slot.availableCapacity} available</span>
                    </button>
                  ))}
                </div>
                <button onClick={() => { localStorage.removeItem('pending_booking'); router.push('/'); }}
                  className="w-full text-sm text-black underline hover:text-gray-700 py-2">
                  Try a different date
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  const bookingDate = bookingData.bookingDate
    ? new Date(bookingData.bookingDate + 'T00:00:00').toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
      })
    : 'Wednesday, July 15, 2026';

  const formatTime = (t: string) => {
    const [h, m] = t.split(':').map(Number);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const hour = h % 12 || 12;
    return `${hour}:${String(m).padStart(2, '0')} ${ampm}`;
  };

  const renderProgress = () => (
    <div className="flex items-center justify-center gap-0 mb-8">
      {STEPS.map((s, i) => (
        <div key={s.num} className="flex items-center">
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition ${
              i === currentStep
                ? 'bg-white text-[#031050]'
                : i < currentStep
                  ? 'bg-green-400 text-white'
                  : 'bg-white/20 text-white/60'
            }`}>
              {i < currentStep ? '✓' : s.num}
            </div>
            <span className={`text-xs mt-1 ${i <= currentStep ? 'text-white' : 'text-white/40'}`}>
              {s.label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`w-10 h-0.5 mx-1 mt-[-1.25rem] ${i < currentStep ? 'bg-green-400' : 'bg-white/20'}`} />
          )}
        </div>
      ))}
    </div>
  );

  const renderStep = () => {
    switch (currentStep) {
      case 0: return renderStep1();
      case 1: return renderStep2();
      case 2: return renderStep3();
      case 3: return renderStep4();
      case 4: return renderStep5();
      default: return null;
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0: return true;
      case 1: return !!guestPhone && customerFound !== 'pending';
      case 2: return bodyMassageDuration > 0;
      case 3: return true;
      case 4: return true;
      default: return false;
    }
  };

  // --- Step 1: Date & Time ---
  const renderStep1 = () => (
    <div className="text-center">
      <h2 className="text-lg font-semibold text-white mb-6">Choose Date & Time</h2>
      <div className="bg-white rounded-xl p-6 max-w-sm mx-auto">
        <div className="text-base text-black font-medium">{bookingDate}</div>
        <div className="text-3xl font-bold text-[#031050] mt-2">{formatTime(bookingData.startTime)}</div>
        <div className="text-sm text-black mt-1">
          {bookingData.duration} min &middot; {shopName}
        </div>
      </div>
    </div>
  );

  // --- Step 2: Your Information ---
  const renderStep2 = () => (
    <div>
      <h2 className="text-lg font-semibold text-white mb-6 text-center">Your Information</h2>
      <div className="bg-white rounded-xl p-6 max-w-md mx-auto space-y-4">
        <div className="border border-gray-300 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-black mb-3">Returning Customer</h3>
          <label className="text-xs font-medium text-black mb-1 block">Phone Number</label>
          <input type="tel" value={guestPhone} onChange={e => setGuestPhone(e.target.value)}
            placeholder="090 1234 567"
            className="w-full p-2.5 border border-gray-300 rounded-lg text-sm text-black mb-3" />
          <button onClick={handleFindCustomer}
            className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
            Find My Booking / Continue
          </button>
        </div>

        {customerFound === 'found' && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
            Customer found! Your information has been loaded.
          </div>
        )}

        {customerFound === 'new' && (
          <div className="border border-gray-300 rounded-lg p-4 space-y-3">
            <h3 className="text-sm font-semibold text-black">New Customer</h3>
            <div>
              <label className="text-xs font-medium text-black mb-1 block">Name</label>
              <input type="text" value={customerName} onChange={e => setCustomerName(e.target.value)}
                className="w-full p-2.5 border border-gray-300 rounded-lg text-sm text-black" />
            </div>
            <div>
              <label className="text-xs font-medium text-black mb-1 block">Phone Number</label>
              <input type="tel" value={guestPhone} onChange={e => setGuestPhone(e.target.value)}
                className="w-full p-2.5 border border-gray-300 rounded-lg text-sm text-black" />
            </div>
            <div>
              <label className="text-xs font-medium text-black mb-1 block">Email <span className="text-gray-400">(Optional)</span></label>
              <input type="email" value={customerEmail} onChange={e => setCustomerEmail(e.target.value)}
                className="w-full p-2.5 border border-gray-300 rounded-lg text-sm text-black" />
            </div>
            <div>
              <label className="text-xs font-medium text-black mb-1 block">Date of Birth <span className="text-gray-400">(Optional)</span></label>
              <input type="date" value={customerDOB} onChange={e => setCustomerDOB(e.target.value)}
                className="w-full p-2.5 border border-gray-300 rounded-lg text-sm text-black" />
            </div>
            <div>
              <label className="text-xs font-medium text-black mb-1 block">Gender <span className="text-gray-400">(Optional)</span></label>
              <div className="flex gap-4">
                {['Male', 'Female', 'Other'].map(g => (
                  <label key={g} className="flex items-center gap-1.5 cursor-pointer">
                    <input type="radio" name="customerGender" checked={customerGender === g}
                      onChange={() => setCustomerGender(g)} className="accent-blue-600" />
                    <span className="text-sm text-black">{g}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // --- Step 3: Select Services ---
  const renderStep3 = () => (
    <div>
      <h2 className="text-lg font-semibold text-white mb-6 text-center">Select Your Treatment</h2>
      <div className="max-w-lg mx-auto space-y-4">
        <div className="bg-white rounded-xl p-6">
          <h3 className="text-sm font-semibold text-black mb-3">Body Massage</h3>
          <div className="flex flex-wrap gap-2">
            {bodyMassageOptions.map(d => (
              <button key={d} onClick={() => setBodyMassageDuration(d === bodyMassageDuration ? 0 : d)}
                className={`px-5 py-2.5 rounded-lg border text-sm font-medium transition ${
                  bodyMassageDuration === d
                    ? 'bg-[#337AB7] text-white border-[#337AB7]'
                    : 'bg-white text-black border-gray-300 hover:border-[#337AB7]'
                }`}>
                {d} min
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6">
          <h3 className="text-sm font-semibold text-black mb-3">Add-ons</h3>
          <div className="flex flex-wrap gap-3">
            {addonOptions.map(opt => (
              <label key={opt} className="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" checked={selectedAddons.includes(opt)}
                  onChange={() => toggleAddon(opt)} className="accent-blue-600" />
                <span className="text-sm text-black">{opt}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6">
          <h3 className="text-sm font-semibold text-black mb-3">Optional Extras</h3>
          <div className="flex flex-wrap gap-3">
            {extraOptions.map(opt => (
              <label key={opt} className="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" checked={optionalExtras.includes(opt)}
                  onChange={() => toggleExtra(opt)} className="accent-blue-600" />
                <span className="text-sm text-black">{opt}</span>
              </label>
            ))}
          </div>
        </div>

        {(bodyMassageDuration > 0 || selectedAddons.length > 0) && (
          <div className="bg-white rounded-xl p-6 border-2 border-[#337AB7]">
            <h3 className="text-sm font-semibold text-black mb-3">Summary</h3>
            <div className="space-y-1.5">
              {bodyMassageDuration > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-black">Body Massage</span>
                  <span className="font-medium text-black">{bodyMassageDuration} min</span>
                </div>
              )}
              {selectedAddons.map(a => (
                <div key={a} className="flex justify-between text-sm">
                  <span className="text-black">{a}</span>
                  <span className="font-medium text-black">
                    {a === 'Neck Care' || a === 'Calf Care' ? '15 min' : '30 min'}
                  </span>
                </div>
              ))}
              <div className="border-t border-gray-200 pt-1.5 mt-1.5 flex justify-between text-sm font-semibold">
                <span className="text-black">Total</span>
                <span className="text-black">{totalMinutes} minutes</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // --- Step 4: Preferences ---
  const renderStep4 = () => (
    <div>
      <h2 className="text-lg font-semibold text-white mb-6 text-center">Your Preferences</h2>
      <div className="max-w-lg mx-auto space-y-4">
        <div className="bg-white rounded-xl p-6">
          <h3 className="text-sm font-semibold text-black mb-3">Therapist Preference</h3>
          <div className="flex flex-wrap gap-4">
            {[
              { value: 'no_preference', label: 'No Preference' },
              { value: 'male', label: 'Male Therapist' },
              { value: 'specific', label: 'Specific Therapist' },
            ].map(opt => (
              <label key={opt.value} className="flex items-center gap-1.5 cursor-pointer">
                <input type="radio" name="therapistPref" checked={therapistPref === opt.value}
                  onChange={() => setTherapistPref(opt.value)} className="accent-blue-600" />
                <span className="text-sm text-black">{opt.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6">
          <h3 className="text-sm font-semibold text-black mb-3">Massage Strength</h3>
          <div className="flex flex-wrap gap-3">
            {['Gentle', 'Normal', 'Strong'].map(s => (
              <button key={s} onClick={() => setMassageStrength(s)}
                className={`px-4 py-2 rounded-lg border text-sm transition ${
                  massageStrength === s
                    ? 'bg-[#337AB7] text-white border-[#337AB7]'
                    : 'bg-white text-black border-gray-300 hover:border-[#337AB7]'
                }`}>
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6">
          <h3 className="text-sm font-semibold text-black mb-3">During Treatment</h3>
          <div className="space-y-2">
            {[
              'Prefer Quiet',
              'Feel Free to Chat',
              'Ask Me About Pressure',
            ].map(opt => (
              <label key={opt} className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="chatPref" checked={chatPref === opt}
                  onChange={() => setChatPref(opt)} className="accent-blue-600" />
                <span className="text-sm text-black">{opt}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6">
          <h3 className="text-sm font-semibold text-black mb-3">Areas to Focus On</h3>
          <div className="flex flex-wrap gap-2">
            {bodyParts.map(part => (
              <button key={part} onClick={() => toggleFocus(part)}
                className={`px-3 py-1.5 rounded-full border text-xs transition ${
                  focusAreas.includes(part)
                    ? 'bg-[#337AB7] text-white border-[#337AB7]'
                    : 'bg-white text-black border-gray-300 hover:border-[#337AB7]'
                }`}>
                {part}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6">
          <h3 className="text-sm font-semibold text-black mb-3">Areas to Avoid</h3>
          <div className="flex flex-wrap gap-2">
            {bodyParts.map(part => (
              <button key={part} onClick={() => toggleAvoid(part)}
                className={`px-3 py-1.5 rounded-full border text-xs transition ${
                  avoidAreas.includes(part)
                    ? 'bg-red-500 text-white border-red-500'
                    : 'bg-white text-black border-gray-300 hover:border-red-400'
                }`}>
                {part}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6">
          <h3 className="text-sm font-semibold text-black mb-3">Notes</h3>
          <textarea value={notes} onChange={e => setNotes(e.target.value)}
            placeholder="Anything you'd like us to know?"
            className="w-full p-3 border border-gray-300 rounded-lg text-sm text-black resize-none h-24" />
        </div>
      </div>
    </div>
  );

  // --- Step 5: Review & Confirm ---
  const renderStep5 = () => (
    <div>
      <h2 className="text-lg font-semibold text-white mb-6 text-center">Review Your Booking</h2>
      <div className="max-w-md mx-auto bg-white rounded-xl p-6 space-y-4">
        <div className="text-center pb-3 border-b border-gray-200">
          <div className="text-base font-semibold text-black">{bookingDate}</div>
          <div className="text-2xl font-bold text-[#031050]">{formatTime(bookingData.startTime)}</div>
          <div className="text-sm text-black mt-1">{shopName}</div>
        </div>

        <div className="space-y-2 text-sm">
          {bodyMassageDuration > 0 && (
            <div className="flex justify-between">
              <span className="text-black">Body Massage</span>
              <span className="font-medium text-black">{bodyMassageDuration} min</span>
            </div>
          )}
          {selectedAddons.map(a => (
            <div key={a} className="flex justify-between">
              <span className="text-black">{a}</span>
              <span className="font-medium text-black">{a === 'Neck Care' || a === 'Calf Care' ? '15 min' : '30 min'}</span>
            </div>
          ))}
          <div className="border-t border-gray-200 pt-2 flex justify-between font-semibold">
            <span className="text-black">Total</span>
            <span className="text-black">{totalMinutes || bookingData.duration} minutes</span>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-3 space-y-1.5 text-sm">
          <div className="flex justify-between">
            <span className="text-black">Therapist</span>
            <span className="text-black">
              {therapistPref === 'no_preference' ? 'No Preference' : therapistPref === 'male' ? 'Male' : 'Specific'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-black">Strength</span>
            <span className="text-black capitalize">{massageStrength}</span>
          </div>
          {chatPref && (
            <div className="flex justify-between">
              <span className="text-black">Preference</span>
              <span className="text-black">{chatPref}</span>
            </div>
          )}
          {focusAreas.length > 0 && (
            <div className="flex justify-between">
              <span className="text-black">Focus</span>
              <span className="text-black text-right max-w-[60%]">{focusAreas.join(', ')}</span>
            </div>
          )}
          {avoidAreas.length > 0 && (
            <div className="flex justify-between">
              <span className="text-black">Avoid</span>
              <span className="text-black text-right max-w-[60%]">{avoidAreas.join(', ')}</span>
            </div>
          )}
        </div>

        {optionalExtras.length > 0 && (
          <div className="border-t border-gray-200 pt-3 text-sm">
            <span className="text-black font-medium">Extras: </span>
            <span className="text-black">{optionalExtras.join(', ')}</span>
          </div>
        )}

        {notes && (
          <div className="border-t border-gray-200 pt-3 text-sm">
            <span className="text-black font-medium">Notes: </span>
            <span className="text-black">{notes}</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-black text-sm">{error}</div>
        )}

        {!bodyMassageDuration && !bookingData.duration && (
          <p className="text-sm text-red-500">Please select a treatment duration.</p>
        )}

        <button onClick={handleConfirm}
          disabled={!guestPhone || isConfirming || totalMinutes === 0}
          className="w-full py-3 bg-green-600 text-white text-base font-semibold rounded-lg hover:bg-green-700 disabled:bg-gray-300 transition">
          {isConfirming ? 'Confirming...' : 'Confirm Booking'}
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#031050] py-8">
      <div className="container mx-auto px-4 max-w-2xl">
        {renderProgress()}
        {renderStep()}
        <div className="flex justify-between mt-6 max-w-md mx-auto">
          <button onClick={() => setCurrentStep(s => Math.max(0, s - 1))}
            disabled={currentStep === 0}
            className="px-6 py-2.5 text-sm font-medium text-white bg-white/10 rounded-lg hover:bg-white/20 disabled:opacity-30 transition">
            Back
          </button>
          {currentStep < STEPS.length - 1 ? (
            <button onClick={() => canProceed() && setCurrentStep(s => s + 1)}
              disabled={!canProceed()}
              className="px-6 py-2.5 text-sm font-medium text-white bg-[#337AB7] rounded-lg hover:bg-[#286090] disabled:opacity-30 transition">
              Continue
            </button>
          ) : (
            <div />
          )}
        </div>
      </div>
    </div>
  );
}
