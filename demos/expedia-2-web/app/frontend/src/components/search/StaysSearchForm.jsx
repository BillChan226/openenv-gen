import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../ui/Button';
import Input from '../ui/Input';
import LocationInput from './LocationInput';

export function StaysSearchForm() {
  const navigate = useNavigate();
  const [location, setLocation] = useState(null);
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [guests, setGuests] = useState(2);

  return (
    <form
      className="grid gap-4 md:grid-cols-12"
      onSubmit={(e) => {
        e.preventDefault();
        const sp = new URLSearchParams();
        if (location?.id) sp.set('location_id', location.id);
        if (location?.name) sp.set('location_name', location.name);
        if (checkIn) sp.set('check_in', checkIn);
        if (checkOut) sp.set('check_out', checkOut);
        sp.set('guests', String(guests || 1));
        navigate(`/stays?${sp.toString()}`);
      }}
    >
      <div className="md:col-span-5">
        <LocationInput label="Going to" value={location} onChange={setLocation} placeholder="City, neighborhood, landmark" />
      </div>
      <div className="md:col-span-2">
        <div className="mb-1 text-xs font-bold text-slate-700">Check-in</div>
        <Input type="date" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} />
      </div>
      <div className="md:col-span-2">
        <div className="mb-1 text-xs font-bold text-slate-700">Check-out</div>
        <Input type="date" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
      </div>
      <div className="md:col-span-2">
        <div className="mb-1 text-xs font-bold text-slate-700">Guests</div>
        <Input type="number" min={1} max={12} value={guests} onChange={(e) => setGuests(Number(e.target.value))} />
      </div>
      <div className="md:col-span-1 flex items-end">
        <Button type="submit" className="w-full">
          Search
        </Button>
      </div>
    </form>
  );
}

export default StaysSearchForm;
