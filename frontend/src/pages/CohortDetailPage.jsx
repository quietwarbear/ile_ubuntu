import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import {
  ArrowLeft,
  UsersThree,
  BookOpenText,
  Plus,
  Trash,
  UserPlus,
  SignOut,
  Users,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiDelete } from '../lib/api';

export default function CohortDetailPage({ user }) {
  const { cohortId } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [courses, setCourses] = useState([]);
  const [linkOpen, setLinkOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  useEffect(() => { loadData(); }, [cohortId]);

  const loadData = async () => {
    try {
      const [detailData, coursesData] = await Promise.all([
        apiGet(`/api/cohorts/${cohortId}/detail`),
        isFaculty ? apiGet('/api/courses') : Promise.resolve([]),
      ]);
      setDetail(detailData);
      setCourses(coursesData);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleLinkCourse = async (courseId) => {
    try {
      await apiPost(`/api/cohorts/${cohortId}/courses`, { course_id: courseId });
      setLinkOpen(false);
      loadData();
    } catch (e) { alert(e.message); }
  };

  const handleUnlinkCourse = async (courseId) => {
    try {
      await apiDelete(`/api/cohorts/${cohortId}/courses/${courseId}`);
      loadData();
    } catch (e) { alert(e.message); }
  };

  const handleJoin = async () => {
    try { await apiPost(`/api/cohorts/${cohortId}/join`, {}); loadData(); }
    catch (e) { alert(e.message); }
  };

  const handleLeave = async () => {
    try { await apiPost(`/api/cohorts/${cohortId}/leave`, {}); loadData(); }
    catch (e) { alert(e.message); }
  };

  if (loading) return <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" /></div>;
  if (!detail) return <div className="text-center py-20"><p className="text-[#94A3B8]">Cohort not found</p></div>;

  const isOwner = detail.instructor_id === user?.id;
  const isMember = detail.members?.includes(user?.id);
  const linkedIds = new Set(detail.course_ids || []);
  const availableCourses = courses.filter(c => !linkedIds.has(c.id) && c.status === 'active');

  const statusColor = (s) => {
    if (s === 'active') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    if (s === 'completed') return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  };

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="cohort-detail-page">
      <button onClick={() => navigate('/cohorts')} className="flex items-center gap-2 text-sm text-[#94A3B8] hover:text-[#D4AF37] transition-colors" data-testid="back-to-cohorts">
        <ArrowLeft size={16} /> Back to Cohorts
      </button>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{detail.name}</h1>
            <Badge className={`text-[10px] ${statusColor(detail.status)}`}>{detail.status}</Badge>
          </div>
          <p className="text-sm text-[#94A3B8] mb-2">{detail.description}</p>
          <div className="flex items-center gap-4 text-xs text-[#94A3B8]">
            <span className="flex items-center gap-1"><Users size={14} className="text-[#D4AF37]" /> {detail.members?.length || 0}/{detail.max_members}</span>
            <span className="flex items-center gap-1"><BookOpenText size={14} className="text-[#D4AF37]" /> {detail.linked_courses?.length || 0} courses</span>
            <span>Led by {detail.instructor_name}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {!isOwner && !isMember && (
            <Button onClick={handleJoin} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="join-cohort-btn">
              <UserPlus size={16} className="mr-1" /> Join Cohort
            </Button>
          )}
          {isMember && !isOwner && (
            <Button variant="outline" onClick={handleLeave} className="border-[#1E293B] text-[#94A3B8] hover:text-red-400 text-xs" data-testid="leave-cohort-btn">
              <SignOut size={14} className="mr-1" /> Leave
            </Button>
          )}
        </div>
      </div>

      {/* Linked Courses */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37]">Curriculum</h2>
          {isOwner && (
            <Dialog open={linkOpen} onOpenChange={setLinkOpen}>
              <DialogTrigger asChild>
                <Button size="sm" className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="link-course-btn">
                  <Plus size={14} className="mr-1" /> Link Course
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#0F172A] border-[#1E293B]">
                <DialogHeader>
                  <DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Link a Course</DialogTitle>
                </DialogHeader>
                <div className="space-y-2 max-h-[50vh] overflow-y-auto">
                  {availableCourses.length === 0 ? (
                    <p className="text-sm text-[#94A3B8] text-center py-4">No available courses to link.</p>
                  ) : (
                    availableCourses.map(c => (
                      <div key={c.id} className="flex items-center justify-between p-3 bg-[#050814] border border-[#1E293B] rounded-md" data-testid={`available-course-${c.id}`}>
                        <div>
                          <p className="text-sm text-[#F8FAFC]">{c.title}</p>
                          <p className="text-[10px] text-[#94A3B8]">by {c.instructor_name}</p>
                        </div>
                        <Button size="sm" onClick={() => handleLinkCourse(c.id)} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs">Link</Button>
                      </div>
                    ))
                  )}
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>

        {(detail.linked_courses || []).length === 0 ? (
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-6 text-center">
              <BookOpenText size={32} weight="duotone" className="text-[#94A3B8] mx-auto mb-2" />
              <p className="text-sm text-[#94A3B8]">No courses linked yet.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {detail.linked_courses.map(course => (
              <Card key={course.id} className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/20 transition-all cursor-pointer" data-testid={`linked-course-${course.id}`}>
                <CardContent className="p-4 flex items-center justify-between" onClick={() => navigate(`/courses/${course.id}`)}>
                  <div className="flex items-center gap-3">
                    <BookOpenText size={18} weight="duotone" className="text-[#D4AF37]" />
                    <div>
                      <p className="text-sm text-[#F8FAFC]">{course.title}</p>
                      <div className="flex items-center gap-2 text-[10px] text-[#94A3B8]">
                        <span>{course.lesson_count} lessons</span>
                        <span>{course.enrolled_count} enrolled</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={`text-[10px] ${course.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20'}`}>{course.status}</Badge>
                    {isOwner && (
                      <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); handleUnlinkCourse(course.id); }} className="text-red-400 hover:text-red-300 h-7 w-7 p-0" data-testid={`unlink-course-${course.id}`}>
                        <Trash size={14} />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Members */}
      <div>
        <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37] mb-3">
          Members ({detail.enriched_members?.length || 0})
        </h2>
        {(detail.enriched_members || []).length === 0 ? (
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-6 text-center">
              <UsersThree size={32} weight="duotone" className="text-[#94A3B8] mx-auto mb-2" />
              <p className="text-sm text-[#94A3B8]">No members yet.</p>
            </CardContent>
          </Card>
        ) : (
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-4 space-y-2">
              {detail.enriched_members.map(m => (
                <div key={m.id} className="flex items-center justify-between p-2 bg-[#050814] border border-[#1E293B] rounded-md" data-testid={`member-${m.id}`}>
                  <div className="flex items-center gap-3">
                    <img src={m.picture || `https://ui-avatars.com/api/?name=${m.name}&background=0F172A&color=D4AF37`} alt="" className="w-8 h-8 rounded-full" />
                    <div>
                      <p className="text-sm text-[#F8FAFC]">{m.name}</p>
                      <p className="text-[10px] text-[#D4AF37]">{m.role}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-[#050814] rounded-full overflow-hidden border border-[#1E293B]">
                      <div className="h-full bg-[#D4AF37] rounded-full" style={{ width: `${m.overall_progress}%` }} />
                    </div>
                    <span className="text-[10px] text-[#94A3B8] w-8 text-right">{Math.round(m.overall_progress)}%</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
