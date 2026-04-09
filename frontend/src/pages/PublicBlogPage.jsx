import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import BrandMark from '../components/brand/BrandMark';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  ChatDots, CalendarBlank, FunnelSimple, ArrowLeft, ArrowRight, Newspaper,
} from '@phosphor-icons/react';

const API = process.env.REACT_APP_BACKEND_URL || "https://www.ile-ubuntu.org";
const CATEGORIES = ['Announcements', 'Teaching', 'Community', 'Culture', 'Research', 'Events', 'Reflections'];

export default function PublicBlogPage({ onLogin }) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState(searchParams.get('category') || '');

  const loadPosts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeCategory) params.set('category', activeCategory);
      const res = await fetch(`${API}/api/blog/posts/public?${params.toString()}`);
      const data = await res.json();
      setPosts(data.posts || []);
    } catch (e) { console.error('Failed to load posts:', e); }
    finally { setLoading(false); }
  }, [activeCategory]);

  useEffect(() => { loadPosts(); }, [loadPosts]);

  const handleCategoryFilter = (cat) => {
    const newCat = activeCategory === cat ? '' : cat;
    setActiveCategory(newCat);
    if (newCat) { setSearchParams({ category: newCat }); } else { setSearchParams({}); }
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-[#050814]" data-testid="public-blog-page">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[#050814]/80 border-b border-[#1E293B]/50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-9 h-9 rounded-md bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center">
              <BrandMark className="w-6 h-6 object-contain" />
            </div>
            <span className="text-[#F8FAFC] text-lg tracking-wide" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              The Ile Ubuntu
            </span>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="text-xs text-[#94A3B8] hover:text-[#D4AF37] transition-colors">Home</button>
            <Button onClick={onLogin} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs px-5" data-testid="public-blog-signin">
              Sign In
            </Button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-light text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Blog & News
          </h1>
          <p className="text-sm text-[#94A3B8]">Stories, insights, and updates from the commons</p>
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 mb-8">
          <FunnelSimple size={14} className="text-[#94A3B8] flex-shrink-0" />
          <button
            onClick={() => handleCategoryFilter('')}
            className={`px-3 py-1.5 text-[10px] rounded-full border whitespace-nowrap transition-all ${
              !activeCategory ? 'bg-[#D4AF37] text-[#050814] border-[#D4AF37]' : 'text-[#94A3B8] border-[#1E293B] hover:border-[#D4AF37]/30'
            }`}
          >All</button>
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => handleCategoryFilter(cat)}
              className={`px-3 py-1.5 text-[10px] rounded-full border whitespace-nowrap transition-all ${
                activeCategory === cat ? 'bg-[#D4AF37] text-[#050814] border-[#D4AF37]' : 'text-[#94A3B8] border-[#1E293B] hover:border-[#D4AF37]/30'
              }`}
            >{cat}</button>
          ))}
        </div>

        {/* Posts */}
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : posts.length === 0 ? (
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-12 text-center">
              <Newspaper size={40} weight="duotone" className="text-[#94A3B8] mx-auto mb-4" />
              <p className="text-sm text-[#94A3B8] mb-4">No public posts yet. Check back soon!</p>
              <Button onClick={onLogin} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs">
                Sign in to see all content <ArrowRight size={12} className="ml-1" />
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {posts.map(post => (
              <Card
                key={post.id}
                className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/30 transition-all cursor-pointer group"
                onClick={onLogin}
                data-testid={`public-blog-card-${post.slug}`}
              >
                {post.cover_image && (
                  <div className="h-40 overflow-hidden rounded-t-lg">
                    <img src={post.cover_image} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                  </div>
                )}
                <CardContent className={`p-4 ${post.cover_image ? '' : 'pt-5'}`}>
                  {post.category && (
                    <Badge className="text-[8px] bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20 mb-2">{post.category}</Badge>
                  )}
                  <h3 className="text-sm text-[#F8FAFC] font-medium mb-1 line-clamp-2 group-hover:text-[#D4AF37] transition-colors">
                    {post.title}
                  </h3>
                  <p className="text-[11px] text-[#94A3B8] line-clamp-2 mb-3">{post.excerpt}</p>
                  <div className="flex items-center justify-between text-[10px] text-[#64748B]">
                    <span>{post.author_name}</span>
                    <span className="flex items-center gap-0.5">
                      <CalendarBlank size={10} /> {formatDate(post.created_at)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* CTA */}
        <div className="mt-12 text-center">
          <p className="text-sm text-[#94A3B8] mb-4">Sign in to read members-only content and join the conversation.</p>
          <Button onClick={onLogin} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-sm px-8" data-testid="public-blog-cta">
            Join The Ile Ubuntu <ArrowRight size={14} className="ml-2" />
          </Button>
        </div>
      </div>
    </div>
  );
}
