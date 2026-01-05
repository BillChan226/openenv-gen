import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../ui/Button';
import Input from '../ui/Input';
import LocationInput from './LocationInput';

export function PackagesSearchForm() {
  const navigate = useNavigate();
  const [from, setFrom] = useState(null);
  const [to, setTo] = useState(null);
  const [departDate, setDepartDate] = useState('');
  const [returnDate, setReturnDate] = useState('');

  return (
    <form
      className="grid gap-4 md:grid-cols-12"
      onSubmit={(e) => {
        e.preventDefault();
        const sp = new URLSearchParams();
        if (from?.id) sp.set('from_id', from.id);
        if (to?.id) sp.set('to_id', to.id);
        if (from?.name) sp.set('from_name', from.name);
        if (to?.name) sp.set('to_name', to.name);
        if (departDate) sp.set('depart_date', departDate);
        if (returnDate) sp.set('return_date', returnDate);
        navigate(`/packages?${sp.toString()}`);
      }}
    >
      <div className="md:col-span-4">
        <LocationInput label="Leaving from" value={from} onChange={setFrom} placeholder="Airport or city" />
      </div>
      <div className="md:col-span-4">
        <LocationInput label="Going to" value={to} onChange={setTo} placeholder="Destination" />
      </div>
      <div className="md:col-span-2">
        <div className="mb-1 text-xs font-bold text-slate-700">Depart</div>
        <Input type="date" value={departDate} onChange={(e) => setDepartDate(e.target.value)} />
      </div>
      <div className="md:col-span-2">
        <div className="mb-1 text-xs font-bold text-slate-700">Return</div>
        <Input type="date" value={returnDate} onChange={(e) => setReturnDate(e.target.value)} />
      </div>
      <div className="md:col-span-12">
        <Button type="submit" className="w-full">
          Search packages
        </Button>
      </div>
    </form>
  );
}

export default PackagesSearchForm;
