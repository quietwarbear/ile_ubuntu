import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { apiGet, apiPost, apiDelete } from '../../lib/api';

function displayName(person) {
  const name = (person?.name || '').trim();
  if (name) return name;
  return (person?.email || '').split('@')[0] || 'Teacher';
}

/**
 * Manage who teaches a course. Owner-only: a co-teacher holds full rights over
 * lessons and modules but cannot appoint further co-teachers, which mirrors the
 * backend rule rather than restating it loosely.
 */
export function CourseStaffPanel({ courseId, isOwner }) {
  const [staff, setStaff] = useState(null);
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try {
      setStaff(await apiGet(`/api/courses/${courseId}/staff`));
    } catch (e) {
      setError(e.message);
    }
  }, [courseId]);

  useEffect(() => { if (isOwner) load(); }, [isOwner, load]);

  if (!isOwner || !staff) return null;

  const coTeachers = staff.co_instructors || [];
  const atCap = coTeachers.length >= (staff.max_co_instructors || 2);

  const add = async () => {
    const value = email.trim();
    if (!value) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const res = await apiPost(`/api/courses/${courseId}/co-instructors`, { email: value });
      setEmail('');
      setNotice(res.already
        ? `${displayName(res.co_instructor)} already teaches this course.`
        : `${displayName(res.co_instructor)} can now edit lessons and see discussions.`);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (person) => {
    if (!window.confirm(
      `Remove ${displayName(person)} as a co-teacher? They keep anything they already created — only their access ends.`
    )) return;
    setBusy(true); setError(''); setNotice('');
    try {
      await apiDelete(`/api/courses/${courseId}/co-instructors/${person.id}`);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="course-staff-panel">
      <h2 className="text-xs tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-4">
        Teaching Team
      </h2>
      <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
        <CardContent className="p-4 space-y-3">
          {staff.instructor && (
            <div className="flex items-center justify-between p-2 bg-[rgb(var(--ink-deep))] rounded border border-[rgb(var(--ink-border))]">
              <div>
                <p className="text-sm text-[rgb(var(--text-main))]">{displayName(staff.instructor)}</p>
                <p className="text-[10px] text-[rgb(var(--text-muted))] break-all">{staff.instructor.email}</p>
              </div>
              <span className="text-[10px] uppercase tracking-wide text-[rgb(var(--gold))]">Owner</span>
            </div>
          )}

          {coTeachers.map(person => (
            <div key={person.id}
              className="flex items-center justify-between p-2 bg-[rgb(var(--ink-deep))] rounded border border-[rgb(var(--ink-border))]"
              data-testid={`co-instructor-${person.id}`}>
              <div>
                <p className="text-sm text-[rgb(var(--text-main))]">{displayName(person)}</p>
                <p className="text-[10px] text-[rgb(var(--text-muted))] break-all">{person.email}</p>
              </div>
              <Button onClick={() => remove(person)} disabled={busy} size="sm" variant="ghost"
                className="text-[rgb(var(--text-muted))] hover:text-red-400 text-xs"
                data-testid={`remove-co-instructor-${person.id}`}>
                Remove
              </Button>
            </div>
          ))}

          {atCap ? (
            <p className="text-[11px] text-[rgb(var(--text-dim))]">
              This course has its {staff.max_co_instructors} co-teachers. Remove one to add another.
            </p>
          ) : (
            <div className="flex flex-col sm:flex-row gap-2 pt-1">
              <Input type="email" placeholder="Co-teacher's email" value={email}
                onChange={e => setEmail(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') add(); }}
                className="flex-1 bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))] text-xs"
                data-testid="co-instructor-email" />
              <Button onClick={add} disabled={busy || !email.trim()} size="sm"
                className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-xs"
                data-testid="add-co-instructor-btn">
                {busy ? 'Adding…' : 'Add Co-teacher'}
              </Button>
            </div>
          )}

          <p className="text-[11px] text-[rgb(var(--text-dim))]">
            Co-teachers can edit lessons and take part in discussions. They cannot
            delete the course, change who can find it, or add other teachers.
            They need an Ile Ubuntu account first.
          </p>

          {error && <p className="text-[11px] text-red-400" data-testid="staff-error">{error}</p>}
          {notice && <p className="text-[11px] text-emerald-400" data-testid="staff-notice">{notice}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
