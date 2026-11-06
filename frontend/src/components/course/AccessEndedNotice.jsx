import React from 'react';
import { Card, CardContent } from '../ui/card';
import { formatAccessDate } from '../../lib/courseAccess';

// Shown in place of lessons once a person's access to a course has ended (I6).
export function AccessEndedNotice({ endedAt, courseTitle }) {
  const when = formatAccessDate(endedAt);
  return (
    <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--gold)/0.3)]" data-testid="access-ended">
      <CardContent className="p-6 text-center space-y-2">
        <h2 className="text-lg text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
          Your access has ended
        </h2>
        <p className="text-sm text-[rgb(var(--text-muted))]">
          Access to {courseTitle ? <strong>{courseTitle}</strong> : 'this course'}'s lessons and recordings
          {when ? ` ended on ${when}` : ' has ended'}. Your certificate, if you earned one, is still yours.
          If you think this is a mistake, contact the course organizer.
        </p>
      </CardContent>
    </Card>
  );
}

export default AccessEndedNotice;
