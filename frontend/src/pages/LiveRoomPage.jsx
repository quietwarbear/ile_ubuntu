import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  ArrowLeft,
  Stop,
  Users,
  Circle,
  Microphone,
  MicrophoneSlash,
  VideoCamera,
  VideoCameraSlash,
  ScreenShare,
  Chat,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut } from '../lib/api';

export default function LiveRoomPage({ user }) {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const jitsiContainerRef = useRef(null);
  const jitsiApiRef = useRef(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [jitsiLoaded, setJitsiLoaded] = useState(false);
  const [participantCount, setParticipantCount] = useState(0);

  const isHost = session?.host_id === user?.id;

  useEffect(() => {
    loadSession();
    return () => {
      if (jitsiApiRef.current) {
        jitsiApiRef.current.dispose();
        jitsiApiRef.current = null;
      }
    };
  }, [sessionId]);

  useEffect(() => {
    if (session && !jitsiApiRef.current) {
      loadJitsiScript();
    }
  }, [session]);

  const loadSession = async () => {
    try {
      const data = await apiGet(`/api/live-sessions/${sessionId}`);
      setSession(data);

      // Join the session
      await apiPost(`/api/live-sessions/${sessionId}/join`, {});
    } catch (e) {
      console.error('Failed to load session:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadJitsiScript = () => {
    if (window.JitsiMeetExternalAPI) {
      initJitsi();
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://meet.jit.si/external_api.js';
    script.async = true;
    script.onload = () => initJitsi();
    script.onerror = () => console.error('Failed to load Jitsi API');
    document.head.appendChild(script);
  };

  const initJitsi = () => {
    if (!jitsiContainerRef.current || !session || jitsiApiRef.current) return;

    const api = new window.JitsiMeetExternalAPI('meet.jit.si', {
      roomName: session.room_name,
      parentNode: jitsiContainerRef.current,
      width: '100%',
      height: '100%',
      configOverwrite: {
        startWithAudioMuted: !isHost,
        startWithVideoMuted: false,
        disableDeepLinking: true,
        prejoinPageEnabled: false,
        toolbarButtons: [
          'microphone', 'camera', 'desktop', 'chat',
          'raisehand', 'participants-pane', 'tileview',
          'select-background', 'fullscreen',
        ],
        disableModeratorIndicator: false,
        enableWelcomePage: false,
        enableClosePage: false,
        hideConferenceSubject: true,
      },
      interfaceConfigOverwrite: {
        SHOW_JITSI_WATERMARK: false,
        SHOW_WATERMARK_FOR_GUESTS: false,
        SHOW_BRAND_WATERMARK: false,
        TOOLBAR_ALWAYS_VISIBLE: true,
        HIDE_INVITE_MORE_HEADER: true,
        MOBILE_APP_PROMO: false,
        DEFAULT_BACKGROUND: '#050814',
      },
      userInfo: {
        displayName: user?.name || 'Participant',
        email: user?.email || '',
      },
    });

    api.addEventListener('participantJoined', () => {
      setParticipantCount(prev => prev + 1);
    });

    api.addEventListener('participantLeft', () => {
      setParticipantCount(prev => Math.max(0, prev - 1));
    });

    api.addEventListener('videoConferenceJoined', () => {
      setJitsiLoaded(true);
      setParticipantCount(api.getNumberOfParticipants());
    });

    api.addEventListener('readyToClose', () => {
      handleLeave();
    });

    jitsiApiRef.current = api;
  };

  const handleEndSession = async () => {
    if (!window.confirm('End this session for everyone?')) return;
    try {
      await apiPut(`/api/live-sessions/${sessionId}/end`, {});
      if (jitsiApiRef.current) {
        jitsiApiRef.current.dispose();
        jitsiApiRef.current = null;
      }
      navigate('/live');
    } catch (e) { alert(e.message); }
  };

  const handleLeave = () => {
    if (jitsiApiRef.current) {
      jitsiApiRef.current.dispose();
      jitsiApiRef.current = null;
    }
    navigate('/live');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm text-[#94A3B8]">Connecting to session...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="text-center py-20">
        <p className="text-[#94A3B8]">Session not found</p>
        <Button onClick={() => navigate('/live')} variant="ghost" className="mt-4 text-[#D4AF37]">
          Back to Sessions
        </Button>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-5rem)] flex flex-col" data-testid="live-room-page">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#0A1128] border-b border-[#1E293B]">
        <div className="flex items-center gap-3">
          <button
            onClick={handleLeave}
            className="text-[#94A3B8] hover:text-[#F8FAFC] transition-colors"
            data-testid="leave-room-btn"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <h2
                className="text-sm font-medium text-[#F8FAFC]"
                style={{ fontFamily: 'Cormorant Garamond, serif' }}
                data-testid="room-title"
              >
                {session.title}
              </h2>
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-[10px] text-[#94A3B8]">Host: {session.host_name}</span>
              {session.course_title && (
                <span className="text-[10px] text-[#D4AF37]">{session.course_title}</span>
              )}
              <span className="text-[10px] text-[#94A3B8] flex items-center gap-1">
                <Users size={10} /> {participantCount} in room
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isHost && (
            <Button
              size="sm"
              onClick={handleEndSession}
              className="bg-red-500 text-white hover:bg-red-600 text-xs"
              data-testid="end-session-btn"
            >
              <Stop size={14} weight="fill" className="mr-1" /> End Session
            </Button>
          )}
          {!isHost && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleLeave}
              className="border-[#1E293B] text-[#94A3B8] hover:text-red-400 text-xs"
              data-testid="leave-session-btn"
            >
              Leave
            </Button>
          )}
        </div>
      </div>

      {/* Jitsi Container */}
      <div className="flex-1 relative bg-[#050814]">
        {!jitsiLoaded && (
          <div className="absolute inset-0 flex items-center justify-center z-10 bg-[#050814]">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto rounded-lg bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center mb-4">
                <VideoCamera size={28} weight="duotone" className="text-[#D4AF37]" />
              </div>
              <p className="text-sm text-[#94A3B8] mb-1">Setting up your classroom...</p>
              <p className="text-[10px] text-[#94A3B8]">Camera and microphone access may be required</p>
            </div>
          </div>
        )}
        <div
          ref={jitsiContainerRef}
          className="w-full h-full"
          data-testid="jitsi-container"
        />
      </div>
    </div>
  );
}
