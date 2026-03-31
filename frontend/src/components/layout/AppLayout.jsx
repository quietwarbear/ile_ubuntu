import React from 'react';
import Sidebar from './Sidebar';

export default function AppLayout({ user, onLogout, children }) {
  return (
    <div className="min-h-screen bg-[#050814]">
      <Sidebar user={user} onLogout={onLogout} />
      <main className="lg:ml-60 min-h-screen">
        <div className="p-6 md:p-8 lg:p-10 max-w-[1400px] mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
