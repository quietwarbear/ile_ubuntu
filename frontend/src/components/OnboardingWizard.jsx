import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkle, BookOpenText, UsersThree, Chats,
  ArrowRight, ArrowLeft, Check, X,
  GraduationCap, ChalkboardTeacher, HandHeart, House,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut } from '../lib/api';
import { useI18n } from '../i18n';
import BrandMark from './brand/BrandMark';

const INTEREST_TAGS = [
  'African Studies', 'History', 'Language & Culture', 'Philosophy',
  'Science & Technology', 'Arts & Music', 'Spirituality', 'Community Building',
  'Leadership', 'Health & Wellness', 'Business', 'Education',
];

// The learner walks the full path; other intents go straight to a tailored
// completion (their experiences arrive with later slices of the roadmap).
const STEPS_BY_INTENT = {
  learner: ['welcome', 'path', 'about', 'interests', 'courses', 'cohort', 'complete'],
  educator: ['welcome', 'path', 'complete'],
  mentor: ['welcome', 'path', 'complete'],
  family: ['welcome', 'path', 'complete'],
};

const CURRENT_YEAR = new Date().getFullYear();
const BIRTH_YEARS = Array.from({ length: 90 }, (_, i) => CURRENT_YEAR - 5 - i);

const PATHS = [
  { id: 'learner', icon: GraduationCap, labelKey: 'path_learner', descKey: 'path_learner_desc' },
  { id: 'educator', icon: ChalkboardTeacher, labelKey: 'path_educator', descKey: 'path_educator_desc' },
  { id: 'mentor', icon: HandHeart, labelKey: 'path_mentor', descKey: 'path_mentor_desc' },
  { id: 'family', icon: House, labelKey: 'path_family', descKey: 'path_family_desc' },
];

export default function OnboardingWizard({ user, onComplete }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [intent, setIntent] = useState('learner');
  const [birthYear, setBirthYear] = useState('');
  const [interests, setInterests] = useState([]);
  const [courses, setCourses] = useState([]);
  const [cohorts, setCohorts] = useState([]);
  const STEPS = STEPS_BY_INTENT[intent];

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
      const payload = { interests, intent };
      if (birthYear) payload.birth_year = parseInt(birthYear, 10);
      await apiPut('/api/auth/me/onboarding', payload);
      if (onComplete) onComplete();
      navigate(intent === 'family' ? '/family' : '/dashboard');
    } catch (e) { console.error(e); }
  };

  const handleSkip = async () => {
    try {
      await apiPut('/api/auth/me/onboarding', { interests: [], intent });
      if (onComplete) onComplete();
    } catch (e) { console.error(e); }
  };

  const filteredCourses = interests.length > 0
    ? courses.filter(c => c.tags?.some(tag => interests.includes(tag)) || true).slice(0, 4)
    : courses.slice(0, 4);

  const currentStep = STEPS[step];

  return (
    <div className="fixed inset-0 z-50 bg-[rgb(var(--ink-deep))] flex items-center justify-center" data-testid="onboarding-wizard">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: 'radial-gradient(circle at 25% 50%, rgb(var(--gold)) 1px, transparent 1px), radial-gradient(circle at 75% 50%, rgb(var(--gold)) 1px, transparent 1px)',
        backgroundSize: '80px 80px',
      }} />

      <div className="relative w-full max-w-lg mx-4">
        {/* Skip button */}
        {step < STEPS.length - 1 && (
          <button
            onClick={handleSkip}
            className="absolute -top-10 right-0 text-xs text-[rgb(var(--text-faint))] hover:text-[rgb(var(--text-muted))] transition-colors flex items-center gap-1"
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
                i === step ? 'w-8 bg-[rgb(var(--gold))]' : i < step ? 'w-4 bg-[rgb(var(--gold)/0.4)]' : 'w-4 bg-[rgb(var(--ink-border))]'
              }`}
            />
          ))}
        </div>

        {/* Step content */}
        <div className="bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))] rounded-xl p-8 min-h-[400px] flex flex-col">
          {/* Step 1: Welcome */}
          {currentStep === 'welcome' && (
            <div className="flex-1 flex flex-col items-center justify-center text-center animate-fade-in" data-testid="onboarding-step-welcome">
              <div className="w-16 h-16 rounded-full bg-[rgb(var(--gold)/0.1)] border border-[rgb(var(--gold)/0.3)] flex items-center justify-center mb-4">
                <BrandMark className="w-10 h-10 object-contain" />
              </div>
              <h1 className="text-2xl text-[rgb(var(--text-main))] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                {t('onboard_welcome')}
              </h1>
              <p className="text-sm text-[rgb(var(--text-muted))] max-w-sm">{t('onboard_subtitle')}</p>
              {user?.name && (
                <p className="text-xs text-[rgb(var(--gold))] mt-3">
                  {t('welcome_back')}, {user.name.split(' ')[0]}
                </p>
              )}
            </div>
          )}

          {/* Step 2: Path (role fork) */}
          {currentStep === 'path' && (
            <div className="flex-1 animate-fade-in" data-testid="onboarding-step-path">
              <div className="text-center mb-5">
                <h2 className="text-lg text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  {t('onboard_path')}
                </h2>
                <p className="text-xs text-[rgb(var(--text-muted))] mt-1">{t('onboard_path_sub')}</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {PATHS.map(p => (
                  <button
                    key={p.id}
                    onClick={() => setIntent(p.id)}
                    className={`text-left p-3.5 rounded-md border transition-all ${
                      intent === p.id
                        ? 'bg-[rgb(var(--gold)/0.1)] border-[rgb(var(--gold)/0.5)]'
                        : 'bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] hover:border-[rgb(var(--gold)/0.25)]'
                    }`}
                    data-testid={`path-${p.id}`}
                  >
                    <p.icon size={20} weight="duotone" className={intent === p.id ? 'text-[rgb(var(--gold))]' : 'text-[rgb(var(--text-muted))]'} />
                    <p className={`text-sm mt-1.5 ${intent === p.id ? 'text-[rgb(var(--text-main))]' : 'text-[rgb(var(--text-muted))]'}`}>
                      {t(p.labelKey)}
                    </p>
                    <p className="text-[10px] text-[rgb(var(--text-faint))] mt-0.5 leading-snug">{t(p.descKey)}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step: About you (birth year — minor-safety foundation) */}
          {currentStep === 'about' && (
            <div className="flex-1 flex flex-col items-center justify-center animate-fade-in" data-testid="onboarding-step-about">
              <div className="text-center mb-5 max-w-sm">
                <h2 className="text-lg text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  {t('onboard_about')}
                </h2>
                <p className="text-xs text-[rgb(var(--text-muted))] mt-1">{t('onboard_about_sub')}</p>
              </div>
              <select
                value={birthYear}
                onChange={(e) => setBirthYear(e.target.value)}
                className="w-48 px-3 py-2.5 rounded-md bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-sm text-[rgb(var(--text-main))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]"
                data-testid="onboarding-birth-year"
              >
                <option value="">{t('onboard_birth_skip')}</option>
                {BIRTH_YEARS.map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
          )}

          {/* Step: Interests */}
          {currentStep === 'interests' && (
            <div className="flex-1 animate-fade-in" data-testid="onboarding-step-interests">
              <div className="text-center mb-6">
                <Sparkle size={24} weight="duotone" className="text-[rgb(var(--gold))] mx-auto mb-2" />
                <h2 className="text-lg text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  {t('onboard_interests')}
                </h2>
                <p className="text-xs text-[rgb(var(--text-muted))] mt-1">{t('onboard_interests_sub')}</p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center">
                {INTEREST_TAGS.map(tag => (
                  <button
                    key={tag}
                    onClick={() => toggleInterest(tag)}
                    className={`px-3 py-1.5 rounded-full text-xs border transition-all ${
                      interests.includes(tag)
                        ? 'bg-[rgb(var(--gold)/0.15)] border-[rgb(var(--gold)/0.4)] text-[rgb(var(--gold))]'
                        : 'bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] text-[rgb(var(--text-muted))] hover:border-[rgb(var(--gold)/0.2)]'
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
                <BookOpenText size={24} weight="duotone" className="text-[rgb(var(--gold))] mx-auto mb-2" />
                <h2 className="text-lg text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  {t('onboard_courses')}
                </h2>
                <p className="text-xs text-[rgb(var(--text-muted))] mt-1">{t('onboard_courses_sub')}</p>
              </div>
              <div className="space-y-2 max-h-[220px] overflow-y-auto">
                {filteredCourses.length === 0 ? (
                  <p className="text-xs text-[rgb(var(--text-faint))] text-center py-4">No courses available yet. You can explore them later!</p>
                ) : (
                  filteredCourses.map(c => (
                    <div key={c.id} className="flex items-center gap-3 p-3 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md hover:border-[rgb(var(--gold)/0.2)] transition-all">
                      <BookOpenText size={16} weight="duotone" className="text-[rgb(var(--gold))] flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-[rgb(var(--text-main))] truncate">{c.title}</p>
                        <p className="text-[9px] text-[rgb(var(--text-muted))] truncate">{c.description}</p>
                      </div>
                      <span className="text-[9px] text-[rgb(var(--gold))]">{c.enrolled_count || 0} enrolled</span>
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
                <UsersThree size={24} weight="duotone" className="text-[rgb(var(--gold))] mx-auto mb-2" />
                <h2 className="text-lg text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  {t('onboard_cohort')}
                </h2>
                <p className="text-xs text-[rgb(var(--text-muted))] mt-1">{t('onboard_cohort_sub')}</p>
              </div>
              <div className="space-y-2 max-h-[220px] overflow-y-auto">
                {cohorts.length === 0 ? (
                  <p className="text-xs text-[rgb(var(--text-faint))] text-center py-4">No cohorts yet — check back later!</p>
                ) : (
                  cohorts.slice(0, 4).map(ch => (
                    <div key={ch.id} className="flex items-center gap-3 p-3 bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] rounded-md hover:border-[rgb(var(--gold)/0.2)] transition-all">
                      <UsersThree size={16} weight="duotone" className="text-[rgb(var(--gold))] flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-[rgb(var(--text-main))] truncate">{ch.name}</p>
                        <p className="text-[9px] text-[rgb(var(--text-muted))]">{(ch.members || []).length} members</p>
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
              <h1 className="text-2xl text-[rgb(var(--text-main))] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                {t('onboard_complete')}
              </h1>
              <p className="text-sm text-[rgb(var(--text-muted))] max-w-sm">
                {intent === 'learner' ? t('onboard_complete_sub') : t(`onboard_complete_${intent}`)}
              </p>
              {interests.length > 0 && (
                <div className="flex flex-wrap gap-1 justify-center mt-3">
                  {interests.map(i => (
                    <span key={i} className="px-2 py-0.5 rounded-full text-[9px] bg-[rgb(var(--gold)/0.1)] text-[rgb(var(--gold))] border border-[rgb(var(--gold)/0.2)]">
                      {i}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-6 pt-4 border-t border-[rgb(var(--ink-border))]">
            <div className="text-[10px] text-[rgb(var(--text-faint))]">
              {t('onboard_step')} {step + 1} {t('onboard_of')} {STEPS.length}
            </div>
            <div className="flex gap-2">
              {step > 0 && step < STEPS.length - 1 && (
                <button
                  onClick={() => setStep(s => s - 1)}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs text-[rgb(var(--text-muted))] border border-[rgb(var(--ink-border))] rounded-md hover:bg-[rgb(var(--ink-border)/0.5)] transition-all"
                  data-testid="onboarding-back"
                >
                  <ArrowLeft size={12} /> {t('onboard_back')}
                </button>
              )}
              {step < STEPS.length - 1 ? (
                <button
                  onClick={() => setStep(s => s + 1)}
                  className="flex items-center gap-1 px-4 py-1.5 text-xs text-[rgb(var(--ink-deep))] bg-[rgb(var(--gold))] rounded-md hover:bg-[rgb(var(--gold)/0.9)] transition-all font-medium"
                  data-testid="onboarding-next"
                >
                  {t('onboard_next')} <ArrowRight size={12} />
                </button>
              ) : (
                <button
                  onClick={handleFinish}
                  className="flex items-center gap-1 px-4 py-1.5 text-xs text-[rgb(var(--ink-deep))] bg-[rgb(var(--gold))] rounded-md hover:bg-[rgb(var(--gold)/0.9)] transition-all font-medium"
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
