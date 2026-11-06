import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { apiDelete, apiGet, apiPost } from '../../lib/api';

// Kindred handoff (X2): a teacher issues a connection key here and gives it
// to the event organizer, who pastes it into Kindred. Kindred can then enroll
// the event's attendees into the courses this teacher runs, through the same
// import as "Enroll a list". The key is shown once; issuing a new one or
// disconnecting stops the old one at once.

const muted = 'text-[rgb(var(--text-muted))]';

export function KindredConnection() {
  const [status, setStatus] = useState(null);
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    apiGet('/api/kindred-handoff/key').then(setStatus).catch(() => setStatus({ active: false }));
  }, []);

  const issue = async () => {
    if (status?.active && !window.confirm('Make a new key? The current key stops working right away.')) return;
    setBusy(true); setError(''); setCopied(false);
    try {
      const result = await apiPost('/api/kindred-handoff/key', {});
      setKey(result.key);
      setStatus({ active: true, last4: result.last4 });
    } catch (e) {
      setError(e.message || 'Could not create a key.');
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async () => {
    if (!window.confirm('Disconnect Kindred? It will no longer be able to enroll people into your courses.')) return;
    setBusy(true); setError('');
    try {
      await apiDelete('/api/kindred-handoff/key');
      setKey('');
      setStatus({ active: false });
    } catch (e) {
      setError(e.message || 'Could not disconnect.');
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(key);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]" data-testid="kindred-connection">
      <CardContent className="p-4 space-y-3">
        <h3 className="text-sm text-[rgb(var(--text-main))]">Receive attendees from Kindred</h3>
        <p className={`text-xs ${muted}`}>
          If your event was organized in Kindred, the organizer can send its attendees here after the event.
          Each person is enrolled in the courses for the activities they came to and gets a welcome email with a
          sign-in link. Create a key and give it to the organizer; it only reaches courses you teach.
        </p>
        {status?.active && !key ? (
          <p className="text-xs text-[rgb(var(--text-main))]" data-testid="kindred-key-active">
            Connected. Key ending in <strong>{status.last4}</strong>.
          </p>
        ) : null}
        {key ? (
          <div className="space-y-2" data-testid="kindred-key-new">
            <label className={`block text-xs ${muted}`} htmlFor="kindred-key-value">
              Copy this key now. It won't be shown again.
            </label>
            <input
              className="w-full text-xs px-2 py-1 rounded border bg-[rgb(var(--ink-deep))] text-[rgb(var(--text-main))] border-[rgb(var(--ink-border))] font-mono"
              id="kindred-key-value"
              onFocus={(e) => e.target.select()}
              readOnly
              value={key}
            />
            <Button onClick={copy} size="sm" type="button" variant="outline">{copied ? 'Copied' : 'Copy key'}</Button>
          </div>
        ) : null}
        {error ? <p className="text-xs text-red-400" role="alert">{error}</p> : null}
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy} onClick={issue} size="sm" type="button">
            {status?.active ? 'Make a new key' : 'Create a key'}
          </Button>
          {status?.active ? (
            <Button disabled={busy} onClick={disconnect} size="sm" type="button" variant="outline">Disconnect</Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

export default KindredConnection;
