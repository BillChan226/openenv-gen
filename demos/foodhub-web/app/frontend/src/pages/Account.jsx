import React from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';

export function Account() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-white shadow-sm ring-1 ring-zinc-200 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Account</div>
            <div className="mt-2 text-2xl font-black tracking-tight text-zinc-900">
              {user?.name || user?.full_name || 'User'}
            </div>
            <div className="mt-1 text-sm text-zinc-600">{user?.email}</div>
          </div>

          <div className="h-12 w-12 rounded-2xl bg-[#FF3008] text-white flex items-center justify-center font-black shadow-sm">
            {(user?.name || 'U').slice(0, 1).toUpperCase()}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="rounded-2xl bg-zinc-50 ring-1 ring-zinc-200 p-4">
            <div className="text-xs font-semibold text-zinc-500">Default address</div>
            <div className="mt-1 text-sm font-bold text-zinc-900">123 Main St</div>
            <div className="mt-1 text-sm text-zinc-600">San Francisco, CA</div>
          </div>
          <div className="rounded-2xl bg-zinc-50 ring-1 ring-zinc-200 p-4">
            <div className="text-xs font-semibold text-zinc-500">Payment</div>
            <div className="mt-1 text-sm font-bold text-zinc-900">•••• 4242</div>
            <div className="mt-1 text-sm text-zinc-600">Visa</div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => navigate('/orders')}>
            View orders
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              logout();
              navigate('/');
            }}
          >
            Sign out
          </Button>
        </div>
      </div>
    </div>
  );
}

export default Account;
