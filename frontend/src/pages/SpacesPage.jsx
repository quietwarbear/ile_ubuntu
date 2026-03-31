import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import {
  ShieldCheck,
  Plus,
  Lock,
  Globe,
  Users,
  Eye,
  Trash,
  UserPlus,
  CheckCircle,
  XCircle,
  BookOpen,
  ArrowSquareOut,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut, apiDelete, parseTierError } from '../lib/api';
import UpgradePrompt from '../components/UpgradePrompt';

export default function SpacesPage({ user }) {
  const [spaces, setSpaces] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedSpace, setSelectedSpace] = useState(null);
  const [addResourceOpen, setAddResourceOpen] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', access_level: 'members', content: '' });
  const [resourceForm, setResourceForm] = useState({ title: '', type: 'text', content: '', url: '' });

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  useEffect(() => { loadSpaces(); }, []);

  const loadSpaces = async () => {
    try { setSpaces(await apiGet('/api/spaces')); } catch (e) { console.error(e); }
  };

  const handleCreate = async () => {
    try {
      const space = await apiPost('/api/spaces', form);
      setForm({ name: '', description: '', access_level: 'members', content: '' });
      setCreateOpen(false);
      loadSpaces();
      setSelectedSpace(space.id);
    } catch (e) { alert(e.message); }
  };

  const [upgradePrompt, setUpgradePrompt] = useState(null);

  const handleRequestAccess = async (spaceId) => {
    try { await apiPost(`/api/spaces/${spaceId}/request-access`, {}); loadSpaces(); }
    catch (e) {
      const tierErr = parseTierError(e.message);
      if (tierErr) setUpgradePrompt({ feature: 'space_access', requiredTier: 'scholar' });
      else alert(e.message);
    }
  };

  const handleApprove = async (spaceId, userId) => {
    try { await apiPost(`/api/spaces/${spaceId}/approve/${userId}`, {}); loadSpaces(); }
    catch (e) { alert(e.message); }
  };

  const handleDeny = async (spaceId, userId) => {
    try { await apiPost(`/api/spaces/${spaceId}/deny/${userId}`, {}); loadSpaces(); }
    catch (e) { alert(e.message); }
  };

  const handleDelete = async (spaceId) => {
    if (!window.confirm('Delete this space?')) return;
    try { await apiDelete(`/api/spaces/${spaceId}`); setSelectedSpace(null); loadSpaces(); }
    catch (e) { alert(e.message); }
  };

  const handleAddResource = async () => {
    if (!selectedSpace) return;
    try {
      await apiPost(`/api/spaces/${selectedSpace}/resources`, resourceForm);
      setResourceForm({ title: '', type: 'text', content: '', url: '' });
      setAddResourceOpen(false);
      loadSpaces();
    } catch (e) { alert(e.message); }
  };

  const accessConfig = {
    public: { icon: Globe, color: 'text-emerald-400', label: 'Public', badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
    members: { icon: Users, color: 'text-blue-400', label: 'Members Only', badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
    faculty: { icon: ShieldCheck, color: 'text-[#D4AF37]', label: 'Faculty+', badge: 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20' },
    elder: { icon: Lock, color: 'text-red-400', label: 'Elders Only', badge: 'bg-red-500/10 text-red-400 border-red-500/20' },
  };

  const activeSpace = spaces.find(s => s.id === selectedSpace);

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="spaces-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Knowledge Spaces</h1>
          <p className="text-sm text-[#94A3B8]">Protected repositories of sacred and restricted knowledge</p>
        </div>
        {isFaculty && (
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="create-space-btn">
                <Plus size={16} weight="bold" className="mr-1.5" /> New Space
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#0F172A] border-[#1E293B]">
              <DialogHeader>
                <DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Create Knowledge Space</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Input placeholder="Space Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="space-name-input" />
                <Textarea placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="space-desc-input" />
                <div>
                  <label className="text-xs text-[#94A3B8] mb-1 block">Access Level</label>
                  <select value={form.access_level} onChange={e => setForm({ ...form, access_level: e.target.value })} className="w-full p-2 rounded-md bg-[#050814] border border-[#1E293B] text-[#F8FAFC] text-sm" data-testid="space-access-select">
                    <option value="public">Public — visible to all</option>
                    <option value="members">Members Only — invite or request access</option>
                    <option value="faculty">Faculty+ — restricted to faculty and above</option>
                    <option value="elder">Elders Only — sacred/restricted knowledge</option>
                  </select>
                </div>
                <Textarea placeholder="Initial content (optional)" value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] min-h-[80px]" />
                <Button onClick={handleCreate} className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="submit-space-btn">Create Space</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Space List */}
        <div className="space-y-2">
          {spaces.length === 0 ? (
            <Card className="bg-[#0F172A] border-[#1E293B]">
              <CardContent className="p-8 text-center">
                <ShieldCheck size={40} weight="duotone" className="text-[#D4AF37] mx-auto mb-3" />
                <p className="text-sm text-[#94A3B8]">No spaces available.</p>
              </CardContent>
            </Card>
          ) : (
            spaces.map(space => {
              const config = accessConfig[space.access_level] || accessConfig.members;
              const AccessIcon = config.icon;
              const isMember = space.members?.includes(user?.id);
              const isOwner = space.owner_id === user?.id;

              return (
                <Card
                  key={space.id}
                  className={`bg-[#0F172A] border-[#1E293B] cursor-pointer transition-all ${
                    selectedSpace === space.id ? 'border-[#D4AF37]/50 bg-[#D4AF37]/5' : 'hover:border-[#D4AF37]/20'
                  }`}
                  onClick={() => setSelectedSpace(space.id)}
                  data-testid={`space-card-${space.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <AccessIcon size={16} className={config.color} />
                        <h3 className="text-sm text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{space.name}</h3>
                      </div>
                      <Badge className={`text-[9px] ${config.badge}`}>{config.label}</Badge>
                    </div>
                    <p className="text-[10px] text-[#94A3B8] line-clamp-2">{space.description}</p>
                    <div className="flex items-center gap-3 mt-2 text-[10px] text-[#94A3B8]">
                      <span>{space.members?.length || 0} members</span>
                      <span>{space.resources?.length || 0} resources</span>
                    </div>
                    {!isMember && !isOwner && space.access_level === 'members' && (
                      <Button size="sm" onClick={(e) => { e.stopPropagation(); handleRequestAccess(space.id); }} className="mt-2 bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-[10px] h-7 w-full" data-testid={`request-access-${space.id}`}>
                        Request Access
                      </Button>
                    )}
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>

        {/* Space Detail */}
        <div className="lg:col-span-2">
          {activeSpace ? (
            <Card className="bg-[#0F172A] border-[#1E293B]">
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle className="text-lg text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{activeSpace.name}</CardTitle>
                  <p className="text-xs text-[#94A3B8] mt-1">{activeSpace.description}</p>
                </div>
                <div className="flex gap-2">
                  {isFaculty && (
                    <Dialog open={addResourceOpen} onOpenChange={setAddResourceOpen}>
                      <DialogTrigger asChild>
                        <Button size="sm" className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="add-resource-btn">
                          <Plus size={14} className="mr-1" /> Add Resource
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="bg-[#0F172A] border-[#1E293B]">
                        <DialogHeader>
                          <DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Add Resource</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                          <Input placeholder="Title" value={resourceForm.title} onChange={e => setResourceForm({ ...resourceForm, title: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="resource-title-input" />
                          <select value={resourceForm.type} onChange={e => setResourceForm({ ...resourceForm, type: e.target.value })} className="w-full p-2 rounded-md bg-[#050814] border border-[#1E293B] text-[#F8FAFC] text-sm">
                            <option value="text">Text / Notes</option>
                            <option value="link">External Link</option>
                            <option value="embed">Embed (Google Slides/Docs)</option>
                          </select>
                          {resourceForm.type === 'link' || resourceForm.type === 'embed' ? (
                            <Input placeholder="URL" value={resourceForm.url} onChange={e => setResourceForm({ ...resourceForm, url: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" />
                          ) : null}
                          <Textarea placeholder="Content" value={resourceForm.content} onChange={e => setResourceForm({ ...resourceForm, content: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] min-h-[100px]" data-testid="resource-content-input" />
                          <Button onClick={handleAddResource} className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="submit-resource-btn">Add</Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  )}
                  {activeSpace.owner_id === user?.id && (
                    <Button size="sm" variant="ghost" onClick={() => handleDelete(activeSpace.id)} className="text-red-400 hover:text-red-300 h-8 w-8 p-0" data-testid="delete-space-btn">
                      <Trash size={14} />
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Content */}
                {activeSpace.content && (
                  <div className="p-3 bg-[#050814] border border-[#1E293B] rounded-md">
                    <p className="text-sm text-[#94A3B8] whitespace-pre-wrap leading-relaxed">{activeSpace.content}</p>
                  </div>
                )}

                {/* Resources */}
                {activeSpace.resources?.length > 0 && (
                  <div>
                    <h3 className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-2">Resources</h3>
                    <div className="space-y-2">
                      {activeSpace.resources.map(res => (
                        <div key={res.id} className="p-3 bg-[#050814] border border-[#1E293B] rounded-md" data-testid={`resource-${res.id}`}>
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="text-sm text-[#F8FAFC]">{res.title}</h4>
                            <Badge className="text-[9px] bg-[#0F172A] text-[#94A3B8] border-[#1E293B]">{res.type}</Badge>
                          </div>
                          {res.content && <p className="text-xs text-[#94A3B8] whitespace-pre-wrap">{res.content}</p>}
                          {res.url && (
                            res.type === 'embed' ? (
                              <iframe src={res.url} className="w-full h-[300px] mt-2 rounded border border-[#1E293B]" allowFullScreen title={res.title} />
                            ) : (
                              <a href={res.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-[#D4AF37] hover:underline mt-1">
                                Open Link <ArrowSquareOut size={12} />
                              </a>
                            )
                          )}
                          <p className="text-[9px] text-[#94A3B8] mt-1">Added by {res.added_by_name}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Pending Requests (Owner only) */}
                {activeSpace.owner_id === user?.id && activeSpace.pending_requests?.length > 0 && (
                  <div>
                    <h3 className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-2">Access Requests</h3>
                    <div className="space-y-1.5">
                      {activeSpace.pending_requests.map(req => (
                        <div key={req.user_id} className="flex items-center justify-between p-2 bg-[#050814] border border-[#D4AF37]/20 rounded-md" data-testid={`request-${req.user_id}`}>
                          <span className="text-sm text-[#F8FAFC]">{req.user_name}</span>
                          <div className="flex gap-1.5">
                            <Button size="sm" onClick={() => handleApprove(activeSpace.id, req.user_id)} className="bg-emerald-500 text-white hover:bg-emerald-600 h-7 w-7 p-0" data-testid={`approve-${req.user_id}`}>
                              <CheckCircle size={14} />
                            </Button>
                            <Button size="sm" onClick={() => handleDeny(activeSpace.id, req.user_id)} variant="ghost" className="text-red-400 hover:text-red-300 h-7 w-7 p-0" data-testid={`deny-${req.user_id}`}>
                              <XCircle size={14} />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-[#0F172A] border-[#1E293B]">
              <CardContent className="p-12 text-center">
                <Eye size={40} weight="duotone" className="text-[#94A3B8] mx-auto mb-3" />
                <p className="text-sm text-[#94A3B8]">Select a space to view its contents</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

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
