import React from 'react';
import { Card, CardContent } from '../../components/ui/card';

function getFirstName(name = '', email = '') {
  const trimmedName = name.trim();
  if (trimmedName) return trimmedName.split(/\s+/)[0];
  return email.split('@')[0] || 'Student';
}

export function EnrolledStudents({ enrollments }) {
  if (!enrollments.length) return null;

  return (
    <div>
      <h2 className="text-xs tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-4">
        Enrolled Students ({enrollments.length})
      </h2>
      <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
        <CardContent className="p-4 space-y-2">
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
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
