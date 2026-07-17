'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import type { TimeSlot, TherapistInfo } from '@/types';

interface Props {
  shopId: number;
  date: string;
  duration: number;
  numberOfPeople: number;
  startTime?: string;
  gender?: string;
  onSelectSlot?: (startTime: string, therapistId: number) => void;
}

export default function TherapistGantt({ shopId, date, duration, numberOfPeople, startTime, gender, onSelectSlot }: Props) {
  const [therapists, setTherapists] = useState<TherapistInfo[]>([]);
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const params: Record<string, string> = {
      date,
      duration: String(duration),
      numberOfPeople: String(numberOfPeople),
      show_therapists: 'true',
    };
    if (startTime) params.startTime = startTime;
    if (gender) params.gender = gender;

    api.shops.getAvailableSlots(shopId, params)
      .then((res: any) => {
        if (cancelled) return;
        const data = res?.data ?? res ?? [];
        const t = res?.therapists ?? [];
        setTherapists(t);
        setSlots(Array.isArray(data) ? data : []);
      })
      .catch((err: any) => {
        if (cancelled) return;
        setError(err.message || 'Failed to load availability');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [shopId, date, duration, numberOfPeople, startTime, gender]);

  if (loading) {
    return <div className="text-center py-8 text-black">Loading therapist availability...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-red-600">{error}</div>;
  }

  if (!therapists.length) {
    return <div className="text-center py-8 text-black">No therapists found for this shop.</div>;
  }

  const cellW = 72;
  const rowH = 36;
  const headerH = 40;
  const nameColW = 140;

  const isAvailable = (therapistId: number, slot: TimeSlot) =>
    slot.availableTherapistIds?.includes(therapistId) ?? false;

  const handleCellClick = (startTime: string, therapistId: number) => {
    onSelectSlot?.(startTime, therapistId);
  };

  return (
    <div className="flex h-full min-h-0">
      {/* Therapist names column */}
      <div className="flex-shrink-0 border-r border-gray-200 bg-gray-50" style={{ width: nameColW }}>
        <div className="h-[40px] border-b border-gray-200 bg-gray-100 flex items-center px-3 text-xs font-semibold text-black sticky top-0 z-20">
          Therapist
        </div>
        {therapists.map(t => (
          <div
            key={t.therapistId}
            className="flex items-center px-3 border-b border-gray-100 text-sm font-medium text-black"
            style={{ height: rowH }}
          >
            {t.name}
          </div>
        ))}
      </div>

      {/* Scrollable grid */}
      <div ref={scrollRef} className="overflow-auto flex-1 min-w-0">
        <div style={{ width: slots.length * cellW, minWidth: '100%' }}>
          {/* Header row */}
          <div className="flex h-10 border-b border-gray-200 bg-gray-100 sticky top-0 z-10">
            {slots.map(slot => (
              <div
                key={slot.startTime}
                className="flex-shrink-0 flex items-center justify-center text-xs font-mono text-black border-r border-gray-200 last:border-r-0"
                style={{ width: cellW }}
              >
                {slot.startTime}
              </div>
            ))}
          </div>

          {/* Therapist rows */}
          {therapists.map(t => (
            <div key={t.therapistId} className="flex" style={{ height: rowH }}>
              {slots.map(slot => {
                const avail = isAvailable(t.therapistId, slot);
                return (
                  <button
                    key={slot.startTime}
                    disabled={!avail}
                    onClick={() => avail && handleCellClick(slot.startTime, t.therapistId)}
                    className={`flex-shrink-0 border-r border-b border-gray-100 transition ${
                      avail
                        ? 'bg-green-100 hover:bg-green-200 cursor-pointer'
                        : 'bg-white cursor-default'
                    }`}
                    style={{ width: cellW }}
                    title={`${t.name} @ ${slot.startTime}: ${avail ? 'Available' : 'Unavailable'}`}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
