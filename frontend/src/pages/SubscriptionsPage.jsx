import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Crown, Star, ShieldCheck, Check,
  CreditCard, Sparkle, DeviceMobile, ArrowsClockwise,
} from '@phosphor-icons/react';
import { apiGet, apiPost } from '../lib/api';
import {
  isNative,
  TIER_TO_PRODUCT_ID,
  makePurchase,
  restorePurchases,
} from '../lib/revenuecat';

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
  const [billingPeriod, setBillingPeriod] = useState('monthly'); // 'monthly' or 'annual'
  const [restoringPurchases, setRestoringPurchases] = useState(false);

  const onNativePlatform = isNative();

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

  // Check for returning from Stripe checkout (web only)
  useEffect(() => {
    const sessionId = getUrlParameter('session_id');
    if (sessionId) {
      setCheckingPayment(true);
      pollPaymentStatus(sessionId, 0);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []); // eslint-disable-line -- mount-only checkout check

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
        fetchData();
        return;
      } else if (res.status === 'expired') {
        setPaymentResult({ status: 'error', message: 'Payment session expired.' });
        setCheckingPayment(false);
        return;
      }
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), 2000);
    } catch (e) {
      setPaymentResult({ status: 'error', message: 'Error checking payment.' });
      setCheckingPayment(false);
    }
  };

  const handleSubscribe = async (tierId) => {
    setProcessingTier(tierId);
    try {
      if (onNativePlatform && tierId !== 'explorer') {
        // Native in-app purchase via RevenueCat
        await handleNativePurchase(tierId);
      } else {
        // Web Stripe checkout
        await handleWebCheckout(tierId);
      }
    } catch (e) {
      console.error(e);
      setPaymentResult({ status: 'error', message: 'Something went wrong. Please try again.' });
    } finally {
      setProcessingTier(null);
    }
  };

  const handleWebCheckout = async (tierId) => {
    const originUrl = window.location.origin;
    const res = await apiPost('/api/subscriptions/checkout', {
      tier_id: tierId,
      billing_period: billingPeriod,
      origin_url: originUrl,
    });
    if (res.free) {
      fetchData();
      setPaymentResult({ status: 'success', message: 'Switched to Explorer (free) tier.' });
    } else if (res.url) {
      window.location.href = res.url;
    }
  };

  const handleNativePurchase = async (tierId) => {
    const productIds = TIER_TO_PRODUCT_ID[tierId];
    if (!productIds) {
      setPaymentResult({ status: 'error', message: 'Product not available.' });
      return;
    }

    const productId = billingPeriod === 'annual' ? productIds.annual : productIds.monthly;
    const result = await makePurchase(productId);

    if (result.success) {
      // Sync the subscription to our backend
      await apiPost('/api/subscriptions/activate-mobile', {
        product_id: productId,
        tier_id: tierId,
        platform: navigator.userAgent.includes('iPhone') ? 'ios' : 'android',
      });
      setPaymentResult({ status: 'success', message: 'Subscription activated! Welcome aboard.' });
      fetchData();
    } else if (result.cancelled) {
      // User cancelled — no error message needed
    } else {
      setPaymentResult({ status: 'error', message: result.message || 'Purchase failed.' });
    }
  };

  const handleRestorePurchases = async () => {
    setRestoringPurchases(true);
    try {
      const customerInfo = await restorePurchases();
      if (customerInfo?.entitlements?.active && Object.keys(customerInfo.entitlements.active).length > 0) {
        setPaymentResult({ status: 'success', message: 'Purchases restored successfully!' });
        fetchData();
      } else {
        setPaymentResult({ status: 'error', message: 'No active subscriptions found to restore.' });
      }
    } catch (e) {
      setPaymentResult({ status: 'error', message: 'Failed to restore purchases.' });
    } finally {
      setRestoringPurchases(false);
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

      {/* Billing Period Toggle */}
      <div className="flex items-center justify-center gap-1 bg-[#0F172A] rounded-lg p-1 border border-[#1E293B]">
        <button
          onClick={() => setBillingPeriod('monthly')}
          className={`flex-1 py-2 px-4 rounded-md text-xs font-medium transition-all ${
            billingPeriod === 'monthly'
              ? 'bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/30'
              : 'text-[#94A3B8] hover:text-[#F8FAFC]'
          }`}
        >
          Monthly
        </button>
        <button
          onClick={() => setBillingPeriod('annual')}
          className={`flex-1 py-2 px-4 rounded-md text-xs font-medium transition-all ${
            billingPeriod === 'annual'
              ? 'bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/30'
              : 'text-[#94A3B8] hover:text-[#F8FAFC]'
          }`}
        >
          Annual
          <span className="ml-1 text-[9px] text-emerald-400">Save ~17%</span>
        </button>
      </div>

      {/* Tier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="tier-cards">
        {tierIds.map((tierId) => {
          const tier = tiers.find(t => t.id === tierId)
            || tiers.find(t => t.name.toLowerCase().replace(/\s+/g, '_') === tierId);

          if (!tier) return null;

          const Icon = TIER_ICONS[tierId] || Star;
          const isActive = currentTier === tierId;
          const accent = TIER_ACCENT[tierId];
          const price = billingPeriod === 'annual' ? tier.price_annual : tier.price;
          const monthlyEquivalent = billingPeriod === 'annual' && tier.price_annual > 0
            ? (tier.price_annual / 12).toFixed(2)
            : null;

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
                <div className="flex items-baseline gap-1 mt-1 mb-1">
                  <span className="text-2xl font-bold text-[#F8FAFC]">
                    {price === 0 ? 'Free' : `$${price}`}
                  </span>
                  {price > 0 && (
                    <span className="text-[10px] text-[#94A3B8]">
                      /{billingPeriod === 'annual' ? 'year' : 'month'}
                    </span>
                  )}
                </div>
                {monthlyEquivalent && (
                  <p className="text-[10px] text-emerald-400 mb-2">
                    ${monthlyEquivalent}/mo equivalent
                  </p>
                )}
                {!monthlyEquivalent && <div className="mb-2" />}
                <p className="text-xs text-[#94A3B8] mb-3">{tier.description}</p>
                <ul className="space-y-1.5 mb-4">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-[11px] text-[#94A3B8]">
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
                        {onNativePlatform && tier.price > 0 ? (
                          <DeviceMobile size={14} weight="duotone" />
                        ) : (
                          <CreditCard size={14} weight="duotone" />
                        )}
                        {price === 0 ? 'Switch to Free' : 'Subscribe'}
                      </>
                    )}
                  </button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Restore Purchases (native only) */}
      {onNativePlatform && (
        <div className="text-center pt-2">
          <button
            onClick={handleRestorePurchases}
            disabled={restoringPurchases}
            className="text-xs text-[#94A3B8] hover:text-[#D4AF37] transition-colors flex items-center justify-center gap-1 mx-auto"
          >
            <ArrowsClockwise size={12} weight={restoringPurchases ? 'bold' : 'regular'} className={restoringPurchases ? 'animate-spin' : ''} />
            {restoringPurchases ? 'Restoring...' : 'Restore Purchases'}
          </button>
        </div>
      )}
    </div>
  );
}
