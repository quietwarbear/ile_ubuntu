import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkle, BookOpenText, UsersThree, Chats,
  ArrowRight, ArrowLeft, Check, X,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut } from '../lib/api';
import { useI18n } from '../i18n';

const INTEREST_TAGS = [
  'African Studies', 'History', 'Language & Culture', 'Philosophy',
  'Science & Technology', 'Arts & Music', 'Spirituality', 'Community Building',
  'Leadership', 'Health & Wellness', 'Business', 'Education',
];

const STEPS = ['welcome', 'interests', 'courses', 'cohort', 'complete'];

export default function OnboardingWizard({ user, onComplete }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [interests, setInterests] = useState([]);
  const [courses, setCourses] = useState([]);
  const [cohorts, setCohorts] = useState([]);

  useEffect(() => {
    // Preload courses and cohorts
    apiGet('/api/courses').then(setCourses).catch(() => {});
    apiGet('/api/cohorts').then(setCohorts).catch(() => {});
  }, []);

  const toggleInterest = (tag) => {
    setInterests(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
  };

  const handleFinish = async () => {
    try {
      await apiPut('/api/auth/me/onboarding', { interests });
      if (onComplete) onComplete();
      navigate('/dashboard');
    } catch (e) { console.error(e); }
  };

  const handleSkip = async () => {
    try {
      await apiPut('/api/auth/me/onboarding', { interests: [] });
      if (onComplete) onComplete();
    } catch (e) { console.error(e); }
  };

  const filteredCourses = interests.length > 0
    ? courses.filter(c => c.tags?.some(tag => interests.includes(tag)) || true).slice(0, 4)
    : courses.slice(0, 4);

  const currentStep = STEPS[step];

  return (
    <div className="fixed inset-0 z-50 bg-[#050814] flex items-center justify-center" data-testid="onboarding-wizard">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: 'radial-gradient(circle at 25% 50%, #D4AF37 1px, transparent 1px), radial-gradient(circle at 75% 50%, #D4AF37 1px, transparent 1px)',
        backgroundSize: '80px 80px',
      }} />

      <div className="relative w-full max-w-lg mx-4">
        {/* Skip button */}
        {step < STEPS.length - 1 && (
          <button
            onClick={handleSkip}
            className="absolute -top-10 right-0 text-xs text-[#475569] hover:text-[#94A3B8] transition-colors flex items-center gap-1"
            data-testid="onboarding-skip"
          >
            <X size={12} /> {t('onboard_skip')}
          </button>
        )}

        {/* Progress dots */}
        <div className="flex justify-center gap-2 mb-6">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all duration-500 ${
                i === step ? 'w-8 bg-[#D4AF37]' : i < step ? 'w-4 bg-[#D4AF37]/40' : 'w-4 bg-[#1E293B]'
              }`}
            />
          ))}
        </div>

        {/* Step content */}
        <div className="bg-[#0F172A] border border-[#1E293B] rounded-xl p-8 min-h-[400px] flex flex-col">
          {/* Step 1: Welcome */}
          {currentStep === 'welcome' && (
            <div className="flex-1 flex flex-col items-center justify-center text-center animate-fade-in" data-testid="onboarding-step-welcome">
              <div className="w-16 h-16 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/30 flex items-center justify-center mb-4">
                <span className="text-3xl text-[#D4AF37]">&#9775;</span>
              </div>
              <h1 className="text-2xl text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                {t('onboard_welcome')}
              </h1>
              <p className="text-sm text-[#94A3B8] max-w-sm">{t('onboard_subtitle')}</p>
              {user?.name && (
                <p className="text-xs text-[#D4AF37] mt-3">
                  {t('welcome_back')}, {user.name.split(' ')[0]}
                </p>
              )}
            </div>
          )}

          {/* Step 2: Interests */}
          {currentStep === 'interests' && (
            <div className="flex-1 animate-fade-in" data-testid="onboarding-step-interests">
              <div className="text-center mb-6">
                <Sparkle size={24} weight="duotone" className="text-[#D4AF37] mx-auto mb-2" />
                <h2 className="text-lg text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  {t('onboard_interests')}
                </h2>
                <p className="text-xs text-[#94A3B8] mt-1">{t('onboard_interests_sub')}</p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center">
                {INTEREST_TAGS.map(tag => (
                  <button
                    key={tag}
                    onClick={() => toggleInterest(tag)}
                    className={`px-3 py-1.5 rounded-full text-xs border transition-all ${
                      interests.includes(tag)
                        ? 'bg-[#D4AF37]/15 border-[#D4AF37]/40 text-[#D4AF37]'
                        : 'bg-[#050814] border-[#1E293B] text-[#94A3B8] hover:border-[#D4AF37]/20'
                    }`}
                    data-testid={`interest-${tag.toLowerCase().replace(/\s+/g, '-')}`}
                  >
                    {interests.includes(tag) && <Check size={10} className="inline mr-1" />}
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: Recommended Courses */}
          {currentStep === 'courses' && (
            <div className="flex-1 animate-fade-in" data-testid="onboarding-step-courses">
              <div className="text-center mb-4">
                <BookOpenText size={24} weight="duotone" className="text-[#D4AF37] mx-auto mb-2" />
                <h2 className="text-lg text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  {t('onboard_courses')}
                </h2>
                <p className="text-xs text-[#94A3B8] mt-1">{t('onboard_courses_sub')}</p>
              </div>
              <div className="space-y-2 max-h-[220px] overflow-y-auto">
                {filteredCourses.length === 0 ? (
                  <p className="text-xs text-[#475569] text-center py-4">No courses available yet. You can explore them later!</p>
                ) : (
                  filteredCourses.map(c => (
                    <div key={c.id} className="flex items-center gap-3 p-3 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-all">
                      <BookOpenText size={16} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-[#F8FAFC] truncate">{c.title}</p>
                        <p className="text-[9px] text-[#94A3B8] truncate">{c.description}</p>
                      </div>
                      <span className="text-[9px] text-[#D4AF37]">{c.enrolled_count || 0} enrolled</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Step 4: Join Cohort */}
          {currentStep === 'cohort' && (
            <div className="flex-1 animate-fade-in" data-testid="onboarding-step-cohort">
              <div className="text-center mb-4">
                <UsersThree size={24} weight="duotone" className="text-[#D4AF37] mx-auto mb-2" />
                <h2 className="text-lg text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  {t('onboard_cohort')}
                </h2>
                <p className="text-xs text-[#94A3B8] mt-1">{t('onboard_cohort_sub')}</p>
              </div>
              <div className="space-y-2 max-h-[220px] overflow-y-auto">
                {cohorts.length === 0 ? (
                  <p className="text-xs text-[#475569] text-center py-4">No cohorts yet — check back later!</p>
                ) : (
                  cohorts.slice(0, 4).map(ch => (
                    <div key={ch.id} className="flex items-center gap-3 p-3 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-all">
                      <UsersThree size={16} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-[#F8FAFC] truncate">{ch.name}</p>
                        <p className="text-[9px] text-[#94A3B8]">{(ch.members || []).length} members</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Step 5: Complete */}
          {currentStep === 'complete' && (
            <div className="flex-1 flex flex-col items-center justify-center text-center animate-fade-in" data-testid="onboarding-step-complete">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-4">
                <Check size={28} weight="bold" className="text-emerald-400" />
              </div>
              <h1 className="text-2xl text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                {t('onboard_complete')}
              </h1>
              <p className="text-sm text-[#94A3B8] max-w-sm">{t('onboard_complete_sub')}</p>
              {interests.length > 0 && (
                <div className="flex flex-wrap gap-1 justify-center mt-3">
                  {interests.map(i => (
                    <span key={i} className="px-2 py-0.5 rounded-full text-[9px] bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/20">
                      {i}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-6 pt-4 border-t border-[#1E293B]">
            <div className="text-[10px] text-[#475569]">
              {t('onboard_step')} {step + 1} {t('onboard_of')} {STEPS.length}
            </div>
            <div className="flex gap-2">
              {step > 0 && step < STEPS.length - 1 && (
                <button
                  onClick={() => setStep(s => s - 1)}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs text-[#94A3B8] border border-[#1E293B] rounded-md hover:bg-[#1E293B]/50 transition-all"
                  data-testid="onboarding-back"
                >
                  <ArrowLeft size={12} /> {t('onboard_back')}
                </button>
              )}
              {step < STEPS.length - 1 ? (
                <button
                  onClick={() => setStep(s => s + 1)}
                  className="flex items-center gap-1 px-4 py-1.5 text-xs text-[#050814] bg-[#D4AF37] rounded-md hover:bg-[#D4AF37]/90 transition-all font-medium"
                  data-testid="onboarding-next"
                >
                  {t('onboard_next')} <ArrowRight size={12} />
                </button>
              ) : (
                <button
                  onClick={handleFinish}
                  className="flex items-center gap-1 px-4 py-1.5 text-xs text-[#050814] bg-[#D4AF37] rounded-md hover:bg-[#D4AF37]/90 transition-all font-medium"
                  data-testid="onboarding-finish"
                >
                  {t('onboard_finish')} <ArrowRight size={12} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
