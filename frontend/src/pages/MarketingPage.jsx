import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  InstagramLogo, TwitterLogo, LinkedinLogo, Lightning, ArrowLeft,
  BookOpenText, VideoCamera, UsersThree, ShieldCheck, Chats, Archive,
  ChartBar, MagnifyingGlass, CreditCard, Envelope, FilmSlate, GlobeSimple,
  Bell, Certificate, UsersFour, Rocket, Check, DownloadSimple,
} from '@phosphor-icons/react';
import { useNavigate } from 'react-router-dom';

const BRAND = {
  primary: '#D4AF37',
  dark: '#050814',
  navy: '#0A1128',
  card: '#0F172A',
  light: '#F8FAFC',
  muted: '#94A3B8',
  border: '#1E293B',
};

const ALL_FEATURES = [
  { icon: BookOpenText, name: 'Course Management', detail: 'Create, manage, and enroll in structured courses with lessons, file attachments, markdown/media content, and progress tracking.' },
  { icon: VideoCamera, name: 'Live Teaching (Jitsi)', detail: 'Embedded video conferencing with branded backgrounds. Schedule, host, and join live sessions seamlessly.' },
  { icon: UsersThree, name: 'Cohort-Based Learning', detail: 'Group learners into cohorts with linked courses. Visual leaderboards with per-course progress breakdowns.' },
  { icon: ShieldCheck, name: 'Knowledge Spaces', detail: 'Protected knowledge vaults with 4 access levels: public, members, faculty, elders. Request/approval workflow.' },
  { icon: Chats, name: 'Community Forums', detail: 'Categorized discussions with posts, replies, likes. Keep conversations organized across the learning commons.' },
  { icon: Archive, name: 'Archives', detail: 'Public and restricted archives. Faculty-curated collections preserving community knowledge.' },
  { icon: ChartBar, name: 'Analytics Dashboard', detail: 'Enrollment trends, course performance rankings, cohort comparisons, community activity metrics. CSV export.' },
  { icon: MagnifyingGlass, name: 'Cross-Platform Search', detail: 'Instant search across courses, posts, archives, cohorts, and spaces with faceted filters and categorized results.' },
  { icon: CreditCard, name: 'Stripe Subscriptions', detail: '3 membership tiers (Explorer/Scholar/Elder Circle) with strict backend gating and upgrade prompts.' },
  { icon: Envelope, name: 'Email Notifications', detail: 'Branded HTML emails via Resend for enrollment confirmations, cohort joins, and session reminders.' },
  { icon: FilmSlate, name: 'Session Records', detail: 'Review past live sessions with attendee tracking, notes, key takeaways, tags, and CSV export.' },
  { icon: GlobeSimple, name: 'Multilingual (i18n)', detail: 'Full interface in English, Spanish, and Yoruba. Language preference saved per user.' },
  { icon: Bell, name: 'PWA Push Notifications', detail: 'Browser push notifications for real-time updates on enrollments, cohort activity, and community events.' },
  { icon: Certificate, name: 'Course Certificates', detail: 'Auto-generated branded PDF certificates on course completion. Downloadable from dashboard and course pages.' },
  { icon: UsersFour, name: '5-Role Governance', detail: 'Student, Assistant, Faculty, Elder, Admin — differentiated access and capabilities across the platform.' },
  { icon: Rocket, name: 'Guided Onboarding', detail: '5-step wizard for new students: welcome, interests, course browse, cohort discovery, completion.' },
];

const SOCIAL_POSTS = {
  instagram: {
    icon: InstagramLogo,
    color: 'text-pink-400',
    platform: 'Instagram',
    posts: [
      {
        type: 'Launch Announcement',
        caption: `Introducing The Ile Ubuntu ☥

A Living Learning Commons where courses, cohorts, and community converge under one digital roof.

Live teaching sessions · Protected knowledge spaces · Progress tracking with leaderboards · Multilingual (EN/ES/YO)

All wrapped in midnight blue & gold.

#TheIleUbuntu #LivingLearningCommons #Ubuntu #EdTech #OnlineLearning #AfricanWisdom #CommunityLearning #DigitalClassroom #KnowledgeKeepers`,
      },
      {
        type: 'Feature Spotlight',
        caption: `Knowledge isn't just stored. It's protected. ☥

The Ile Ubuntu features tiered Knowledge Spaces — from public resources to elder-only vaults. Access is earned, not assumed.

Because some wisdom deserves a gatekeeper.

#KnowledgeSpaces #ProtectedWisdom #TheIleUbuntu #EdTech #CulturalPreservation`,
      },
      {
        type: 'Community Post',
        caption: `Learning alone? That's not Ubuntu.

The Ile Ubuntu brings cohort-based learning with leaderboards, community forums, and live video sessions — because growth happens together.

Join a cohort. Find your people. Learn forward.

#CohortLearning #Ubuntu #TheIleUbuntu #LearnTogether #Community`,
      },
    ],
  },
  twitter: {
    icon: TwitterLogo,
    color: 'text-sky-400',
    platform: 'X (Twitter)',
    posts: [
      {
        type: 'Thread Opener',
        caption: `The Ile Ubuntu isn't another LMS.

It's a Living Learning Commons — courses, cohorts, live teaching, archives, and community in one platform.

5 governance roles. 3 membership tiers. 3 languages. 16+ features.

Built for communities that value intergenerational knowledge transfer. 🧵`,
      },
      {
        type: 'Single Tweet',
        caption: `"I am because we are."

That's the philosophy behind The Ile Ubuntu — a platform where elders preserve wisdom, faculty shape minds, and students carry it forward.

Live video · Cohorts · Protected spaces · Certificates · Analytics

theileubuntu.com ☥`,
      },
      {
        type: 'Engagement Tweet',
        caption: `What if your learning platform had:
- Role-based governance (student → elder)
- Protected knowledge vaults
- Live teaching w/ branded backgrounds  
- Cohort leaderboards
- Auto-generated certificates
- 3 languages (EN/ES/YO)

That's The Ile Ubuntu. And it's real. ☥`,
      },
    ],
  },
  linkedin: {
    icon: LinkedinLogo,
    color: 'text-blue-400',
    platform: 'LinkedIn',
    posts: [
      {
        type: 'Thought Leadership',
        caption: `We didn't build another LMS.

We built The Ile Ubuntu — a Living Learning Commons designed for communities that value intergenerational knowledge transfer.

Here's what makes it different:

→ 5 governance roles (Student, Assistant, Faculty, Elder, Admin)
→ 3 membership tiers with Stripe-powered subscriptions
→ Live video teaching with Jitsi Meet integration
→ Protected knowledge spaces with tiered access
→ Cohort-based learning with visual leaderboards
→ Full analytics dashboard with CSV export
→ Branded PDF certificates on course completion
→ Email notifications for key platform events
→ Cross-platform search with faceted filters
→ Multilingual: English, Spanish, Yoruba
→ PWA with push notifications
→ Guided onboarding for new learners

The tech stack: React, FastAPI, MongoDB, Tailwind CSS, Jitsi, Stripe, Resend, Google APIs.

Built for elders who preserve wisdom, faculty who shape minds, and students who carry it forward.

#EdTech #LearningPlatform #Ubuntu #CommunityFirst #DigitalTransformation #OnlineLearning #AfricanWisdom`,
      },
      {
        type: 'Announcement Post',
        caption: `Excited to share something we've been building: The Ile Ubuntu.

It's a Living Learning Commons — think of it as the digital equivalent of a community schoolhouse where wisdom flows in all directions.

Key differentiators:
• Not just courses — cohorts, archives, and protected knowledge spaces
• Not just content — live teaching, community forums, and session records
• Not just access — role-based governance respecting the wisdom hierarchy
• Not just English — multilingual (EN, ES, Yoruba)

If you believe learning should be communal, not just individual, I'd love your thoughts.

#EdTech #TheIleUbuntu #Ubuntu #LivingLearningCommons`,
      },
    ],
  },
};

const HASHTAG_BANK = [
  '#TheIleUbuntu', '#LivingLearningCommons', '#Ubuntu', '#EdTech',
  '#OnlineLearning', '#AfricanWisdom', '#CommunityLearning', '#LearnTogether',
  '#DigitalClassroom', '#KnowledgeKeepers', '#CulturalPreservation',
  '#CohortLearning', '#IntergenerationalWisdom', '#EdTechInnovation',
  '#CommunityFirst', '#DigitalTransformation', '#LearningPlatform',
];

export default function MarketingPage() {
  const navigate = useNavigate();

  const handlePrint = () => window.print();

  return (
    <div className="space-y-8 animate-fade-in-up" data-testid="marketing-page">
      {/* Header */}
      <div className="flex items-center justify-between print:hidden">
        <div>
          <button onClick={() => navigate('/dashboard')} className="text-xs text-[#94A3B8] hover:text-[#D4AF37] flex items-center gap-1 mb-2">
            <ArrowLeft size={12} /> Back to Dashboard
          </button>
          <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Marketing & Branding
          </h1>
          <p className="text-sm text-[#94A3B8]">Strategy, copy, and feature summary for The Ile Ubuntu</p>
        </div>
        <button
          onClick={handlePrint}
          className="px-4 py-2 bg-[#D4AF37]/10 border border-[#D4AF37]/30 text-[#D4AF37] rounded-md text-xs hover:bg-[#D4AF37]/20 transition-all flex items-center gap-2"
          data-testid="print-marketing-btn"
        >
          <DownloadSimple size={14} /> Print / Save PDF
        </button>
      </div>

      {/* ==================== ONE-PAGER ==================== */}
      <div data-testid="one-pager-section">
        <div className="flex items-center gap-2 mb-4">
          <Rocket size={16} weight="duotone" className="text-[#D4AF37]" />
          <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37]">Platform One-Pager</h2>
        </div>

        {/* Brand Identity */}
        <Card className="bg-[#0F172A] border-[#1E293B] mb-4">
          <CardContent className="p-5">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/30 flex items-center justify-center flex-shrink-0">
                <span className="text-3xl text-[#D4AF37]">&#9775;</span>
              </div>
              <div>
                <h3 className="text-lg text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>The Ile Ubuntu</h3>
                <p className="text-xs text-[#D4AF37]">A Living Learning Commons</p>
                <p className="text-[10px] text-[#94A3B8] mt-1">
                  "I am because we are" — a platform where elders preserve wisdom, faculty shape minds, and students carry it forward.
                </p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-2 rounded bg-[#050814] border border-[#1E293B]">
                <div className="w-6 h-6 rounded mx-auto mb-1" style={{ background: BRAND.primary }} />
                <p className="text-[9px] text-[#94A3B8]">Gold {BRAND.primary}</p>
              </div>
              <div className="p-2 rounded bg-[#050814] border border-[#1E293B]">
                <div className="w-6 h-6 rounded mx-auto mb-1" style={{ background: BRAND.navy }} />
                <p className="text-[9px] text-[#94A3B8]">Navy {BRAND.navy}</p>
              </div>
              <div className="p-2 rounded bg-[#050814] border border-[#1E293B]">
                <div className="w-6 h-6 rounded mx-auto mb-1" style={{ background: BRAND.dark }} />
                <p className="text-[9px] text-[#94A3B8]">Dark {BRAND.dark}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* All Features List */}
        <Card className="bg-[#0F172A] border-[#1E293B] mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              16 Platform Features
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {ALL_FEATURES.map((f) => {
                const Icon = f.icon;
                return (
                  <div key={f.name} className="flex items-start gap-2 p-2 rounded bg-[#050814] border border-[#1E293B]" data-testid={`onepager-feature-${f.name.toLowerCase().replace(/\s+/g, '-')}`}>
                    <Icon size={14} weight="duotone" className="text-[#D4AF37] mt-0.5 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-[11px] text-[#F8FAFC] font-medium">{f.name}</p>
                      <p className="text-[9px] text-[#94A3B8] leading-relaxed">{f.detail}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          {[
            { label: 'Features', value: '16+' },
            { label: 'Roles', value: '5' },
            { label: 'Tiers', value: '3' },
            { label: 'Languages', value: '3' },
          ].map((s) => (
            <Card key={s.label} className="bg-[#0F172A] border-[#1E293B]">
              <CardContent className="p-3 text-center">
                <p className="text-xl font-bold text-[#D4AF37]">{s.value}</p>
                <p className="text-[9px] text-[#94A3B8] uppercase tracking-wider">{s.label}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Membership Tiers Summary */}
        <Card className="bg-[#0F172A] border-[#1E293B] mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Membership Tiers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {[
                { name: 'Explorer', price: 'Free', highlights: ['2 courses', 'Community', 'Public archives'] },
                { name: 'Scholar', price: '$19.99/mo', highlights: ['Unlimited courses', 'Cohorts', 'Knowledge spaces'] },
                { name: 'Elder Circle', price: '$49.99/mo', highlights: ['Live teaching', 'Protected archives', 'Governance'] },
              ].map((t) => (
                <div key={t.name} className="p-3 rounded bg-[#050814] border border-[#1E293B] text-center">
                  <p className="text-sm text-[#D4AF37] font-medium">{t.name}</p>
                  <p className="text-base font-bold text-[#F8FAFC]">{t.price}</p>
                  <div className="mt-2 space-y-1">
                    {t.highlights.map((h, i) => (
                      <p key={i} className="text-[9px] text-[#94A3B8] flex items-center gap-1 justify-center">
                        <Check size={8} className="text-[#D4AF37]" /> {h}
                      </p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Tech Stack */}
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Technology Stack
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {['React', 'FastAPI', 'MongoDB', 'Tailwind CSS', 'Jitsi Meet', 'Stripe', 'Resend', 'Google APIs', 'PWA', 'Service Workers', 'i18n'].map(tech => (
                <span key={tech} className="px-3 py-1 text-[10px] bg-[#050814] border border-[#1E293B] rounded-full text-[#94A3B8]">{tech}</span>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ==================== SOCIAL MEDIA STRATEGY ==================== */}
      <div data-testid="social-strategy-section">
        <div className="flex items-center gap-2 mb-4">
          <Lightning size={16} weight="duotone" className="text-[#D4AF37]" />
          <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37]">Social Media Branding Strategy</h2>
        </div>

        {/* Brand Voice */}
        <Card className="bg-[#0F172A] border-[#1E293B] mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Brand Voice & Guidelines
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3 rounded bg-[#050814] border border-[#1E293B]">
                <p className="text-[10px] text-[#D4AF37] uppercase tracking-wider mb-1">Tone</p>
                <p className="text-xs text-[#F8FAFC]">Wise, warm, dignified</p>
                <p className="text-[9px] text-[#94A3B8] mt-1">Speak as an elder sharing knowledge — authoritative yet inviting.</p>
              </div>
              <div className="p-3 rounded bg-[#050814] border border-[#1E293B]">
                <p className="text-[10px] text-[#D4AF37] uppercase tracking-wider mb-1">Visual Identity</p>
                <p className="text-xs text-[#F8FAFC]">Midnight blue, black & gold</p>
                <p className="text-[9px] text-[#94A3B8] mt-1">Ankh symbol. Serif headings. Clean, reverent aesthetic.</p>
              </div>
              <div className="p-3 rounded bg-[#050814] border border-[#1E293B]">
                <p className="text-[10px] text-[#D4AF37] uppercase tracking-wider mb-1">Core Message</p>
                <p className="text-xs text-[#F8FAFC]">"I am because we are"</p>
                <p className="text-[9px] text-[#94A3B8] mt-1">Learning is communal. Knowledge flows between generations.</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Platform-Specific Copy */}
        {Object.entries(SOCIAL_POSTS).map(([key, platform]) => {
          const Icon = platform.icon;
          return (
            <Card key={key} className="bg-[#0F172A] border-[#1E293B] mb-4" data-testid={`social-${key}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  <Icon size={20} weight="duotone" className={platform.color} />
                  {platform.platform}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {platform.posts.map((post, i) => (
                  <div key={i} className="p-3 rounded bg-[#050814] border border-[#1E293B]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] text-[#D4AF37] uppercase tracking-wider">{post.type}</span>
                      <button
                        onClick={() => navigator.clipboard.writeText(post.caption)}
                        className="text-[9px] text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
                        data-testid={`copy-${key}-${i}`}
                      >
                        Copy
                      </button>
                    </div>
                    <p className="text-xs text-[#F8FAFC] whitespace-pre-line leading-relaxed">{post.caption}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}

        {/* Hashtag Bank */}
        <Card className="bg-[#0F172A] border-[#1E293B] mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Hashtag Bank
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {HASHTAG_BANK.map((tag) => (
                <button
                  key={tag}
                  onClick={() => navigator.clipboard.writeText(tag)}
                  className="px-2.5 py-1 text-[10px] bg-[#050814] border border-[#D4AF37]/20 text-[#D4AF37] rounded-full hover:bg-[#D4AF37]/10 transition-all cursor-pointer"
                >
                  {tag}
                </button>
              ))}
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(HASHTAG_BANK.join(' '))}
              className="mt-3 text-[10px] text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
              data-testid="copy-all-hashtags"
            >
              Copy all hashtags
            </button>
          </CardContent>
        </Card>

        {/* Content Calendar Suggestions */}
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Content Calendar Themes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                { week: 'Week 1', theme: 'Platform Launch', desc: 'Announce The Ile Ubuntu. Share the vision, elevator pitch, and hero imagery.' },
                { week: 'Week 2', theme: 'Feature Deep Dives', desc: 'Spotlight 1 feature per day — live teaching, knowledge spaces, cohorts, etc.' },
                { week: 'Week 3', theme: 'Community Stories', desc: 'Share user testimonials, cohort success stories, and elder wisdom quotes.' },
                { week: 'Week 4', theme: 'Behind the Build', desc: 'Tech stack breakdown, design decisions, cultural inspirations behind the platform.' },
              ].map((w) => (
                <div key={w.week} className="p-3 rounded bg-[#050814] border border-[#1E293B]">
                  <p className="text-[10px] text-[#D4AF37] uppercase tracking-wider">{w.week}</p>
                  <p className="text-xs text-[#F8FAFC] font-medium mt-1">{w.theme}</p>
                  <p className="text-[9px] text-[#94A3B8] mt-0.5">{w.desc}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
