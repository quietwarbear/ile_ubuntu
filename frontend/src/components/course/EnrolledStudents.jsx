import React, { useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { apiDelete, apiPost } from '../../lib/api';

function getFirstName(name = '', email = '') {
  const trimmedName = name.trim();
  if (trimmedName) return trimmedName.split(/\s+/)[0];
  return email.split('@')[0] || 'Student';
}

export function EnrolledStudents({ courseId, enrollments, onChanged }) {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const addStudent = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setBusy(true); setError(''); setMessage('');
    try {
      await apiPost(`/api/courses/${courseId}/enrollments`, { email: email.trim() });
      setMessage('Student added to the course.');
      setEmail('');
      await onChanged?.();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  const removeStudent = async (enrollment) => {
    const name = enrollment.user_name || enrollment.user_email || 'this student';
    if (!window.confirm(`Remove ${name} from this course? Their course progress will be removed.`)) return;
    setBusy(true); setError(''); setMessage('');
    try {
      await apiDelete(`/api/courses/${courseId}/enrollments/${enrollment.user_id}`);
      setMessage('Student removed from the course.');
      await onChanged?.();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <h2 className="text-xs tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-4">
        Enrolled Students ({enrollments.length})
      </h2>
      <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
        <CardContent className="p-4 space-y-3">
          <form onSubmit={addStudent} className="flex flex-col sm:flex-row gap-2" data-testid="add-student-form">
            <Input type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="Student's Ile Ubuntu email" required
              className="bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))]" />
            <Button type="submit" disabled={busy || !email.trim()}
              className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] whitespace-nowrap"
              data-testid="add-student-button">
              {busy ? 'Working…' : 'Add student'}
            </Button>
          </form>
          <p className="text-[10px] text-[rgb(var(--text-muted))]">The student must already have an Ile Ubuntu account.</p>
          {message && <p className="text-xs text-emerald-400" role="status">{message}</p>}
          {error && <p className="text-xs text-red-400" role="alert">{error}</p>}
          {!enrollments.length && (
            <p className="text-xs text-[rgb(var(--text-muted))] py-2">No students are enrolled yet.</p>
          )}
          {enrollments.map(e => (
            <div key={e.id} className="flex items-center justify-between p-2 bg-[rgb(var(--ink-deep))] rounded border border-[rgb(var(--ink-border))]" data-testid={`enrollment-${e.id}`}>
              <div>
                <p className="text-sm text-[rgb(var(--text-main))]">{getFirstName(e.user_name, e.user_email)}</p>
                <p className="text-[10px] text-[rgb(var(--text-muted))] break-all">{e.user_email || 'Email unavailable'}</p>
                <p className="text-[10px] text-[rgb(var(--text-muted))]">
                  Enrolled {new Date(e.enrolled_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-16 h-1.5 bg-[rgb(var(--ink-deep))] rounded-full overflow-hidden border border-[rgb(var(--ink-border))]">
                  <div className="h-full bg-[rgb(var(--gold))] rounded-full" style={{ width: `${e.progress || 0}%` }} />
                </div>
                <span className="text-[10px] text-[rgb(var(--text-muted))] w-8 text-right">{Math.round(e.progress || 0)}%</span>
                <Button type="button" size="sm" variant="ghost" disabled={busy}
                  onClick={() => removeStudent(e)}
                  className="text-[11px] text-[rgb(var(--text-muted))] hover:text-red-400"
                  data-testid={`remove-student-${e.user_id}`}>
                  Remove student
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
