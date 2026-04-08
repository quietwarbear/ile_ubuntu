import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import BrandMark from '../components/brand/BrandMark';

export default function TermsPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#050814]">
      {/* Header */}
      <div className="max-w-4xl mx-auto px-6 pt-12 pb-6">
        <button
          onClick={() => navigate(-1)}
          className="text-sm text-[#94A3B8] hover:text-[#D4AF37] transition-colors mb-8 flex items-center gap-2"
        >
          <span>&larr;</span> Back
        </button>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/30 flex items-center justify-center">
            <BrandMark className="w-6 h-6 object-contain" />
          </div>
          <span className="text-[#D4AF37] text-sm tracking-[0.15em] uppercase" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            The Ile Ubuntu
          </span>
        </div>
        <h1
          className="text-3xl sm:text-4xl text-[#F8FAFC] mb-2"
          style={{ fontFamily: 'Cormorant Garamond, serif' }}
        >
          Terms of Use
        </h1>
        <p className="text-sm text-[#94A3B8]">Last updated: April 4, 2026</p>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 pb-20">
        <div className="prose prose-invert max-w-none text-[#CBD5E1] text-[15px] leading-relaxed space-y-6">

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>1. Acceptance of Terms</h2>
            <p>
              By accessing or using The Ile Ubuntu platform, including the website at www.ile-ubuntu.org and
              The Ile Ubuntu mobile application (collectively, the "Service"), operated by Ubuntu Markets, LLC
              ("we," "our," or "us"), you agree to be bound by these Terms of Use. If you do not agree to
              these terms, do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>2. Description of Service</h2>
            <p>
              The Ile Ubuntu is a learning management platform rooted in the Ubuntu philosophy. The Service
              provides access to structured courses, live teaching sessions, community forums, cohort-based
              learning, knowledge spaces, and archives. Access to certain features requires a paid subscription.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>3. Account Registration</h2>
            <p>
              To use the Service, you must create an account by providing accurate and complete information.
              You are responsible for maintaining the confidentiality of your account credentials and for all
              activities that occur under your account. You must be at least 13 years of age to use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>4. Subscription Plans and Pricing</h2>
            <p>The Ile Ubuntu offers the following membership tiers:</p>

            <div className="mt-4 space-y-4">
              <div className="p-4 rounded-lg border border-[#1E293B] bg-[#0F172A]">
                <h3 className="text-[#E2E8F0] font-semibold">Explorer (Free)</h3>
                <p className="text-sm text-[#94A3B8] mt-1">
                  Browse public courses, access community features, basic archives, and enroll in up to 2 courses.
                  No payment required.
                </p>
              </div>

              <div className="p-4 rounded-lg border border-[#D4AF37]/20 bg-[#D4AF37]/5">
                <h3 className="text-[#D4AF37] font-semibold">Scholar &mdash; $19.99/month or annual pricing</h3>
                <p className="text-sm text-[#94A3B8] mt-1">
                  All Explorer features plus unlimited course enrollment, cohort membership, knowledge spaces
                  access, and priority support.
                </p>
              </div>

              <div className="p-4 rounded-lg border border-violet-500/20 bg-violet-500/5">
                <h3 className="text-violet-400 font-semibold">Elder Circle &mdash; $49.99/month or annual pricing</h3>
                <p className="text-sm text-[#94A3B8] mt-1">
                  All Scholar features plus live teaching sessions, protected archives access, and governance
                  participation within the community.
                </p>
              </div>
            </div>

            <p className="mt-4">
              Prices are in US dollars and may vary by region. Current pricing for all regions is displayed
              at the time of purchase within the app.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>5. Auto-Renewable Subscriptions</h2>
            <p>
              Paid subscriptions (Scholar and Elder Circle) are offered as <strong className="text-[#E2E8F0]">auto-renewable subscriptions</strong>.
              By subscribing, you acknowledge and agree to the following:
            </p>
            <ul className="list-disc pl-6 space-y-2 text-[#94A3B8] mt-3">
              <li>
                <strong className="text-[#E2E8F0]">Payment:</strong> Payment is charged to your Apple ID account
                (for iOS), your Google Play account (for Android), or your payment method on file (for web via
                Stripe) at confirmation of purchase.
              </li>
              <li>
                <strong className="text-[#E2E8F0]">Auto-Renewal:</strong> Subscriptions automatically renew unless
                auto-renew is turned off at least 24 hours before the end of the current billing period. Your account
                will be charged for renewal within 24 hours prior to the end of the current period at the same rate.
              </li>
              <li>
                <strong className="text-[#E2E8F0]">Managing Subscriptions:</strong> You can manage and cancel your
                subscription at any time. On iOS, go to Settings &gt; [Your Name] &gt; Subscriptions. On Android,
                go to Google Play Store &gt; Menu &gt; Subscriptions. On web, manage your subscription through
                your account settings or contact us at support@ubuntu-village.org.
              </li>
              <li>
                <strong className="text-[#E2E8F0]">Cancellation:</strong> If you cancel your subscription, you will
                continue to have access to your paid features until the end of your current billing period. No refunds
                are provided for partial billing periods.
              </li>
              <li>
                <strong className="text-[#E2E8F0]">Free Trial:</strong> If a free trial is offered, any unused portion
                of the trial period will be forfeited when you purchase a subscription.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>6. User Conduct</h2>
            <p>You agree not to:</p>
            <ul className="list-disc pl-6 space-y-1 text-[#94A3B8]">
              <li>Use the Service for any unlawful purpose</li>
              <li>Post content that is abusive, harassing, defamatory, or discriminatory</li>
              <li>Share your account credentials with others</li>
              <li>Attempt to gain unauthorized access to other accounts or platform systems</li>
              <li>Distribute malware or engage in activities that disrupt the Service</li>
              <li>Reproduce, distribute, or create derivative works from course content without permission</li>
            </ul>
            <p className="mt-2">
              We reserve the right to suspend or terminate accounts that violate these terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>7. Intellectual Property</h2>
            <p>
              All content on the Service, including courses, materials, designs, logos, and software, is the
              property of Ubuntu Markets, LLC or its content creators and is protected by intellectual property
              laws. Course content created by faculty remains the intellectual property of the respective creators
              unless otherwise agreed.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>8. User-Generated Content</h2>
            <p>
              By posting content to community forums, discussions, or other public areas of the Service, you
              grant us a non-exclusive, worldwide, royalty-free license to use, display, and distribute that
              content within the Service. You retain ownership of your content and may delete it at any time.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>9. Disclaimer of Warranties</h2>
            <p>
              The Service is provided "as is" and "as available" without warranties of any kind, whether express
              or implied. We do not guarantee that the Service will be uninterrupted, error-free, or secure.
              Educational content is provided for informational purposes and does not constitute professional advice.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>10. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by law, Ubuntu Markets, LLC shall not be liable for any indirect,
              incidental, special, consequential, or punitive damages arising from your use of the Service,
              including but not limited to loss of data, loss of profits, or interruption of service.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>11. Changes to These Terms</h2>
            <p>
              We may update these Terms of Use from time to time. We will notify you of material changes by
              posting the updated terms on this page and updating the "Last updated" date. Your continued use
              of the Service after changes are posted constitutes your acceptance of the revised terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>12. Governing Law</h2>
            <p>
              These Terms of Use shall be governed by and construed in accordance with the laws of the State
              of California, without regard to its conflict of law provisions.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>13. Contact Us</h2>
            <p>If you have questions about these Terms of Use, please contact us at:</p>
            <div className="mt-2 text-[#94A3B8]">
              <p>Ubuntu Markets, LLC</p>
              <p>Email: support@ubuntu-village.org</p>
              <p>Website: www.ile-ubuntu.org</p>
            </div>
          </section>

          <section className="mt-8 pt-6 border-t border-[#1E293B]">
            <p className="text-sm text-[#64748B]">
              See also our{' '}
              <Link to="/privacy-policy" className="text-[#D4AF37] hover:underline">Privacy Policy</Link>.
            </p>
          </section>

        </div>
      </div>
    </div>
  );
}
