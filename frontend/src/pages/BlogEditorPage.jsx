import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import {
  ArrowLeft, Eye, EyeSlash, Image as ImageIcon, X,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut } from '../lib/api';

const CATEGORIES = ['Announcements', 'Teaching', 'Community', 'Culture', 'Research', 'Events', 'Reflections'];

export default function BlogEditorPage({ user }) {
  const { postId } = useParams();
  const navigate = useNavigate();
  const isEdit = !!postId;

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [category, setCategory] = useState('');
  const [tags, setTags] = useState('');
  const [coverImage, setCoverImage] = useState('');
  const [visibility, setVisibility] = useState('public');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(isEdit);

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  const loadPost = useCallback(async () => {
    if (!postId) return;
    try {
      const posts = await apiGet('/api/blog/posts/mine');
      const post = posts.find(p => p.id === postId);
      if (!post) { navigate('/blog'); return; }
      setTitle(post.title);
      setCategory(post.category || '');
      setTags((post.tags || []).join(', '));
      setCoverImage(post.cover_image || '');
      setVisibility(post.visibility || 'public');
      // Load full content
      const full = await apiGet(`/api/blog/posts/by-slug/${post.slug}`);
      setContent(full.content || '');
    } catch (e) { console.error('Failed to load post:', e); }
    finally { setLoading(false); }
  }, [postId, navigate]);

  useEffect(() => { loadPost(); }, [loadPost]);

  if (!isFaculty) {
    return (
      <div className="text-center py-20">
        <p className="text-[#94A3B8]">Only faculty, elders, and admins can write posts.</p>
        <Button onClick={() => navigate('/blog')} variant="ghost" className="mt-4 text-[#D4AF37]">Back to Blog</Button>
      </div>
    );
  }

  const handleSubmit = async (status = 'published') => {
    if (!title.trim()) { alert('Title is required'); return; }
    if (!content.trim()) { alert('Content is required'); return; }
    setSaving(true);
    try {
      const payload = {
        title: title.trim(),
        content,
        category,
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        cover_image: coverImage.trim(),
        visibility,
        status,
      };
      if (isEdit) {
        const updated = await apiPut(`/api/blog/posts/${postId}`, payload);
        navigate(`/blog/${updated.slug}`);
      } else {
        const created = await apiPost('/api/blog/posts', payload);
        navigate(`/blog/${created.slug}`);
      }
    } catch (e) { alert(e.message); }
    finally { setSaving(false); }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in-up" data-testid="blog-editor-page">
      <button
        onClick={() => navigate('/blog')}
        className="flex items-center gap-2 text-sm text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
      >
        <ArrowLeft size={16} /> Back to Blog
      </button>

      <h1
        className="text-3xl font-light text-[#F8FAFC]"
        style={{ fontFamily: 'Cormorant Garamond, serif' }}
      >
        {isEdit ? 'Edit Post' : 'Write a New Post'}
      </h1>

      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardContent className="p-6 space-y-5">
          {/* Title */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-[#D4AF37] block mb-1.5">Title</label>
            <Input
              placeholder="Your post title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-lg"
              style={{ fontFamily: 'Cormorant Garamond, serif' }}
              data-testid="post-title-input"
            />
          </div>

          {/* Cover Image */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-[#D4AF37] block mb-1.5">
              <ImageIcon size={10} className="inline mr-1" /> Cover Image URL (optional)
            </label>
            <div className="flex gap-2">
              <Input
                placeholder="https://images.unsplash.com/..."
                value={coverImage}
                onChange={(e) => setCoverImage(e.target.value)}
                className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs flex-1"
                data-testid="cover-image-input"
              />
              {coverImage && (
                <button onClick={() => setCoverImage('')} className="text-[#94A3B8] hover:text-red-400 p-2">
                  <X size={14} />
                </button>
              )}
            </div>
            {coverImage && (
              <div className="mt-2 h-32 rounded-md overflow-hidden border border-[#1E293B]">
                <img src={coverImage} alt="Cover preview" className="w-full h-full object-cover" />
              </div>
            )}
          </div>

          {/* Category */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-[#D4AF37] block mb-1.5">Category</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  onClick={() => setCategory(category === cat ? '' : cat)}
                  className={`px-3 py-1.5 text-[10px] rounded-full border transition-all ${
                    category === cat
                      ? 'bg-[#D4AF37] text-[#050814] border-[#D4AF37]'
                      : 'text-[#94A3B8] border-[#1E293B] hover:border-[#D4AF37]/30'
                  }`}
                  data-testid={`category-${cat.toLowerCase()}`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Content */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-[#D4AF37] block mb-1.5">
              Content (Markdown supported)
            </label>
            <Textarea
              placeholder="Write your post content here... Markdown is fully supported:&#10;&#10;## Heading&#10;**Bold**, *italic*&#10;- Lists&#10;> Blockquotes&#10;[Links](url)&#10;![Images](url)"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-sm min-h-[300px] font-mono leading-relaxed"
              data-testid="post-content-input"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-[#D4AF37] block mb-1.5">Tags (comma-separated)</label>
            <Input
              placeholder="ubuntu, education, community"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs"
              data-testid="post-tags-input"
            />
          </div>

          {/* Visibility */}
          <div>
            <label className="text-[10px] uppercase tracking-wider text-[#D4AF37] block mb-1.5">Visibility</label>
            <div className="flex gap-3">
              <button
                onClick={() => setVisibility('public')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-md border text-xs transition-all ${
                  visibility === 'public'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'text-[#94A3B8] border-[#1E293B] hover:border-[#D4AF37]/30'
                }`}
                data-testid="visibility-public"
              >
                <Eye size={14} /> Public — Anyone can read
              </button>
              <button
                onClick={() => setVisibility('members')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-md border text-xs transition-all ${
                  visibility === 'members'
                    ? 'bg-violet-500/10 text-violet-400 border-violet-500/30'
                    : 'text-[#94A3B8] border-[#1E293B] hover:border-[#D4AF37]/30'
                }`}
                data-testid="visibility-members"
              >
                <EyeSlash size={14} /> Members Only — Signed-in users
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-[#1E293B]">
            <Button variant="ghost" onClick={() => navigate('/blog')} className="text-[#94A3B8] text-xs">
              Cancel
            </Button>
            <div className="flex gap-2">
              <Button
                onClick={() => handleSubmit('draft')}
                variant="outline"
                disabled={saving}
                className="border-[#1E293B] text-[#94A3B8] text-xs"
                data-testid="save-draft-btn"
              >
                Save as Draft
              </Button>
              <Button
                onClick={() => handleSubmit('published')}
                disabled={saving}
                className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs"
                data-testid="publish-btn"
              >
                {saving ? 'Publishing...' : isEdit ? 'Update Post' : 'Publish'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
