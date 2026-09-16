import React from 'react';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';
import {
  BookOpenText, Users, UserPlus, SignOut, Trophy,
} from '@phosphor-icons/react';
import { BACKEND_URL } from '../../lib/api';

export function CourseHeader({ course, lessons, enrollment, progress, user, isInstructor, onEnroll, onUnenroll }) {
  const isEnrolled = enrollment?.enrolled;
  const progressPct = progress?.progress || 0;
  const isCompleted = progress?.status === 'completed';
  const completedLessons = progress?.completed_lessons || [];

  return (
    <>
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h1
              className="text-3xl sm:text-4xl font-light text-[rgb(var(--text-main))]"
              style={{ fontFamily: 'Cormorant Garamond, serif' }}
              data-testid="course-title"
            >
              {course.title}
            </h1>
            <Badge className={`text-[10px] ${
              course.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              course.status === 'archived' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
              'bg-[rgb(var(--gold)/0.1)] text-[rgb(var(--gold))] border-[rgb(var(--gold)/0.2)]'
            }`}>
              {course.status}
            </Badge>
          </div>
          <p className="text-sm text-[rgb(var(--text-muted))] mb-3 leading-relaxed">{course.description}</p>
          <div className="flex items-center gap-4 text-xs text-[rgb(var(--text-muted))]">
            <span className="flex items-center gap-1">
              <BookOpenText size={14} className="text-[rgb(var(--gold))]" /> {lessons.length} lessons
            </span>
            <span className="flex items-center gap-1">
              <Users size={14} className="text-[rgb(var(--gold))]" /> {course.enrolled_count || 0} enrolled
            </span>
            <span>by {course.instructor_name}</span>
          </div>
          {course.tags?.length > 0 && (
            <div className="flex gap-1.5 mt-3">
              {course.tags.map(tag => (
                <span key={tag} className="text-[10px] px-2 py-0.5 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-[rgb(var(--text-muted))]">{tag}</span>
              ))}
            </div>
          )}
        </div>

        <div className="flex-shrink-0">
          {!isInstructor && course.status === 'active' && (
            isEnrolled ? (
              <div className="space-y-2 text-right">
                {isCompleted ? (
                  <div className="flex items-center gap-2 text-emerald-400 text-sm">
                    <Trophy size={18} weight="fill" /> Course Completed!
                  </div>
                ) : (
                  <div className="text-sm text-[rgb(var(--text-muted))]">
                    {Math.round(progressPct)}% complete
                  </div>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onUnenroll}
                  className="border-[rgb(var(--ink-border))] text-[rgb(var(--text-muted))] hover:text-red-400 hover:border-red-400/30 text-xs"
                  data-testid="unenroll-btn"
                >
                  <SignOut size={14} className="mr-1" /> Unenroll
                </Button>
              </div>
            ) : (
              <Button
                onClick={onEnroll}
                className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] font-medium"
                data-testid="enroll-btn"
              >
                <UserPlus size={16} className="mr-2" /> Enroll in Course
              </Button>
            )
          )}
        </div>
      </div>

      {isEnrolled && lessons.length > 0 && (
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]" data-testid="progress-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs tracking-[0.15em] uppercase text-[rgb(var(--gold))]">Your Progress</span>
              <span className="text-sm text-[rgb(var(--text-main))] font-medium">
                {completedLessons.length} / {lessons.length} lessons
              </span>
            </div>
            <div className="w-full h-2 bg-[rgb(var(--ink-deep))] rounded-full overflow-hidden">
              <div
                className="h-full bg-[rgb(var(--gold))] rounded-full transition-all duration-500"
                style={{ width: `${progressPct}%` }}
                data-testid="progress-bar"
              />
            </div>
            {progressPct >= 100 && (
              <a
                href={`${BACKEND_URL}/api/certificates/download/${course.id}`}
                className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-[rgb(var(--gold)/0.15)] border border-[rgb(var(--gold)/0.3)] text-[rgb(var(--gold))] rounded-md text-xs font-medium hover:bg-[rgb(var(--gold)/0.25)] transition-all"
                data-testid="download-certificate"
                target="_blank"
                rel="noopener noreferrer"
              >
                Download Certificate
              </a>
            )}
          </CardContent>
        </Card>
      )}
    </>
  );
}
