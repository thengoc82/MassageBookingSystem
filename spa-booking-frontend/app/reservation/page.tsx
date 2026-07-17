'use client';

import { useState, useMemo, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';

const BODY_PARTS = ['Neck', 'Back', 'Right Shoulder', 'Left Shoulder', 'Right Arm', 'Left Arm', 'Right Buttock', 'Left Buttock', 'Right Thigh', 'Left Thigh', 'Right Calf', 'Left Calf', 'Right Foot Sole', 'Left Foot Sole'];
const OPTIONS = ['Premium Mattress', 'Cool Premium Mattress', 'Neck & Shoulder Focus', 'Back Focus', 'Lower Back Focus', 'HPM Mattress Pad', 'Premium Face Pillow', 'Recovery Wear', 'Other'];
const MEMBERSHIPS = ['Royal Member', 'App Member', 'Card Member', 'Web Member', 'Senior Member', 'Non-member'];

interface ApiCourse {
  courseId: number;
  courseName: string;
  duration: number;
  price: number;
  courseType: 'main' | 'addon';
}

function parseDisplayDate(s: string | null): string {
  if (!s) return 'Select a date';
  try {
    const d = new Date(s + 'T00:00:00');
    return d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  } catch { return s; }
}

export default function ReservationPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F5F7FA] flex items-center justify-center text-sm text-gray-500">Loading...</div>}>
      <ReservationForm />
    </Suspense>
  );
}

function ReservationForm() {
  const router = useRouter();
  const sp = useSearchParams();

  const initShopId = sp.get('shopId');
  const initDate = sp.get('date');
  const initTime = sp.get('time') || '12:00';
  const preselectedTherapistId = sp.get('therapistId');

  const [shopId] = useState<number>(Number(initShopId) || 0);
  const [courses, setCourses] = useState<ApiCourse[]>([]);
  const [displayDate] = useState(() => parseDisplayDate(initDate));
  const [selectedTime, setSelectedTime] = useState(initTime);
  const [timeMin] = useState(() => initTime);
  const [timeMax] = useState(() => initTime);
  const [customerType, setCustomerType] = useState<'member' | 'guest'>('member');
  const [phoneNo, setPhoneNo] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [courseDurations, setCourseDurations] = useState<Record<number, number>>({});
  const [options, setOptions] = useState<string[]>([]);
  const [tiredParts, setTiredParts] = useState<string[]>([]);
  const [avoidAreas, setAvoidAreas] = useState<string[]>([]);
  const [therapistPref, setTherapistPref] = useState(preselectedTherapistId ? 'specific' : '');
  const [conversationPref, setConversationPref] = useState('');
  const [strength, setStrength] = useState('Normal');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ code: string; name: string } | null>(null);
  const [error, setError] = useState('');

  const mainCourses = useMemo(() => courses.filter(c => c.courseType === 'main'), [courses]);

  const totalDuration = Object.values(courseDurations).reduce((a, b) => a + b, 0);
  // Pick first selected main course ID for the API call
  const selectedMainId = useMemo(() => {
    const found = mainCourses.find(c => courseDurations[c.courseId]);
    return found?.courseId;
  }, [mainCourses, courseDurations]);

  useEffect(() => {
    if (!shopId) return;
    api.shops.getCourses(shopId).then((d: unknown) => {
      const list: ApiCourse[] = Array.isArray(d) ? d as ApiCourse[] : (d as { data?: ApiCourse[] }).data || [];
      setCourses(list);
    }).catch(() => {});
  }, [shopId]);

  const toggleOption = (o: string) => setOptions(p => p.includes(o) ? p.filter(x => x !== o) : [...p, o]);
  const toggleTired = (p: string) => setTiredParts(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);
  const toggleAvoid = (p: string) => setAvoidAreas(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);

  const handleSubmit = async () => {
    if (!shopId || !phoneNo || !selectedMainId || !selectedTime || !initDate) {
      setError('Phone number, course, and time are required');
      return;
    }
    setSubmitting(true);
    setError('');

    try {
      const payload: Record<string, unknown> = {
        phoneNumber: phoneNo,
        shopId,
        bookingDate: initDate,
        startTime: selectedTime,
        duration: totalDuration || 60,
        numberOfPeople: 1,
        courseId: selectedMainId,
        services: [{ personIndex: 1, courseId: selectedMainId }],
        addOns: [],
        customerName: customerName || undefined,
        massageStrength: strength,
        conversationPreference: conversationPref || undefined,
        focusAreas: tiredParts.length > 0 ? tiredParts : undefined,
        avoidAreas: avoidAreas.length > 0 ? avoidAreas : undefined,
        extraOptions: options.length > 0 ? options : undefined,
      };
      if (therapistPref) payload.therapistPreferenceType = therapistPref === 'No Preference' ? 'no_preference' : therapistPref.toLowerCase().includes('male') ? 'gender' : therapistPref.toLowerCase().includes('female') ? 'gender' : undefined;
      if (therapistPref?.toLowerCase().includes('male')) payload.therapistPreferenceValue = 'Male';
      if (therapistPref?.toLowerCase().includes('female')) payload.therapistPreferenceValue = 'Female';
      if (preselectedTherapistId) {
        payload.therapistPreferenceType = 'specific';
        payload.therapistPreferenceValue = preselectedTherapistId;
      }

      const res = await api.bookings.create(payload) as { data?: { bookingCode?: string; therapistName?: string }; bookingCode?: string; therapistName?: string };
      const data = res.data || res;
      // Track booking so dashboard shows it as unavailable
      try {
        const recent = JSON.parse(localStorage.getItem('recentBookings') || '[]');
        recent.push({ shopId, date: initDate, startTime: selectedTime, duration: totalDuration || 60 });
        localStorage.setItem('recentBookings', JSON.stringify(recent.slice(-20)));
      } catch { /* ignore */ }
      setResult({ code: data.bookingCode || '', name: data.therapistName || '' });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Booking failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="min-h-screen bg-[#F5F7FA] flex items-center justify-center">
        <div className="bg-white rounded-lg border border-gray-200 p-8 max-w-md w-full text-center space-y-4">
          <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
            <span className="text-emerald-600 text-xl font-bold">&#10003;</span>
          </div>
          <h2 className="text-lg font-bold text-gray-900">Booking Confirmed</h2>
          <div className="bg-gray-50 rounded p-4">
            <div className="text-[11px] text-gray-500 uppercase tracking-wider">Code</div>
            <div className="text-lg font-mono font-bold text-[#031050]">{result.code}</div>
          </div>
          {result.name && <div className="text-sm text-gray-600">Therapist: <span className="font-semibold">{result.name}</span></div>}
          <button onClick={() => router.push('/dashboard')}
            className="w-full py-2 bg-[#031050] text-white text-sm font-semibold rounded hover:bg-[#1a2a6b]">Back to Booking</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F5F7FA]">
      <div className="max-w-7xl mx-auto p-4 space-y-4">

        {/* Row 1: Date + Time — time is fixed to the selected slot (read-only) */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 flex gap-8 items-center">
          <div>
            <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Date</label>
            <div className="text-base font-semibold text-gray-900 mt-0.5">{displayDate}</div>
          </div>
          <div className="w-px h-8 bg-gray-200" />
          <div>
            <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Time</label>
            <input type="time" value={selectedTime} readOnly
              min={timeMin} max={timeMax}
              className="mt-0.5 border border-gray-300 rounded px-3 py-1 text-sm font-semibold text-gray-900 bg-gray-100 cursor-not-allowed" />
          </div>
        </div>

        {/* Customer info */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-3 mb-4">
            <button onClick={() => setCustomerType('member')}
              className={`px-4 py-1.5 rounded text-xs font-medium transition ${customerType === 'member' ? 'bg-[#031050] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>Member</button>
            <button onClick={() => setCustomerType('guest')}
              className={`px-4 py-1.5 rounded text-xs font-medium transition ${customerType === 'guest' ? 'bg-[#031050] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>Guest</button>
          </div>
          <div className="flex items-start gap-6 flex-wrap">
            {customerType === 'member' ? (
              <>
                <div className="min-w-[200px] flex-1">
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Membership Number</label>
                  <div className="flex gap-2">
                    <input placeholder="Enter membership no." className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-900" />
                    <button className="px-3 py-1.5 bg-[#031050] text-white text-xs rounded hover:bg-[#1a2a6b] shrink-0">Search</button>
                  </div>
                </div>
                <div className="min-w-[200px] flex-1">
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Phone Number</label>
                  <input value={phoneNo} onChange={e => setPhoneNo(e.target.value)} placeholder="090 1234 567" className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-900" />
                </div>
              </>
            ) : (
              <>
                <div className="min-w-[200px] flex-1">
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Customer Name</label>
                  <input value={customerName} onChange={e => setCustomerName(e.target.value)} placeholder="Full name" className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-900" />
                </div>
                <div className="min-w-[200px] flex-1">
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Phone Number</label>
                  <input value={phoneNo} onChange={e => setPhoneNo(e.target.value)} placeholder="090 1234 567" className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-900" />
                </div>
              </>
            )}
          </div>
        </div>

        {/* Reservation status */}
        <div className="flex items-center gap-4 flex-wrap">
          <span className={`text-xs px-3 py-1 rounded-full font-medium ${phoneNo ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-500'}`}>
            {phoneNo ? 'Reservation Possible' : 'Enter phone number'}
          </span>
          <div className="flex flex-wrap gap-2">
            {MEMBERSHIPS.map(m => (
              <span key={m} className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${m === 'Non-member' ? 'border-gray-300 text-gray-500 bg-gray-50' : 'border-amber-300 bg-amber-50 text-amber-800'}`}>{m}</span>
            ))}
          </div>
        </div>

        {/* Summary + Course section */}
        <div className="flex gap-4">
          <div className="w-80 shrink-0">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-xs font-semibold text-gray-900 mb-3">Selected Course</h3>
              <div className="space-y-1.5 text-xs">
                {mainCourses.map(c => {
                  const dur = courseDurations[c.courseId];
                  if (!dur) return null;
                  return <div key={c.courseId} className="flex justify-between text-gray-700"><span>{c.courseName}</span><span className="font-semibold">{dur} min</span></div>;
                })}
                {Object.keys(courseDurations).length === 0 && <div className="text-gray-400 italic">No courses selected</div>}
              </div>
              <div className="border-t border-gray-200 mt-3 pt-3 flex justify-between text-sm font-bold text-[#031050]">
                <span>Total</span>
                <span>{totalDuration || 60} minutes</span>
              </div>
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-xs font-semibold text-gray-900 mb-3">Choose Course & Duration</h3>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                {mainCourses.map(c => (
                  <div key={c.courseId}>
                    <div className="text-xs font-semibold text-gray-800 mb-1.5">{c.courseName}</div>
                    <button onClick={() => setCourseDurations(p => ({ ...p, [c.courseId]: p[c.courseId] === c.duration ? 0 : c.duration }))}
                      className={`px-3 py-1 rounded text-[10px] font-semibold border transition ${
                        courseDurations[c.courseId] === c.duration
                          ? 'bg-[#031050] text-white border-[#031050]'
                          : 'bg-white text-gray-700 border-gray-200 hover:border-[#031050]'
                      }`}>
                      {c.duration} min
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 2x4 Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Options</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              {OPTIONS.map(o => (
                <label key={o} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" checked={options.includes(o)} onChange={() => toggleOption(o)} className="accent-[#031050] w-3 h-3" />
                  <span className="text-[11px] text-gray-700">{o}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Tired Parts</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {BODY_PARTS.map(p => (
                <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" checked={tiredParts.includes(p)} onChange={() => toggleTired(p)} className="accent-[#031050] w-3 h-3" />
                  <span className="text-[11px] text-gray-700">{p}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Areas Not To Touch</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {BODY_PARTS.map(p => (
                <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" checked={avoidAreas.includes(p)} onChange={() => toggleAvoid(p)} className="accent-[#031050] w-3 h-3" />
                  <span className="text-[11px] text-gray-700">{p}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Therapist Preference</h3>
            {preselectedTherapistId ? (
              <div className="bg-emerald-50 border border-emerald-200 rounded px-3 py-1.5">
                <span className="text-xs text-emerald-800 font-medium">Locked to selected therapist (#{preselectedTherapistId})</span>
              </div>
            ) : (
              <select value={therapistPref} onChange={e => setTherapistPref(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-xs text-gray-700 bg-white">
                <option value="">No Preference</option>
                <option>Male Preferred</option>
                <option>Female Preferred</option>
              </select>
            )}
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Conversation Preference</h3>
            <div className="space-y-1.5">
              {['No Preference', 'Quiet Session', 'Ask Every Time'].map(p => (
                <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="radio" name="convPref" checked={conversationPref === p} onChange={() => setConversationPref(p)} className="accent-[#031050] w-3 h-3" />
                  <span className="text-[11px] text-gray-700">{p}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Massage Strength</h3>
            <div className="flex flex-wrap gap-1">
              {['Stronger', 'Slightly Stronger', 'Normal', 'Slightly Weaker', 'Weaker'].map(s => (
                <button key={s} onClick={() => setStrength(s)}
                  className={`px-2 py-0.5 rounded text-[10px] font-medium border transition ${
                    strength === s ? 'bg-[#031050] text-white border-[#031050]' : 'bg-white text-gray-700 border-gray-200'
                  }`}>{s}</button>
              ))}
            </div>
          </div>
        </div>

        {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-xs text-red-700">{error}</div>}
        <div className="h-16" />
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-4 py-2.5 flex items-center gap-3 z-20">
        <button onClick={() => router.push('/dashboard')} className="text-xs text-gray-500 hover:text-gray-700 underline underline-offset-2">Back</button>
        <span className="text-xs text-gray-600 font-mono">#RSV-{initDate?.replace(/-/g, '') || '00000000'}-001</span>
        <div className="flex-1" />
        <button onClick={handleSubmit} disabled={submitting || !phoneNo || !selectedMainId}
          className="px-6 py-1.5 bg-[#031050] text-white text-xs font-semibold rounded hover:bg-[#1a2a6b] shadow-sm disabled:bg-gray-300 disabled:cursor-not-allowed">
          {submitting ? 'Booking...' : 'Register Reservation'}
        </button>
      </div>
    </div>
  );
}
