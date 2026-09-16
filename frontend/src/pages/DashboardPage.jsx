import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  BookOpenText,
  UsersThree,
  Chats,
  Archive,
  TrendUp,
  ArrowRight,
  GraduationCap,
  Trophy,
  Certificate,
} from '@phosphor-icons/react';
import { apiGet, apiPost, BACKEND_URL } from '../lib/api';

const CHECKIN_QUESTIONS = [
  { key: 'mood', label: 'How are you feeling?' },
  { key: 'connected', label: 'How connected to your people?' },
  { key: 'confident', label: 'How confident in your path?' },
];
const FACES = ['😞', '😕', '😐', '🙂', '✨'];

function CheckInCard({ onDone }) {
  const [values, setValues] = useState({ mood: 0, connected: 0, confident: 0 });
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const ready = values.mood && values.connected && values.confident;

  const submit = async () => {
    setSaving(true);
    try {
      await apiPost('/api/checkins', { ...values, note });
      onDone();
    } catch (e) { console.error(e); setSaving(false); }
  };

  return (
    <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--gold)/0.25)]" style={{ order: 0 }} data-testid="checkin-card">
      <CardContent className="p-5">
        <p className="text-sm text-[rgb(var(--text-main))] mb-1" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
          How are you arriving today?
        </p>
        <p className="text-[10px] text-[rgb(var(--text-muted))] mb-4">
          Your educators see how you're doing — never your words. Your note stays yours.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
          {CHECKIN_QUESTIONS.map(q => (
            <div key={q.key}>
              <p className="text-[10px] text-[rgb(var(--text-muted))] mb-1.5">{q.label}</p>
              <div className="flex gap-1">
                {FACES.map((face, i) => (
                  <button
                    key={i}
                    onClick={() => setValues(v => ({ ...v, [q.key]: i + 1 }))}
                    className={`w-8 h-8 rounded text-sm flex items-center justify-center border transition-all ${
                      values[q.key] === i + 1
                        ? 'bg-[rgb(var(--gold)/0.2)] border-[rgb(var(--gold)/0.5)] scale-110'
                        : 'bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] opacity-60 hover:opacity-100'
                    }`}
                    data-testid={`checkin-${q.key}-${i + 1}`}
                  >
                    {face}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="Anything on your heart? (private, optional)"
            className="flex-1 px-3 py-1.5 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--text-main))] placeholder-[rgb(var(--text-faint))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]"
          />
          <button
            onClick={submit}
            disabled={!ready || saving}
            className={`px-4 py-1.5 rounded text-xs font-medium transition-all ${
              ready ? 'bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))]' : 'bg-[rgb(var(--ink-border))] text-[rgb(var(--text-faint))]'
            }`}
            data-testid="checkin-submit"
          >
            {saving ? '…' : 'Check in'}
          </button>
        </div>
      </CardContent>
    </Card>
  );
}

const StatCard = ({ label, value, icon: Icon, color, to }) => {
  const navigate = useNavigate();
  return (
    <Card
      className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))] hover:border-[rgb(var(--gold)/0.3)] transition-all duration-300 cursor-pointer hover:-translate-y-0.5"
      onClick={() => navigate(to)}
      data-testid={`stat-${label.toLowerCase()}`}
    >
      <CardContent className="p-5 flex items-center justify-between">
        <div>
          <p className="text-xs tracking-[0.15em] uppercase text-[rgb(var(--text-muted))] mb-1">{label}</p>
          <p className="text-2xl font-semibold text-[rgb(var(--text-main))]">{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-md flex items-center justify-center ${color}`}>
          <Icon size={22} weight="duotone" />
        </div>
      </CardContent>
    </Card>
  );
};

export default function DashboardPage({ user }) {
  const [stats, setStats] = useState({ courses: 0, cohorts: 0, posts: 0, archives: 0 });
  const [recentCourses, setRecentCourses] = useState([]);
  const [myEnrollments, setMyEnrollments] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [checkedInToday, setCheckedInToday] = useState(true); // assume done until we know
  const navigate = useNavigate();

  useEffect(() => {
    apiGet('/api/checkins/me')
      .then(r => setCheckedInToday(r.checked_in_today))
      .catch(() => {});
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const [courses, cohorts, posts, archives, enrollments, certs] = await Promise.all([
          apiGet('/api/courses'),
          apiGet('/api/cohorts'),
          apiGet('/api/community/posts'),
          apiGet('/api/archives'),
          apiGet('/api/enrollments/my-courses'),
          apiGet('/api/certificates/my-certificates'),
        ]);
        setStats({
          courses: courses.length,
          cohorts: cohorts.length,
          posts: posts.length,
          archives: archives.length,
        });
        setRecentCourses(courses.slice(0, 4));
        setCertificates(certs || []);
        setMyEnrollments(enrollments.slice(0, 3));
      } catch (e) {
        console.error('Dashboard load error:', e);
      }
    }
    load();
  }, []); // eslint-disable-line -- mount-only data fetch

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  // Role-aware content (product eval §3): learners see learner language and
  // learner actions; course creation stays with faculty/elder/admin.
  const isFaculty = ['admin', 'elder', 'faculty'].includes(user?.role);

  const quickActions = isFaculty
    ? [
        { label: 'New Course', icon: BookOpenText, to: '/courses' },
        { label: 'New Cohort', icon: UsersThree, to: '/cohorts' },
        { label: 'Start Discussion', icon: Chats, to: '/community' },
        { label: 'Browse Archives', icon: Archive, to: '/archives' },
      ]
    : [
        { label: 'Browse Courses', icon: BookOpenText, to: '/courses' },
        { label: 'Join a Cohort', icon: UsersThree, to: '/cohorts' },
        { label: 'Start Discussion', icon: Chats, to: '/community' },
        { label: 'Browse Archives', icon: Archive, to: '/archives' },
      ];

  return (
    <div className="flex flex-col gap-8 animate-fade-in-up" data-testid="dashboard-page">
      {/* Welcome */}
      <div>
        <h1
          className="text-3xl sm:text-4xl font-light text-[rgb(var(--text-main))] mb-1"
          style={{ fontFamily: 'Cormorant Garamond, serif' }}
        >
          {greeting()}, {user?.name?.split(' ')[0]}
        </h1>
        <p className="text-sm text-[rgb(var(--text-muted))]">
          Welcome to your Living Learning Commons
        </p>
      </div>

      {/* Daily check-in (everyone — wellness is for the whole village) */}
      {!checkedInToday && <CheckInCard onDone={() => setCheckedInToday(true)} />}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" style={{ order: 1 }}>
        <StatCard label="Courses" value={stats.courses} icon={BookOpenText} color="bg-[rgb(var(--gold)/0.1)] text-[rgb(var(--gold))]" to="/courses" />
        <StatCard label="Cohorts" value={stats.cohorts} icon={UsersThree} color="bg-blue-500/10 text-blue-400" to="/cohorts" />
        <StatCard label="Discussions" value={stats.posts} icon={Chats} color="bg-emerald-500/10 text-emerald-400" to="/community" />
        <StatCard label="Archives" value={stats.archives} icon={Archive} color="bg-purple-500/10 text-purple-400" to="/archives" />
      </div>

      {/* Recent/Explore Courses */}
      {/* Faculty see their recent courses first; learners see their own learning first */}
      <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]" style={{ order: isFaculty ? 2 : 3 }}>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle
            className="text-lg text-[rgb(var(--text-main))]"
            style={{ fontFamily: 'Cormorant Garamond, serif' }}
          >
            {isFaculty ? 'Recent Courses' : 'Explore Courses'}
          </CardTitle>
          <button
            className="text-xs text-[rgb(var(--gold))] flex items-center gap-1 hover:underline"
            onClick={() => navigate('/courses')}
            data-testid="view-all-courses"
          >
            View all <ArrowRight size={12} />
          </button>
        </CardHeader>
        <CardContent className="space-y-3">
          {recentCourses.length === 0 ? (
            <p className="text-sm text-[rgb(var(--text-muted))] py-4 text-center">
              {isFaculty
                ? 'No courses yet. Create your first course to get started.'
                : 'No courses are open yet. Your community’s offerings will appear here.'}
            </p>
          ) : (
            recentCourses.map((course) => (
              <div
                key={course.id}
                className="flex items-center justify-between p-3 rounded-md bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] hover:border-[rgb(var(--gold)/0.2)] transition-colors cursor-pointer"
                onClick={() => navigate(`/courses`)}
                data-testid={`recent-course-${course.id}`}
              >
                <div className="flex items-center gap-3">
                  <BookOpenText size={18} weight="duotone" className="text-[rgb(var(--gold))]" />
                  <div>
                    <p className="text-sm text-[rgb(var(--text-main))]">{course.title}</p>
                    <p className="text-xs text-[rgb(var(--text-muted))]">by {course.instructor_name}</p>
                  </div>
                </div>
                <span className="text-[10px] tracking-wider uppercase px-2 py-0.5 rounded border border-[rgb(var(--ink-border))] text-[rgb(var(--text-muted))]">
                  {course.status}
                </span>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* My Learning */}
      {myEnrollments.length > 0 && (
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]" style={{ order: isFaculty ? 3 : 2 }}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle
              className="text-lg text-[rgb(var(--text-main))] flex items-center gap-2"
              style={{ fontFamily: 'Cormorant Garamond, serif' }}
            >
              <GraduationCap size={20} weight="duotone" className="text-[rgb(var(--gold))]" />
              My Learning
            </CardTitle>
            <button
              className="text-xs text-[rgb(var(--gold))] flex items-center gap-1 hover:underline"
              onClick={() => navigate('/courses')}
              data-testid="view-my-learning"
            >
              View all <ArrowRight size={12} />
            </button>
          </CardHeader>
          <CardContent className="space-y-3">
            {myEnrollments.map(enrollment => (
              <div
                key={enrollment.id}
                className="flex items-center gap-3 p-3 rounded-md bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] hover:border-[rgb(var(--gold)/0.2)] transition-colors cursor-pointer"
                onClick={() => navigate(`/courses/${enrollment.course_id}`)}
                data-testid={`dash-enrollment-${enrollment.course_id}`}
              >
                <div className="relative w-10 h-10 flex-shrink-0">
                  <svg className="w-10 h-10 -rotate-90" viewBox="0 0 40 40">
                    <circle cx="20" cy="20" r="16" fill="none" stroke="rgb(var(--ink-border))" strokeWidth="2.5" />
                    <circle cx="20" cy="20" r="16" fill="none" stroke="rgb(var(--gold))" strokeWidth="2.5"
                      strokeDasharray={`${(enrollment.progress || 0) * 1.005} 100.5`} strokeLinecap="round" />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    {enrollment.status === 'completed' ? (
                      <Trophy size={12} weight="fill" className="text-[rgb(var(--gold))]" />
                    ) : (
                      <span className="text-[9px] font-semibold text-[rgb(var(--text-main))]">{Math.round(enrollment.progress || 0)}%</span>
                    )}
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[rgb(var(--text-main))] truncate">{enrollment.course_title}</p>
                  <p className="text-[10px] text-[rgb(var(--text-muted))]">
                    {enrollment.completed_lessons?.length || 0} / {enrollment.total_lessons} lessons
                  </p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <div style={{ order: 4 }}>
        <h3
          className="text-sm tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-3"
        >
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {quickActions.map((action) => (
            <button
              key={action.label}
              onClick={() => navigate(action.to)}
              className="flex items-center gap-2 p-3 rounded-md bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))] text-sm text-[rgb(var(--text-muted))] hover:text-[rgb(var(--gold))] hover:border-[rgb(var(--gold)/0.3)] transition-all"
              data-testid={`quick-${action.label.toLowerCase().replace(' ', '-')}`}
            >
              <action.icon size={16} weight="duotone" />
              {action.label}
            </button>
          ))}
        </div>
      </div>
      {/* My Certificates */}
      {certificates.length > 0 && (
        <div data-testid="my-certificates" style={{ order: 5 }}>
          <div className="flex items-center gap-2 mb-3">
            <Certificate size={16} weight="duotone" className="text-[rgb(var(--gold))]" />
            <h2 className="text-xs tracking-[0.15em] uppercase text-[rgb(var(--gold))]">My Certificates</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {certificates.map(cert => (
              <Card key={cert.course_id} className="bg-[rgb(var(--ink-card))] border-[rgb(var(--gold)/0.2)]">
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-[rgb(var(--text-main))] truncate">{cert.course_title}</p>
                    <p className="text-[9px] text-[rgb(var(--text-muted))] mt-0.5">
                      Completed {cert.completed_at ? new Date(cert.completed_at).toLocaleDateString() : ''}
                    </p>
                  </div>
                  <a
                    href={`${BACKEND_URL}/api/certificates/download/${cert.course_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-3 px-3 py-1.5 bg-[rgb(var(--gold)/0.1)] border border-[rgb(var(--gold)/0.3)] text-[rgb(var(--gold))] rounded text-[10px] hover:bg-[rgb(var(--gold)/0.2)] transition-all flex-shrink-0"
                    data-testid={`cert-download-${cert.course_id}`}
                  >
                    Download
                  </a>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
