import React from 'react';
import { Card, CardContent } from '../../components/ui/card';

export function EnrolledStudents({ enrollments }) {
  if (!enrollments.length) return null;

  return (
    <div>
      <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37] mb-4">
        Enrolled Students ({enrollments.length})
      </h2>
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardContent className="p-4 space-y-2">
          {enrollments.map(e => (
            <div key={e.id} className="flex items-center justify-between p-2 bg-[#050814] rounded border border-[#1E293B]" data-testid={`enrollment-${e.id}`}>
              <div>
                <p className="text-sm text-[#F8FAFC]">{e.user_name}</p>
                <p className="text-[10px] text-[#94A3B8]">
                  Enrolled {new Date(e.enrolled_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-16 h-1.5 bg-[#050814] rounded-full overflow-hidden border border-[#1E293B]">
                  <div className="h-full bg-[#D4AF37] rounded-full" style={{ width: `${e.progress || 0}%` }} />
                </div>
                <span className="text-[10px] text-[#94A3B8] w-8 text-right">{Math.round(e.progress || 0)}%</span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
