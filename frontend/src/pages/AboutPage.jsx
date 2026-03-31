import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../i18n';
import {
  BookOpenText, UsersThree, VideoCamera, ShieldCheck, Chats, Archive,
  ChartBar, MagnifyingGlass, CreditCard, Envelope, FilmSlate,
  GlobeSimple, Star, Crown, Lightning, ArrowRight, Check,
} from '@phosphor-icons/react';

const FEATURES = [
  { icon: BookOpenText, title: 'Course Management', desc: 'Create, manage, and enroll in structured courses with lessons, file attachments, and progress tracking. Rich markdown content with auto-embedded media.', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
  { icon: VideoCamera, title: 'Live Teaching', desc: 'Embedded video conferencing via Jitsi Meet with branded virtual backgrounds. Schedule, host, and join sessions seamlessly.', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
  { icon: UsersThree, title: 'Cohorts & Progress', desc: 'Group learners into cohorts with linked courses. Visual leaderboards show individual progress with per-course breakdowns.', color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/20' },
  { icon: ShieldCheck, title: 'Knowledge Spaces', desc: 'Protected knowledge vaults with 4 access levels: public, members, faculty, and elders. Access request/approval workflow.', color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20' },
  { icon: Chats, title: 'Community Forums', desc: 'Post discussions, reply, and like. Categorized threads keep conversations organized across the learning commons.', color: 'text-pink-400', bg: 'bg-pink-500/10 border-pink-500/20' },
  { icon: Archive, title: 'Archives', desc: 'Preserve and access knowledge with public and restricted archives. Faculty curate collections for the community.', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
  { icon: ChartBar, title: 'Analytics Dashboard', desc: 'Platform-wide metrics: enrollment trends, course performance rankings, cohort comparisons, and community activity. CSV export.', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
  { icon: MagnifyingGlass, title: 'Cross-Platform Search', desc: 'Instant search across courses, community posts, archives, cohorts, and spaces with categorized dropdown results.', color: 'text-teal-400', bg: 'bg-teal-500/10 border-teal-500/20' },
  { icon: CreditCard, title: 'Membership Tiers', desc: 'Stripe-powered subscriptions: Explorer (free), Scholar ($19.99), Elder Circle ($49.99). Feature gating enforced platform-wide.', color: 'text-[#D4AF37]', bg: 'bg-[#D4AF37]/10 border-[#D4AF37]/20' },
  { icon: Envelope, title: 'Email Notifications', desc: 'Branded HTML emails on enrollment, cohort joins, and session reminders via Resend. Non-blocking delivery.', color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20' },
  { icon: FilmSlate, title: 'Session Records', desc: 'Review past live sessions with attendee tracking, notes, key takeaways, and tags. Export individual sessions as CSV.', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/20' },
  { icon: GlobeSimple, title: 'Multilingual', desc: 'Full interface in English, Spanish, and Yoruba. Language preference saved per user for a culturally connected experience.', color: 'text-lime-400', bg: 'bg-lime-500/10 border-lime-500/20' },
];

const TIERS = [
  { id: 'explorer', name: 'Explorer', price: 'Free', icon: Star, color: 'text-blue-400', border: 'border-blue-500/20', features: ['Browse public courses', 'Community access', 'Basic archives', 'Enroll in 2 courses'] },
  { id: 'scholar', name: 'Scholar', price: '$19.99/mo', icon: Crown, color: 'text-[#D4AF37]', border: 'border-[#D4AF37]/30', features: ['All Explorer features', 'Unlimited enrollment', 'Cohort membership', 'Knowledge spaces', 'Priority support'] },
  { id: 'elder_circle', name: 'Elder Circle', price: '$49.99/mo', icon: ShieldCheck, color: 'text-violet-400', border: 'border-violet-500/30', features: ['All Scholar features', 'Live teaching sessions', 'Protected archives', 'Governance participation'] },
];

const ROLES = [
  { name: 'Student', desc: 'Enroll, learn, track progress' },
  { name: 'Assistant', desc: 'Support faculty operations' },
  { name: 'Faculty', desc: 'Create courses, manage cohorts' },
  { name: 'Elder', desc: 'Governance and oversight' },
  { name: 'Admin', desc: 'Full platform control' },
];

export default function AboutPage() {
  const navigate = useNavigate();
  const { t } = useI18n();

  return (
    <div className="min-h-screen bg-[#050814]" data-testid="about-page">
      {/* Hero */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 opacity-[0.04]" style={{
          backgroundImage: 'radial-gradient(circle at 30% 40%, #D4AF37 1px, transparent 1px), radial-gradient(circle at 70% 60%, #D4AF37 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }} />
        <div className="max-w-4xl mx-auto px-6 py-20 text-center relative">
          <div className="w-20 h-20 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/30 flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl text-[#D4AF37]">&#9775;</span>
          </div>
          <h1 className="text-4xl sm:text-5xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            The Ile Ubuntu
          </h1>
          <p className="text-base text-[#D4AF37] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            {t('about_hero')}
          </p>
          <p className="text-sm text-[#94A3B8] max-w-xl mx-auto mb-6">
            {t('about_subtitle')}
          </p>
          <p className="text-xs text-[#475569] max-w-md mx-auto">
            {t('about_tagline')}
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-8 px-6 py-2.5 bg-[#D4AF37] text-[#050814] rounded-md text-sm font-medium hover:bg-[#D4AF37]/90 transition-all inline-flex items-center gap-2"
            data-testid="about-cta"
          >
            Enter the Commons <ArrowRight size={16} />
          </button>
        </div>
      </div>

      {/* Features Grid */}
      <div className="max-w-5xl mx-auto px-6 py-16">
        <h2 className="text-2xl text-[#F8FAFC] text-center mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
          Platform Features
        </h2>
        <p className="text-xs text-[#94A3B8] text-center mb-10">Everything you need for a thriving learning community</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="features-grid">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.title} className={`p-4 rounded-lg border ${f.bg} transition-all hover:-translate-y-0.5`} data-testid={`feature-${f.title.toLowerCase().replace(/\s+/g, '-')}`}>
                <Icon size={22} weight="duotone" className={`${f.color} mb-2`} />
                <h3 className="text-sm text-[#F8FAFC] font-medium mb-1">{f.title}</h3>
                <p className="text-[10px] text-[#94A3B8] leading-relaxed">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Membership Tiers */}
      <div className="bg-[#0A1128] py-16">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-2xl text-[#F8FAFC] text-center mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Membership Tiers
          </h2>
          <p className="text-xs text-[#94A3B8] text-center mb-8">Choose your path</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="tiers-section">
            {TIERS.map((tier) => {
              const Icon = tier.icon;
              return (
                <div key={tier.id} className={`p-5 rounded-lg border ${tier.border} bg-[#0F172A]`} data-testid={`about-tier-${tier.id}`}>
                  <Icon size={24} weight="duotone" className={tier.color} />
                  <h3 className="text-base text-[#F8FAFC] mt-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                    {tier.name}
                  </h3>
                  <p className="text-xl font-bold text-[#F8FAFC] mt-1">{tier.price}</p>
                  <ul className="mt-3 space-y-1.5">
                    {tier.features.map((feat, i) => (
                      <li key={i} className="flex items-start gap-2 text-[10px] text-[#94A3B8]">
                        <Check size={10} weight="bold" className={tier.color} />
                        <span>{feat}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Roles */}
      <div className="max-w-4xl mx-auto px-6 py-16">
        <h2 className="text-2xl text-[#F8FAFC] text-center mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
          Access Roles
        </h2>
        <p className="text-xs text-[#94A3B8] text-center mb-8">Differentiated governance for the learning commons</p>
        <div className="flex flex-wrap justify-center gap-3" data-testid="roles-section">
          {ROLES.map((r) => (
            <div key={r.name} className="p-3 rounded-lg bg-[#0F172A] border border-[#1E293B] text-center min-w-[120px]">
              <p className="text-sm text-[#D4AF37] font-medium">{r.name}</p>
              <p className="text-[9px] text-[#94A3B8] mt-1">{r.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Tech Stack */}
      <div className="bg-[#0A1128] py-12">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-lg text-[#F8FAFC] mb-4" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Built With
          </h2>
          <div className="flex flex-wrap justify-center gap-2 text-[10px] text-[#94A3B8]">
            {['React', 'FastAPI', 'MongoDB', 'Tailwind CSS', 'Jitsi Meet', 'Stripe', 'Resend', 'Google APIs', 'PWA'].map(tech => (
              <span key={tech} className="px-3 py-1 bg-[#0F172A] border border-[#1E293B] rounded-full">{tech}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Social Media Strategy */}
      <div className="max-w-4xl mx-auto px-6 py-16" data-testid="social-strategy">
        <h2 className="text-2xl text-[#F8FAFC] text-center mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
          Share the Vision
        </h2>
        <p className="text-xs text-[#94A3B8] text-center mb-8">Copy-ready content for your social channels</p>

        <div className="space-y-4">
          {/* Instagram/Twitter */}
          <div className="p-4 bg-[#0F172A] border border-[#1E293B] rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Lightning size={14} weight="duotone" className="text-pink-400" />
              <span className="text-xs text-pink-400 uppercase tracking-wider">Instagram / Twitter</span>
            </div>
            <p className="text-sm text-[#F8FAFC] leading-relaxed mb-2">
              Introducing The Ile Ubuntu — a Living Learning Commons where courses, cohorts, and community converge.
            </p>
            <p className="text-sm text-[#F8FAFC] leading-relaxed mb-2">
              Live teaching sessions. Protected knowledge spaces. Progress tracking. All wrapped in midnight blue & gold.
            </p>
            <p className="text-xs text-[#D4AF37]">
              #TheIleUbuntu #LivingLearningCommons #Ubuntu #EdTech #OnlineLearning #AfricanWisdom #CommunityLearning #LearnTogether #DigitalClassroom
            </p>
          </div>

          {/* LinkedIn */}
          <div className="p-4 bg-[#0F172A] border border-[#1E293B] rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Lightning size={14} weight="duotone" className="text-blue-400" />
              <span className="text-xs text-blue-400 uppercase tracking-wider">LinkedIn</span>
            </div>
            <p className="text-sm text-[#F8FAFC] leading-relaxed mb-2">
              We built something different. The Ile Ubuntu isn't another LMS — it's a Living Learning Commons designed for communities that value intergenerational knowledge transfer.
            </p>
            <p className="text-sm text-[#94A3B8] leading-relaxed mb-2">
              12 features including live video teaching, cohort-based learning with progress leaderboards, protected knowledge spaces with tiered access, community forums, analytics dashboards, and Stripe-powered membership tiers — all in a multilingual platform supporting English, Spanish, and Yoruba.
            </p>
            <p className="text-sm text-[#94A3B8] leading-relaxed mb-2">
              Built for elders who preserve wisdom, faculty who shape minds, and students who carry it forward.
            </p>
            <p className="text-xs text-[#D4AF37]">
              #EdTech #LearningPlatform #Ubuntu #CommunityFirst #DigitalTransformation
            </p>
          </div>

          {/* One-liner */}
          <div className="p-4 bg-[#0F172A] border border-[#D4AF37]/20 rounded-lg text-center">
            <p className="text-[9px] text-[#D4AF37] uppercase tracking-wider mb-2">Elevator Pitch</p>
            <p className="text-sm text-[#F8FAFC] italic">
              "The Ile Ubuntu is a Living Learning Commons — a single platform where courses, live teaching, cohorts, archives, and community come together under one roof, with role-based governance and tiered access that respects the wisdom hierarchy."
            </p>
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="py-12 text-center border-t border-[#1E293B]">
        <button
          onClick={() => navigate('/dashboard')}
          className="px-6 py-2.5 bg-[#D4AF37] text-[#050814] rounded-md text-sm font-medium hover:bg-[#D4AF37]/90 transition-all inline-flex items-center gap-2"
        >
          Start Learning <ArrowRight size={16} />
        </button>
        <p className="text-[10px] text-[#475569] mt-3">The Ile Ubuntu &mdash; Living Learning Commons</p>
      </div>
    </div>
  );
}
