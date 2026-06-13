import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Navigate } from 'react-router-dom';
import {
  ArrowLeft, CheckCircle, Circle, CaretRight, List, X,
  FilePdf, File as FileIcon, DownloadSimple, Eye,
} from '@phosphor-icons/react';
import { apiGet, apiPost, BACKEND_URL } from '../lib/api';
import LessonContentViewer from '../components/LessonContentViewer';
import { LessonVideoPlayer } from '../components/course/LessonVideoPlayer';
import { LessonQuiz } from '../components/course/LessonQuiz';
import { LessonComments } from '../components/course/LessonComments';

// Order lessons the way the curriculum reads: each module (by order) with its
// lessons (by order), then any ungrouped lessons last. One flat list powers
// both the sidebar and Complete & Continue.
function buildCurriculum(course, lessons) {
  const modules = [...(course?.modules || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  const byModule = (mid) => lessons
    .filter(l => (l.module_id || null) === mid)
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  const groups = modules.map(m => ({ module: m, lessons: byModule(m.id) }));
  const ungrouped = byModule(null);
  if (ungrouped.length) groups.push({ module: null, lessons: ungrouped });
  const flat = groups.flatMap(g => g.lessons);
  return { groups, flat };
}

export default function CoursePlayerPage({ user }) {
  const { courseId, lessonId } = useParams();
  const navigate = useNavigate();

  const [course, setCourse] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [enrollment, setEnrollment] = useState(null);
  const [progress, setProgress] = useState(null);
  const [filesMap, setFilesMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [viewingPdf, setViewingPdf] = useState(null);
  const [completing, setCompleting] = useState(false);

  const isInstructor = ['faculty', 'elder', 'admin'].includes(user?.role) && course?.instructor_id === user?.id;

  const load = useCallback(async () => {
    try {
      const [c, l, e, p, files] = await Promise.all([
        apiGet(`/api/courses/${courseId}`),
        apiGet(`/api/courses/${courseId}/lessons`),
        apiGet(`/api/courses/${courseId}/enrollment`),
        apiGet(`/api/courses/${courseId}/progress`),
        apiGet(`/api/files?course_id=${courseId}`),
      ]);
      setCourse(c); setLessons(l); setEnrollment(e); setProgress(p);
      const fMap = {};
      (files.files || []).forEach(f => { (fMap[f.lesson_id || '_course'] ||= []).push(f); });
      setFilesMap(fMap);
    } catch (err) { console.error('player load failed:', err); }
    finally { setLoading(false); }
  }, [courseId]);

  useEffect(() => { load(); }, [load]);

  const { groups, flat } = useMemo(() => buildCurriculum(course, lessons), [course, lessons]);
  const completed = progress?.completed_lessons || [];
  const pct = flat.length ? Math.round((completed.filter(id => flat.some(l => l.id === id)).length / flat.length) * 100) : 0;

  const current = flat.find(l => l.id === lessonId) || flat[0];
  const currentIdx = current ? flat.findIndex(l => l.id === current.id) : -1;
  const next = currentIdx >= 0 && currentIdx < flat.length - 1 ? flat[currentIdx + 1] : null;

  // Land on the first lesson when none is specified in the URL.
  useEffect(() => {
    if (!loading && !lessonId && flat.length) {
      navigate(`/courses/${courseId}/learn/${flat[0].id}`, { replace: true });
    }
  }, [loading, lessonId, flat, courseId, navigate]);

  if (loading) return <p className="text-sm text-[#94A3B8]">Opening the course…</p>;
  if (!course) return <Navigate to="/courses" replace />;
  // Players are for enrolled learners or the instructor.
  if (!enrollment?.enrolled && !isInstructor) return <Navigate to={`/courses/${courseId}`} replace />;
  if (!current) {
    return (
      <div className="max-w-2xl">
        <button onClick={() => navigate(`/courses/${courseId}`)} className="flex items-center gap-2 text-sm text-[#94A3B8] hover:text-[#D4AF37] mb-4">
          <ArrowLeft size={16} /> Course overview
        </button>
        <p className="text-sm text-[#94A3B8]">This course has no lessons yet.</p>
      </div>
    );
  }

  const isDone = completed.includes(current.id);

  const handleCompleteContinue = async () => {
    setCompleting(true);
    try {
      if (!isDone && enrollment?.enrolled) {
        await apiPost(`/api/courses/${courseId}/lessons/${current.id}/complete`, {});
        setProgress(p => ({ ...p, completed_lessons: [...(p?.completed_lessons || []), current.id] }));
      }
      if (next) navigate(`/courses/${courseId}/learn/${next.id}`);
      else navigate(`/courses/${courseId}`);
    } catch (e) { alert(e.message); }
    setCompleting(false);
  };

  const files = filesMap[current.id] || [];

  const SidebarInner = (
    <div className="flex flex-col h-full">
      <div className="px-4 py-4 border-b border-[#1E293B]">
        <button onClick={() => navigate(`/courses/${courseId}`)} className="flex items-center gap-1.5 text-[10px] tracking-[0.15em] uppercase text-[#94A3B8] hover:text-[#D4AF37] mb-2">
          <ArrowLeft size={12} /> Overview
        </button>
        <p className="text-sm text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{course.title}</p>
        <div className="mt-2 h-1.5 rounded-full bg-[#050814] border border-[#1E293B] overflow-hidden">
          <div className="h-full bg-[#D4AF37]/70 transition-all" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-[10px] text-[#94A3B8] mt-1">{pct}% complete</p>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {groups.map((g, gi) => (
          <div key={g.module?.id || `ungrouped-${gi}`} className="mb-1">
            <p className="px-4 pt-3 pb-1 text-[9px] tracking-[0.2em] uppercase text-[#475569]">
              {g.module ? g.module.title : 'Lessons'}
            </p>
            {g.lessons.map((l, li) => {
              const done = completed.includes(l.id);
              const active = l.id === current.id;
              const num = flat.findIndex(x => x.id === l.id) + 1;
              return (
                <button
                  key={l.id}
                  onClick={() => { setSidebarOpen(false); navigate(`/courses/${courseId}/learn/${l.id}`); }}
                  className={`w-full flex items-center gap-2.5 px-4 py-2 text-left text-xs border-l-2 transition-colors ${
                    active ? 'border-[#D4AF37] bg-[#D4AF37]/5 text-[#F8FAFC]' : 'border-transparent text-[#94A3B8] hover:bg-[#0F172A] hover:text-[#F8FAFC]'
                  }`}
                  data-testid={`player-nav-${l.id}`}
                >
                  {done
                    ? <CheckCircle size={16} weight="fill" className="text-emerald-400 flex-shrink-0" />
                    : <Circle size={16} className="text-[#475569] flex-shrink-0" />}
                  <span className="flex-1 min-w-0 truncate">{num}. {l.title}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>
    </div>
  );

  return (
    <div className="flex gap-0 -mt-2" data-testid="course-player">
      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-72 flex-shrink-0 border-r border-[#1E293B] sticky top-0 h-[calc(100vh-1rem)]">
        {SidebarInner}
      </aside>

      {/* Mobile sidebar toggle + drawer */}
      <button onClick={() => setSidebarOpen(true)} className="lg:hidden fixed bottom-4 right-4 z-40 flex items-center gap-1.5 px-3 py-2 rounded-full bg-[#D4AF37] text-[#050814] text-xs shadow-lg">
        <List size={16} /> Lessons
      </button>
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="w-72 bg-[#050814] border-r border-[#1E293B] h-full">{SidebarInner}</div>
          <div className="flex-1 bg-black/60" onClick={() => setSidebarOpen(false)} />
          <button onClick={() => setSidebarOpen(false)} className="absolute top-4 right-4 text-[#94A3B8]"><X size={22} /></button>
        </div>
      )}

      {/* Main lesson panel */}
      <main className="flex-1 min-w-0 px-0 lg:px-8 max-w-3xl mx-auto animate-fade-in-up">
        <p className="text-[10px] tracking-[0.2em] uppercase text-[#D4AF37] mb-1">
          Lesson {currentIdx + 1} of {flat.length}
        </p>
        <h1 className="text-2xl text-[#F8FAFC] mb-1" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{current.title}</h1>
        {current.description && <p className="text-sm text-[#94A3B8] mb-4">{current.description}</p>}

        {/* Video first, like a course */}
        {(current.video_url || current.video_file_id || isInstructor) && (
          <div className="mb-5">
            <LessonVideoPlayer lesson={current} courseId={courseId} isInstructor={isInstructor} onUpdate={load} />
          </div>
        )}

        {/* Banner + rich content, full width */}
        {(current.content || current.banner_url) && (
          <div className="mb-5">
            <LessonContentViewer content={current.content} banner={current.banner_url} />
          </div>
        )}

        {/* Materials */}
        {files.length > 0 && (
          <div className="mb-5">
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-2">Materials</p>
            <div className="space-y-1.5">
              {files.map(file => {
                const isPdf = file.mime_type === 'application/pdf';
                const open = viewingPdf === file.id;
                return (
                  <div key={file.id}>
                    <div className="flex items-center gap-3 p-2.5 bg-[#050814] border border-[#1E293B] rounded-md">
                      {isPdf ? <FilePdf size={18} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                             : <FileIcon size={18} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />}
                      <span className="flex-1 min-w-0 text-xs text-[#F8FAFC] truncate">{file.original_filename}</span>
                      {isPdf && (
                        <button onClick={() => setViewingPdf(open ? null : file.id)} className={`p-1 ${open ? 'text-[#D4AF37]' : 'text-[#94A3B8] hover:text-[#D4AF37]'}`} title={open ? 'Close' : 'View'}>
                          {open ? <X size={14} /> : <Eye size={14} />}
                        </button>
                      )}
                      <a href={`${BACKEND_URL}/api/files/${file.id}/download`} target="_blank" rel="noopener noreferrer" className="p-1 text-[#94A3B8] hover:text-[#D4AF37]" title="Download">
                        <DownloadSimple size={14} />
                      </a>
                    </div>
                    {isPdf && open && (
                      <div className="mt-1 rounded-md overflow-hidden border border-[#1E293B]">
                        <iframe src={`${BACKEND_URL}/api/files/${file.id}/download`} className="w-full h-[600px] bg-white" title={file.original_filename} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Quiz */}
        <div className="mb-5">
          <LessonQuiz courseId={courseId} lessonId={current.id} user={user} isInstructor={isInstructor} />
        </div>

        {/* Complete & Continue */}
        <div className="flex items-center justify-between gap-3 py-5 border-t border-[#1E293B]">
          <span className="text-xs text-[#94A3B8]">
            {isDone ? 'Completed' : enrollment?.enrolled ? 'Mark this lesson complete' : 'Preview mode'}
          </span>
          <button
            onClick={handleCompleteContinue}
            disabled={completing}
            className="flex items-center gap-2 px-5 py-2.5 rounded-md bg-[#D4AF37] text-[#050814] text-sm font-medium hover:bg-[#F3E5AB] disabled:opacity-60"
            data-testid="complete-continue"
          >
            {next ? (isDone ? 'Continue' : 'Complete & Continue') : (isDone ? 'Back to overview' : 'Complete & Finish')}
            <CaretRight size={15} />
          </button>
        </div>

        {/* Discussion */}
        <div className="mb-10">
          <LessonComments courseId={courseId} lessonId={current.id} user={user} isInstructor={isInstructor} />
        </div>
      </main>
    </div>
  );
}
