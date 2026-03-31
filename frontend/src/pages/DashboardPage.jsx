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
} from '@phosphor-icons/react';
import { apiGet } from '../lib/api';

const StatCard = ({ label, value, icon: Icon, color, to }) => {
  const navigate = useNavigate();
  return (
    <Card
      className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/30 transition-all duration-300 cursor-pointer hover:-translate-y-0.5"
      onClick={() => navigate(to)}
      data-testid={`stat-${label.toLowerCase()}`}
    >
      <CardContent className="p-5 flex items-center justify-between">
        <div>
          <p className="text-xs tracking-[0.15em] uppercase text-[#94A3B8] mb-1">{label}</p>
          <p className="text-2xl font-semibold text-[#F8FAFC]">{value}</p>
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
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        const [courses, cohorts, posts, archives] = await Promise.all([
          apiGet('/api/courses'),
          apiGet('/api/cohorts'),
          apiGet('/api/community/posts'),
          apiGet('/api/archives'),
        ]);
        setStats({
          courses: courses.length,
          cohorts: cohorts.length,
          posts: posts.length,
          archives: archives.length,
        });
        setRecentCourses(courses.slice(0, 4));
      } catch (e) {
        console.error('Dashboard load error:', e);
      }
    }
    load();
  }, []);

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div className="space-y-8 animate-fade-in-up" data-testid="dashboard-page">
      {/* Welcome */}
      <div>
        <h1
          className="text-3xl sm:text-4xl font-light text-[#F8FAFC] mb-1"
          style={{ fontFamily: 'Cormorant Garamond, serif' }}
        >
          {greeting()}, {user?.name?.split(' ')[0]}
        </h1>
        <p className="text-sm text-[#94A3B8]">
          Welcome to your Living Learning Commons
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Courses" value={stats.courses} icon={BookOpenText} color="bg-[#D4AF37]/10 text-[#D4AF37]" to="/courses" />
        <StatCard label="Cohorts" value={stats.cohorts} icon={UsersThree} color="bg-blue-500/10 text-blue-400" to="/cohorts" />
        <StatCard label="Discussions" value={stats.posts} icon={Chats} color="bg-emerald-500/10 text-emerald-400" to="/community" />
        <StatCard label="Archives" value={stats.archives} icon={Archive} color="bg-purple-500/10 text-purple-400" to="/archives" />
      </div>

      {/* Recent Courses */}
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle
            className="text-lg text-[#F8FAFC]"
            style={{ fontFamily: 'Cormorant Garamond, serif' }}
          >
            Recent Courses
          </CardTitle>
          <button
            className="text-xs text-[#D4AF37] flex items-center gap-1 hover:underline"
            onClick={() => navigate('/courses')}
            data-testid="view-all-courses"
          >
            View all <ArrowRight size={12} />
          </button>
        </CardHeader>
        <CardContent className="space-y-3">
          {recentCourses.length === 0 ? (
            <p className="text-sm text-[#94A3B8] py-4 text-center">
              No courses yet. Create your first course to get started.
            </p>
          ) : (
            recentCourses.map((course) => (
              <div
                key={course.id}
                className="flex items-center justify-between p-3 rounded-md bg-[#050814] border border-[#1E293B] hover:border-[#D4AF37]/20 transition-colors cursor-pointer"
                onClick={() => navigate(`/courses`)}
                data-testid={`recent-course-${course.id}`}
              >
                <div className="flex items-center gap-3">
                  <BookOpenText size={18} weight="duotone" className="text-[#D4AF37]" />
                  <div>
                    <p className="text-sm text-[#F8FAFC]">{course.title}</p>
                    <p className="text-xs text-[#94A3B8]">by {course.instructor_name}</p>
                  </div>
                </div>
                <span className="text-[10px] tracking-wider uppercase px-2 py-0.5 rounded border border-[#1E293B] text-[#94A3B8]">
                  {course.status}
                </span>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div>
        <h3
          className="text-sm tracking-[0.15em] uppercase text-[#D4AF37] mb-3"
        >
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'New Course', icon: BookOpenText, to: '/courses' },
            { label: 'New Cohort', icon: UsersThree, to: '/cohorts' },
            { label: 'Start Discussion', icon: Chats, to: '/community' },
            { label: 'Browse Archives', icon: Archive, to: '/archives' },
          ].map((action) => (
            <button
              key={action.label}
              onClick={() => navigate(action.to)}
              className="flex items-center gap-2 p-3 rounded-md bg-[#0F172A] border border-[#1E293B] text-sm text-[#94A3B8] hover:text-[#D4AF37] hover:border-[#D4AF37]/30 transition-all"
              data-testid={`quick-${action.label.toLowerCase().replace(' ', '-')}`}
            >
              <action.icon size={16} weight="duotone" />
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
