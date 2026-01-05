import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../ui/Button';
import Input from '../ui/Input';
import LocationInput from './LocationInput';

export function CarsSearchForm() {
  const navigate = useNavigate();
  const [pickup, setPickup] = useState(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  return (
    <form
      className="grid gap-4 md:grid-cols-12"
      onSubmit={(e) => {
        e.preventDefault();
        const sp = new URLSearchParams();
        if (pickup?.id) sp.set('location_id', pickup.id);
        if (pickup?.name) sp.set('location_name', pickup.name);
        if (startDate) sp.set('start_date', startDate);
        if (endDate) sp.set('end_date', endDate);
        navigate(`/cars?${sp.toString()}`);
      }}
    >
      <div className="md:col-span-6">
        <LocationInput label="Pick-up" value={pickup} onChange={setPickup} placeholder="City or airport" />
      </div>
      <div className="md:col-span-2">
        <div className="mb-1 text-xs font-bold text-slate-700">Pick-up</div>
        <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
      </div>
      <div className="md:col-span-2">
        <div className="mb-1 text-xs font-bold text-slate-700">Drop-off</div>
        <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
      </div>
      <div className="md:col-span-2 flex items-end">
        <Button type="submit" className="w-full">
          Search cars
        </Button>
      </div>
    </form>
  );
}

export default CarsSearchForm;
