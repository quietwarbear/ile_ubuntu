import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  ChalkboardTeacher, CurrencyDollar, ArrowSquareOut,
  CheckCircle, Warning, Lightning, ChartLineUp,
  CreditCard, Storefront,
} from '@phosphor-icons/react';
import { apiGet, apiPost } from '../lib/api';

export default function TeacherDashboardPage({ user }) {
  const [connectStatus, setConnectStatus] = useState(null);
  const [earnings, setEarnings] = useState(null);
  const [myCourses, setMyCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [onboardingLoading, setOnboardingLoading] = useState(false);
  const [pricingCourse, setPricingCourse] = useState(null);
  const [priceInput, setPriceInput] = useState('');
  const [pricingLoading, setPricingLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  const fetchAll = useCallback(async () => {
    // Each call degrades independently — a failing payment-status check must
    // never blank the course list (and vice versa).
    const [status, earningsRes, coursesRes] = await Promise.all([
      apiGet('/api/marketplace/connect/status').catch(e => ({ connected: false, charges_enabled: false, _error: e.message })),
      apiGet('/api/marketplace/earnings').catch(() => null),
      apiGet('/api/courses').catch(e => { console.error('courses load failed:', e); return []; }),
    ]);
    setConnectStatus(status);
    if (status?._error || status?.status_error) {
      setStatusMessage({ type: 'error', text: `Payment account status check failed: ${status._error || status.status_error}` });
    }
    setEarnings(earningsRes);
    // Only show courses created by this teacher
    setMyCourses((coursesRes || []).filter(c => c.instructor_id === user?.id));
    setLoading(false);
  }, [user?.id]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const openUrlInAppOrBrowser = async (url) => {
    const isNativePlatform = window.Capacitor && typeof window.Capacitor.isNativePlatform === 'function' && window.Capacitor.isNativePlatform();
    if (isNativePlatform) {
      const { Browser } = await import('@capacitor/browser');
      await Browser.open({ url, presentationStyle: 'fullscreen' });
    } else {
      window.location.href = url;
    }
  };

  const handleStartOnboarding = async () => {
    setOnboardingLoading(true);
    try {
      const res = await apiPost('/api/marketplace/connect/onboard', {
        return_url: `${window.location.origin}/teacher-dashboard`,
        refresh_url: `${window.location.origin}/teacher-dashboard`,
      });
      if (res.url) {
        await openUrlInAppOrBrowser(res.url);
      }
    } catch (e) {
      setStatusMessage({ type: 'error', text: e.message || 'Failed to start onboarding' });
    } finally {
      setOnboardingLoading(false);
    }
  };

  const handleOpenStripeDashboard = async () => {
    try {
      const res = await apiGet('/api/marketplace/connect/dashboard-link');
      if (res.url) {
        await openUrlInAppOrBrowser(res.url);
      }
    } catch (e) {
      setStatusMessage({ type: 'error', text: 'Could not open Stripe dashboard' });
    }
  };

  const handleToggleVisibility = async (course) => {
    const isListed = course.visibility !== 'unlisted';
    const next = isListed ? 'unlisted' : 'listed';
    try {
      await apiPost(`/api/courses/${course.id}/visibility`, { visibility: next });
      setStatusMessage({
        type: 'success',
        text: next === 'listed'
          ? `"${course.title}" is now listed in the community catalog`
          : `"${course.title}" is now invite-only`,
      });
      fetchAll();
    } catch (e) {
      setStatusMessage({ type: 'error', text: e.message || 'Failed to update visibility' });
    }
  };

  const handleSetPremium = async (courseId) => {
    const price = parseFloat(priceInput);
    if (isNaN(price) || price < 0) {
      setStatusMessage({ type: 'error', text: 'Enter a valid price' });
      return;
    }
    setPricingLoading(true);
    try {
      await apiPost(`/api/marketplace/courses/${courseId}/set-premium`, { price });
      setStatusMessage({ type: 'success', text: price > 0 ? `Course set to $${price}` : 'Course set to free' });
      setPricingCourse(null);
      setPriceInput('');
      fetchAll();
    } catch (e) {
      setStatusMessage({ type: 'error', text: e.message || 'Failed to set price' });
    } finally {
      setPricingLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const isConnected = connectStatus?.charges_enabled;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Storefront size={20} weight="duotone" className="text-[#D4AF37]" />
          <h1 className="text-xl text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Teacher Marketplace
          </h1>
        </div>
        <p className="text-xs text-[#94A3B8]">Manage premium courses and view your earnings</p>
      </div>

      {/* How it works */}
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardContent className="p-5">
          <p className="text-xs tracking-[0.15em] uppercase text-[#D4AF37] mb-3">How the marketplace works</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-[#F8FAFC] mb-1">1 · Connect your account</p>
              <p className="text-xs text-[#94A3B8]">
                Payments run through Stripe, the same processor used across the platform.
                Onboarding takes a few minutes — Stripe asks for your details so they can
                deposit your earnings directly to your bank.
              </p>
            </div>
            <div>
              <p className="text-sm text-[#F8FAFC] mb-1">2 · Set a price on a course</p>
              <p className="text-xs text-[#94A3B8]">
                Any course you teach can become premium. Learners then purchase it once
                for lifetime access instead of enrolling free. Set the price to $0 anytime
                to make it free again.
              </p>
            </div>
            <div>
              <p className="text-sm text-[#F8FAFC] mb-1">3 · You keep 85%</p>
              <p className="text-xs text-[#94A3B8]">
                The platform keeps a 15% fee to sustain the commons; the rest lands in your
                Stripe account and pays out to your bank on Stripe's schedule (typically
                2 business days). Purchases happen on the website — app-store rules don't
                allow card checkout inside the mobile apps.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Status messages */}
      {statusMessage && (
        <div className={`p-3 rounded-md text-sm ${
          statusMessage.type === 'success'
            ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/30 text-red-400'
        }`}>
          {statusMessage.text}
        </div>
      )}

      {/* Stripe Connect Status */}
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <CreditCard size={18} weight="duotone" className="text-[#D4AF37]" />
              <span className="text-sm text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                Payment Account
              </span>
            </div>
            <Badge className={isConnected
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            }>
              {isConnected ? 'Active' : 'Setup Required'}
            </Badge>
          </div>

          {!connectStatus?.connected ? (
            <div>
              <p className="text-xs text-[#94A3B8] mb-3">
                Connect your Stripe account to receive payments from premium courses.
                The platform takes a 15% fee; you keep the rest.
              </p>
              <button
                onClick={handleStartOnboarding}
                disabled={onboardingLoading}
                className="px-4 py-2 rounded-md text-xs font-medium bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/30 transition-all flex items-center gap-2"
              >
                {onboardingLoading ? (
                  <div className="w-4 h-4 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Lightning size={14} weight="duotone" />
                )}
                Connect with Stripe
              </button>
            </div>
          ) : !isConnected ? (
            <div>
              <p className="text-xs text-[#94A3B8] mb-3">
                Your Stripe account is connected but onboarding isn't complete yet.
              </p>
              <button
                onClick={handleStartOnboarding}
                disabled={onboardingLoading}
                className="px-4 py-2 rounded-md text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 transition-all flex items-center gap-2"
              >
                <Warning size={14} weight="duotone" />
                Complete Onboarding
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs text-emerald-400">
                <CheckCircle size={14} weight="duotone" />
                <span>Payments enabled</span>
              </div>
              <button
                onClick={handleOpenStripeDashboard}
                className="text-xs text-[#94A3B8] hover:text-[#D4AF37] transition-colors flex items-center gap-1"
              >
                <ArrowSquareOut size={12} />
                Stripe Dashboard
              </button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Earnings Summary */}
      {isConnected && earnings && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Total Sales', value: earnings.summary.total_sales, icon: ChartLineUp },
            { label: 'Gross Revenue', value: `$${earnings.summary.total_gross.toFixed(2)}`, icon: CurrencyDollar },
            { label: 'Platform Fees', value: `$${earnings.summary.total_fees.toFixed(2)}`, icon: Storefront },
            { label: 'Your Earnings', value: `$${earnings.summary.total_net.toFixed(2)}`, icon: CurrencyDollar, highlight: true },
          ].map(({ label, value, icon: Icon, highlight }) => (
            <Card key={label} className={`bg-[#0F172A] ${highlight ? 'border-[#D4AF37]/30' : 'border-[#1E293B]'}`}>
              <CardContent className="p-4">
                <Icon size={16} weight="duotone" className={highlight ? 'text-[#D4AF37]' : 'text-[#94A3B8]'} />
                <p className={`text-lg font-bold mt-1 ${highlight ? 'text-[#D4AF37]' : 'text-[#F8FAFC]'}`}>{value}</p>
                <p className="text-[9px] text-[#94A3B8] uppercase tracking-widest">{label}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* My Courses with Pricing */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <ChalkboardTeacher size={18} weight="duotone" className="text-[#D4AF37]" />
          <h2 className="text-sm text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Your Courses
          </h2>
        </div>

        {myCourses.length === 0 ? (
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardContent className="p-5 text-center">
              <p className="text-xs text-[#94A3B8]">No courses yet. Create a course first, then set premium pricing here.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {myCourses.map(course => {
              const isPremium = course.is_premium && course.premium_price > 0;
              const courseEarnings = earnings?.by_course?.find(c => c.course_id === course.id);

              return (
                <Card key={course.id} className="bg-[#0F172A] border-[#1E293B]">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <h3 className="text-sm text-[#F8FAFC] truncate">{course.title}</h3>
                          {isPremium && (
                            <Badge className="bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20 text-[8px] shrink-0">
                              ${course.premium_price}
                            </Badge>
                          )}
                          <Badge className={`text-[8px] shrink-0 ${
                            course.status === 'active'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : 'bg-[#94A3B8]/10 text-[#94A3B8] border-[#94A3B8]/20'
                          }`}>
                            {course.status}
                          </Badge>
                          <button
                            onClick={() => handleToggleVisibility(course)}
                            title="Toggle whether this course appears in the community catalog"
                            className={`text-[8px] uppercase tracking-wider px-1.5 py-0.5 rounded border shrink-0 transition-colors ${
                              course.visibility !== 'unlisted'
                                ? 'bg-sky-500/10 text-sky-400 border-sky-500/20 hover:bg-sky-500/20'
                                : 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20 hover:bg-[#D4AF37]/20'
                            }`}
                            data-testid={`visibility-${course.id}`}
                          >
                            {course.visibility !== 'unlisted' ? 'Listed' : 'Invite-only'}
                          </button>
                        </div>
                        {courseEarnings && (
                          <p className="text-[10px] text-[#94A3B8]">
                            {courseEarnings.total_sales} sale{courseEarnings.total_sales !== 1 ? 's' : ''} · ${courseEarnings.net_earnings.toFixed(2)} earned
                          </p>
                        )}
                      </div>

                      {isConnected && (
                        <div className="ml-3 shrink-0">
                          {pricingCourse === course.id ? (
                            <div className="flex items-center gap-2">
                              <div className="relative">
                                <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[#94A3B8] text-xs">$</span>
                                <input
                                  type="number"
                                  min="0"
                                  step="0.01"
                                  value={priceInput}
                                  onChange={e => setPriceInput(e.target.value)}
                                  placeholder="0.00"
                                  className="w-24 pl-5 pr-2 py-1.5 rounded bg-[#1E293B] border border-[#334155] text-xs text-[#F8FAFC] focus:outline-none focus:border-[#D4AF37]"
                                />
                              </div>
                              <button
                                onClick={() => handleSetPremium(course.id)}
                                disabled={pricingLoading}
                                className="px-2 py-1.5 rounded text-[10px] font-medium bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/30"
                              >
                                {pricingLoading ? '...' : 'Set'}
                              </button>
                              <button
                                onClick={() => { setPricingCourse(null); setPriceInput(''); }}
                                className="px-2 py-1.5 rounded text-[10px] text-[#94A3B8] hover:text-[#F8FAFC]"
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => {
                                setPricingCourse(course.id);
                                setPriceInput(course.premium_price ? String(course.premium_price) : '');
                              }}
                              className="text-[10px] text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
                            >
                              {isPremium ? 'Edit Price' : 'Set Price'}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent Transactions */}
      {isConnected && earnings?.recent_transactions?.length > 0 && (
        <div>
          <h2 className="text-sm text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Recent Sales
          </h2>
          <div className="space-y-1">
            {earnings.recent_transactions.slice(0, 10).map(txn => (
              <div key={txn.id} className="flex items-center justify-between py-2 px-3 rounded bg-[#0F172A] border border-[#1E293B]">
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-[#F8FAFC] truncate">{txn.course_title}</p>
                  <p className="text-[9px] text-[#94A3B8]">
                    {txn.user_email} · {new Date(txn.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="text-right ml-3">
                  <p className="text-xs text-[#D4AF37]">+${txn.teacher_earnings?.toFixed(2)}</p>
                  <p className="text-[9px] text-[#94A3B8]">${txn.amount?.toFixed(2)} gross</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
