import { useEffect, useState } from 'react';

import { useTheme } from '../state/ThemeContext.jsx';
import { useAuth } from '../state/AuthContext.jsx';
import { useToast } from '../state/ToastContext.jsx';
import { getSettings, updateSettings } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { Spinner } from '../shared/ui/Spinner.jsx';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const toast = useToast();

  const { data, loading, error, refetch } = useResource(() => getSettings(), []);

  const [notifEmail, setNotifEmail] = useState(true);
  const [notifInApp, setNotifInApp] = useState(true);

  useEffect(() => {
    const s = data?.settings || data;
    if (!s) return;
    const n = s.notifications;
    if (typeof n === 'object' && n) {
      setNotifEmail(Boolean(n.email));
      setNotifInApp(Boolean(n.inApp));
    } else if (typeof n === 'boolean') {
      setNotifEmail(Boolean(n));
      setNotifInApp(Boolean(n));
    }
  }, [data]);

  async function save() {
    try {
      await updateSettings({
        theme,
        notifications: { email: notifEmail, inApp: notifInApp },
      });
      toast.push({ title: 'Settings saved', variant: 'success' });
      await refetch();
    } catch (e) {
      toast.push({ title: 'Failed to save settings', message: e?.message, variant: 'error' });
    }
  }

  return (
    <div className="max-w-3xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Settings</h1>
        <p className="text-sm text-fg-muted mt-1">Manage your profile and preferences.</p>
      </div>

      <div className="surface p-4">
        <div className="text-sm font-semibold">Profile</div>
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-fg-muted">Name</div>
            <div className="text-sm">{user?.name || '—'}</div>
          </div>
          <div>
            <div className="text-xs text-fg-muted">Email</div>
            <div className="text-sm">{user?.email || '—'}</div>
          </div>
        </div>
      </div>

      <div className="surface p-4">
        <div className="text-sm font-semibold">Theme</div>
        <div className="mt-3 flex items-center gap-3">
          <select
            className="input h-10"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            data-testid="settings-theme"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
          <button type="button" className="btn btn-primary" onClick={save} data-testid="save-settings">
            Save
          </button>
        </div>
      </div>

      <div className="surface p-4">
        <div className="text-sm font-semibold">Notifications</div>

        {loading && (
          <div className="mt-3 flex items-center gap-2 text-fg-muted">
            <Spinner size="sm" /> Loading…
          </div>
        )}
        {error && (
          <div className="mt-3 text-sm text-danger">
            {error}{' '}
            <button type="button" className="btn ml-2" onClick={refetch} data-testid="retry-settings">
              Retry
            </button>
          </div>
        )}

        <div className="mt-3 space-y-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={notifEmail}
              onChange={(e) => setNotifEmail(e.target.checked)}
              data-testid="notif-email"
            />
            Email notifications
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={notifInApp}
              onChange={(e) => setNotifInApp(e.target.checked)}
              data-testid="notif-inapp"
            />
            In-app notifications
          </label>
        </div>

        <div className="mt-4">
          <button type="button" className="btn btn-primary" onClick={save} data-testid="save-notifications">
            Save notifications
          </button>
        </div>
      </div>

      <div className="surface p-4">
        <div className="text-sm font-semibold">Keyboard shortcuts</div>
        <div className="mt-3 text-sm text-fg-muted">
          <div>
            <span className="font-mono">/</span> Focus search
          </div>
          <div>
            <span className="font-mono">Esc</span> Close dialogs
          </div>
        </div>
      </div>
    </div>
  );
}
