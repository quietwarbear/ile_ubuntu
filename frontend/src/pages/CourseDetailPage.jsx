import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import MarkdownEditor from '../components/course/MarkdownEditor';
import {
  ArrowLeft, BookOpenText, Plus,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiUpload, apiDelete, parseTierError } from '../lib/api';
import UpgradePrompt from '../components/UpgradePrompt';
import { CourseHeader } from '../components/course/CourseHeader';
import { LessonCard } from '../components/course/LessonCard';
import { EnrolledStudents } from '../components/course/EnrolledStudents';
import { GoogleImportDialog } from '../components/course/GoogleImportDialog';

export default function CourseDetailPage({ user }) {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [course, setCourse] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [enrollment, setEnrollment] = useState(null);
  const [inviteCode, setInviteCode] = useState(null);
  const [inviteCopied, setInviteCopied] = useState(false);
  const [progress, setProgress] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [filesMap, setFilesMap] = useState({});
  const [loading, setLoading] = useState(true);

  const [expandedLesson, setExpandedLesson] = useState(null);
  const [showAddLesson, setShowAddLesson] = useState(false);
  const [lessonForm, setLessonForm] = useState({ title: '', description: '', content: '', module_id: '', banner_url: '' });
  const [newModule, setNewModule] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadingFor, setUploadingFor] = useState(null);

  const [googleConnected, setGoogleConnected] = useState(false);
  const [importOpen, setImportOpen] = useState(null);
  const [importTab, setImportTab] = useState('slides');
  const [googleSlides, setGoogleSlides] = useState([]);
  const [googleDocs, setGoogleDocs] = useState([]);
  const [importing, setImporting] = useState(false);
  const [upgradePrompt, setUpgradePrompt] = useState(null);

  const isInstructor = ['faculty', 'elder', 'admin'].includes(user?.role) && course?.instructor_id === user?.id;
  const completedLessons = progress?.completed_lessons || [];

  const checkGoogleStatus = useCallback(async () => {
    try {
      const data = await apiGet('/api/google/status');
      setGoogleConnected(data.connected);
    } catch (e) { console.error('Google status check failed:', e); }
  }, []);

  const loadCourseData = useCallback(async () => {
    try {
      const [courseData, lessonData, enrollmentData, progressData] = await Promise.all([
        apiGet(`/api/courses/${courseId}`),
        apiGet(`/api/courses/${courseId}/lessons`),
        apiGet(`/api/courses/${courseId}/enrollment`),
        apiGet(`/api/courses/${courseId}/progress`),
      ]);
      setCourse(courseData);
      setLessons(lessonData);
      setEnrollment(enrollmentData);
      setProgress(progressData);

      const filesResult = await apiGet(`/api/files?course_id=${courseId}`);
      const fMap = {};
      (filesResult.files || []).forEach(f => {
        const lid = f.lesson_id || '_course';
        if (!fMap[lid]) fMap[lid] = [];
        fMap[lid].push(f);
      });
      setFilesMap(fMap);

      if (['faculty', 'elder', 'admin'].includes(user?.role) && courseData.instructor_id === user?.id) {
        try {
          const enrollList = await apiGet(`/api/courses/${courseId}/enrollments`);
          setEnrollments(enrollList);
        } catch (e) { console.error('Failed to load enrollments:', e); }
      }
    } catch (e) {
      console.error('Failed to load course:', e);
    } finally {
      setLoading(false);
    }
  }, [courseId, user?.role, user?.id]);

  useEffect(() => {
    loadCourseData();
    checkGoogleStatus();
  }, [loadCourseData, checkGoogleStatus]);

  const handleEnroll = async () => {
    try {
      await apiPost(`/api/courses/${courseId}/enroll`, {});
      loadCourseData();
    } catch (e) {
      // Premium course → purchase flow (web only; app stores require IAP for
      // in-app digital purchases, so native users are pointed to the website)
      const premiumMatch = /premium_required:([\d.]+)/.exec(e.message || '');
      if (premiumMatch) {
        const price = premiumMatch[1];
        const isNative = window.Capacitor?.isNativePlatform?.();
        if (isNative) {
          alert(`This is a premium course ($${price}). Premium courses can be purchased on the web at ile-ubuntu.org.`);
          return;
        }
        if (!window.confirm(`This is a premium course: $${price} (one-time). Continue to secure checkout?`)) return;
        try {
          const res = await apiPost(`/api/marketplace/courses/${courseId}/checkout`, {
            success_url: window.location.href,
            cancel_url: window.location.href,
          });
          if (res.url) window.location.href = res.url;
        } catch (err) {
          alert(err.message);
        }
        return;
      }
      const tierErr = parseTierError(e.message);
      if (tierErr) {
        setUpgradePrompt({ feature: 'enrollment', requiredTier: tierErr.requiredTier || 'scholar' });
      } else { alert(e.message); }
    }
  };

  const handleUnenroll = async () => {
    if (!window.confirm('Leave this course? Your progress will be lost.')) return;
    try { await apiPost(`/api/courses/${courseId}/unenroll`, {}); loadCourseData(); }
    catch (e) { alert(e.message); }
  };

  const handleCompleteLesson = async (lessonId) => {
    try { await apiPost(`/api/courses/${courseId}/lessons/${lessonId}/complete`, {}); loadCourseData(); }
    catch (e) { alert(e.message); }
  };

  const handleAddLesson = async () => {
    if (!lessonForm.title.trim()) return;
    try {
      await apiPost(`/api/courses/${courseId}/lessons`, {
        title: lessonForm.title, description: lessonForm.description,
        content: lessonForm.content, order: lessons.length + 1,
        module_id: lessonForm.module_id || null,
        banner_url: lessonForm.banner_url,
      });
      setLessonForm({ title: '', description: '', content: '', module_id: '', banner_url: '' });
      setShowAddLesson(false);
      loadCourseData();
    } catch (e) { alert(e.message); }
  };

  const handleAddModule = async () => {
    if (!newModule.trim()) return;
    try {
      await apiPost(`/api/courses/${courseId}/modules`, { title: newModule });
      setNewModule('');
      loadCourseData();
    } catch (e) { alert(e.message); }
  };

  // Curriculum order: modules (by order) each with their lessons (by order),
  // then any ungrouped lessons. Mirrors the player.
  const modules = [...(course?.modules || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  const lessonsByModule = (mid) => lessons
    .filter(l => (l.module_id || null) === mid)
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  const curriculumGroups = [
    ...modules.map(m => ({ module: m, items: lessonsByModule(m.id) })),
    ...(lessonsByModule(null).length ? [{ module: null, items: lessonsByModule(null) }] : []),
  ];
  const firstLessonId = curriculumGroups.flatMap(g => g.items)[0]?.id;
  const nextLessonId = lessons.find(l => !completedLessons.includes(l.id))?.id || firstLessonId;

  const handleUploadClick = (lessonId) => { setUploadingFor(lessonId); fileInputRef.current?.click(); };

  const handleFileSelected = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !uploadingFor) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('lesson_id', uploadingFor);
      formData.append('course_id', courseId);
      await apiUpload('/api/files/upload', formData);
      loadCourseData();
    } catch (err) { alert(err.message); }
    finally { setUploading(false); setUploadingFor(null); e.target.value = ''; }
  };

  const handleDeleteFile = async (fileId) => {
    if (!window.confirm('Delete this file?')) return;
    try { await apiDelete(`/api/files/${fileId}`); loadCourseData(); }
    catch (e) { alert(e.message); }
  };

  const handleOpenImport = async (lessonId) => {
    setImportOpen(lessonId);
    try {
      const [slidesData, docsData] = await Promise.all([apiGet('/api/google/slides'), apiGet('/api/google/docs')]);
      setGoogleSlides(slidesData.slides || []);
      setGoogleDocs(docsData.docs || []);
    } catch (e) { alert('Failed to load Google content. Please reconnect in Settings.'); }
  };

  const handleImportSlide = async (slideId, lessonId) => {
    setImporting(true);
    try { await apiPost(`/api/google/slides/${slideId}/import`, { lesson_id: lessonId, course_id: courseId }); setImportOpen(null); loadCourseData(); }
    catch (e) { alert(e.message); }
    finally { setImporting(false); }
  };

  const handleImportDoc = async (docId, lessonId) => {
    setImporting(true);
    try { await apiPost(`/api/google/docs/${docId}/import`, { lesson_id: lessonId, course_id: courseId }); setImportOpen(null); loadCourseData(); }
    catch (e) { alert(e.message); }
    finally { setImporting(false); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!course) {
    return (
      <div className="text-center py-20">
        <p className="text-[#94A3B8]">Course not found</p>
        <Button onClick={() => navigate('/courses')} variant="ghost" className="mt-4 text-[#D4AF37]">Back to Courses</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="course-detail-page">
      <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileSelected}
        accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.jpg,.jpeg,.png,.gif" data-testid="file-upload-input" />

      <button onClick={() => navigate('/courses')}
        className="flex items-center gap-2 text-sm text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
        data-testid="back-to-courses">
        <ArrowLeft size={16} /> Back to Courses
      </button>

      <CourseHeader
        course={course} lessons={lessons} enrollment={enrollment} progress={progress}
        user={user} isInstructor={isInstructor}
        onEnroll={handleEnroll} onUnenroll={handleUnenroll}
      />

      {/* Invite students (instructor only) */}
      {isInstructor && (
        <div className="p-4 rounded-md bg-[#0F172A] border border-[#1E293B]">
          {!inviteCode ? (
            <button
              onClick={async () => {
                try {
                  const res = await apiPost(`/api/courses/${courseId}/invite-code`, {});
                  setInviteCode(res.code);
                } catch (e) { alert(e.message); }
              }}
              className="text-sm text-[#D4AF37] hover:underline"
              data-testid="invite-students-btn"
            >
              Invite students to this course →
            </button>
          ) : (
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=120x120&bgcolor=15-23-42&color=212-175-55&data=${encodeURIComponent(`${window.location.origin}/join/${inviteCode}`)}`}
                alt="Course invite QR code"
                className="w-[120px] h-[120px] rounded border border-[#1E293B] flex-shrink-0"
              />
              <div className="flex-1 min-w-0 text-center sm:text-left">
                <p className="text-xs tracking-[0.15em] uppercase text-[#D4AF37] mb-1">Invite link</p>
                <p className="text-sm text-[#F8FAFC] break-all">{window.location.origin}/join/{inviteCode}</p>
                <p className="text-xs text-[#94A3B8] mt-1">
                  Share the link or let students scan the code. Anyone with it can join
                  {course.is_premium && course.premium_price > 0 ? ' after purchasing' : ''} — even if the course is unlisted.
                </p>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(`${window.location.origin}/join/${inviteCode}`);
                    setInviteCopied(true);
                    setTimeout(() => setInviteCopied(false), 2000);
                  }}
                  className="mt-2 px-3 py-1.5 rounded text-xs bg-[#D4AF37]/15 text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/25"
                  data-testid="copy-invite-link"
                >
                  {inviteCopied ? 'Copied!' : 'Copy link'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Curriculum */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37]">Curriculum</h2>
          <div className="flex items-center gap-2">
            {(enrollment?.enrolled || isInstructor) && firstLessonId && (
              <Button size="sm" onClick={() => navigate(`/courses/${courseId}/learn/${nextLessonId}`)}
                className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="start-learning">
                {completedLessons.length > 0 ? 'Continue learning' : 'Start learning'}
              </Button>
            )}
            {isInstructor && (
              <Button size="sm" variant="ghost" onClick={() => setShowAddLesson(!showAddLesson)}
                className="text-[#D4AF37] hover:text-[#F3E5AB] text-xs" data-testid="add-lesson-toggle">
                <Plus size={14} className="mr-1" /> Add Lesson
              </Button>
            )}
          </div>
        </div>

        {/* Instructor: modules (sections) */}
        {isInstructor && (
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <span className="text-[10px] tracking-[0.15em] uppercase text-[#475569]">Sections:</span>
            {modules.map(m => (
              <span key={m.id} className="text-[11px] text-[#94A3B8] bg-[#0F172A] border border-[#1E293B] rounded-full px-2.5 py-1">{m.title}</span>
            ))}
            <input
              value={newModule}
              onChange={e => setNewModule(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAddModule()}
              placeholder="New section…"
              className="px-2.5 py-1 rounded-full bg-[#050814] border border-[#1E293B] text-[11px] text-[#F8FAFC] placeholder-[#475569] focus:outline-none focus:border-[#D4AF37]/50 w-32"
              data-testid="new-module-input"
            />
            <button onClick={handleAddModule} className="text-[#D4AF37] hover:text-[#F3E5AB]" title="Add section"><Plus size={14} /></button>
          </div>
        )}

        {showAddLesson && isInstructor && (
          <Card className="bg-[#0F172A] border-[#D4AF37]/30 mb-4">
            <CardContent className="p-4 space-y-3">
              <Input placeholder="Lesson Title" value={lessonForm.title}
                onChange={e => setLessonForm({ ...lessonForm, title: e.target.value })}
                className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="new-lesson-title" />
              <Input placeholder="Brief description" value={lessonForm.description}
                onChange={e => setLessonForm({ ...lessonForm, description: e.target.value })}
                className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="new-lesson-desc" />
              <MarkdownEditor
                value={lessonForm.content}
                onChange={(v) => setLessonForm({ ...lessonForm, content: v })}
                placeholder="Lesson content — write, and use the toolbar to insert images, video, PDFs, links…"
                testId="new-lesson-content"
              />
              <div className="flex flex-col sm:flex-row gap-2">
                <select value={lessonForm.module_id}
                  onChange={e => setLessonForm({ ...lessonForm, module_id: e.target.value })}
                  className="flex-1 px-3 py-2 rounded-md bg-[#050814] border border-[#1E293B] text-xs text-[#F8FAFC] focus:outline-none focus:border-[#D4AF37]/50"
                  data-testid="new-lesson-module">
                  <option value="">No section</option>
                  {modules.map(m => <option key={m.id} value={m.id}>{m.title}</option>)}
                </select>
                <Input placeholder="Banner image URL (optional)" value={lessonForm.banner_url}
                  onChange={e => setLessonForm({ ...lessonForm, banner_url: e.target.value })}
                  className="flex-1 bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs" data-testid="new-lesson-banner" />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleAddLesson} size="sm" className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="submit-lesson-btn">Create Lesson</Button>
                <Button onClick={() => setShowAddLesson(false)} size="sm" variant="ghost" className="text-[#94A3B8] text-xs">Cancel</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {lessons.length === 0 ? (
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-8 text-center">
              <BookOpenText size={36} weight="duotone" className="text-[#94A3B8] mx-auto mb-3" />
              <p className="text-sm text-[#94A3B8]">No lessons have been added yet.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {curriculumGroups.map((group, gi) => (
              <div key={group.module?.id || `ungrouped-${gi}`}>
                {group.module && (
                  <p className="text-[11px] tracking-[0.15em] uppercase text-[#94A3B8] mb-2 mt-2">{group.module.title}</p>
                )}
                <div className="space-y-2">
                  {group.items.map((lesson) => (
                    <LessonCard
                      key={lesson.id}
                      lesson={lesson}
                      idx={lessons.findIndex(l => l.id === lesson.id)}
                      isEnrolled={enrollment?.enrolled}
                      isLessonCompleted={completedLessons.includes(lesson.id)}
                      isExpanded={expandedLesson === lesson.id}
                      isInstructor={isInstructor}
                      lessonFiles={filesMap[lesson.id] || []}
                      googleConnected={googleConnected}
                      uploading={uploading}
                      uploadingFor={uploadingFor}
                      onToggleExpand={(id) => setExpandedLesson(expandedLesson === id ? null : id)}
                      onComplete={handleCompleteLesson}
                      onUploadClick={handleUploadClick}
                      onDeleteFile={handleDeleteFile}
                      onOpenImport={handleOpenImport}
                      courseId={courseId}
                      user={user}
                      onReloadCourse={loadCourseData}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {isInstructor && <EnrolledStudents enrollments={enrollments} />}

      <GoogleImportDialog
        importOpen={importOpen} importTab={importTab}
        googleSlides={googleSlides} googleDocs={googleDocs} importing={importing}
        onClose={() => setImportOpen(null)} onSetTab={setImportTab}
        onImportSlide={handleImportSlide} onImportDoc={handleImportDoc}
      />

      {upgradePrompt && (
        <UpgradePrompt feature={upgradePrompt.feature} requiredTier={upgradePrompt.requiredTier}
          onClose={() => setUpgradePrompt(null)} />
      )}
    </div>
  );
}
