import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  ArrowLeft,
  BookOpenText,
  CheckCircle,
  Circle,
  UserPlus,
  SignOut,
  Users,
  Clock,
  Trophy,
} from '@phosphor-icons/react';
import { apiGet, apiPost } from '../lib/api';

export default function CourseDetailPage({ user }) {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [enrollment, setEnrollment] = useState(null);
  const [progress, setProgress] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [loading, setLoading] = useState(true);

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);
  const isInstructor = course?.instructor_id === user?.id;

  useEffect(() => {
    loadCourseData();
  }, [courseId]);

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

  const handleEnroll = async () => {
    try {
      await apiPost(`/api/courses/${courseId}/enroll`, {});
      loadCourseData();
    } catch (e) { alert(e.message); }
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

      {/* Progress Bar (enrolled students) */}
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

      {/* Lessons */}
      <div>
        <h2
          className="text-xs tracking-[0.15em] uppercase text-[#D4AF37] mb-4"
        >
          Curriculum
        </h2>

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
              return (
                <Card
                  key={lesson.id}
                  className={`bg-[#0F172A] border-[#1E293B] transition-all ${
                    isLessonCompleted ? 'border-l-2 border-l-emerald-500' : ''
                  }`}
                  data-testid={`lesson-card-${lesson.id}`}
                >
                  <CardContent className="p-4 flex items-center gap-4">
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
                    <div className="flex-1 min-w-0">
                      <h3 className={`text-sm font-medium ${isLessonCompleted ? 'text-emerald-400' : 'text-[#F8FAFC]'}`}>
                        {lesson.title}
                      </h3>
                      {lesson.description && (
                        <p className="text-xs text-[#94A3B8] mt-0.5 truncate">{lesson.description}</p>
                      )}
                    </div>

                    {/* Status badge */}
                    {isLessonCompleted && (
                      <Badge className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                        Done
                      </Badge>
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
    </div>
  );
}
