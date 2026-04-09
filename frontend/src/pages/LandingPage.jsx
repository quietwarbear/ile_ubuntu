import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import {
  BookOpenText, VideoCamera, UsersThree, ShieldCheck, Chats, Archive,
  ChartBar, GlobeSimple, Certificate, Rocket, ArrowRight, Quotes,
  CaretLeft, CaretRight, Star, Lightning, UsersFour, CalendarBlank, Newspaper,
} from '@phosphor-icons/react';
import { Badge } from '../components/ui/badge';

const HERO_IMG = 'https://images.unsplash.com/photo-1694286068561-3233c946e9be?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTJ8MHwxfHNlYXJjaHwxfHxhZnJpY2FuJTIwY29tbXVuaXR5JTIwbGVhcm5pbmclMjB0b2dldGhlcnxlbnwwfHx8fDE3NzUwMDYyNjh8MA&ixlib=rb-4.1.0&q=85';
const COMMUNITY_IMG = 'https://images.unsplash.com/photo-1695131497431-1ca16e3381e3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTJ8MHwxfHNlYXJjaHwzfHxhZnJpY2FuJTIwY29tbXVuaXR5JTIwbGVhcm5pbmclMjB0b2dldGhlcnxlbnwwfHx8fDE3NzUwMDYyNjh8MA&ixlib=rb-4.1.0&q=85';
const LEARNING_IMG = 'https://images.pexels.com/photos/6684506/pexels-photo-6684506.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940';
const API = process.env.REACT_APP_BACKEND_URL || "https://www.ile-ubuntu.org";

const FEATURES = [
  { icon: BookOpenText, title: 'Structured Courses', desc: 'Rich multimedia lessons with progress tracking, file attachments, and completion certificates.' },
  { icon: VideoCamera, title: 'Live Teaching', desc: 'Embedded video sessions with branded backgrounds. Schedule, host, and join from anywhere.' },
  { icon: UsersThree, title: 'Cohort Learning', desc: 'Group learners into cohorts with visual leaderboards and collective progress tracking.' },
  { icon: ShieldCheck, title: 'Knowledge Spaces', desc: 'Protected vaults with tiered access. Some wisdom deserves a gatekeeper.' },
  { icon: Chats, title: 'Community Forums', desc: 'Categorized discussions that keep conversations alive across the learning commons.' },
  { icon: Archive, title: 'Living Archives', desc: 'Curated collections preserving community knowledge for generations to come.' },
  { icon: ChartBar, title: 'Analytics Dashboard', desc: 'Enrollment trends, course performance, cohort comparisons — all exportable.' },
  { icon: GlobeSimple, title: 'Multilingual', desc: 'Full interface in English, Spanish, and Yoruba. Your language, your learning.' },
  { icon: Certificate, title: 'Certificates', desc: 'Branded PDF certificates auto-generated when you complete a course.' },
];

const TESTIMONIALS = [
  {
    quote: "The Ile Ubuntu transformed how our community shares knowledge. It's not just a platform — it's a digital village.",
    name: 'Dr. Amara Okafor',
    role: 'Elder & Community Leader',
  },
  {
    quote: "The cohort model keeps students accountable in a way I've never seen in an online platform. The leaderboard is pure motivation.",
    name: 'Prof. Kwame Mensah',
    role: 'Faculty of African Studies',
  },
  {
    quote: "I earned my first certificate last month. The protected knowledge spaces make me feel like I'm part of something sacred.",
    name: 'Fatima Diallo',
    role: 'Graduate Student',
  },
  {
    quote: "Finally, a learning platform that respects the hierarchy of wisdom. Elders lead, faculty teach, students carry it forward.",
    name: 'Oluwatobi Adeyemi',
    role: 'Assistant Instructor',
  },
];

const PILLARS = [
  { icon: UsersFour, title: '5 Governance Roles', desc: 'Student, Assistant, Faculty, Elder, Admin — each with distinct access and purpose.' },
  { icon: Lightning, title: 'Intergenerational', desc: 'Wisdom flows in all directions. Elders preserve, faculty shape, students carry forward.' },
  { icon: Rocket, title: 'Free to Start', desc: 'Begin your learning journey today. No credit card required.' },
];

export default function LandingPage({ onLogin }) {
  const navigate = useNavigate();
  const [currentTestimonial, setCurrentTestimonial] = useState(0);
  const [visibleFeatures, setVisibleFeatures] = useState(new Set());
  const [latestPosts, setLatestPosts] = useState([]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTestimonial(prev => (prev + 1) % TESTIMONIALS.length);
    }, 6000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    fetch(`${API}/api/blog/posts/public?limit=3`)
      .then(r => r.json())
      .then(d => setLatestPosts(d.posts || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          setVisibleFeatures(prev => new Set([...prev, entry.target.dataset.idx]));
        }
      });
    }, { threshold: 0.15 });

    document.querySelectorAll('[data-feature-card]').forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-[#050814] overflow-x-hidden" data-testid="landing-page">
      {/* ===== NAVBAR ===== */}
      <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-[#050814]/80 border-b border-[#1E293B]/50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-md bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center">
              <BrandMark className="w-6 h-6 object-contain" />
            </div>
            <span className="text-[#F8FAFC] text-lg tracking-wide" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              The Ile Ubuntu
            </span>
          </div>
          <div className="flex items-center gap-4">
            <a href="/blog" className="text-xs text-[#94A3B8] hover:text-[#D4AF37] transition-colors hidden sm:block">Blog</a>
            <a href="/about" className="text-xs text-[#94A3B8] hover:text-[#D4AF37] transition-colors hidden sm:block">About</a>
            <Button
              onClick={onLogin}
              className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs font-medium px-5"
              data-testid="nav-sign-in-btn"
            >
              Sign In
            </Button>
          </div>
        </div>
      </nav>

      {/* ===== HERO ===== */}
      <section className="relative min-h-screen flex items-center pt-16" data-testid="hero-section">
        <div className="absolute inset-0">
          <img src={HERO_IMG} alt="" className="w-full h-full object-cover" loading="eager" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#050814] via-[#050814]/85 to-[#050814]/60" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#050814] via-transparent to-transparent" />
        </div>

        <div className="relative z-10 max-w-6xl mx-auto px-6 py-24 lg:py-0">
          <div className="max-w-2xl">
            <p className="text-xs tracking-[0.3em] uppercase text-[#D4AF37] mb-6 animate-fade-in-up">
              A Living Learning Commons
            </p>

            <h1
              className="text-4xl sm:text-5xl lg:text-6xl font-light text-[#F8FAFC] leading-[1.1] mb-6"
              style={{ fontFamily: 'Cormorant Garamond, serif' }}
            >
              I am because <br />
              <span className="text-[#D4AF37]">we are.</span>
            </h1>

            <p className="text-base sm:text-lg text-[#94A3B8] leading-relaxed mb-4 max-w-lg" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Ubuntu — the belief that our humanity is bound together.
            </p>

            <p className="text-sm text-[#64748B] leading-relaxed mb-10 max-w-lg">
              The Ile Ubuntu is where elders preserve wisdom, faculty shape minds, and students carry knowledge forward.
              Courses, cohorts, community, and archives — woven into one coherent environment for learning that honors
              tradition and embraces the future.
            </p>

            <div className="flex flex-wrap items-center gap-4">
              <Button
                onClick={onLogin}
                size="lg"
                className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] font-medium text-sm px-8 py-6 rounded-md group"
                data-testid="hero-cta-btn"
              >
                Begin Your Journey
                <ArrowRight size={16} className="ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>
              <span className="text-xs text-[#64748B]">Free to start. No credit card required.</span>
            </div>

            <div className="flex items-center gap-6 mt-12 pt-8 border-t border-[#1E293B]/50">
              {[
                { num: '16+', label: 'Features' },
                { num: '5', label: 'Governance Roles' },
                { num: '3', label: 'Languages' },
              ].map(s => (
                <div key={s.label}>
                  <p className="text-2xl font-light text-[#D4AF37]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{s.num}</p>
                  <p className="text-[10px] uppercase tracking-wider text-[#64748B]">{s.label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===== PHILOSOPHY ===== */}
      <section className="relative py-24" data-testid="philosophy-section">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <p className="text-xs tracking-[0.25em] uppercase text-[#D4AF37] mb-4">Our Philosophy</p>
              <h2
                className="text-3xl sm:text-4xl font-light text-[#F8FAFC] leading-tight mb-6"
                style={{ fontFamily: 'Cormorant Garamond, serif' }}
              >
                Not another LMS. <br />
                A <span className="text-[#D4AF37]">schoolhouse</span> for the digital age.
              </h2>
              <p className="text-sm text-[#94A3B8] leading-relaxed mb-8">
                Most learning platforms treat education as content delivery. The Ile Ubuntu treats it as
                community building. Here, a student can grow into an assistant, an assistant into faculty,
                and faculty into an elder. Knowledge isn't consumed — it's cultivated, protected, and passed on.
              </p>

              <div className="space-y-4">
                {PILLARS.map(p => {
                  const Icon = p.icon;
                  return (
                    <div key={p.title} className="flex items-start gap-4 p-4 bg-[#0A1128] border border-[#1E293B] rounded-lg">
                      <div className="w-10 h-10 rounded-md bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center flex-shrink-0">
                        <Icon size={18} weight="duotone" className="text-[#D4AF37]" />
                      </div>
                      <div>
                        <h3 className="text-sm text-[#F8FAFC] font-medium mb-1">{p.title}</h3>
                        <p className="text-xs text-[#94A3B8] leading-relaxed">{p.desc}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="relative">
              <div className="rounded-xl overflow-hidden border border-[#1E293B]">
                <img
                  src={COMMUNITY_IMG}
                  alt="Community learning"
                  className="w-full h-[480px] object-cover"
                  loading="lazy"
                />
              </div>
              <div className="absolute -bottom-6 -left-6 bg-[#0F172A] border border-[#D4AF37]/20 rounded-lg p-5 max-w-[240px]">
                <p className="text-xs text-[#D4AF37] italic leading-relaxed" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  "If you want to go fast, go alone. If you want to go far, go together."
                </p>
                <p className="text-[10px] text-[#64748B] mt-2">— African Proverb</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== FEATURES ===== */}
      <section className="py-24 bg-[#0A1128]/50" data-testid="features-section">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-xs tracking-[0.25em] uppercase text-[#D4AF37] mb-4">Platform Features</p>
            <h2
              className="text-3xl sm:text-4xl font-light text-[#F8FAFC]"
              style={{ fontFamily: 'Cormorant Garamond, serif' }}
            >
              Everything a learning community needs
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              const isVisible = visibleFeatures.has(String(i));
              return (
                <div
                  key={f.title}
                  data-feature-card
                  data-idx={i}
                  className={`group p-5 bg-[#0F172A] border border-[#1E293B] rounded-lg hover:border-[#D4AF37]/30 transition-all duration-500 ${
                    isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
                  }`}
                  style={{ transitionDelay: `${(i % 3) * 100}ms` }}
                  data-testid={`feature-card-${f.title.toLowerCase().replace(/\s+/g, '-')}`}
                >
                  <div className="w-10 h-10 rounded-md bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center mb-4 group-hover:bg-[#D4AF37]/20 transition-colors">
                    <Icon size={18} weight="duotone" className="text-[#D4AF37]" />
                  </div>
                  <h3 className="text-sm text-[#F8FAFC] font-medium mb-2">{f.title}</h3>
                  <p className="text-xs text-[#94A3B8] leading-relaxed">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ===== SOCIAL PROOF / TESTIMONIALS ===== */}
      <section className="py-24" data-testid="testimonials-section">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div className="relative rounded-xl overflow-hidden border border-[#1E293B]">
              <img
                src={LEARNING_IMG}
                alt="Students learning"
                className="w-full h-[400px] object-cover"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#050814] via-transparent to-transparent" />
            </div>

            <div>
              <p className="text-xs tracking-[0.25em] uppercase text-[#D4AF37] mb-4">What People Say</p>
              <h2
                className="text-3xl sm:text-4xl font-light text-[#F8FAFC] mb-10"
                style={{ fontFamily: 'Cormorant Garamond, serif' }}
              >
                Voices from <span className="text-[#D4AF37]">the commons</span>
              </h2>

              <div className="relative min-h-[180px]">
                {TESTIMONIALS.map((t, i) => (
                  <div
                    key={t.name}
                    className={`absolute inset-0 transition-all duration-700 ${
                      i === currentTestimonial ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-8 pointer-events-none'
                    }`}
                  >
                    <Quotes size={28} weight="fill" className="text-[#D4AF37]/30 mb-4" />
                    <blockquote
                      className="text-base text-[#F8FAFC] leading-relaxed mb-6 italic"
                      style={{ fontFamily: 'Cormorant Garamond, serif' }}
                    >
                      "{t.quote}"
                    </blockquote>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center">
                        <span className="text-xs text-[#D4AF37] font-medium">
                          {t.name.split(' ').map(n => n[0]).join('')}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm text-[#F8FAFC]">{t.name}</p>
                        <p className="text-[10px] text-[#94A3B8]">{t.role}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-3 mt-8">
                <button
                  onClick={() => setCurrentTestimonial((currentTestimonial - 1 + TESTIMONIALS.length) % TESTIMONIALS.length)}
                  className="w-8 h-8 rounded-full border border-[#1E293B] flex items-center justify-center text-[#94A3B8] hover:text-[#D4AF37] hover:border-[#D4AF37]/30 transition-colors"
                  data-testid="testimonial-prev"
                >
                  <CaretLeft size={14} />
                </button>
                <div className="flex gap-1.5">
                  {TESTIMONIALS.map((_, i) => (
                    <button
                      key={`dot-${i}`}
                      onClick={() => setCurrentTestimonial(i)}
                      className={`w-1.5 h-1.5 rounded-full transition-all ${
                        i === currentTestimonial ? 'bg-[#D4AF37] w-4' : 'bg-[#1E293B]'
                      }`}
                    />
                  ))}
                </div>
                <button
                  onClick={() => setCurrentTestimonial((currentTestimonial + 1) % TESTIMONIALS.length)}
                  className="w-8 h-8 rounded-full border border-[#1E293B] flex items-center justify-center text-[#94A3B8] hover:text-[#D4AF37] hover:border-[#D4AF37]/30 transition-colors"
                  data-testid="testimonial-next"
                >
                  <CaretRight size={14} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== HOW IT WORKS ===== */}
      <section className="py-24 bg-[#0A1128]/50" data-testid="how-it-works-section">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-xs tracking-[0.25em] uppercase text-[#D4AF37] mb-4">How It Works</p>
            <h2
              className="text-3xl sm:text-4xl font-light text-[#F8FAFC]"
              style={{ fontFamily: 'Cormorant Garamond, serif' }}
            >
              Your path through the commons
            </h2>
          </div>

          <div className="grid sm:grid-cols-4 gap-6">
            {[
              { step: '01', title: 'Sign In', desc: 'Create your free account with one click via Google OAuth.' },
              { step: '02', title: 'Explore Courses', desc: 'Browse structured courses, enroll, and start learning at your pace.' },
              { step: '03', title: 'Join a Cohort', desc: 'Learn with peers. Track collective progress on the leaderboard.' },
              { step: '04', title: 'Grow Your Role', desc: 'From student to assistant, faculty, and beyond. Your journey evolves.' },
            ].map(s => (
              <div key={s.step} className="text-center group">
                <div className="w-14 h-14 rounded-full border-2 border-[#D4AF37]/20 flex items-center justify-center mx-auto mb-4 group-hover:border-[#D4AF37]/60 group-hover:bg-[#D4AF37]/5 transition-all">
                  <span className="text-lg text-[#D4AF37] font-light" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{s.step}</span>
                </div>
                <h3 className="text-sm text-[#F8FAFC] font-medium mb-2">{s.title}</h3>
                <p className="text-xs text-[#94A3B8] leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== LATEST FROM THE COMMONS (Blog) ===== */}
      {latestPosts.length > 0 && (
        <section className="py-24" data-testid="latest-posts-section">
          <div className="max-w-6xl mx-auto px-6">
            <div className="flex items-center justify-between mb-10">
              <div>
                <p className="text-xs tracking-[0.25em] uppercase text-[#D4AF37] mb-3">Latest from the Commons</p>
                <h2 className="text-3xl sm:text-4xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  Stories & Insights
                </h2>
              </div>
              <Button
                variant="ghost"
                onClick={() => navigate('/blog')}
                className="text-[#D4AF37] hover:text-[#F3E5AB] text-xs"
                data-testid="view-all-posts-btn"
              >
                View All <ArrowRight size={12} className="ml-1" />
              </Button>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {latestPosts.map(post => (
                <Card
                  key={post.id}
                  className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/30 transition-all cursor-pointer group"
                  onClick={onLogin}
                  data-testid={`landing-post-${post.slug}`}
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
                    <h3 className="text-sm text-[#F8FAFC] font-medium mb-1 line-clamp-2 group-hover:text-[#D4AF37] transition-colors">{post.title}</h3>
                    <p className="text-[11px] text-[#94A3B8] line-clamp-2 mb-3">{post.excerpt}</p>
                    <div className="flex items-center justify-between text-[10px] text-[#64748B]">
                      <span>{post.author_name}</span>
                      <span className="flex items-center gap-0.5">
                        <CalendarBlank size={10} />
                        {new Date(post.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ===== FINAL CTA ===== */}
      <section className="py-24" data-testid="final-cta-section">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <div className="w-16 h-16 mx-auto rounded-lg bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center mb-8">
            <BrandMark className="w-10 h-10 object-contain" />
          </div>

          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-light text-[#F8FAFC] leading-tight mb-6"
            style={{ fontFamily: 'Cormorant Garamond, serif' }}
          >
            Ready to join the <span className="text-[#D4AF37]">commons</span>?
          </h2>

          <p className="text-sm text-[#94A3B8] leading-relaxed mb-10 max-w-lg mx-auto">
            Start with a free Explorer account. Discover courses, connect with community,
            and begin your journey in a platform built on the belief that knowledge grows when shared.
          </p>

          <Button
            onClick={onLogin}
            size="lg"
            className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] font-medium text-sm px-10 py-6 rounded-md group"
            data-testid="final-cta-btn"
          >
            Get Started — It's Free
            <ArrowRight size={16} className="ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>

          <p className="text-[10px] text-[#64748B] mt-4">No credit card required. Start learning in seconds.</p>
        </div>
      </section>

      {/* ===== FOOTER ===== */}
      <footer className="border-t border-[#1E293B]/50 py-12" data-testid="landing-footer">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-md bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center">
                <BrandMark className="w-5 h-5 object-contain" />
              </div>
              <span className="text-sm text-[#94A3B8]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                The Ile Ubuntu
              </span>
            </div>
            <div className="flex items-center gap-6">
              <a href="/about" className="text-xs text-[#64748B] hover:text-[#D4AF37] transition-colors">About</a>
              <button onClick={onLogin} className="text-xs text-[#64748B] hover:text-[#D4AF37] transition-colors">Sign In</button>
            </div>
            <p className="text-[10px] text-[#475569]">
              &copy; {new Date().getFullYear()} The Ile Ubuntu. A Living Learning Commons.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
