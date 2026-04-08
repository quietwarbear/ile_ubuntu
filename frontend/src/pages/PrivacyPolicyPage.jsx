import React from 'react';
import { useNavigate } from 'react-router-dom';
import BrandMark from '../components/brand/BrandMark';

export default function PrivacyPolicyPage() {
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
          Privacy Policy
        </h1>
        <p className="text-sm text-[#94A3B8]">Last updated: April 4, 2026</p>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 pb-20">
        <div className="prose prose-invert max-w-none text-[#CBD5E1] text-[15px] leading-relaxed space-y-6">

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>1. Introduction</h2>
            <p>
              Ubuntu Markets, LLC ("we," "our," or "us") operates The Ile Ubuntu platform, including the website at
              www.ile-ubuntu.org and The Ile Ubuntu mobile application (collectively, the "Service"). This Privacy Policy
              explains how we collect, use, disclose, and safeguard your information when you use our Service.
            </p>
            <p>
              By accessing or using the Service, you agree to this Privacy Policy. If you do not agree with the terms of
              this policy, please do not access the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>2. Information We Collect</h2>

            <h3 className="text-lg text-[#E2E8F0] mt-4 mb-2">Personal Information</h3>
            <p>When you create an account or use our Service, we may collect:</p>
            <ul className="list-disc pl-6 space-y-1 text-[#94A3B8]">
              <li>Name and email address</li>
              <li>Profile information (role, language preference, profile photo)</li>
              <li>Authentication credentials (password hash, or Google OAuth tokens)</li>
              <li>Subscription and purchase history</li>
            </ul>

            <h3 className="text-lg text-[#E2E8F0] mt-4 mb-2">Usage Information</h3>
            <p>We automatically collect certain information when you use the Service:</p>
            <ul className="list-disc pl-6 space-y-1 text-[#94A3B8]">
              <li>Course enrollment and progress data</li>
              <li>Community interaction data (posts, discussions, likes)</li>
              <li>Session attendance records</li>
              <li>Device type, operating system, and browser information</li>
              <li>IP address and general location data</li>
            </ul>

            <h3 className="text-lg text-[#E2E8F0] mt-4 mb-2">Payment Information</h3>
            <p>
              Subscription payments are processed by Apple (via the App Store for iOS), Google (via Google Play
              for Android), and Stripe (for web). We do not store your credit card number or full payment details.
              We receive only transaction confirmations, subscription status, and billing identifiers from these
              payment processors.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>3. How We Use Your Information</h2>
            <p>We use the information we collect to:</p>
            <ul className="list-disc pl-6 space-y-1 text-[#94A3B8]">
              <li>Provide, maintain, and improve the Service</li>
              <li>Process your account registration and manage your subscription</li>
              <li>Track course enrollment, progress, and completion</li>
              <li>Facilitate community features (discussions, cohorts, knowledge spaces)</li>
              <li>Send transactional emails (enrollment confirmations, session reminders)</li>
              <li>Generate aggregated analytics and platform metrics</li>
              <li>Respond to your inquiries and provide customer support</li>
              <li>Enforce our Terms of Use and protect against misuse</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>4. Information Sharing</h2>
            <p>We do not sell your personal information. We may share your information with:</p>
            <ul className="list-disc pl-6 space-y-1 text-[#94A3B8]">
              <li><strong className="text-[#E2E8F0]">Service Providers:</strong> Third-party services that help us operate the platform (e.g., MongoDB for data storage, Resend for email, Stripe and Apple for payments, RevenueCat for subscription management, Jitsi for video conferencing).</li>
              <li><strong className="text-[#E2E8F0]">Other Users:</strong> Your display name, role, and profile photo may be visible to other users within courses, cohorts, community forums, and knowledge spaces you participate in.</li>
              <li><strong className="text-[#E2E8F0]">Legal Requirements:</strong> We may disclose information if required by law, regulation, or legal process.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>5. Data Security</h2>
            <p>
              We use industry-standard security measures to protect your information, including encrypted data
              transmission (HTTPS/TLS), secure authentication, and access controls. However, no method of
              electronic transmission or storage is 100% secure, and we cannot guarantee absolute security.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>6. Data Retention</h2>
            <p>
              We retain your personal information for as long as your account is active or as needed to provide
              the Service. You may request deletion of your account and associated data by contacting us at
              support@ubuntu-village.org. Some information may be retained as required by law or for legitimate
              business purposes (e.g., fraud prevention, financial records).
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>7. Your Rights</h2>
            <p>Depending on your jurisdiction, you may have the right to:</p>
            <ul className="list-disc pl-6 space-y-1 text-[#94A3B8]">
              <li>Access the personal information we hold about you</li>
              <li>Request correction of inaccurate information</li>
              <li>Request deletion of your personal information</li>
              <li>Object to or restrict certain processing of your data</li>
              <li>Request portability of your data</li>
            </ul>
            <p className="mt-2">
              To exercise these rights, contact us at support@ubuntu-village.org.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>8. Children's Privacy</h2>
            <p>
              The Service is not intended for children under the age of 13. We do not knowingly collect personal
              information from children under 13. If we learn that we have collected information from a child
              under 13, we will promptly delete that information.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>9. Third-Party Services</h2>
            <p>
              Our Service integrates with third-party services including Google (authentication and Google Play
              payments), Apple App Store (iOS subscriptions and payments), Stripe (web payments), RevenueCat
              (subscription management), Jitsi (video conferencing), and Resend (email). Each of these services
              has its own privacy policy governing the use of your information. We encourage you to review their
              policies.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>10. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of any changes by posting
              the new policy on this page and updating the "Last updated" date. Your continued use of the Service
              after any changes constitutes your acceptance of the updated policy.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-[#F8FAFC] mb-3" style={{ fontFamily: 'Cormorant Garamond, serif' }}>11. Contact Us</h2>
            <p>If you have questions about this Privacy Policy, please contact us at:</p>
            <div className="mt-2 text-[#94A3B8]">
              <p>Ubuntu Markets, LLC</p>
              <p>Email: support@ubuntu-village.org</p>
              <p>Website: www.ile-ubuntu.org</p>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
