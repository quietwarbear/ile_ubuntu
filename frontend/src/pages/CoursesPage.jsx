import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { BookOpenText, Plus, PencilSimple, Trash, CaretDown, CaretUp } from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api';

export default function CoursesPage({ user }) {
  const [courses, setCourses] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ title: '', description: '', tags: '' });
  const [expandedCourse, setExpandedCourse] = useState(null);
  const [lessons, setLessons] = useState({});
  const [lessonForm, setLessonForm] = useState({ title: '', description: '', content: '' });

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    try {
      const data = await apiGet('/api/courses');
      setCourses(data);
    } catch (e) { console.error(e); }
  };

  const handleCreate = async () => {
    try {
      await apiPost('/api/courses', {
        title: form.title,
        description: form.description,
        tags: form.tags ? form.tags.split(',').map(t => t.trim()) : [],
      });
      setForm({ title: '', description: '', tags: '' });
      setCreateOpen(false);
      loadCourses();
    } catch (e) { alert(e.message); }
  };

  const handleUpdate = async () => {
    try {
      await apiPut(`/api/courses/${editId}`, {
        title: form.title,
        description: form.description,
        tags: form.tags ? form.tags.split(',').map(t => t.trim()) : [],
      });
      setEditId(null);
      setForm({ title: '', description: '', tags: '' });
      loadCourses();
    } catch (e) { alert(e.message); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this course and all its lessons?')) return;
    try {
      await apiDelete(`/api/courses/${id}`);
      loadCourses();
    } catch (e) { alert(e.message); }
  };

  const handlePublish = async (id) => {
    try {
      await apiPut(`/api/courses/${id}`, { status: 'active' });
      loadCourses();
    } catch (e) { alert(e.message); }
  };

  const toggleExpand = async (courseId) => {
    if (expandedCourse === courseId) {
      setExpandedCourse(null);
      return;
    }
    setExpandedCourse(courseId);
    if (!lessons[courseId]) {
      try {
        const data = await apiGet(`/api/courses/${courseId}/lessons`);
        setLessons(prev => ({ ...prev, [courseId]: data }));
      } catch (e) { console.error(e); }
    }
  };

  const handleCreateLesson = async (courseId) => {
    try {
      const lesson = await apiPost(`/api/courses/${courseId}/lessons`, {
        title: lessonForm.title,
        description: lessonForm.description,
        content: lessonForm.content,
        order: (lessons[courseId]?.length || 0) + 1,
      });
      setLessons(prev => ({
        ...prev,
        [courseId]: [...(prev[courseId] || []), lesson],
      }));
      setLessonForm({ title: '', description: '', content: '' });
    } catch (e) { alert(e.message); }
  };

  const statusColor = (status) => {
    if (status === 'active') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    if (status === 'archived') return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    return 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20';
  };

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="courses-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Courses
          </h1>
          <p className="text-sm text-[#94A3B8]">Structured learning paths and curricula</p>
        </div>
        {isFaculty && (
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="create-course-btn">
                <Plus size={16} weight="bold" className="mr-1.5" /> New Course
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#0F172A] border-[#1E293B]">
              <DialogHeader>
                <DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Create Course</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Input placeholder="Course Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="course-title-input" />
                <Textarea placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="course-desc-input" />
                <Input placeholder="Tags (comma separated)" value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="course-tags-input" />
                <Button onClick={handleCreate} className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="submit-course-btn">Create Course</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Course List */}
      {courses.length === 0 ? (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardContent className="p-10 text-center">
            <BookOpenText size={48} weight="duotone" className="text-[#D4AF37] mx-auto mb-4" />
            <h3 className="text-lg text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>No courses yet</h3>
            <p className="text-sm text-[#94A3B8]">Create your first course to start building your curriculum.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {courses.map(course => (
            <Card key={course.id} className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/20 transition-all" data-testid={`course-card-${course.id}`}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1 cursor-pointer" onClick={() => toggleExpand(course.id)}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{course.title}</h3>
                      <Badge className={`text-[10px] ${statusColor(course.status)}`}>{course.status}</Badge>
                    </div>
                    <p className="text-sm text-[#94A3B8] mb-2">{course.description}</p>
                    <div className="flex items-center gap-2 text-xs text-[#94A3B8]">
                      <span>by {course.instructor_name}</span>
                      {course.tags?.length > 0 && (
                        <>
                          <span className="text-[#1E293B]">|</span>
                          {course.tags.map(tag => (
                            <span key={tag} className="px-1.5 py-0.5 rounded bg-[#050814] border border-[#1E293B] text-[10px]">{tag}</span>
                          ))}
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 ml-4">
                    {isFaculty && course.status === 'draft' && (
                      <Button size="sm" variant="ghost" onClick={() => handlePublish(course.id)} className="text-emerald-400 hover:text-emerald-300 text-xs" data-testid={`publish-course-${course.id}`}>
                        Publish
                      </Button>
                    )}
                    {isFaculty && (
                      <Dialog open={editId === course.id} onOpenChange={(open) => {
                        if (open) { setEditId(course.id); setForm({ title: course.title, description: course.description, tags: course.tags?.join(', ') || '' }); }
                        else setEditId(null);
                      }}>
                        <DialogTrigger asChild>
                          <Button size="sm" variant="ghost" className="text-[#D4AF37] hover:text-[#F3E5AB] h-8 w-8 p-0" data-testid={`edit-course-${course.id}`}>
                            <PencilSimple size={16} weight="duotone" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="bg-[#0F172A] border-[#1E293B]">
                          <DialogHeader><DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Edit Course</DialogTitle></DialogHeader>
                          <div className="space-y-4">
                            <Input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" />
                            <Textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" />
                            <Input value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" />
                            <Button onClick={handleUpdate} className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]">Save Changes</Button>
                          </div>
                        </DialogContent>
                      </Dialog>
                    )}
                    {isFaculty && (
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(course.id)} className="text-red-400 hover:text-red-300 h-8 w-8 p-0" data-testid={`delete-course-${course.id}`}>
                        <Trash size={16} weight="duotone" />
                      </Button>
                    )}
                    <button onClick={() => toggleExpand(course.id)} className="text-[#94A3B8] hover:text-[#F8FAFC] p-1">
                      {expandedCourse === course.id ? <CaretUp size={16} /> : <CaretDown size={16} />}
                    </button>
                  </div>
                </div>

                {/* Expanded: Lessons */}
                {expandedCourse === course.id && (
                  <div className="mt-4 pt-4 border-t border-[#1E293B] space-y-3">
                    <h4 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37]">Lessons</h4>
                    {(lessons[course.id] || []).map(lesson => (
                      <div key={lesson.id} className="p-3 bg-[#050814] border border-[#1E293B] rounded-md">
                        <p className="text-sm text-[#F8FAFC]">{lesson.title}</p>
                        <p className="text-xs text-[#94A3B8]">{lesson.description}</p>
                      </div>
                    ))}
                    {(lessons[course.id] || []).length === 0 && <p className="text-xs text-[#94A3B8]">No lessons yet.</p>}

                    {isFaculty && (
                      <div className="space-y-2 pt-2">
                        <Input placeholder="Lesson Title" value={lessonForm.title} onChange={e => setLessonForm({ ...lessonForm, title: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-sm" data-testid="lesson-title-input" />
                        <Input placeholder="Description" value={lessonForm.description} onChange={e => setLessonForm({ ...lessonForm, description: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-sm" />
                        <Button size="sm" onClick={() => handleCreateLesson(course.id)} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="add-lesson-btn">
                          <Plus size={14} className="mr-1" /> Add Lesson
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
