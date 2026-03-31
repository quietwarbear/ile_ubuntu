import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import {
  BookOpenText,
  Plus,
  PencilSimple,
  Trash,
  Users,
  GraduationCap,
  MagnifyingGlass,
  Trophy,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api';

export default function CoursesPage({ user }) {
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [myEnrollments, setMyEnrollments] = useState([]);
  const [activeView, setActiveView] = useState('browse');
  const [createOpen, setCreateOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ title: '', description: '', tags: '' });
  const [search, setSearch] = useState('');

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    try {
      const [coursesData, enrollData] = await Promise.all([
        apiGet('/api/courses'),
        apiGet('/api/enrollments/my-courses'),
      ]);
      setCourses(coursesData);
      setMyEnrollments(enrollData);
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
      loadAll();
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
      loadAll();
    } catch (e) { alert(e.message); }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this course and all its lessons?')) return;
    try { await apiDelete(`/api/courses/${id}`); loadAll(); }
    catch (err) { alert(err.message); }
  };

  const handlePublish = async (id, e) => {
    e.stopPropagation();
    try { await apiPut(`/api/courses/${id}`, { status: 'active' }); loadAll(); }
    catch (err) { alert(err.message); }
  };

  const handleEnroll = async (courseId, e) => {
    e.stopPropagation();
    try { await apiPost(`/api/courses/${courseId}/enroll`, {}); loadAll(); }
    catch (err) { alert(err.message); }
  };

  const statusColor = (s) => {
    if (s === 'active') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    if (s === 'archived') return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    return 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20';
  };

  const enrolledCourseIds = new Set(myEnrollments.map(e => e.course_id));

  const filteredCourses = courses.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase()) ||
    c.description.toLowerCase().includes(search.toLowerCase()) ||
    c.tags?.some(t => t.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="courses-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Courses
          </h1>
          <p className="text-sm text-[#94A3B8]">Explore and enroll in learning paths</p>
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

      {/* View Toggle + Search */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex gap-1 p-1 bg-[#0F172A] border border-[#1E293B] rounded-md w-fit">
          <button
            onClick={() => setActiveView('browse')}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded transition-all ${
              activeView === 'browse' ? 'bg-[#D4AF37] text-[#050814]' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
            data-testid="tab-browse"
          >
            <MagnifyingGlass size={14} /> Browse All
          </button>
          <button
            onClick={() => setActiveView('learning')}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded transition-all ${
              activeView === 'learning' ? 'bg-[#D4AF37] text-[#050814]' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
            data-testid="tab-my-learning"
          >
            <GraduationCap size={14} /> My Learning ({myEnrollments.length})
          </button>
        </div>
        {activeView === 'browse' && (
          <div className="relative flex-1 max-w-sm">
            <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
            <Input
              placeholder="Search courses..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-[#0F172A] border-[#1E293B] text-[#F8FAFC] pl-9 text-sm"
              data-testid="search-courses"
            />
          </div>
        )}
      </div>

      {/* Browse View */}
      {activeView === 'browse' && (
        filteredCourses.length === 0 ? (
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-10 text-center">
              <BookOpenText size={48} weight="duotone" className="text-[#D4AF37] mx-auto mb-4" />
              <h3 className="text-lg text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                {search ? 'No matching courses' : 'No courses yet'}
              </h3>
              <p className="text-sm text-[#94A3B8]">
                {search ? 'Try a different search term.' : 'Create your first course to start building your curriculum.'}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredCourses.map(course => {
              const enrolled = enrolledCourseIds.has(course.id);
              const isOwner = course.instructor_id === user?.id;
              const myEnrollment = myEnrollments.find(e => e.course_id === course.id);

              return (
                <Card
                  key={course.id}
                  className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/30 transition-all duration-300 cursor-pointer hover:-translate-y-0.5 group"
                  onClick={() => navigate(`/courses/${course.id}`)}
                  data-testid={`course-card-${course.id}`}
                >
                  <CardContent className="p-5 space-y-3">
                    {/* Title + Status */}
                    <div className="flex items-start justify-between">
                      <h3
                        className="text-base text-[#F8FAFC] group-hover:text-[#D4AF37] transition-colors line-clamp-2"
                        style={{ fontFamily: 'Cormorant Garamond, serif' }}
                      >
                        {course.title}
                      </h3>
                      <Badge className={`text-[10px] flex-shrink-0 ml-2 ${statusColor(course.status)}`}>
                        {course.status}
                      </Badge>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-[#94A3B8] line-clamp-2">{course.description}</p>

                    {/* Tags */}
                    {course.tags?.length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {course.tags.slice(0, 3).map(tag => (
                          <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-[#050814] border border-[#1E293B] text-[#94A3B8]">{tag}</span>
                        ))}
                      </div>
                    )}

                    {/* Meta */}
                    <div className="flex items-center justify-between text-xs text-[#94A3B8] pt-1">
                      <span>by {course.instructor_name}</span>
                      <span className="flex items-center gap-1">
                        <Users size={12} /> {course.enrolled_count || 0}
                      </span>
                    </div>

                    {/* Progress bar for enrolled */}
                    {enrolled && myEnrollment && (
                      <div className="pt-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] text-[#D4AF37]">Enrolled</span>
                          <span className="text-[10px] text-[#94A3B8]">{Math.round(myEnrollment.progress || 0)}%</span>
                        </div>
                        <div className="w-full h-1 bg-[#050814] rounded-full overflow-hidden">
                          <div className="h-full bg-[#D4AF37] rounded-full transition-all" style={{ width: `${myEnrollment.progress || 0}%` }} />
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-1">
                      {!isOwner && course.status === 'active' && !enrolled && (
                        <Button size="sm" onClick={(e) => handleEnroll(course.id, e)} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs flex-1" data-testid={`enroll-course-${course.id}`}>
                          Enroll
                        </Button>
                      )}
                      {isOwner && isFaculty && (
                        <div className="flex gap-1 ml-auto" onClick={e => e.stopPropagation()}>
                          {course.status === 'draft' && (
                            <Button size="sm" variant="ghost" onClick={(e) => handlePublish(course.id, e)} className="text-emerald-400 text-[10px] h-7" data-testid={`publish-course-${course.id}`}>
                              Publish
                            </Button>
                          )}
                          <Dialog open={editId === course.id} onOpenChange={(open) => {
                            if (open) { setEditId(course.id); setForm({ title: course.title, description: course.description, tags: course.tags?.join(', ') || '' }); }
                            else setEditId(null);
                          }}>
                            <DialogTrigger asChild>
                              <Button size="sm" variant="ghost" className="text-[#D4AF37] h-7 w-7 p-0" data-testid={`edit-course-${course.id}`}>
                                <PencilSimple size={14} />
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="bg-[#0F172A] border-[#1E293B]">
                              <DialogHeader><DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Edit Course</DialogTitle></DialogHeader>
                              <div className="space-y-4">
                                <Input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" />
                                <Textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" />
                                <Input value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" />
                                <Button onClick={handleUpdate} className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]">Save</Button>
                              </div>
                            </DialogContent>
                          </Dialog>
                          <Button size="sm" variant="ghost" onClick={(e) => handleDelete(course.id, e)} className="text-red-400 h-7 w-7 p-0" data-testid={`delete-course-${course.id}`}>
                            <Trash size={14} />
                          </Button>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )
      )}

      {/* My Learning View */}
      {activeView === 'learning' && (
        myEnrollments.length === 0 ? (
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-10 text-center">
              <GraduationCap size={48} weight="duotone" className="text-[#D4AF37] mx-auto mb-4" />
              <h3 className="text-lg text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>No courses yet</h3>
              <p className="text-sm text-[#94A3B8] mb-4">Browse and enroll in courses to start learning.</p>
              <Button onClick={() => setActiveView('browse')} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="browse-courses-cta">
                Browse Courses
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {myEnrollments.map(enrollment => (
              <Card
                key={enrollment.id}
                className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/30 cursor-pointer transition-all"
                onClick={() => navigate(`/courses/${enrollment.course_id}`)}
                data-testid={`my-course-${enrollment.course_id}`}
              >
                <CardContent className="p-5">
                  <div className="flex items-center gap-4">
                    {/* Progress circle */}
                    <div className="relative w-12 h-12 flex-shrink-0">
                      <svg className="w-12 h-12 -rotate-90" viewBox="0 0 48 48">
                        <circle cx="24" cy="24" r="20" fill="none" stroke="#1E293B" strokeWidth="3" />
                        <circle
                          cx="24" cy="24" r="20" fill="none" stroke="#D4AF37" strokeWidth="3"
                          strokeDasharray={`${(enrollment.progress || 0) * 1.257} 125.7`}
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        {enrollment.status === 'completed' ? (
                          <Trophy size={16} weight="fill" className="text-[#D4AF37]" />
                        ) : (
                          <span className="text-[10px] font-semibold text-[#F8FAFC]">{Math.round(enrollment.progress || 0)}%</span>
                        )}
                      </div>
                    </div>

                    {/* Course info */}
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                        {enrollment.course_title}
                      </h3>
                      <p className="text-xs text-[#94A3B8] truncate">{enrollment.course_description}</p>
                      <div className="flex items-center gap-3 mt-1 text-[10px] text-[#94A3B8]">
                        <span>by {enrollment.instructor_name}</span>
                        <span>{enrollment.completed_lessons?.length || 0} / {enrollment.total_lessons} lessons</span>
                      </div>
                    </div>

                    {/* Status */}
                    <Badge className={`text-[10px] ${
                      enrollment.status === 'completed'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20'
                    }`}>
                      {enrollment.status === 'completed' ? 'Completed' : 'In Progress'}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      )}
    </div>
  );
}
