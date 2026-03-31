import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
  VideoCamera, NotePencil, Tag, Users, Clock, CalendarBlank,
  Export, MagnifyingGlass, Eye,
} from '@phosphor-icons/react';
import { apiGet, apiPut } from '../lib/api';

export default function SessionRecordsPage({ user }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notes, setNotes] = useState('');
  const [takeaways, setTakeaways] = useState('');
  const [tags, setTags] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    apiGet('/api/session-records')
      .then(setRecords)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const loadDetail = async (id) => {
    setSelected(id);
    try {
      const d = await apiGet(`/api/session-records/${id}`);
      setDetail(d);
      setNotes(d.notes || '');
      setTakeaways((d.key_takeaways || []).join('\n'));
      setTags((d.tags || []).join(', '));
    } catch (e) { console.error(e); }
  };

  const saveNotes = async () => {
    try {
      await apiPut(`/api/session-records/${selected}/notes`, {
        notes,
        key_takeaways: takeaways.split('\n').filter(Boolean),
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      });
      setEditingNotes(false);
      loadDetail(selected);
    } catch (e) { alert(e.message); }
  };

  const exportCSV = async () => {
    if (!selected) return;
    try {
      const data = await apiGet(`/api/session-records/${selected}/export`);
      const rows = [
        ['Session Title', 'Host', 'Status', 'Started', 'Ended', 'Attendees', 'Notes'],
        [data.session_title, data.host, data.status, data.started_at || '', data.ended_at || '', data.attendee_count, data.notes],
        [],
        ['Attendees'],
        ['Name', 'Email', 'Role'],
        ...data.attendees.map(a => [a.name, a.email || '', a.role]),
        [],
        ['Key Takeaways'],
        ...data.key_takeaways.map(t => [t]),
      ];
      const csv = rows.map(r => r.join(',')).join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `session_${data.session_title.replace(/\s/g, '_')}.csv`;
      a.click();
    } catch (e) { console.error(e); }
  };

  const isFaculty = ['admin', 'elder', 'faculty'].includes(user?.role);
  const filtered = records.filter(r =>
    !search || r.title?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="records-loading">
        <div className="w-6 h-6 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="session-records-page">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <VideoCamera size={20} weight="duotone" className="text-[#D4AF37]" />
          <h1 className="text-xl text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Session Records
          </h1>
        </div>
        <p className="text-xs text-[#94A3B8]">Review past live sessions, add notes, and track attendance</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* List */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 bg-[#0F172A] border border-[#1E293B] rounded-md px-3 py-1.5">
            <MagnifyingGlass size={14} className="text-[#94A3B8]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search sessions..."
              className="bg-transparent text-xs text-[#F8FAFC] outline-none flex-1"
              data-testid="records-search"
            />
          </div>

          {filtered.length === 0 ? (
            <Card className="bg-[#0F172A] border-[#1E293B]">
              <CardContent className="p-6 text-center">
                <VideoCamera size={32} weight="duotone" className="text-[#94A3B8] mx-auto mb-2" />
                <p className="text-xs text-[#94A3B8]">No ended sessions yet.</p>
              </CardContent>
            </Card>
          ) : (
            filtered.map(r => (
              <button
                key={r.id}
                onClick={() => loadDetail(r.id)}
                className={`w-full text-left p-3 rounded-md border transition-all ${
                  selected === r.id
                    ? 'bg-[#0F172A] border-[#D4AF37]/30'
                    : 'bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/20'
                }`}
                data-testid={`record-${r.id}`}
              >
                <p className="text-xs text-[#F8FAFC] font-medium truncate">{r.title}</p>
                <div className="flex items-center gap-2 mt-1 text-[9px] text-[#94A3B8]">
                  <span>{r.host_name}</span>
                  {r.ended_at && <span>{new Date(r.ended_at).toLocaleDateString()}</span>}
                  <span>{(r.attendees || []).length} attendees</span>
                </div>
                {r.notes && <Badge className="mt-1 bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[8px]">Has Notes</Badge>}
              </button>
            ))
          )}
        </div>

        {/* Detail */}
        <div className="md:col-span-2">
          {!detail ? (
            <Card className="bg-[#0F172A] border-[#1E293B]">
              <CardContent className="p-12 text-center">
                <Eye size={40} weight="duotone" className="text-[#94A3B8] mx-auto mb-3" />
                <p className="text-sm text-[#94A3B8]">Select a session to view details</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              <Card className="bg-[#0F172A] border-[#1E293B]">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                      {detail.title}
                    </CardTitle>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" className="h-7 text-[10px] border-[#1E293B] text-[#94A3B8]" onClick={exportCSV} data-testid="export-csv">
                        <Export size={12} className="mr-1" /> Export CSV
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
                    <div className="p-2 bg-[#050814] border border-[#1E293B] rounded text-center">
                      <Clock size={14} weight="duotone" className="text-[#D4AF37] mx-auto mb-1" />
                      <p className="text-[9px] text-[#94A3B8]">
                        {detail.started_at ? new Date(detail.started_at).toLocaleTimeString() : '—'}
                        {detail.ended_at ? ` → ${new Date(detail.ended_at).toLocaleTimeString()}` : ''}
                      </p>
                    </div>
                    <div className="p-2 bg-[#050814] border border-[#1E293B] rounded text-center">
                      <CalendarBlank size={14} weight="duotone" className="text-[#D4AF37] mx-auto mb-1" />
                      <p className="text-[9px] text-[#94A3B8]">{detail.ended_at ? new Date(detail.ended_at).toLocaleDateString() : '—'}</p>
                    </div>
                    <div className="p-2 bg-[#050814] border border-[#1E293B] rounded text-center">
                      <Users size={14} weight="duotone" className="text-[#D4AF37] mx-auto mb-1" />
                      <p className="text-[9px] text-[#94A3B8]">{(detail.attendees || []).length} attendees</p>
                    </div>
                    <div className="p-2 bg-[#050814] border border-[#1E293B] rounded text-center">
                      <VideoCamera size={14} weight="duotone" className="text-[#D4AF37] mx-auto mb-1" />
                      <p className="text-[9px] text-[#94A3B8]">{detail.host_name}</p>
                    </div>
                  </div>

                  {/* Attendees */}
                  {(detail.attendee_details || []).length > 0 && (
                    <div className="mb-3">
                      <p className="text-[9px] text-[#D4AF37] uppercase tracking-wider mb-1">Attendees</p>
                      <div className="flex flex-wrap gap-1">
                        {detail.attendee_details.map(a => (
                          <div key={a.id} className="flex items-center gap-1 p-1 bg-[#050814] border border-[#1E293B] rounded text-[9px]">
                            <img src={a.picture || `https://ui-avatars.com/api/?name=${a.name}&background=050814&color=D4AF37&size=16`} alt="" className="w-4 h-4 rounded-full" />
                            <span className="text-[#F8FAFC]">{a.name}</span>
                            <Badge className="bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20 text-[7px]">{a.role}</Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tags */}
                  {!editingNotes && (detail.tags || []).length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {detail.tags.map((t) => (
                        <Badge key={t} className="bg-violet-500/10 text-violet-400 border-violet-500/20 text-[8px]">
                          <Tag size={8} className="mr-0.5" />{t}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Notes Section */}
              <Card className="bg-[#0F172A] border-[#1E293B]">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                      <NotePencil size={16} weight="duotone" className="text-[#D4AF37]" /> Session Notes
                    </CardTitle>
                    {isFaculty && !editingNotes && (
                      <Button size="sm" variant="outline" className="h-7 text-[10px] border-[#1E293B] text-[#D4AF37]" onClick={() => setEditingNotes(true)} data-testid="edit-notes-btn">
                        Edit
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {editingNotes ? (
                    <div className="space-y-3">
                      <div>
                        <label className="text-[9px] text-[#94A3B8] uppercase tracking-wider">Notes</label>
                        <textarea
                          value={notes}
                          onChange={(e) => setNotes(e.target.value)}
                          className="w-full mt-1 bg-[#050814] border border-[#1E293B] rounded-md p-2 text-xs text-[#F8FAFC] h-24 outline-none focus:border-[#D4AF37]/40"
                          data-testid="notes-textarea"
                        />
                      </div>
                      <div>
                        <label className="text-[9px] text-[#94A3B8] uppercase tracking-wider">Key Takeaways (one per line)</label>
                        <textarea
                          value={takeaways}
                          onChange={(e) => setTakeaways(e.target.value)}
                          className="w-full mt-1 bg-[#050814] border border-[#1E293B] rounded-md p-2 text-xs text-[#F8FAFC] h-16 outline-none focus:border-[#D4AF37]/40"
                          data-testid="takeaways-textarea"
                        />
                      </div>
                      <div>
                        <label className="text-[9px] text-[#94A3B8] uppercase tracking-wider">Tags (comma-separated)</label>
                        <input
                          value={tags}
                          onChange={(e) => setTags(e.target.value)}
                          className="w-full mt-1 bg-[#050814] border border-[#1E293B] rounded-md px-2 py-1.5 text-xs text-[#F8FAFC] outline-none focus:border-[#D4AF37]/40"
                          data-testid="tags-input"
                        />
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" className="bg-[#D4AF37] text-[#050814] text-[10px] h-7" onClick={saveNotes} data-testid="save-notes-btn">Save</Button>
                        <Button size="sm" variant="outline" className="border-[#1E293B] text-[#94A3B8] text-[10px] h-7" onClick={() => setEditingNotes(false)}>Cancel</Button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      {detail.notes ? (
                        <p className="text-xs text-[#94A3B8] whitespace-pre-wrap">{detail.notes}</p>
                      ) : (
                        <p className="text-xs text-[#475569] italic">No notes yet. {isFaculty ? 'Click Edit to add notes.' : ''}</p>
                      )}
                      {(detail.key_takeaways || []).length > 0 && (
                        <div className="mt-3">
                          <p className="text-[9px] text-[#D4AF37] uppercase tracking-wider mb-1">Key Takeaways</p>
                          <ul className="space-y-1">
                            {detail.key_takeaways.map((t) => (
                              <li key={t} className="text-xs text-[#94A3B8] flex items-start gap-2">
                                <span className="text-[#D4AF37] mt-0.5">&#9679;</span>{t}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
