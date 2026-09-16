import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import BrandMark from '../components/brand/BrandMark';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  ChatDots, CalendarBlank, FunnelSimple, ArrowLeft, ArrowRight, Newspaper,
} from '@phosphor-icons/react';

const API = process.env.REACT_APP_BACKEND_URL || "https://ileubuntu-production.up.railway.app";
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
    <div className="min-h-screen bg-[rgb(var(--ink-deep))]" data-testid="public-blog-page">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[rgb(var(--ink-deep)/0.8)] border-b border-[rgb(var(--ink-border)/0.5)]">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-9 h-9 rounded-md bg-[rgb(var(--gold)/0.1)] border border-[rgb(var(--gold)/0.2)] flex items-center justify-center">
              <BrandMark className="w-6 h-6 object-contain" />
            </div>
            <span className="text-[rgb(var(--text-main))] text-lg tracking-wide" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              The Ile Ubuntu
            </span>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/')} className="text-xs text-[rgb(var(--text-muted))] hover:text-[rgb(var(--gold))] transition-colors">Home</button>
            <Button onClick={onLogin} className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-xs px-5" data-testid="public-blog-signin">
              Sign In
            </Button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-light text-[rgb(var(--text-main))] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Blog & News
          </h1>
          <p className="text-sm text-[rgb(var(--text-muted))]">Stories, insights, and updates from the commons</p>
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 mb-8">
          <FunnelSimple size={14} className="text-[rgb(var(--text-muted))] flex-shrink-0" />
          <button
            onClick={() => handleCategoryFilter('')}
            className={`px-3 py-1.5 text-[10px] rounded-full border whitespace-nowrap transition-all ${
              !activeCategory ? 'bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] border-[rgb(var(--gold))]' : 'text-[rgb(var(--text-muted))] border-[rgb(var(--ink-border))] hover:border-[rgb(var(--gold)/0.3)]'
            }`}
          >All</button>
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => handleCategoryFilter(cat)}
              className={`px-3 py-1.5 text-[10px] rounded-full border whitespace-nowrap transition-all ${
                activeCategory === cat ? 'bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] border-[rgb(var(--gold))]' : 'text-[rgb(var(--text-muted))] border-[rgb(var(--ink-border))] hover:border-[rgb(var(--gold)/0.3)]'
              }`}
            >{cat}</button>
          ))}
        </div>

        {/* Posts */}
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-2 border-[rgb(var(--gold))] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : posts.length === 0 ? (
          <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
            <CardContent className="p-12 text-center">
              <Newspaper size={40} weight="duotone" className="text-[rgb(var(--text-muted))] mx-auto mb-4" />
              <p className="text-sm text-[rgb(var(--text-muted))] mb-4">No public posts yet. Check back soon!</p>
              <Button onClick={onLogin} className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-xs">
                Sign in to see all content <ArrowRight size={12} className="ml-1" />
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {posts.map(post => (
              <Card
                key={post.id}
                className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))] hover:border-[rgb(var(--gold)/0.3)] transition-all cursor-pointer group"
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
                    <Badge className="text-[8px] bg-[rgb(var(--gold)/0.1)] text-[rgb(var(--gold))] border-[rgb(var(--gold)/0.2)] mb-2">{post.category}</Badge>
                  )}
                  <h3 className="text-sm text-[rgb(var(--text-main))] font-medium mb-1 line-clamp-2 group-hover:text-[rgb(var(--gold))] transition-colors">
                    {post.title}
                  </h3>
                  <p className="text-[11px] text-[rgb(var(--text-muted))] line-clamp-2 mb-3">{post.excerpt}</p>
                  <div className="flex items-center justify-between text-[10px] text-[rgb(var(--text-dim))]">
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
          <p className="text-sm text-[rgb(var(--text-muted))] mb-4">Sign in to read members-only content and join the conversation.</p>
          <Button onClick={onLogin} className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-sm px-8" data-testid="public-blog-cta">
            Join The Ile Ubuntu <ArrowRight size={14} className="ml-2" />
          </Button>
        </div>
      </div>
    </div>
  );
}
