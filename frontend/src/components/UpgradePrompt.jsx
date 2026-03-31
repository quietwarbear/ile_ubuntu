import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Crown, Sparkle } from '@phosphor-icons/react';

const TIER_INFO = {
  scholar: {
    name: 'Scholar',
    price: '$19.99/mo',
    icon: Crown,
    color: 'text-[#D4AF37]',
    bg: 'bg-[#D4AF37]/10 border-[#D4AF37]/30',
  },
  elder_circle: {
    name: 'Elder Circle',
    price: '$49.99/mo',
    icon: ShieldCheck,
    color: 'text-violet-400',
    bg: 'bg-violet-500/10 border-violet-500/30',
  },
};

const FEATURE_MESSAGES = {
  enrollment: 'You\'ve reached your free enrollment limit (2 courses).',
  cohort_join: 'Cohort membership requires a Scholar plan or above.',
  space_access: 'Knowledge Spaces require a Scholar plan or above.',
  live_session: 'Live Teaching sessions require an Elder Circle plan.',
  restricted_archive: 'Protected archives require an Elder Circle plan.',
};

export default function UpgradePrompt({ feature, requiredTier = 'scholar', onClose }) {
  const navigate = useNavigate();
  const tier = TIER_INFO[requiredTier] || TIER_INFO.scholar;
  const Icon = tier.icon;
  const message = FEATURE_MESSAGES[feature] || 'This feature requires a higher membership tier.';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-fade-in-up" data-testid="upgrade-prompt">
      <div className={`w-full max-w-sm mx-4 p-6 rounded-lg border ${tier.bg} bg-[#0F172A]`}>
        <div className="text-center">
          <div className={`w-12 h-12 mx-auto rounded-full flex items-center justify-center mb-3 ${tier.bg}`}>
            <Icon size={24} weight="duotone" className={tier.color} />
          </div>
          <h3 className="text-base text-[#F8FAFC] mb-1" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Upgrade to {tier.name}
          </h3>
          <p className="text-xs text-[#94A3B8] mb-4">{message}</p>

          <div className="p-3 bg-[#050814] border border-[#1E293B] rounded-md mb-4">
            <div className="flex items-center justify-center gap-1">
              <Sparkle size={14} weight="duotone" className={tier.color} />
              <span className="text-sm font-semibold text-[#F8FAFC]">{tier.name}</span>
              <span className="text-xs text-[#94A3B8]">— {tier.price}</span>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => { if (onClose) onClose(); navigate('/subscriptions'); }}
              className={`flex-1 py-2.5 rounded-md text-xs font-medium ${
                requiredTier === 'elder_circle'
                  ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30 hover:bg-violet-500/30'
                  : 'bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/30'
              } transition-all`}
              data-testid="upgrade-btn"
            >
              View Plans
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="flex-1 py-2.5 rounded-md text-xs font-medium text-[#94A3B8] border border-[#1E293B] hover:bg-[#1E293B]/50 transition-all"
                data-testid="upgrade-dismiss"
              >
                Maybe Later
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
