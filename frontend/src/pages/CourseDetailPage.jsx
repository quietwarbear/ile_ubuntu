import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import {
  ArrowLeft,
  BookOpenText,
  CheckCircle,
  Circle,
  UserPlus,
  SignOut,
  Users,
  Trophy,
  Plus,
  Paperclip,
  DownloadSimple,
  Trash,
  File as FileIcon,
  FilePdf,
  FileDoc,
  FileXls,
  FilePpt,
  FileImage,
  CaretDown,
  CaretUp,
  GoogleLogo,
  Presentation,
  Article,
  ArrowSquareOut,
} from '@phosphor-icons/react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { apiGet, apiPost, apiUpload, apiDelete, BACKEND_URL, parseTierError } from '../lib/api';
import LessonContentViewer from '../components/LessonContentViewer';
import UpgradePrompt from '../components/UpgradePrompt';

const FILE_ICONS = {
  'application/pdf': FilePdf,
  'application/msword': FileDoc,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileDoc,
  'application/vnd.ms-powerpoint': FilePpt,
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': FilePpt,
  'application/vnd.ms-excel': FileXls,
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileXls,
  'image/jpeg': FileImage,
  'image/png': FileImage,
  'image/gif': FileImage,
};

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

export default function CourseDetailPage({ user }) {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [course, setCourse] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [enrollment, setEnrollment] = useState(null);
  const [progress, setProgress] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [filesMap, setFilesMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [expandedLesson, setExpandedLesson] = useState(null);
  const [uploadingFor, setUploadingFor] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showAddLesson, setShowAddLesson] = useState(false);
  const [lessonForm, setLessonForm] = useState({ title: '', description: '', content: '' });
  const [googleConnected, setGoogleConnected] = useState(false);
  const [importOpen, setImportOpen] = useState(null);
  const [googleSlides, setGoogleSlides] = useState([]);
  const [googleDocs, setGoogleDocs] = useState([]);
  const [importTab, setImportTab] = useState('slides');
  const [importing, setImporting] = useState(false);

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);
  const isInstructor = course?.instructor_id === user?.id;

  useEffect(() => {
    loadCourseData();
    checkGoogleStatus();
  }, [courseId]);

  const checkGoogleStatus = async () => {
    try {
      const data = await apiGet('/api/google/status');
      setGoogleConnected(data.connected);
    } catch (e) { /* not connected */ }
  };

  const loadCourseData = async () => {
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

      // Load files for all lessons
      const filesResult = await apiGet(`/api/files?course_id=${courseId}`);
      const fMap = {};
      (filesResult.files || []).forEach(f => {
        const lid = f.lesson_id || '_course';
        if (!fMap[lid]) fMap[lid] = [];
        fMap[lid].push(f);
      });
      setFilesMap(fMap);

      if (isFaculty && courseData.instructor_id === user?.id) {
        try {
          const enrollList = await apiGet(`/api/courses/${courseId}/enrollments`);
          setEnrollments(enrollList);
        } catch (e) { /* not instructor */ }
      }
    } catch (e) {
      console.error('Failed to load course:', e);
    } finally {
      setLoading(false);
    }
  };

  const [upgradePrompt, setUpgradePrompt] = useState(null);

  const handleEnroll = async () => {
    try {
      await apiPost(`/api/courses/${courseId}/enroll`, {});
      loadCourseData();
    } catch (e) {
      const tierErr = parseTierError(e.message);
      if (tierErr) {
        setUpgradePrompt({ feature: 'enrollment', requiredTier: tierErr.requiredTier || 'scholar' });
      } else {
        alert(e.message);
      }
    }
  };

  const handleUnenroll = async () => {
    if (!window.confirm('Leave this course? Your progress will be lost.')) return;
    try {
      await apiPost(`/api/courses/${courseId}/unenroll`, {});
      loadCourseData();
    } catch (e) { alert(e.message); }
  };

  const handleCompleteLesson = async (lessonId) => {
    try {
      await apiPost(`/api/courses/${courseId}/lessons/${lessonId}/complete`, {});
      loadCourseData();
    } catch (e) { alert(e.message); }
  };

  const handleAddLesson = async () => {
    if (!lessonForm.title.trim()) return;
    try {
      await apiPost(`/api/courses/${courseId}/lessons`, {
        title: lessonForm.title,
        description: lessonForm.description,
        content: lessonForm.content,
        order: lessons.length + 1,
      });
      setLessonForm({ title: '', description: '', content: '' });
      setShowAddLesson(false);
      loadCourseData();
    } catch (e) { alert(e.message); }
  };

  const handleUploadClick = (lessonId) => {
    setUploadingFor(lessonId);
    fileInputRef.current?.click();
  };

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
    } catch (err) {
      alert(err.message);
    } finally {
      setUploading(false);
      setUploadingFor(null);
      e.target.value = '';
    }
  };

  const handleDeleteFile = async (fileId) => {
    if (!window.confirm('Delete this file?')) return;
    try {
      await apiDelete(`/api/files/${fileId}`);
      loadCourseData();
    } catch (e) { alert(e.message); }
  };

  const handleOpenImport = async (lessonId) => {
    setImportOpen(lessonId);
    try {
      const [slidesData, docsData] = await Promise.all([
        apiGet('/api/google/slides'),
        apiGet('/api/google/docs'),
      ]);
      setGoogleSlides(slidesData.slides || []);
      setGoogleDocs(docsData.docs || []);
    } catch (e) {
      alert('Failed to load Google content. Please reconnect in Settings.');
    }
  };

  const handleImportSlide = async (slideId, lessonId) => {
    setImporting(true);
    try {
      await apiPost(`/api/google/slides/${slideId}/import`, { lesson_id: lessonId, course_id: courseId });
      setImportOpen(null);
      loadCourseData();
    } catch (e) { alert(e.message); }
    finally { setImporting(false); }
  };

  const handleImportDoc = async (docId, lessonId) => {
    setImporting(true);
    try {
      await apiPost(`/api/google/docs/${docId}/import`, { lesson_id: lessonId, course_id: courseId });
      setImportOpen(null);
      loadCourseData();
    } catch (e) { alert(e.message); }
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
        <Button onClick={() => navigate('/courses')} variant="ghost" className="mt-4 text-[#D4AF37]">
          Back to Courses
        </Button>
      </div>
    );
  }

  const isEnrolled = enrollment?.enrolled;
  const completedLessons = progress?.completed_lessons || [];
  const progressPct = progress?.progress || 0;
  const isCompleted = progress?.status === 'completed';

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="course-detail-page">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileSelected}
        accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.jpg,.jpeg,.png,.gif"
        data-testid="file-upload-input"
      />

      {/* Back button */}
      <button
        onClick={() => navigate('/courses')}
        className="flex items-center gap-2 text-sm text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
        data-testid="back-to-courses"
      >
        <ArrowLeft size={16} /> Back to Courses
      </button>

      {/* Course Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h1
              className="text-3xl sm:text-4xl font-light text-[#F8FAFC]"
              style={{ fontFamily: 'Cormorant Garamond, serif' }}
              data-testid="course-title"
            >
              {course.title}
            </h1>
            <Badge className={`text-[10px] ${
              course.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              course.status === 'archived' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
              'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20'
            }`}>
              {course.status}
            </Badge>
          </div>
          <p className="text-sm text-[#94A3B8] mb-3 leading-relaxed">{course.description}</p>
          <div className="flex items-center gap-4 text-xs text-[#94A3B8]">
            <span className="flex items-center gap-1">
              <BookOpenText size={14} className="text-[#D4AF37]" /> {lessons.length} lessons
            </span>
            <span className="flex items-center gap-1">
              <Users size={14} className="text-[#D4AF37]" /> {course.enrolled_count || 0} enrolled
            </span>
            <span>by {course.instructor_name}</span>
          </div>
          {course.tags?.length > 0 && (
            <div className="flex gap-1.5 mt-3">
              {course.tags.map(tag => (
                <span key={tag} className="text-[10px] px-2 py-0.5 rounded bg-[#050814] border border-[#1E293B] text-[#94A3B8]">{tag}</span>
              ))}
            </div>
          )}
        </div>

        {/* Enrollment CTA */}
        <div className="flex-shrink-0">
          {!isInstructor && course.status === 'active' && (
            isEnrolled ? (
              <div className="space-y-2 text-right">
                {isCompleted ? (
                  <div className="flex items-center gap-2 text-emerald-400 text-sm">
                    <Trophy size={18} weight="fill" /> Course Completed!
                  </div>
                ) : (
                  <div className="text-sm text-[#94A3B8]">
                    {Math.round(progressPct)}% complete
                  </div>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleUnenroll}
                  className="border-[#1E293B] text-[#94A3B8] hover:text-red-400 hover:border-red-400/30 text-xs"
                  data-testid="unenroll-btn"
                >
                  <SignOut size={14} className="mr-1" /> Unenroll
                </Button>
              </div>
            ) : (
              <Button
                onClick={handleEnroll}
                className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] font-medium"
                data-testid="enroll-btn"
              >
                <UserPlus size={16} className="mr-2" /> Enroll in Course
              </Button>
            )
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {isEnrolled && lessons.length > 0 && (
        <Card className="bg-[#0F172A] border-[#1E293B]" data-testid="progress-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs tracking-[0.15em] uppercase text-[#D4AF37]">Your Progress</span>
              <span className="text-sm text-[#F8FAFC] font-medium">
                {completedLessons.length} / {lessons.length} lessons
              </span>
            </div>
            <div className="w-full h-2 bg-[#050814] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#D4AF37] rounded-full transition-all duration-500"
                style={{ width: `${progressPct}%` }}
                data-testid="progress-bar"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Curriculum */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37]">Curriculum</h2>
          {isInstructor && (
            <Button
              size="sm"
              onClick={() => setShowAddLesson(!showAddLesson)}
              className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs"
              data-testid="add-lesson-toggle"
            >
              <Plus size={14} className="mr-1" /> Add Lesson
            </Button>
          )}
        </div>

        {/* Add Lesson Form */}
        {showAddLesson && isInstructor && (
          <Card className="bg-[#0F172A] border-[#D4AF37]/30 mb-4">
            <CardContent className="p-4 space-y-3">
              <Input
                placeholder="Lesson Title"
                value={lessonForm.title}
                onChange={e => setLessonForm({ ...lessonForm, title: e.target.value })}
                className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]"
                data-testid="new-lesson-title"
              />
              <Input
                placeholder="Brief description"
                value={lessonForm.description}
                onChange={e => setLessonForm({ ...lessonForm, description: e.target.value })}
                className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]"
                data-testid="new-lesson-desc"
              />
              <Textarea
                placeholder="Lesson content (instructions, notes, references...)"
                value={lessonForm.content}
                onChange={e => setLessonForm({ ...lessonForm, content: e.target.value })}
                className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] min-h-[80px]"
                data-testid="new-lesson-content"
              />
              <div className="flex gap-2">
                <Button onClick={handleAddLesson} size="sm" className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="submit-lesson-btn">
                  Create Lesson
                </Button>
                <Button onClick={() => setShowAddLesson(false)} size="sm" variant="ghost" className="text-[#94A3B8] text-xs">
                  Cancel
                </Button>
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
          <div className="space-y-2">
            {lessons.map((lesson, idx) => {
              const isLessonCompleted = completedLessons.includes(lesson.id);
              const isExpanded = expandedLesson === lesson.id;
              const lessonFiles = filesMap[lesson.id] || [];

              return (
                <Card
                  key={lesson.id}
                  className={`bg-[#0F172A] border-[#1E293B] transition-all ${
                    isLessonCompleted ? 'border-l-2 border-l-emerald-500' : ''
                  }`}
                  data-testid={`lesson-card-${lesson.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-4">
                      {/* Completion indicator */}
                      <div className="flex-shrink-0">
                        {isEnrolled ? (
                          isLessonCompleted ? (
                            <CheckCircle size={24} weight="fill" className="text-emerald-400" />
                          ) : (
                            <button
                              onClick={() => handleCompleteLesson(lesson.id)}
                              className="text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
                              data-testid={`complete-lesson-${lesson.id}`}
                              title="Mark as complete"
                            >
                              <Circle size={24} weight="regular" />
                            </button>
                          )
                        ) : (
                          <div className="w-6 h-6 rounded-full bg-[#050814] border border-[#1E293B] flex items-center justify-center">
                            <span className="text-[10px] text-[#94A3B8]">{idx + 1}</span>
                          </div>
                        )}
                      </div>

                      {/* Lesson info */}
                      <div
                        className="flex-1 min-w-0 cursor-pointer"
                        onClick={() => setExpandedLesson(isExpanded ? null : lesson.id)}
                      >
                        <div className="flex items-center gap-2">
                          <h3 className={`text-sm font-medium ${isLessonCompleted ? 'text-emerald-400' : 'text-[#F8FAFC]'}`}>
                            {lesson.title}
                          </h3>
                          {lessonFiles.length > 0 && (
                            <span className="flex items-center gap-0.5 text-[10px] text-[#94A3B8]">
                              <Paperclip size={10} /> {lessonFiles.length}
                            </span>
                          )}
                        </div>
                        {lesson.description && (
                          <p className="text-xs text-[#94A3B8] mt-0.5 truncate">{lesson.description}</p>
                        )}
                      </div>

                      {/* Right side */}
                      <div className="flex items-center gap-2">
                        {isLessonCompleted && (
                          <Badge className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                            Done
                          </Badge>
                        )}
                        <button
                          onClick={() => setExpandedLesson(isExpanded ? null : lesson.id)}
                          className="text-[#94A3B8] hover:text-[#F8FAFC] p-1"
                          data-testid={`expand-lesson-${lesson.id}`}
                        >
                          {isExpanded ? <CaretUp size={16} /> : <CaretDown size={16} />}
                        </button>
                      </div>
                    </div>

                    {/* Expanded content */}
                    {isExpanded && (
                      <div className="mt-4 pt-4 border-t border-[#1E293B] space-y-4">
                        {/* Lesson content */}
                        {lesson.content && (
                          <div className="p-3 bg-[#050814] rounded-md border border-[#1E293B]">
                            <LessonContentViewer content={lesson.content} />
                          </div>
                        )}

                        {/* Files section */}
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] flex items-center gap-1">
                              <Paperclip size={12} /> Materials ({lessonFiles.length})
                            </span>
                            {isInstructor && (
                              <div className="flex gap-1">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleUploadClick(lesson.id)}
                                  className="text-[#D4AF37] hover:text-[#F3E5AB] text-[10px] h-7"
                                  disabled={uploading}
                                  data-testid={`upload-file-${lesson.id}`}
                                >
                                  {uploading && uploadingFor === lesson.id ? (
                                    <span className="flex items-center gap-1">
                                      <span className="w-3 h-3 border border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
                                      Uploading...
                                    </span>
                                  ) : (
                                    <><Plus size={12} className="mr-1" /> Attach File</>
                                  )}
                                </Button>
                                {googleConnected && (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleOpenImport(lesson.id)}
                                    className="text-[#94A3B8] hover:text-[#F3E5AB] text-[10px] h-7"
                                    data-testid={`import-google-${lesson.id}`}
                                  >
                                    <GoogleLogo size={12} className="mr-1" /> Import
                                  </Button>
                                )}
                              </div>
                            )}
                          </div>

                          {lessonFiles.length > 0 ? (
                            <div className="space-y-1.5">
                              {lessonFiles.map(file => {
                                const Icon = FILE_ICONS[file.mime_type] || FileIcon;
                                return (
                                  <div
                                    key={file.id}
                                    className="flex items-center gap-3 p-2.5 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-colors group"
                                    data-testid={`file-${file.id}`}
                                  >
                                    <Icon size={18} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                      <p className="text-xs text-[#F8FAFC] truncate">{file.original_filename}</p>
                                      <p className="text-[10px] text-[#94A3B8]">{formatFileSize(file.file_size)}</p>
                                    </div>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                      <a
                                        href={`${BACKEND_URL}/api/files/${file.id}/download`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="p-1 text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
                                        title="Download"
                                        data-testid={`download-file-${file.id}`}
                                        onClick={e => e.stopPropagation()}
                                      >
                                        <DownloadSimple size={14} />
                                      </a>
                                      {isInstructor && (
                                        <button
                                          onClick={() => handleDeleteFile(file.id)}
                                          className="p-1 text-[#94A3B8] hover:text-red-400 transition-colors"
                                          title="Delete"
                                          data-testid={`delete-file-${file.id}`}
                                        >
                                          <Trash size={14} />
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          ) : (
                            <p className="text-[10px] text-[#94A3B8]">
                              {isInstructor ? 'No files attached. Click "Attach File" to add materials.' : 'No materials attached to this lesson.'}
                            </p>
                          )}
                        </div>

                        {/* Google Resources */}
                        {lesson.google_resources?.length > 0 && (
                          <div>
                            <span className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] flex items-center gap-1 mb-2">
                              <GoogleLogo size={12} /> Imported from Google
                            </span>
                            <div className="space-y-1.5">
                              {lesson.google_resources.map((res, i) => (
                                <a
                                  key={i}
                                  href={res.view_url || res.embed_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-3 p-2.5 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-colors group"
                                  data-testid={`google-resource-${res.google_id}`}
                                >
                                  {res.type === 'google_slide' ? (
                                    <Presentation size={18} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                                  ) : (
                                    <Article size={18} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                                  )}
                                  <div className="flex-1 min-w-0">
                                    <p className="text-xs text-[#F8FAFC] truncate">{res.title}</p>
                                    <p className="text-[10px] text-[#94A3B8]">
                                      {res.type === 'google_slide' ? `${res.slide_count} slides` : 'Google Doc'}
                                    </p>
                                  </div>
                                  <ArrowSquareOut size={14} className="text-[#94A3B8] opacity-0 group-hover:opacity-100 transition-opacity" />
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Instructor: Enrolled Students */}
      {isInstructor && enrollments.length > 0 && (
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
                      <div
                        className="h-full bg-[#D4AF37] rounded-full"
                        style={{ width: `${e.progress || 0}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#94A3B8] w-8 text-right">{Math.round(e.progress || 0)}%</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Google Import Dialog */}
      <Dialog open={importOpen !== null} onOpenChange={(open) => { if (!open) setImportOpen(null); }}>
        <DialogContent className="bg-[#0F172A] border-[#1E293B] max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              <GoogleLogo size={20} className="text-[#D4AF37]" /> Import from Google
            </DialogTitle>
          </DialogHeader>

          <div className="flex gap-1 p-1 bg-[#050814] border border-[#1E293B] rounded-md mb-4">
            <button
              onClick={() => setImportTab('slides')}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded transition-all ${
                importTab === 'slides' ? 'bg-[#D4AF37] text-[#050814]' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
              data-testid="import-tab-slides"
            >
              <Presentation size={14} /> Slides
            </button>
            <button
              onClick={() => setImportTab('docs')}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded transition-all ${
                importTab === 'docs' ? 'bg-[#D4AF37] text-[#050814]' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
              data-testid="import-tab-docs"
            >
              <Article size={14} /> Docs
            </button>
          </div>

          <div className="space-y-2">
            {importTab === 'slides' && (
              googleSlides.length === 0 ? (
                <p className="text-sm text-[#94A3B8] text-center py-4">No Google Slides found in your account.</p>
              ) : (
                googleSlides.map(slide => (
                  <div
                    key={slide.id}
                    className="flex items-center gap-3 p-3 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-colors"
                    data-testid={`import-slide-${slide.id}`}
                  >
                    <Presentation size={20} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[#F8FAFC] truncate">{slide.name}</p>
                      <p className="text-[10px] text-[#94A3B8]">
                        Modified {new Date(slide.modifiedTime).toLocaleDateString()}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleImportSlide(slide.id, importOpen)}
                      className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-[10px]"
                      disabled={importing}
                    >
                      {importing ? 'Importing...' : 'Import'}
                    </Button>
                  </div>
                ))
              )
            )}
            {importTab === 'docs' && (
              googleDocs.length === 0 ? (
                <p className="text-sm text-[#94A3B8] text-center py-4">No Google Docs found in your account.</p>
              ) : (
                googleDocs.map(doc => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-3 p-3 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-colors"
                    data-testid={`import-doc-${doc.id}`}
                  >
                    <Article size={20} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[#F8FAFC] truncate">{doc.name}</p>
                      <p className="text-[10px] text-[#94A3B8]">
                        Modified {new Date(doc.modifiedTime).toLocaleDateString()}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleImportDoc(doc.id, importOpen)}
                      className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-[10px]"
                      disabled={importing}
                    >
                      {importing ? 'Importing...' : 'Import'}
                    </Button>
                  </div>
                ))
              )
            )}
          </div>
        </DialogContent>
      </Dialog>

      {upgradePrompt && (
        <UpgradePrompt
          feature={upgradePrompt.feature}
          requiredTier={upgradePrompt.requiredTier}
          onClose={() => setUpgradePrompt(null)}
        />
      )}
    </div>
  );
}
