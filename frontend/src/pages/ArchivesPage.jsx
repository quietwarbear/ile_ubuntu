import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { Archive, Plus, Lock, Globe } from '@phosphor-icons/react';
import { apiGet, apiPost, apiDelete } from '../lib/api';

export default function ArchivesPage({ user }) {
  const [archives, setArchives] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', type: 'document', access_level: 'public', tags: '' });

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  useEffect(() => { loadArchives(); }, []);

  const loadArchives = async () => {
    try { setArchives(await apiGet('/api/archives')); } catch (e) { console.error(e); }
  };

  const handleCreate = async () => {
    try {
      await apiPost('/api/archives', {
        ...form,
        tags: form.tags ? form.tags.split(',').map(t => t.trim()) : [],
      });
      setForm({ title: '', description: '', type: 'document', access_level: 'public', tags: '' });
      setCreateOpen(false);
      loadArchives();
    } catch (e) { alert(e.message); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this archive?')) return;
    try { await apiDelete(`/api/archives/${id}`); loadArchives(); }
    catch (e) { alert(e.message); }
  };

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="archives-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Archives</h1>
          <p className="text-sm text-[#94A3B8]">Knowledge repository and preserved materials</p>
        </div>
        {isFaculty && (
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="create-archive-btn">
                <Plus size={16} weight="bold" className="mr-1.5" /> Add to Archive
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#0F172A] border-[#1E293B]">
              <DialogHeader>
                <DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Archive Item</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Input placeholder="Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="archive-title-input" />
                <Textarea placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="archive-desc-input" />
                <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} className="w-full p-2 rounded-md bg-[#050814] border border-[#1E293B] text-[#F8FAFC] text-sm">
                  <option value="course">Course</option>
                  <option value="document">Document</option>
                  <option value="recording">Recording</option>
                  <option value="tradition">Tradition/Knowledge</option>
                </select>
                <select value={form.access_level} onChange={e => setForm({ ...form, access_level: e.target.value })} className="w-full p-2 rounded-md bg-[#050814] border border-[#1E293B] text-[#F8FAFC] text-sm">
                  <option value="public">Public</option>
                  <option value="restricted">Restricted (Faculty+)</option>
                </select>
                <Input placeholder="Tags (comma separated)" value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" />
                <Button onClick={handleCreate} className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="submit-archive-btn">Archive</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {archives.length === 0 ? (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardContent className="p-10 text-center">
            <Archive size={48} weight="duotone" className="text-purple-400 mx-auto mb-4" />
            <h3 className="text-lg text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Archives are empty</h3>
            <p className="text-sm text-[#94A3B8]">Preserved knowledge and materials will appear here.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {archives.map(archive => (
            <Card key={archive.id} className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/20 transition-all" data-testid={`archive-card-${archive.id}`}>
              <CardContent className="p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <h3 className="text-base text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{archive.title}</h3>
                  {archive.access_level === 'restricted' ? (
                    <Lock size={14} className="text-[#D4AF37]" />
                  ) : (
                    <Globe size={14} className="text-[#94A3B8]" />
                  )}
                </div>
                <p className="text-xs text-[#94A3B8]">{archive.description}</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge className="text-[10px] bg-purple-500/10 text-purple-400 border-purple-500/20">{archive.type}</Badge>
                  {archive.tags?.map(tag => (
                    <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-[#050814] border border-[#1E293B] text-[#94A3B8]">{tag}</span>
                  ))}
                </div>
                <div className="flex items-center justify-between text-xs text-[#94A3B8]">
                  <span>by {archive.archived_by_name}</span>
                  {user?.role === 'admin' && (
                    <button onClick={() => handleDelete(archive.id)} className="text-red-400 hover:text-red-300" data-testid={`delete-archive-${archive.id}`}>Delete</button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
