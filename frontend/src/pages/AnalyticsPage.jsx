import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
  ChartBar, Users, BookOpenText, UsersThree, ShieldCheck,
  Archive, ChatCircle, VideoCamera, TrendUp, Trophy, Crown,
  GraduationCap, Heartbeat, Export,
} from '@phosphor-icons/react';
import { apiGet, BACKEND_URL } from '../lib/api';

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [trends, setTrends] = useState([]);

  useEffect(() => {
    Promise.all([
      apiGet('/api/analytics/dashboard'),
      apiGet('/api/analytics/enrollment-trends?days=14'),
    ]).then(([d, t]) => {
      setData(d);
      setTrends(t || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="analytics-loading">
        <div className="w-6 h-6 border-2 border-[rgb(var(--gold))] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div className="text-center py-16" data-testid="analytics-restricted">
        <ShieldCheck size={48} weight="duotone" className="text-[rgb(var(--text-muted))] mx-auto mb-3" />
        <p className="text-[rgb(var(--text-muted))]">Analytics require faculty or higher access.</p>
      </div>
    );
  }

  const { overview, enrollment, courses, cohorts, community } = data;

  const statCards = [
    { label: 'Total Users', value: overview.total_users, icon: Users, color: 'text-blue-400' },
    { label: 'Active Courses', value: overview.active_courses, icon: BookOpenText, color: 'text-emerald-400' },
    { label: 'Enrollments', value: enrollment.total, icon: GraduationCap, color: 'text-[rgb(var(--gold))]' },
    { label: 'Completion Rate', value: `${enrollment.completion_rate}%`, icon: TrendUp, color: 'text-violet-400' },
    { label: 'Live Now', value: overview.live_now, icon: VideoCamera, color: 'text-red-400' },
    { label: 'Cohorts', value: overview.total_cohorts, icon: UsersThree, color: 'text-cyan-400' },
    { label: 'Community Posts', value: overview.total_posts, icon: ChatCircle, color: 'text-pink-400' },
    { label: 'Archives', value: overview.total_archives, icon: Archive, color: 'text-amber-400' },
  ];

  return (
    <div className="space-y-6" data-testid="analytics-page">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <ChartBar size={20} weight="duotone" className="text-[rgb(var(--gold))]" />
          <h1 className="text-xl text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Analytics Dashboard
          </h1>
        </div>
        <p className="text-xs text-[rgb(var(--text-muted))]">Platform performance at a glance</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="stat-cards">
        {statCards.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.label} className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <Icon size={18} weight="duotone" className={s.color} />
                  <span className="text-lg font-semibold text-[rgb(var(--text-main))]">{s.value}</span>
                </div>
                <p className="text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-wider">{s.label}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Enrollment Trend Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-[rgb(var(--gold))]">{enrollment.new_this_week}</p>
            <p className="text-[10px] text-[rgb(var(--text-muted))] mt-1">New This Week</p>
          </CardContent>
        </Card>
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-emerald-400">{enrollment.new_this_month}</p>
            <p className="text-[10px] text-[rgb(var(--text-muted))] mt-1">New This Month</p>
          </CardContent>
        </Card>
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-violet-400">{enrollment.completed}</p>
            <p className="text-[10px] text-[rgb(var(--text-muted))] mt-1">Completions</p>
          </CardContent>
        </Card>
      </div>

      {/* Enrollment Trend Chart (last 14 days) */}
      {trends.length > 0 && (
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm text-[rgb(var(--text-main))] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                <TrendUp size={16} weight="duotone" className="text-emerald-400" /> Enrollment Trend (14 days)
              </CardTitle>
              <Button
                size="sm" variant="outline"
                className="h-7 text-[10px] border-[rgb(var(--ink-border))] text-[rgb(var(--text-muted))]"
                onClick={() => {
                  window.open(`${BACKEND_URL}/api/analytics/export/csv`, '_blank');
                }}
                data-testid="export-csv-btn"
              >
                <Export size={12} className="mr-1" /> Export CSV
              </Button>
            </div>
          </CardHeader>
          <CardContent data-testid="enrollment-trend-chart">
            <div className="flex items-end gap-[3px] h-24">
              {(() => {
                const maxVal = Math.max(...trends.map(t => t.enrollments), 1);
                return trends.map((t) => (
                  <div key={t.date} className="flex-1 flex flex-col items-center gap-1 group relative">
                    <div
                      className="w-full bg-[rgb(var(--gold)/0.8)] rounded-t-sm transition-all hover:bg-[rgb(var(--gold))] min-h-[2px]"
                      style={{ height: `${Math.max((t.enrollments / maxVal) * 80, 2)}px` }}
                    />
                    <span className="text-[7px] text-[rgb(var(--text-faint))] group-hover:text-[rgb(var(--text-muted))]">
                      {t.date.slice(5)}
                    </span>
                    <div className="absolute -top-5 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded px-1.5 py-0.5 text-[8px] text-[rgb(var(--gold))] opacity-0 group-hover:opacity-100 pointer-events-none">
                      {t.enrollments}
                    </div>
                  </div>
                ));
              })()}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Users by Role */}
      <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Users by Role
          </CardTitle>
        </CardHeader>
        <CardContent data-testid="users-by-role">
          <div className="flex gap-2 flex-wrap">
            {Object.entries(overview.users_by_role).map(([role, count]) => (
              <div key={role} className="flex items-center gap-2 p-2 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md">
                <Badge className="bg-[rgb(var(--gold)/0.1)] text-[rgb(var(--gold))] border-[rgb(var(--gold)/0.2)] text-[9px]">{role}</Badge>
                <span className="text-sm text-[rgb(var(--text-main))] font-semibold">{count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Course Performance */}
      <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-[rgb(var(--text-main))] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <Trophy size={16} weight="duotone" className="text-[rgb(var(--gold))]" /> Course Performance
          </CardTitle>
        </CardHeader>
        <CardContent data-testid="course-performance">
          {courses.length === 0 ? (
            <p className="text-xs text-[rgb(var(--text-muted))]">No courses yet.</p>
          ) : (
            <div className="space-y-2">
              {courses.slice(0, 10).map((c, i) => (
                <div key={c.id} className="flex items-center gap-3 p-2 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md" data-testid={`course-stat-${c.id}`}>
                  <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0" style={{
                    background: i === 0 ? 'rgb(var(--gold)/0.15)' : 'rgb(var(--ink-border)/0.5)',
                    border: i === 0 ? '1px solid rgb(var(--gold)/0.3)' : '1px solid rgb(var(--ink-border)/1)',
                  }}>
                    {i === 0 ? <Crown size={12} weight="fill" className="text-[rgb(var(--gold))]" /> : <span className="text-[9px] text-[rgb(var(--text-muted))]">{i + 1}</span>}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-[rgb(var(--text-main))] truncate">{c.title}</p>
                    <div className="flex items-center gap-3 mt-1 text-[9px] text-[rgb(var(--text-muted))]">
                      <span>{c.enrolled_count} enrolled</span>
                      <span>{c.lesson_count} lessons</span>
                      <span>{c.completions} completed</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="w-16 h-2 bg-[rgb(var(--ink-secondary))] rounded-full overflow-hidden">
                      <div className="h-full bg-[rgb(var(--gold))] rounded-full" style={{ width: `${Math.max(c.avg_progress, 2)}%` }} />
                    </div>
                    <span className="text-[10px] text-[rgb(var(--text-muted))] w-8 text-right">{c.avg_progress}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Cohort Comparison + Community Side by Side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Cohort Comparison */}
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Cohort Comparison
            </CardTitle>
          </CardHeader>
          <CardContent data-testid="cohort-comparison">
            {cohorts.length === 0 ? (
              <p className="text-xs text-[rgb(var(--text-muted))]">No cohorts yet.</p>
            ) : (
              <div className="space-y-2">
                {cohorts.map((ch) => (
                  <div key={ch.id} className="p-2 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-[rgb(var(--text-main))]">{ch.name}</span>
                      <span className="text-[9px] text-[rgb(var(--gold))]">{ch.member_count} members</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-[rgb(var(--ink-secondary))] rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-400 rounded-full" style={{ width: `${Math.max(ch.avg_progress, 2)}%` }} />
                      </div>
                      <span className="text-[10px] text-[rgb(var(--text-muted))]">{ch.avg_progress}% avg</span>
                    </div>
                    <p className="text-[9px] text-[rgb(var(--text-muted))] mt-1">{ch.linked_courses} linked courses</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Community Activity */}
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-[rgb(var(--text-main))] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              <Heartbeat size={16} weight="duotone" className="text-pink-400" /> Community Activity
            </CardTitle>
          </CardHeader>
          <CardContent data-testid="community-activity">
            <div className="grid grid-cols-3 gap-2 mb-3">
              <div className="p-2 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md text-center">
                <p className="text-sm font-bold text-[rgb(var(--text-main))]">{community.total_posts}</p>
                <p className="text-[9px] text-[rgb(var(--text-muted))]">Posts</p>
              </div>
              <div className="p-2 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md text-center">
                <p className="text-sm font-bold text-[rgb(var(--text-main))]">{community.total_replies}</p>
                <p className="text-[9px] text-[rgb(var(--text-muted))]">Replies</p>
              </div>
              <div className="p-2 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md text-center">
                <p className="text-sm font-bold text-[rgb(var(--text-main))]">{community.total_likes}</p>
                <p className="text-[9px] text-[rgb(var(--text-muted))]">Likes</p>
              </div>
            </div>
            {community.top_contributors.length > 0 && (
              <>
                <p className="text-[9px] text-[rgb(var(--gold))] uppercase tracking-wider mb-2">Top Contributors</p>
                <div className="space-y-1">
                  {community.top_contributors.map((c) => (
                    <div key={c.name} className="flex items-center justify-between p-1.5 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded">
                      <span className="text-xs text-[rgb(var(--text-main))]">{c.name}</span>
                      <Badge className="bg-[rgb(var(--gold)/0.1)] text-[rgb(var(--gold))] border-[rgb(var(--gold)/0.2)] text-[9px]">{c.posts} posts</Badge>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
