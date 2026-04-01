import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import {
  ArrowLeft, CalendarBlank, ChatDots, Eye, EyeSlash,
  PaperPlaneRight, Trash, PencilSimple,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiDelete } from '../lib/api';
import LessonContentViewer from '../components/LessonContentViewer';

export default function BlogPostPage({ user }) {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const isAuthor = post?.author_id === user?.id;
  const isAdmin = user?.role === 'admin';

  const loadPost = useCallback(async () => {
    try {
      const data = await apiGet(`/api/blog/posts/by-slug/${slug}`);
      setPost(data);
      const cmts = await apiGet(`/api/blog/posts/${data.id}/comments`);
      setComments(cmts);
    } catch (e) {
      console.error('Failed to load post:', e);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => { loadPost(); }, [loadPost]);

  const handleComment = async () => {
    if (!newComment.trim() || submitting) return;
    setSubmitting(true);
    try {
      const comment = await apiPost(`/api/blog/posts/${post.id}/comments`, { content: newComment });
      setComments([...comments, comment]);
      setNewComment('');
      setPost({ ...post, comments_count: (post.comments_count || 0) + 1 });
    } catch (e) { alert(e.message); }
    finally { setSubmitting(false); }
  };

  const handleDeleteComment = async (commentId) => {
    if (!window.confirm('Delete this comment?')) return;
    try {
      await apiDelete(`/api/blog/comments/${commentId}`);
      setComments(comments.filter(c => c.id !== commentId));
      setPost({ ...post, comments_count: Math.max(0, (post.comments_count || 1) - 1) });
    } catch (e) { alert(e.message); }
  };

  const handleDeletePost = async () => {
    if (!window.confirm('Delete this post permanently?')) return;
    try {
      await apiDelete(`/api/blog/posts/${post.id}`);
      navigate('/blog');
    } catch (e) { alert(e.message); }
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!post) {
    return (
      <div className="text-center py-20">
        <p className="text-[#94A3B8]">Post not found</p>
        <Button onClick={() => navigate('/blog')} variant="ghost" className="mt-4 text-[#D4AF37]">Back to Blog</Button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in-up" data-testid="blog-post-page">
      {/* Back */}
      <button
        onClick={() => navigate('/blog')}
        className="flex items-center gap-2 text-sm text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
        data-testid="back-to-blog"
      >
        <ArrowLeft size={16} /> Back to Blog
      </button>

      {/* Cover Image */}
      {post.cover_image && (
        <div className="rounded-xl overflow-hidden border border-[#1E293B] h-64 sm:h-80">
          <img src={post.cover_image} alt="" className="w-full h-full object-cover" />
        </div>
      )}

      {/* Meta */}
      <div>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {post.category && (
            <Badge className="text-[10px] bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20">{post.category}</Badge>
          )}
          {post.visibility === 'members' && (
            <Badge className="text-[10px] bg-violet-500/10 text-violet-400 border-violet-500/20">
              <EyeSlash size={10} className="mr-0.5" /> Members Only
            </Badge>
          )}
          {post.visibility === 'public' && (
            <Badge className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
              <Eye size={10} className="mr-0.5" /> Public
            </Badge>
          )}
        </div>

        <h1
          className="text-3xl sm:text-4xl font-light text-[#F8FAFC] leading-tight mb-4"
          style={{ fontFamily: 'Cormorant Garamond, serif' }}
          data-testid="post-title"
        >
          {post.title}
        </h1>

        <div className="flex items-center gap-4 text-xs text-[#94A3B8]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center">
              <span className="text-[10px] text-[#D4AF37] font-medium">
                {post.author_name?.split(' ').map(n => n[0]).join('').slice(0, 2)}
              </span>
            </div>
            <div>
              <p className="text-sm text-[#F8FAFC]">{post.author_name}</p>
              <p className="text-[10px] text-[#64748B] capitalize">{post.author_role}</p>
            </div>
          </div>
          <span className="flex items-center gap-1">
            <CalendarBlank size={12} /> {formatDate(post.created_at)}
          </span>
        </div>

        {(isAuthor || isAdmin) && (
          <div className="flex gap-2 mt-4">
            <Button size="sm" variant="outline" onClick={() => navigate(`/blog/edit/${post.id}`)}
              className="border-[#1E293B] text-[#94A3B8] hover:text-[#D4AF37] text-xs" data-testid="edit-post-btn">
              <PencilSimple size={12} className="mr-1" /> Edit
            </Button>
            <Button size="sm" variant="outline" onClick={handleDeletePost}
              className="border-[#1E293B] text-[#94A3B8] hover:text-red-400 hover:border-red-400/30 text-xs" data-testid="delete-post-btn">
              <Trash size={12} className="mr-1" /> Delete
            </Button>
          </div>
        )}
      </div>

      {/* Content */}
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardContent className="p-6">
          <LessonContentViewer content={post.content} />
        </CardContent>
      </Card>

      {/* Tags */}
      {post.tags?.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {post.tags.map(tag => (
            <span key={tag} className="px-2.5 py-1 text-[10px] bg-[#050814] border border-[#1E293B] rounded-full text-[#94A3B8]">
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Comments Section */}
      <div data-testid="comments-section">
        <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37] mb-4 flex items-center gap-2">
          <ChatDots size={14} /> Comments ({comments.length})
        </h2>

        {/* Comment Input */}
        <Card className="bg-[#0F172A] border-[#1E293B] mb-4">
          <CardContent className="p-4">
            <Textarea
              placeholder="Share your thoughts..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] min-h-[80px] text-sm mb-3"
              data-testid="comment-input"
            />
            <div className="flex justify-end">
              <Button
                onClick={handleComment}
                disabled={!newComment.trim() || submitting}
                size="sm"
                className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs"
                data-testid="submit-comment-btn"
              >
                {submitting ? 'Posting...' : <><PaperPlaneRight size={12} className="mr-1" /> Post Comment</>}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Comments List */}
        <div className="space-y-3">
          {comments.map(comment => (
            <Card key={comment.id} className="bg-[#0F172A] border-[#1E293B]" data-testid={`comment-${comment.id}`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center">
                      <span className="text-[8px] text-[#D4AF37] font-medium">
                        {comment.author_name?.split(' ').map(n => n[0]).join('').slice(0, 2)}
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-[#F8FAFC]">{comment.author_name}</span>
                      <span className="text-[10px] text-[#64748B] ml-2">{formatDate(comment.created_at)}</span>
                    </div>
                  </div>
                  {(comment.author_id === user?.id || isAdmin) && (
                    <button
                      onClick={() => handleDeleteComment(comment.id)}
                      className="text-[#94A3B8] hover:text-red-400 transition-colors p-1"
                      data-testid={`delete-comment-${comment.id}`}
                    >
                      <Trash size={12} />
                    </button>
                  )}
                </div>
                <p className="text-xs text-[#94A3B8] leading-relaxed">{comment.content}</p>
              </CardContent>
            </Card>
          ))}
          {comments.length === 0 && (
            <p className="text-xs text-[#64748B] text-center py-4">No comments yet. Be the first to share your thoughts.</p>
          )}
        </div>
      </div>
    </div>
  );
}
