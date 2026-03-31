import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { UsersThree, Plus, UserPlus, SignOut as LeaveIcon } from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api';

export default function CohortsPage({ user }) {
  const navigate = useNavigate();
  const [cohorts, setCohorts] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', max_members: 30 });

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  useEffect(() => { loadCohorts(); }, []);

  const loadCohorts = async () => {
    try { setCohorts(await apiGet('/api/cohorts')); } catch (e) { console.error(e); }
  };

  const handleCreate = async () => {
    try {
      await apiPost('/api/cohorts', form);
      setForm({ name: '', description: '', max_members: 30 });
      setCreateOpen(false);
      loadCohorts();
    } catch (e) { alert(e.message); }
  };

  const handleJoin = async (id) => {
    try { await apiPost(`/api/cohorts/${id}/join`, {}); loadCohorts(); }
    catch (e) { alert(e.message); }
  };

  const handleLeave = async (id) => {
    try { await apiPost(`/api/cohorts/${id}/leave`, {}); loadCohorts(); }
    catch (e) { alert(e.message); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this cohort?')) return;
    try { await apiDelete(`/api/cohorts/${id}`); loadCohorts(); }
    catch (e) { alert(e.message); }
  };

  const statusColor = (s) => {
    if (s === 'active') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    if (s === 'completed') return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  };

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="cohorts-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Cohorts</h1>
          <p className="text-sm text-[#94A3B8]">Time-bound learning groups and study circles</p>
        </div>
        {isFaculty && (
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="create-cohort-btn">
                <Plus size={16} weight="bold" className="mr-1.5" /> New Cohort
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#0F172A] border-[#1E293B]">
              <DialogHeader>
                <DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Create Cohort</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Input placeholder="Cohort Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="cohort-name-input" />
                <Textarea placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="cohort-desc-input" />
                <Input type="number" placeholder="Max Members" value={form.max_members} onChange={e => setForm({ ...form, max_members: parseInt(e.target.value) || 30 })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" />
                <Button onClick={handleCreate} className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="submit-cohort-btn">Create Cohort</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {cohorts.length === 0 ? (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardContent className="p-10 text-center">
            <UsersThree size={48} weight="duotone" className="text-blue-400 mx-auto mb-4" />
            <h3 className="text-lg text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>No cohorts yet</h3>
            <p className="text-sm text-[#94A3B8]">Start a learning cohort to bring students together.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cohorts.map(cohort => {
            const isMember = cohort.members?.includes(user?.id);
            const isOwner = cohort.instructor_id === user?.id;
            return (
              <Card key={cohort.id} className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/20 transition-all cursor-pointer" onClick={() => navigate(`/cohorts/${cohort.id}`)} data-testid={`cohort-card-${cohort.id}`}>
                <CardContent className="p-5 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{cohort.name}</h3>
                      <p className="text-xs text-[#94A3B8] mt-1">{cohort.description}</p>
                    </div>
                    <Badge className={`text-[10px] ${statusColor(cohort.status)}`}>{cohort.status}</Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[#94A3B8]">
                    <span className="flex items-center gap-1"><UsersThree size={14} /> {cohort.members?.length || 0}/{cohort.max_members}</span>
                    <span>Led by {cohort.instructor_name}</span>
                  </div>
                  <div className="flex gap-2 pt-1" onClick={e => e.stopPropagation()}>
                    {!isMember && !isOwner && (
                      <Button size="sm" onClick={() => handleJoin(cohort.id)} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs flex-1" data-testid={`join-cohort-${cohort.id}`}>
                        <UserPlus size={14} className="mr-1" /> Join
                      </Button>
                    )}
                    {isMember && !isOwner && (
                      <Button size="sm" variant="outline" onClick={() => handleLeave(cohort.id)} className="border-[#1E293B] text-[#94A3B8] hover:text-red-400 text-xs flex-1" data-testid={`leave-cohort-${cohort.id}`}>
                        <LeaveIcon size={14} className="mr-1" /> Leave
                      </Button>
                    )}
                    {isOwner && (
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(cohort.id)} className="text-red-400 hover:text-red-300 text-xs" data-testid={`delete-cohort-${cohort.id}`}>
                        Delete
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
