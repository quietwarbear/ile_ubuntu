import React from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function AppLayout({ user, onLogout, children }) {
  const location = useLocation();
  const isLiveRoom = location.pathname.startsWith('/live/');

  return (
    <div className="min-h-screen bg-[#050814]">
      {!isLiveRoom && <Sidebar user={user} onLogout={onLogout} />}
      <main className={`min-h-screen ${isLiveRoom ? '' : 'lg:ml-60'}`} style={{ paddingTop: 'var(--safe-area-top, 0px)' }}>
        <div className={isLiveRoom ? '' : 'p-6 md:p-8 lg:p-10 max-w-[1400px] mx-auto'}>
          {children}
        </div>
      </main>
    </div>
  );
}
