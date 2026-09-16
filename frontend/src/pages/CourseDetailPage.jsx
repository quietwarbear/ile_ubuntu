import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import WysiwygEditor from '../components/course/WysiwygEditor';
import {
  ArrowLeft, BookOpenText, Plus, DotsSixVertical,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiUpload, apiDelete, parseTierError, apiPut } from '../lib/api';
import UpgradePrompt from '../components/UpgradePrompt';
import { CourseHeader } from '../components/course/CourseHeader';
import { LessonCard } from '../components/course/LessonCard';
import { EnrolledStudents } from '../components/course/EnrolledStudents';
import { CourseStaffPanel } from '../components/course/CourseStaffPanel';
import { CourseDiscussion } from '../components/course/CourseDiscussion';
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
  const [lessonForm, setLessonForm] = useState({ title: '', description: '', content: '', module_id: '', banner_url: '', hidden: false, available_at: '' });
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

  // Course staff = the owning instructor plus assigned co-teachers. Gating on
  // instructor_id alone locked co-teachers out of every teaching control.
  const isInstructor = ['faculty', 'elder', 'admin'].includes(user?.role)
    && (course?.instructor_id === user?.id || (course?.co_instructor_ids || []).includes(user?.id));
  // Only the owner staffs the course — a co-teacher cannot appoint others.
  const isOwner = !!course && course.instructor_id === user?.id;
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
        hidden: lessonForm.hidden,
        // datetime-local has no timezone; send the browser's actual instant.
        available_at: lessonForm.available_at
          ? new Date(lessonForm.available_at).toISOString()
          : null,
      });
      setLessonForm({ title: '', description: '', content: '', module_id: '', banner_url: '', hidden: false, available_at: '' });
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
  // Drag-to-reorder (instructors): drop rewrites the whole flat order and
  // persists it in one call; module membership is not changed by dragging.
  const [draggedLessonId, setDraggedLessonId] = useState(null);
  const handleLessonDrop = async (targetId) => {
    const dragged = draggedLessonId;
    setDraggedLessonId(null);
    if (!dragged || dragged === targetId) return;
    const flat = curriculumGroups.flatMap(g => g.items).map(l => l.id);
    const from = flat.indexOf(dragged);
    const to = flat.indexOf(targetId);
    if (from < 0 || to < 0) return;
    flat.splice(from, 1);
    flat.splice(to, 0, dragged);
    // Optimistic: the list snaps into place immediately; reload on failure.
    setLessons(ls => ls.map(l => ({ ...l, order: flat.indexOf(l.id) })));
    try {
      await apiPut(`/api/courses/${courseId}/lessons-reorder`, { lesson_ids: flat });
    } catch (err) {
      alert(err.message);
      loadCourseData();
    }
  };

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
        <div className="w-8 h-8 border-2 border-[rgb(var(--gold))] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!course) {
    return (
      <div className="text-center py-20">
        <p className="text-[rgb(var(--text-muted))]">Course not found</p>
        <Button onClick={() => navigate('/courses')} variant="ghost" className="mt-4 text-[rgb(var(--gold))]">Back to Courses</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="course-detail-page">
      <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileSelected}
        accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.jpg,.jpeg,.png,.gif" data-testid="file-upload-input" />

      <button onClick={() => navigate('/courses')}
        className="flex items-center gap-2 text-sm text-[rgb(var(--text-muted))] hover:text-[rgb(var(--gold))] transition-colors"
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
        <div className="p-4 rounded-md bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))]">
          {!inviteCode ? (
            <button
              onClick={async () => {
                try {
                  const res = await apiPost(`/api/courses/${courseId}/invite-code`, {});
                  setInviteCode(res.code);
                } catch (e) { alert(e.message); }
              }}
              className="text-sm text-[rgb(var(--gold))] hover:underline"
              data-testid="invite-students-btn"
            >
              Invite students to this course →
            </button>
          ) : (
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=120x120&bgcolor=15-23-42&color=212-175-55&data=${encodeURIComponent(`${window.location.origin}/join/${inviteCode}`)}`}
                alt="Course invite QR code"
                className="w-[120px] h-[120px] rounded border border-[rgb(var(--ink-border))] flex-shrink-0"
              />
              <div className="flex-1 min-w-0 text-center sm:text-left">
                <p className="text-xs tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-1">Invite link</p>
                <p className="text-sm text-[rgb(var(--text-main))] break-all">{window.location.origin}/join/{inviteCode}</p>
                <p className="text-xs text-[rgb(var(--text-muted))] mt-1">
                  Share the link or let students scan the code. Anyone with it can join
                  {course.is_premium && course.premium_price > 0 ? ' after purchasing' : ''} — even if the course is unlisted.
                </p>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(`${window.location.origin}/join/${inviteCode}`);
                    setInviteCopied(true);
                    setTimeout(() => setInviteCopied(false), 2000);
                  }}
                  className="mt-2 px-3 py-1.5 rounded text-xs bg-[rgb(var(--gold)/0.15)] text-[rgb(var(--gold))] border border-[rgb(var(--gold)/0.3)] hover:bg-[rgb(var(--gold)/0.25)]"
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
          <h2 className="text-xs tracking-[0.15em] uppercase text-[rgb(var(--gold))]">Curriculum</h2>
          <div className="flex items-center gap-2">
            {(enrollment?.enrolled || isInstructor) && firstLessonId && (
              <Button size="sm" onClick={() => navigate(`/courses/${courseId}/learn/${nextLessonId}`)}
                className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-xs" data-testid="start-learning">
                {completedLessons.length > 0 ? 'Continue learning' : 'Start learning'}
              </Button>
            )}
            {isInstructor && (
              <Button size="sm" variant="ghost" onClick={() => setShowAddLesson(!showAddLesson)}
                className="text-[rgb(var(--gold))] hover:text-[rgb(var(--gold-soft))] text-xs" data-testid="add-lesson-toggle">
                <Plus size={14} className="mr-1" /> Add Lesson
              </Button>
            )}
          </div>
        </div>

        {/* Instructor: modules (sections) */}
        {isInstructor && (
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <span className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--text-faint))]">Sections:</span>
            {modules.map(m => (
              <span key={m.id} className="text-[11px] text-[rgb(var(--text-muted))] bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))] rounded-full px-2.5 py-1">{m.title}</span>
            ))}
            <input
              value={newModule}
              onChange={e => setNewModule(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAddModule()}
              placeholder="New section…"
              className="px-2.5 py-1 rounded-full bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-[11px] text-[rgb(var(--text-main))] placeholder-[rgb(var(--text-faint))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)] w-32"
              data-testid="new-module-input"
            />
            <button onClick={handleAddModule} className="text-[rgb(var(--gold))] hover:text-[rgb(var(--gold-soft))]" title="Add section"><Plus size={14} /></button>
          </div>
        )}

        {showAddLesson && isInstructor && (
          <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--gold)/0.3)] mb-4">
            <CardContent className="p-4 space-y-3">
              <Input placeholder="Lesson Title" value={lessonForm.title}
                onChange={e => setLessonForm({ ...lessonForm, title: e.target.value })}
                className="bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))]" data-testid="new-lesson-title" />
              <Input placeholder="Brief description" value={lessonForm.description}
                onChange={e => setLessonForm({ ...lessonForm, description: e.target.value })}
                className="bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))]" data-testid="new-lesson-desc" />
              <WysiwygEditor
                value={lessonForm.content}
                onChange={(v) => setLessonForm({ ...lessonForm, content: v })}
                placeholder="Write the lesson — format with the toolbar, insert images, video, PDFs, links…"
                testId="new-lesson-content"
              />
              <div className="flex flex-col sm:flex-row gap-2">
                <select value={lessonForm.module_id}
                  onChange={e => setLessonForm({ ...lessonForm, module_id: e.target.value })}
                  className="flex-1 px-3 py-2 rounded-md bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--text-main))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]"
                  data-testid="new-lesson-module">
                  <option value="">No section</option>
                  {modules.map(m => <option key={m.id} value={m.id}>{m.title}</option>)}
                </select>
                <Input placeholder="Banner image URL (optional)" value={lessonForm.banner_url}
                  onChange={e => setLessonForm({ ...lessonForm, banner_url: e.target.value })}
                  className="flex-1 bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))] text-xs" data-testid="new-lesson-banner" />
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-3 pt-1">
                <label className="flex items-center gap-2 text-xs text-[rgb(var(--text-muted))] cursor-pointer">
                  <input type="checkbox" checked={lessonForm.hidden}
                    onChange={e => setLessonForm({ ...lessonForm, hidden: e.target.checked })}
                    className="accent-[rgb(var(--gold))]" data-testid="new-lesson-hidden" />
                  Hide from students
                </label>
                <label className="flex flex-1 items-center gap-2 text-xs text-[rgb(var(--text-muted))]">
                  <span className="whitespace-nowrap">Release on</span>
                  <Input type="datetime-local" value={lessonForm.available_at}
                    disabled={lessonForm.hidden}
                    onChange={e => setLessonForm({ ...lessonForm, available_at: e.target.value })}
                    className="flex-1 bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))] text-xs disabled:opacity-40"
                    data-testid="new-lesson-available-at" />
                </label>
              </div>
              <p className="text-[11px] text-[rgb(var(--text-dim))]">
                {lessonForm.hidden
                  ? 'Hidden lessons stay invisible to students until you unhide them.'
                  : lessonForm.available_at
                    ? 'Students see the title and release time now, and the full lesson opens automatically.'
                    : 'Leave both blank to publish immediately.'}
              </p>
              <div className="flex gap-2">
                <Button onClick={handleAddLesson} size="sm" className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-xs" data-testid="submit-lesson-btn">Create Lesson</Button>
                <Button onClick={() => setShowAddLesson(false)} size="sm" variant="ghost" className="text-[rgb(var(--text-muted))] text-xs">Cancel</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {lessons.length === 0 ? (
          <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
            <CardContent className="p-8 text-center">
              <BookOpenText size={36} weight="duotone" className="text-[rgb(var(--text-muted))] mx-auto mb-3" />
              <p className="text-sm text-[rgb(var(--text-muted))]">No lessons have been added yet.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {curriculumGroups.map((group, gi) => (
              <div key={group.module?.id || `ungrouped-${gi}`}>
                {group.module && (
                  <p className="text-[11px] tracking-[0.15em] uppercase text-[rgb(var(--text-muted))] mb-2 mt-2">{group.module.title}</p>
                )}
                <div className="space-y-2">
                  {group.items.map((lesson) => (
                    <div
                      key={lesson.id}
                      className={`flex items-stretch gap-1 ${draggedLessonId === lesson.id ? 'opacity-40' : ''}`}
                      onDragOver={isInstructor ? (e) => e.preventDefault() : undefined}
                      onDrop={isInstructor ? (e) => { e.preventDefault(); handleLessonDrop(lesson.id); } : undefined}
                    >
                      {isInstructor && (
                        <div
                          draggable
                          onDragStart={(e) => { setDraggedLessonId(lesson.id); e.dataTransfer.effectAllowed = 'move'; }}
                          onDragEnd={() => setDraggedLessonId(null)}
                          className="flex items-center px-1 cursor-grab active:cursor-grabbing text-[#475569] hover:text-[#D4AF37]"
                          title="Drag to reorder"
                          data-testid={`lesson-drag-${lesson.id}`}
                        >
                          <DotsSixVertical size={16} weight="bold" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                    <LessonCard
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
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {(enrollment?.enrolled || isInstructor) && (
        <CourseDiscussion courseId={courseId} user={user} isStaff={isInstructor} />
      )}

      {isOwner && <CourseStaffPanel courseId={courseId} isOwner={isOwner} />}

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
