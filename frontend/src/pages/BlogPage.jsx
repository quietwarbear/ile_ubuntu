import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  PencilSimple, Plus, Eye, EyeSlash, ChatDots, CalendarBlank,
  FunnelSimple, ArrowRight, Newspaper,
} from '@phosphor-icons/react';
import { apiGet } from '../lib/api';

const CATEGORIES = ['Announcements', 'Teaching', 'Community', 'Culture', 'Research', 'Events', 'Reflections'];

export default function BlogPage({ user }) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState(searchParams.get('category') || '');

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  const loadPosts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeCategory) params.set('category', activeCategory);
      const data = await apiGet(`/api/blog/posts?${params.toString()}`);
      setPosts(data.posts || []);
      setTotal(data.total || 0);
    } catch (e) {
      console.error('Failed to load blog posts:', e);
    } finally {
      setLoading(false);
    }
  }, [activeCategory]);

  useEffect(() => { loadPosts(); }, [loadPosts]);

  const handleCategoryFilter = (cat) => {
    const newCat = activeCategory === cat ? '' : cat;
    setActiveCategory(newCat);
    if (newCat) { setSearchParams({ category: newCat }); }
    else { setSearchParams({}); }
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="blog-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl sm:text-4xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Blog & News
          </h1>
          <p className="text-sm text-[#94A3B8] mt-1">Stories, insights, and updates from the commons</p>
        </div>
        {isFaculty && (
          <Button
            onClick={() => navigate('/blog/new')}
            className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs font-medium"
            data-testid="new-post-btn"
          >
            <Plus size={14} className="mr-1" /> Write Post
          </Button>
        )}
      </div>

      {/* Category Filter */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <FunnelSimple size={14} className="text-[#94A3B8] flex-shrink-0" />
        <button
          onClick={() => handleCategoryFilter('')}
          className={`px-3 py-1.5 text-[10px] rounded-full border whitespace-nowrap transition-all ${
            !activeCategory
              ? 'bg-[#D4AF37] text-[#050814] border-[#D4AF37]'
              : 'bg-transparent text-[#94A3B8] border-[#1E293B] hover:border-[#D4AF37]/30'
          }`}
          data-testid="filter-all"
        >
          All
        </button>
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => handleCategoryFilter(cat)}
            className={`px-3 py-1.5 text-[10px] rounded-full border whitespace-nowrap transition-all ${
              activeCategory === cat
                ? 'bg-[#D4AF37] text-[#050814] border-[#D4AF37]'
                : 'bg-transparent text-[#94A3B8] border-[#1E293B] hover:border-[#D4AF37]/30'
            }`}
            data-testid={`filter-${cat.toLowerCase()}`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Posts Grid */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : posts.length === 0 ? (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardContent className="p-12 text-center">
            <Newspaper size={40} weight="duotone" className="text-[#94A3B8] mx-auto mb-4" />
            <p className="text-sm text-[#94A3B8] mb-2">No posts yet{activeCategory ? ` in ${activeCategory}` : ''}</p>
            {isFaculty && (
              <Button
                onClick={() => navigate('/blog/new')}
                variant="ghost" className="text-[#D4AF37] text-xs mt-2"
              >
                Write the first post <ArrowRight size={12} className="ml-1" />
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {posts.map(post => (
            <Card
              key={post.id}
              className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/30 transition-all cursor-pointer group"
              onClick={() => navigate(`/blog/${post.slug}`)}
              data-testid={`blog-card-${post.slug}`}
            >
              {post.cover_image && (
                <div className="h-40 overflow-hidden rounded-t-lg">
                  <img src={post.cover_image} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                </div>
              )}
              <CardContent className={`p-4 ${post.cover_image ? '' : 'pt-5'}`}>
                <div className="flex items-center gap-2 mb-2">
                  {post.category && (
                    <Badge className="text-[8px] bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20">{post.category}</Badge>
                  )}
                  {post.visibility === 'members' && (
                    <Badge className="text-[8px] bg-violet-500/10 text-violet-400 border-violet-500/20">
                      <EyeSlash size={8} className="mr-0.5" /> Members
                    </Badge>
                  )}
                </div>
                <h3 className="text-sm text-[#F8FAFC] font-medium mb-1 line-clamp-2 group-hover:text-[#D4AF37] transition-colors">
                  {post.title}
                </h3>
                <p className="text-[11px] text-[#94A3B8] line-clamp-2 mb-3 leading-relaxed">{post.excerpt}</p>
                <div className="flex items-center justify-between text-[10px] text-[#64748B]">
                  <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center">
                      <span className="text-[7px] text-[#D4AF37] font-medium">
                        {post.author_name?.split(' ').map(n => n[0]).join('').slice(0, 2)}
                      </span>
                    </div>
                    <span>{post.author_name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-0.5">
                      <ChatDots size={10} /> {post.comments_count}
                    </span>
                    <span className="flex items-center gap-0.5">
                      <CalendarBlank size={10} /> {formatDate(post.created_at)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
