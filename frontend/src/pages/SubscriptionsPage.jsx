import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Crown, Star, ShieldCheck, Check,
  CreditCard, Sparkle,
} from '@phosphor-icons/react';
import { apiGet, apiPost } from '../lib/api';

const TIER_ICONS = {
  explorer: Star,
  scholar: Crown,
  elder_circle: ShieldCheck,
};

const TIER_COLORS = {
  explorer: 'border-blue-500/20 bg-blue-500/5',
  scholar: 'border-[#D4AF37]/30 bg-[#D4AF37]/5',
  elder_circle: 'border-violet-500/30 bg-violet-500/5',
};

const TIER_ACCENT = {
  explorer: 'text-blue-400',
  scholar: 'text-[#D4AF37]',
  elder_circle: 'text-violet-400',
};

function getUrlParameter(name) {
  const regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
  const results = regex.exec(window.location.search);
  return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
}

export default function SubscriptionsPage({ user }) {
  const [tiers, setTiers] = useState([]);
  const [mySub, setMySub] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checkingPayment, setCheckingPayment] = useState(false);
  const [paymentResult, setPaymentResult] = useState(null);
  const [processingTier, setProcessingTier] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [tiersRes, subRes] = await Promise.all([
        apiGet('/api/subscriptions/tiers'),
        apiGet('/api/subscriptions/my-subscription'),
      ]);
      setTiers(tiersRes);
      setMySub(subRes);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Check for returning from Stripe checkout
  useEffect(() => {
    const sessionId = getUrlParameter('session_id');
    if (sessionId) {
      setCheckingPayment(true);
      pollPaymentStatus(sessionId, 0);
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []); // Run once on mount

  const pollPaymentStatus = async (sessionId, attempts) => {
    const maxAttempts = 5;
    if (attempts >= maxAttempts) {
      setPaymentResult({ status: 'timeout', message: 'Payment status check timed out. Please refresh.' });
      setCheckingPayment(false);
      return;
    }

    try {
      const res = await apiGet(`/api/subscriptions/checkout/status/${sessionId}`);
      if (res.payment_status === 'paid') {
        setPaymentResult({ status: 'success', message: 'Payment successful! Your membership has been upgraded.' });
        setCheckingPayment(false);
        fetchData(); // Refresh subscription data
        return;
      } else if (res.status === 'expired') {
        setPaymentResult({ status: 'error', message: 'Payment session expired.' });
        setCheckingPayment(false);
        return;
      }
      // Keep polling
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), 2000);
    } catch (e) {
      setPaymentResult({ status: 'error', message: 'Error checking payment.' });
      setCheckingPayment(false);
    }
  };

  const handleSubscribe = async (tierId) => {
    setProcessingTier(tierId);
    try {
      const originUrl = window.location.origin;
      const res = await apiPost('/api/subscriptions/checkout', {
        tier_id: tierId,
        origin_url: originUrl,
      });
      if (res.free) {
        fetchData();
        setPaymentResult({ status: 'success', message: 'Switched to Explorer (free) tier.' });
      } else if (res.url) {
        window.location.href = res.url;
      }
    } catch (e) {
      console.error(e);
    } finally {
      setProcessingTier(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="subscriptions-loading">
        <div className="w-6 h-6 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const currentTier = mySub?.tier || 'explorer';

  const tierIds = ['explorer', 'scholar', 'elder_circle'];

  return (
    <div className="space-y-6" data-testid="subscriptions-page">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Sparkle size={20} weight="duotone" className="text-[#D4AF37]" />
          <h1 className="text-xl text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Membership
          </h1>
        </div>
        <p className="text-xs text-[#94A3B8]">Choose your path within The Ile Ubuntu</p>
      </div>

      {/* Payment status banner */}
      {checkingPayment && (
        <div className="p-3 bg-[#D4AF37]/10 border border-[#D4AF37]/30 rounded-md text-center" data-testid="payment-checking">
          <div className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-[#D4AF37]">Verifying your payment...</span>
          </div>
        </div>
      )}

      {paymentResult && (
        <div className={`p-3 rounded-md text-center ${
          paymentResult.status === 'success'
            ? 'bg-emerald-500/10 border border-emerald-500/30'
            : 'bg-red-500/10 border border-red-500/30'
        }`} data-testid="payment-result">
          <p className={`text-sm ${paymentResult.status === 'success' ? 'text-emerald-400' : 'text-red-400'}`}>
            {paymentResult.message}
          </p>
        </div>
      )}

      {/* Current Plan */}
      <Card className="bg-[#0F172A] border-[#D4AF37]/20">
        <CardContent className="p-4">
          <p className="text-[9px] text-[#94A3B8] uppercase tracking-widest mb-1">Current Plan</p>
          <div className="flex items-center gap-2">
            <Badge className="bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20">
              {currentTier === 'elder_circle' ? 'Elder Circle' : currentTier.charAt(0).toUpperCase() + currentTier.slice(1)}
            </Badge>
            <span className="text-[10px] text-[#94A3B8]">{mySub?.subscription_status || 'active'}</span>
          </div>
        </CardContent>
      </Card>

      {/* Tier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="tier-cards">
        {tierIds.map((tierId) => {
          const tier = tiers.find(t => t.name.toLowerCase().replace(/\s+/g, '_') === tierId)
            || tiers.find(t => t.price === (tierId === 'explorer' ? 0 : tierId === 'scholar' ? 19.99 : 49.99));

          if (!tier) return null;

          const Icon = TIER_ICONS[tierId] || Star;
          const isActive = currentTier === tierId;
          const accent = TIER_ACCENT[tierId];

          return (
            <Card key={tierId} className={`bg-[#0F172A] ${isActive ? 'border-[#D4AF37] ring-1 ring-[#D4AF37]/20' : 'border-[#1E293B]'} ${TIER_COLORS[tierId]} relative overflow-hidden`} data-testid={`tier-${tierId}`}>
              {isActive && (
                <div className="absolute top-2 right-2">
                  <Badge className="bg-[#D4AF37]/20 text-[#D4AF37] border-[#D4AF37]/30 text-[8px]">Current</Badge>
                </div>
              )}
              <CardContent className="p-5">
                <Icon size={28} weight="duotone" className={accent} />
                <h3 className="text-base text-[#F8FAFC] mt-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  {tier.name}
                </h3>
                <div className="flex items-baseline gap-1 mt-1 mb-2">
                  <span className="text-2xl font-bold text-[#F8FAFC]">
                    {tier.price === 0 ? 'Free' : `$${tier.price}`}
                  </span>
                  {tier.price > 0 && <span className="text-[10px] text-[#94A3B8]">/month</span>}
                </div>
                <p className="text-xs text-[#94A3B8] mb-3">{tier.description}</p>
                <ul className="space-y-1.5 mb-4">
                  {tier.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-[11px] text-[#94A3B8]">
                      <Check size={12} weight="bold" className={accent} />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                {!isActive && (
                  <button
                    onClick={() => handleSubscribe(tierId)}
                    disabled={processingTier === tierId}
                    className={`w-full py-2 rounded-md text-xs font-medium transition-all flex items-center justify-center gap-2 ${
                      tierId === 'elder_circle'
                        ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30 hover:bg-violet-500/30'
                        : tierId === 'scholar'
                        ? 'bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/30'
                        : 'bg-blue-500/20 text-blue-300 border border-blue-500/30 hover:bg-blue-500/30'
                    }`}
                    data-testid={`subscribe-${tierId}`}
                  >
                    {processingTier === tierId ? (
                      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <>
                        <CreditCard size={14} weight="duotone" />
                        {tier.price === 0 ? 'Switch to Free' : 'Subscribe'}
                      </>
                    )}
                  </button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
