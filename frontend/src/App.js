import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Bell, MessageSquare, BookOpen, Users, PlusCircle, LogIn, Presentation, FileText, Video, Mic, Send, Upload, File, Download, Trash2, Edit } from 'lucide-react';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [classes, setClasses] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [messages, setMessages] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleSlides, setGoogleSlides] = useState([]);
  const [googleDocs, setGoogleDocs] = useState([]);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showInstallPrompt, setShowInstallPrompt] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    checkAuthStatus();
    
    // PWA Install Prompt Handler
    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstallPrompt(true);
    };

    // Handle Google OAuth callback
    const handleGoogleAuthMessage = async (event) => {
      if (event.data && event.data.type === 'GOOGLE_OAUTH_SUCCESS') {
        const code = event.data.code;
        await completeGoogleAuth(code);
      }
    };

    // Handle Google auth code from URL and localStorage
    const handleGoogleAuthFromURL = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const googleOAuthComplete = urlParams.get('google_oauth_complete');
      
      if (googleOAuthComplete) {
        console.log('Google OAuth completion detected');
        
        const googleAuthCode = localStorage.getItem('google_auth_code');
        const authTimestamp = localStorage.getItem('google_auth_timestamp');
        
        console.log('Auth code from localStorage:', googleAuthCode ? 'Present' : 'Missing');
        console.log('Auth timestamp:', authTimestamp);
        
        if (googleAuthCode) {
          // Check if the auth code is recent (within 10 minutes)
          const now = Date.now();
          const authTime = parseInt(authTimestamp);
          const timeDiff = now - authTime;
          
          if (timeDiff < 10 * 60 * 1000) { // 10 minutes
            console.log('Completing Google auth with code...');
            await completeGoogleAuth(googleAuthCode);
          } else {
            console.log('Auth code expired, please try again');
            alert('Authentication session expired. Please try connecting to Google again.');
          }
          
          // Clean up
          localStorage.removeItem('google_auth_code');
          localStorage.removeItem('google_auth_timestamp');
        } else {
          console.log('No auth code found in localStorage');
          alert('Authentication code not found. Please try connecting to Google again.');
        }
        
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('message', handleGoogleAuthMessage);
    
    // Check for Google auth code in URL on load
    handleGoogleAuthFromURL();

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('message', handleGoogleAuthMessage);
    };
  }, []);

  const completeGoogleAuth = async (code) => {
    const sessionId = getCookie('session_id');
    console.log('Attempting to complete Google auth with session:', sessionId ? 'Present' : 'Missing');
    
    if (!sessionId) {
      alert('Please log in first before connecting Google account.');
      return;
    }
    
    try {
      console.log('Sending auth completion request...');
      const response = await fetch(`${BACKEND_URL}/api/google/complete-auth`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({ code })
      });

      console.log('Auth completion response status:', response.status);
      
      if (response.ok) {
        const result = await response.json();
        console.log('Auth completion successful:', result);
        alert('✅ Google account connected successfully!\n\nYou can now import your Google Slides and Docs.');
        setGoogleConnected(true);
        await loadGoogleData();
      } else {
        const error = await response.json();
        console.error('Auth completion failed:', error);
        alert(`❌ Failed to connect Google account:\n\n${error.detail || 'Unknown error'}\n\nPlease try again.`);
      }
    } catch (error) {
      console.error('Auth completion error:', error);
      alert('❌ Failed to complete Google authentication.\n\nPlease check your internet connection and try again.');
    }
  };

  const installPWA = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      console.log(`User response to the install prompt: ${outcome}`);
      setDeferredPrompt(null);
      setShowInstallPrompt(false);
    }
  };

  const checkAuthStatus = async () => {
    const sessionId = getCookie('session_id');
    if (sessionId) {
      try {
        const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
          headers: {
            'X-Session-ID': sessionId
          }
        });
        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
          await loadDashboardData(sessionId);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
      }
    }
    setLoading(false);
  };

  const loadDashboardData = async (sessionId) => {
    try {
      const headers = { 'X-Session-ID': sessionId };
      
      const [classesRes, lessonsRes, notificationsRes, messagesRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/classes`, { headers }),
        fetch(`${BACKEND_URL}/api/lessons`, { headers }),
        fetch(`${BACKEND_URL}/api/notifications`, { headers }),
        fetch(`${BACKEND_URL}/api/messages`, { headers })
      ]);

      if (classesRes.ok) setClasses(await classesRes.json());
      if (lessonsRes.ok) setLessons(await lessonsRes.json());
      if (notificationsRes.ok) setNotifications(await notificationsRes.json());
      if (messagesRes.ok) setMessages(await messagesRes.json());
      
      // Try to load Google data (will fail silently if not connected)
      loadGoogleData();
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  };

  const handleLogin = () => {
    const currentUrl = window.location.origin;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(currentUrl)}`;
  };

  const handleAuthCallback = async () => {
    const hash = window.location.hash;
    if (hash && hash.includes('session_id=')) {
      const sessionId = hash.split('session_id=')[1];
      
      try {
        const response = await fetch(`${BACKEND_URL}/api/auth/profile`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ session_id: sessionId })
        });

        if (response.ok) {
          const data = await response.json();
          setCookie('session_id', sessionId, 7);
          window.location.hash = '';
          checkAuthStatus();
        }
      } catch (error) {
        console.error('Authentication failed:', error);
      }
    }
  };

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  };

  const setCookie = (name, value, days) => {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${name}=${value}; expires=${expires}; path=/`;
  };

  const handleLogout = () => {
    document.cookie = 'session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    setUser(null);
    setClasses([]);
    setLessons([]);
    setNotifications([]);
    setMessages([]);
  };

  const createClass = async (classData) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/classes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify(classData)
      });

      if (response.ok) {
        const newClass = await response.json();
        setClasses([...classes, newClass]);
        return newClass;
      }
    } catch (error) {
      console.error('Failed to create class:', error);
    }
  };

  const updateClass = async (classId, classData) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/classes/${classId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify(classData)
      });

      if (response.ok) {
        const updatedClass = await response.json();
        setClasses(classes.map(c => c.id === classId ? updatedClass : c));
        return updatedClass;
      } else {
        const error = await response.json();
        alert(`Failed to update class: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to update class:', error);
      alert('Failed to update class. Please try again.');
    }
  };

  const deleteClass = async (classId) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/classes/${classId}`, {
        method: 'DELETE',
        headers: { 'X-Session-ID': sessionId }
      });

      if (response.ok) {
        setClasses(classes.filter(c => c.id !== classId));
        alert('Class deleted successfully!');
      } else {
        const error = await response.json();
        alert(`Failed to delete class: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to delete class:', error);
      alert('Failed to delete class. Please try again.');
    }
  };

  const createLesson = async (lessonData) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/lessons`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify(lessonData)
      });

      if (response.ok) {
        const newLesson = await response.json();
        setLessons([newLesson, ...lessons]);
        return newLesson;
      }
    } catch (error) {
      console.error('Failed to create lesson:', error);
    }
  };

  const connectGoogle = async () => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/google/auth-url`, {
        headers: { 'X-Session-ID': sessionId }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.auth_url) {
          // Open in the same window instead of popup to avoid blocking
          window.location.href = data.auth_url;
        } else if (data.error) {
          alert(`Google OAuth Setup Required:\n\n${data.message}\n\nInstructions:\n${data.instructions.join('\n')}`);
        }
      }
    } catch (error) {
      console.error('Failed to get Google auth URL:', error);
      alert('Failed to connect to Google. Please try again later.');
    }
  };

  const loadGoogleData = async () => {
    const sessionId = getCookie('session_id');
    try {
      const headers = { 'X-Session-ID': sessionId };
      
      const [slidesRes, docsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/google/slides`, { headers }),
        fetch(`${BACKEND_URL}/api/google/docs`, { headers })
      ]);

      if (slidesRes.ok) {
        const slidesData = await slidesRes.json();
        setGoogleSlides(slidesData.presentations);
        setGoogleConnected(true);
      }
      
      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setGoogleDocs(docsData.documents);
      }
    } catch (error) {
      console.error('Failed to load Google data:', error);
    }
  };

  const importSlides = async (slidesId, lessonId = null) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/google/import-slides`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({ slides_id: slidesId, lesson_id: lessonId })
      });

      if (response.ok) {
        const result = await response.json();
        alert('Slides imported successfully!');
        return result;
      }
    } catch (error) {
      console.error('Failed to import slides:', error);
    }
  };

  const importDocs = async (docsId, lessonId = null) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/google/import-docs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({ docs_id: docsId, lesson_id: lessonId })
      });

      if (response.ok) {
        const result = await response.json();
        alert('Document imported successfully!');
        return result;
      }
    } catch (error) {
      console.error('Failed to import document:', error);
    }
  };

  const uploadFile = async (file, lessonId = null, classId = null) => {
    const sessionId = getCookie('session_id');
    setUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (lessonId) formData.append('lesson_id', lessonId);
      if (classId) formData.append('class_id', classId);

      const response = await fetch(`${BACKEND_URL}/api/files/upload`, {
        method: 'POST',
        headers: {
          'X-Session-ID': sessionId
        },
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        setUploadedFiles([result.file, ...uploadedFiles]);
        alert('File uploaded successfully!');
        return result;
      } else {
        const error = await response.json();
        alert(`Upload failed: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to upload file:', error);
      alert('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const loadFiles = async (lessonId = null, classId = null) => {
    const sessionId = getCookie('session_id');
    try {
      let url = `${BACKEND_URL}/api/files`;
      const params = new URLSearchParams();
      if (lessonId) params.append('lesson_id', lessonId);
      if (classId) params.append('class_id', classId);
      if (params.toString()) url += `?${params.toString()}`;

      const response = await fetch(url, {
        headers: { 'X-Session-ID': sessionId }
      });

      if (response.ok) {
        const data = await response.json();
        setUploadedFiles(data.files);
      }
    } catch (error) {
      console.error('Failed to load files:', error);
    }
  };

  const deleteFile = async (fileId) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/files/${fileId}`, {
        method: 'DELETE',
        headers: { 'X-Session-ID': sessionId }
      });

      if (response.ok) {
        setUploadedFiles(uploadedFiles.filter(file => file.id !== fileId));
        alert('File deleted successfully!');
      }
    } catch (error) {
      console.error('Failed to delete file:', error);
    }
  };

  const sendMessage = async (messageData) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify(messageData)
      });

      if (response.ok) {
        const newMessage = await response.json();
        setMessages([newMessage, ...messages]);
        return newMessage;
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  useEffect(() => {
    handleAuthCallback();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-midnight-900 via-black to-midnight-800 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gold-400"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-midnight-900 via-black to-midnight-800 flex items-center justify-center">
        <div className="max-w-md w-full space-y-8 p-8">
          <div className="text-center">
            <img 
              src="https://customer-assets.emergentagent.com/job_lessonhub-4/artifacts/58m7009f_anhk.png" 
              alt="Ankh Symbol" 
              className="mx-auto h-16 w-16 mb-6 object-contain"
            />
            <h2 className="text-4xl font-bold text-white mb-2">The Ile Ubuntu</h2>
            <p className="text-gray-300 mb-8">Your comprehensive classroom management platform</p>
            <Button 
              onClick={handleLogin}
              className="w-full bg-gold-600 hover:bg-gold-700 text-black font-semibold py-3 px-6 rounded-xl transition-all duration-300 transform hover:scale-105"
            >
              <LogIn className="mr-2 h-5 w-5" />
              Sign in with Google
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-midnight-900 via-black to-midnight-800">
      {/* Header */}
      <header className="bg-black/50 backdrop-blur-lg border-b border-midnight-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <img 
                src="https://customer-assets.emergentagent.com/job_lessonhub-4/artifacts/58m7009f_anhk.png" 
                alt="Ankh Symbol" 
                className="h-8 w-8 object-contain"
              />
              <h1 className="text-2xl font-bold text-white">The Ile Ubuntu</h1>
            </div>
            
            <div className="flex items-center space-x-4">
              {showInstallPrompt && (
                <Button 
                  onClick={installPWA}
                  className="bg-gold-600 hover:bg-gold-700 text-black text-sm px-3 py-1"
                >
                  Install App
                </Button>
              )}
              
              <div className="relative">
                <Bell className="h-6 w-6 text-gray-300 hover:text-gold-400 cursor-pointer transition-colors" />
                {notifications.filter(n => !n.read).length > 0 && (
                  <Badge className="absolute -top-2 -right-2 bg-gold-600 text-black text-xs">
                    {notifications.filter(n => !n.read).length}
                  </Badge>
                )}
              </div>
              
              <div className="flex items-center space-x-3">
                <img 
                  src={user.picture} 
                  alt={user.name}
                  className="h-8 w-8 rounded-full border-2 border-gold-400"
                />
                <span className="text-white font-medium">{user.name}</span>
                <Button 
                  variant="ghost" 
                  onClick={handleLogout}
                  className="text-gray-300 hover:text-white hover:bg-midnight-800"
                >
                  Logout
                </Button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-6 mb-8 bg-midnight-800/50 backdrop-blur-lg border border-midnight-700">
            <TabsTrigger value="dashboard" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="classes" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Classes
            </TabsTrigger>
            <TabsTrigger value="lessons" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Lessons
            </TabsTrigger>
            <TabsTrigger value="files" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Files
            </TabsTrigger>
            <TabsTrigger value="google" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Google Import
            </TabsTrigger>
            <TabsTrigger value="messages" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Messages
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatsCard
                title="Classes"
                value={classes.length}
                icon={<Users className="h-8 w-8 text-gold-400" />}
                description="Active classrooms"
              />
              <StatsCard
                title="Lessons"
                value={lessons.length}
                icon={<BookOpen className="h-8 w-8 text-gold-400" />}
                description="Total lessons created"
              />
              <StatsCard
                title="Messages"
                value={messages.length}
                icon={<MessageSquare className="h-8 w-8 text-gold-400" />}
                description="Recent conversations"
              />
              <StatsCard
                title="Notifications"
                value={notifications.filter(n => !n.read).length}
                icon={<Bell className="h-8 w-8 text-gold-400" />}
                description="Unread notifications"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <RecentLessons lessons={lessons.slice(0, 5)} />
              <RecentNotifications notifications={notifications.slice(0, 5)} />
            </div>
          </TabsContent>

          {/* Classes Tab */}
          <TabsContent value="classes" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">My Classes</h2>
              {user.role === 'teacher' && <CreateClassDialog onCreateClass={createClass} />}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {classes.map(classItem => (
                <ClassCard 
                  key={classItem.id} 
                  classData={classItem}
                  onEditClass={updateClass}
                  onDeleteClass={deleteClass}
                  currentUser={user}
                />
              ))}
            </div>
          </TabsContent>

          {/* Lessons Tab */}
          <TabsContent value="lessons" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">Lessons</h2>
              {user.role === 'teacher' && (
                <CreateLessonDialog 
                  classes={classes} 
                  onCreateLesson={createLesson} 
                  onUploadFile={uploadFile}
                  uploading={uploading}
                />
              )}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {lessons.map(lesson => (
                <LessonCard 
                  key={lesson.id} 
                  lesson={lesson}
                  files={uploadedFiles.filter(file => file.lesson_id === lesson.id)}
                />
              ))}
            </div>
          </TabsContent>

          {/* Files Tab */}
          <TabsContent value="files" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">File Manager</h2>
              <div className="space-x-2">
                <input
                  type="file"
                  multiple
                  onChange={(e) => {
                    const files = Array.from(e.target.files);
                    files.forEach(file => uploadFile(file));
                  }}
                  className="hidden"
                  id="bulk-upload"
                  accept=".pdf,.doc,.docx,.ppt,.pptx,.jpg,.jpeg,.png,.gif,.txt,.xls,.xlsx"
                />
                <label
                  htmlFor="bulk-upload"
                  className="inline-flex items-center px-4 py-2 bg-gold-600 hover:bg-gold-700 text-black rounded-md cursor-pointer transition-colors"
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Files
                </label>
                <Button 
                  onClick={() => loadFiles()}
                  variant="outline"
                  className="border-midnight-600 text-white hover:bg-midnight-700"
                >
                  Refresh
                </Button>
              </div>
            </div>
            
            {uploading && (
              <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-3">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gold-400"></div>
                    <span className="text-white">Uploading files...</span>
                  </div>
                </CardContent>
              </Card>
            )}
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {uploadedFiles.map(file => (
                <Card key={file.id} className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <File className="h-5 w-5 text-gold-400" />
                          <span className="text-white font-medium truncate">{file.original_filename}</span>
                        </div>
                        <p className="text-sm text-gray-400">
                          Size: {(file.file_size / 1024 / 1024).toFixed(2)} MB
                        </p>
                        <p className="text-sm text-gray-400">
                          Uploaded: {new Date(file.uploaded_at).toLocaleDateString()}
                        </p>
                        {file.lesson_id && (
                          <Badge className="mt-2 bg-gold-600/20 text-gold-400 border-gold-400/30">
                            Lesson Attached
                          </Badge>
                        )}
                      </div>
                      <div className="flex flex-col space-y-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0 text-gold-400 hover:text-gold-300"
                          onClick={() => window.open(`${BACKEND_URL}${file.download_url}`, '_blank')}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0 text-red-400 hover:text-red-300"
                          onClick={() => {
                            if (window.confirm('Are you sure you want to delete this file?')) {
                              deleteFile(file.id);
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            
            {uploadedFiles.length === 0 && !uploading && (
              <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
                <CardContent className="p-8 text-center">
                  <File className="mx-auto h-16 w-16 text-gold-400 mb-4" />
                  <h3 className="text-xl font-semibold text-white mb-2">No Files Yet</h3>
                  <p className="text-gray-400 mb-6">
                    Upload lesson plans, documents, presentations, and other materials for your classes.
                  </p>
                  <label
                    htmlFor="bulk-upload"
                    className="inline-flex items-center px-6 py-3 bg-gold-600 hover:bg-gold-700 text-black rounded-lg cursor-pointer transition-colors"
                  >
                    <Upload className="mr-2 h-5 w-5" />
                    Upload Your First Files
                  </label>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Google Import Tab */}
          <TabsContent value="google" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">Google Import</h2>
              {!googleConnected && (
                <Button onClick={connectGoogle} className="bg-gold-600 hover:bg-gold-700 text-black">
                  <LogIn className="mr-2 h-4 w-4" />
                  Connect Google Account
                </Button>
              )}
            </div>
            
            {googleConnected ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Google Slides */}
                <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center">
                      <Presentation className="mr-2 h-5 w-5 text-gold-400" />
                      Google Slides
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      Import your presentations into lessons
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Button onClick={loadGoogleData} className="mb-4 bg-midnight-700 hover:bg-midnight-600 text-white">
                      Refresh Lists
                    </Button>
                    {googleSlides.map(slide => (
                      <div key={slide.id} className="flex items-center justify-between p-3 rounded-lg bg-black/30 hover:bg-black/50 transition-colors">
                        <div className="flex-1">
                          <h4 className="font-medium text-white">{slide.name}</h4>
                          <p className="text-sm text-gray-400">
                            Modified: {new Date(slide.modifiedTime).toLocaleDateString()}
                          </p>
                        </div>
                        <Button 
                          onClick={() => importSlides(slide.id)}
                          className="bg-gold-600 hover:bg-gold-700 text-black text-sm"
                        >
                          Import
                        </Button>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                {/* Google Docs */}
                <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center">
                      <FileText className="mr-2 h-5 w-5 text-gold-400" />
                      Google Docs
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      Import your documents as lesson plans
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {googleDocs.map(doc => (
                      <div key={doc.id} className="flex items-center justify-between p-3 rounded-lg bg-black/30 hover:bg-black/50 transition-colors">
                        <div className="flex-1">
                          <h4 className="font-medium text-white">{doc.name}</h4>
                          <p className="text-sm text-gray-400">
                            Modified: {new Date(doc.modifiedTime).toLocaleDateString()}
                          </p>
                        </div>
                        <Button 
                          onClick={() => importDocs(doc.id)}
                          className="bg-gold-600 hover:bg-gold-700 text-black text-sm"
                        >
                          Import
                        </Button>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            ) : (
              <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
                <CardContent className="p-8 text-center">
                  <Presentation className="mx-auto h-16 w-16 text-gold-400 mb-4" />
                  <h3 className="text-xl font-semibold text-white mb-2">Google Integration Setup Required</h3>
                  <div className="text-gray-400 mb-6 text-left max-w-2xl mx-auto">
                    <p className="mb-4">
                      To enable Google Slides and Docs import, you need to configure the OAuth redirect URI in your Google Cloud Console:
                    </p>
                    <div className="bg-black/30 p-4 rounded-lg mb-4">
                      <p className="text-gold-400 font-mono text-sm">
                        https://8bec313c-42bc-492f-8514-71511295d06c.preview.emergentagent.com/auth/google/callback
                      </p>
                    </div>
                    <ol className="list-decimal list-inside space-y-2 text-sm">
                      <li>Go to <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer" className="text-gold-400 hover:text-gold-300">Google Cloud Console</a></li>
                      <li>Select your project</li>
                      <li>Go to "APIs & Services" → "Credentials"</li>
                      <li>Edit your OAuth 2.0 Client ID</li>
                      <li>Add the above URI to "Authorized redirect URIs"</li>
                      <li>Save the changes</li>
                    </ol>
                  </div>
                  <Button onClick={connectGoogle} className="bg-gold-600 hover:bg-gold-700 text-black">
                    <LogIn className="mr-2 h-4 w-4" />
                    Try Connect Google Account
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Messages Tab */}
          <TabsContent value="messages" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">Messages</h2>
              <MessageDialog onSendMessage={sendMessage} />
            </div>
            
            <div className="space-y-4">
              {messages.map(message => (
                <MessageCard key={message.id} message={message} currentUser={user} />
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

// Component definitions
const StatsCard = ({ title, value, icon, description }) => (
  <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700 hover:border-gold-400/50 transition-all duration-300">
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium text-gray-300">{title}</CardTitle>
      {icon}
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold text-white">{value}</div>
      <p className="text-xs text-gray-400">{description}</p>
    </CardContent>
  </Card>
);

const RecentLessons = ({ lessons }) => (
  <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
    <CardHeader>
      <CardTitle className="text-white">Recent Lessons</CardTitle>
    </CardHeader>
    <CardContent className="space-y-4">
      {lessons.map(lesson => (
        <div key={lesson.id} className="flex items-center space-x-4 p-3 rounded-lg bg-black/30 hover:bg-black/50 transition-colors">
          <BookOpen className="h-8 w-8 text-gold-400" />
          <div className="flex-1">
            <h4 className="font-medium text-white">{lesson.title}</h4>
            <p className="text-sm text-gray-400">{lesson.description}</p>
          </div>
        </div>
      ))}
    </CardContent>
  </Card>
);

const RecentNotifications = ({ notifications }) => (
  <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
    <CardHeader>
      <CardTitle className="text-white">Recent Notifications</CardTitle>
    </CardHeader>
    <CardContent className="space-y-4">
      {notifications.map(notification => (
        <div key={notification.id} className="flex items-center space-x-4 p-3 rounded-lg bg-black/30 hover:bg-black/50 transition-colors">
          <Bell className="h-6 w-6 text-gold-400" />
          <div className="flex-1">
            <h4 className="font-medium text-white">{notification.title}</h4>
            <p className="text-sm text-gray-400">{notification.message}</p>
          </div>
          {!notification.read && <div className="w-2 h-2 bg-gold-400 rounded-full"></div>}
        </div>
      ))}
    </CardContent>
  </Card>
);

const ClassCard = ({ classData, onEditClass, onDeleteClass, currentUser }) => {
  // Debug logging
  console.log('ClassCard Debug:', {
    currentUser: currentUser,
    classData: classData,
    userRole: currentUser?.role,
    userId: currentUser?.id,
    teacherId: classData?.teacher_id,
    match: currentUser?.id === classData?.teacher_id
  });

  return (
    <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700 hover:border-gold-400/50 transition-all duration-300 hover:scale-105">
      <CardHeader>
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <CardTitle className="text-white">{classData.name}</CardTitle>
            <CardDescription className="text-gray-400">{classData.description}</CardDescription>
          </div>
          {/* Debug: Show the condition result */}
          <div className="text-xs text-gray-500 mb-2">
            Role: {currentUser?.role} | Owner: {currentUser?.id === classData?.teacher_id ? 'Yes' : 'No'}
          </div>
          {currentUser?.role === 'teacher' && currentUser?.id === classData?.teacher_id && (
            <div className="flex space-x-1 ml-2">
              <EditClassDialog classData={classData} onUpdateClass={onEditClass} />
              <Button
                size="sm"
                variant="ghost"
                className="h-8 w-8 p-0 text-red-400 hover:text-red-300"
                onClick={() => {
                  if (window.confirm(`Are you sure you want to delete "${classData.name}"? This will also delete all associated lessons and cannot be undone.`)) {
                    onDeleteClass(classData.id);
                  }
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <Badge className="bg-gold-600/20 text-gold-400 border-gold-400/30">
            {classData.students.length} Students
          </Badge>
          <Users className="h-5 w-5 text-gray-400" />
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Created: {new Date(classData.created_at).toLocaleDateString()}
        </div>
      </CardContent>
    </Card>
  );
};

const LessonCard = ({ lesson, onLoadFiles, files = [] }) => (
  <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700 hover:border-gold-400/50 transition-all duration-300 hover:scale-105">
    <CardHeader>
      <CardTitle className="text-white">{lesson.title}</CardTitle>
      <CardDescription className="text-gray-400">{lesson.description}</CardDescription>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="flex items-center space-x-2">
        {lesson.google_slides_id && <Presentation className="h-4 w-4 text-gold-400" />}
        {lesson.google_docs_id && <FileText className="h-4 w-4 text-gold-400" />}
        {lesson.video_url && <Video className="h-4 w-4 text-gold-400" />}
        {lesson.audio_url && <Mic className="h-4 w-4 text-gold-400" />}
        {lesson.files && lesson.files.length > 0 && (
          <div className="flex items-center space-x-1">
            <File className="h-4 w-4 text-gold-400" />
            <span className="text-xs text-gold-400">{lesson.files.length}</span>
          </div>
        )}
      </div>
      
      {/* Show uploaded files */}
      {files.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-400">Lesson Materials:</p>
          {files.slice(0, 3).map(file => (
            <div key={file.id} className="flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2">
                <File className="h-3 w-3 text-gold-400" />
                <span className="text-gray-300 truncate max-w-32">{file.original_filename}</span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="h-6 w-6 p-0 text-gold-400 hover:text-gold-300"
                onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}${file.download_url}`, '_blank')}
              >
                <Download className="h-3 w-3" />
              </Button>
            </div>
          ))}
          {files.length > 3 && (
            <p className="text-xs text-gray-500">+{files.length - 3} more files</p>
          )}
        </div>
      )}
      
      <Badge className="bg-midnight-700 text-gray-300">
        {new Date(lesson.created_at).toLocaleDateString()}
      </Badge>
    </CardContent>
  </Card>
);

const MessageCard = ({ message, currentUser }) => (
  <Card className={`bg-midnight-800/50 backdrop-blur-lg border-midnight-700 ${
    message.sender_id === currentUser.id ? 'ml-auto max-w-md' : 'mr-auto max-w-md'
  }`}>
    <CardContent className="p-4">
      <div className="flex items-start space-x-3">
        <div className="flex-1">
          <p className="text-white">{message.message}</p>
          <p className="text-xs text-gray-400 mt-2">
            {new Date(message.created_at).toLocaleString()}
          </p>
        </div>
      </div>
    </CardContent>
  </Card>
);

const CreateClassDialog = ({ onCreateClass }) => {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    await onCreateClass({ name, description });
    setName('');
    setDescription('');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-gold-600 hover:bg-gold-700 text-black">
          <PlusCircle className="mr-2 h-4 w-4" />
          Create Class
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-midnight-800 border-midnight-700">
        <DialogHeader>
          <DialogTitle className="text-white">Create New Class</DialogTitle>
          <DialogDescription className="text-gray-400">
            Create a new classroom to organize your lessons and students.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Class Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
            required
          />
          <Textarea
            placeholder="Class Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
          />
          <Button type="submit" className="w-full bg-gold-600 hover:bg-gold-700 text-black">
            Create Class
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

const EditClassDialog = ({ classData, onUpdateClass }) => {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(classData?.name || '');
  const [description, setDescription] = useState(classData?.description || '');

  useEffect(() => {
    if (classData) {
      setName(classData.name);
      setDescription(classData.description);
    }
  }, [classData]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (classData) {
      await onUpdateClass(classData.id, { name, description });
      setOpen(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          size="sm"
          variant="ghost" 
          className="h-8 w-8 p-0 text-gold-400 hover:text-gold-300"
        >
          <Edit className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-midnight-800 border-midnight-700">
        <DialogHeader>
          <DialogTitle className="text-white">Edit Class</DialogTitle>
          <DialogDescription className="text-gray-400">
            Update your class information.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Class Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
            required
          />
          <Textarea
            placeholder="Class Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
          />
          <div className="flex space-x-2">
            <Button type="submit" className="flex-1 bg-gold-600 hover:bg-gold-700 text-black">
              Update Class
            </Button>
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => setOpen(false)}
              className="border-midnight-600 text-white hover:bg-midnight-700"
            >
              Cancel
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

const CreateLessonDialog = ({ classes, onCreateLesson, onUploadFile, uploading }) => {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [classId, setClassId] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files);
    setSelectedFiles(files);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newLesson = await onCreateLesson({ title, description, class_id: classId });
    
    // Upload files if lesson created successfully and files selected
    if (newLesson && selectedFiles.length > 0) {
      for (const file of selectedFiles) {
        await onUploadFile(file, newLesson.id, classId);
      }
    }
    
    setTitle('');
    setDescription('');
    setClassId('');
    setSelectedFiles([]);
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-gold-600 hover:bg-gold-700 text-black">
          <PlusCircle className="mr-2 h-4 w-4" />
          Create Lesson
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-midnight-800 border-midnight-700 max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-white">Create New Lesson</DialogTitle>
          <DialogDescription className="text-gray-400">
            Create a new lesson with files, Google Slides and Docs integration.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Lesson Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
            required
          />
          <Textarea
            placeholder="Lesson Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
          />
          <select
            value={classId}
            onChange={(e) => setClassId(e.target.value)}
            className="w-full p-2 rounded-md bg-midnight-900 border border-midnight-600 text-white"
            required
          >
            <option value="">Select Class</option>
            {classes.map(classItem => (
              <option key={classItem.id} value={classItem.id}>
                {classItem.name}
              </option>
            ))}
          </select>
          
          {/* File Upload Section */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-300">
              Upload Lesson Materials
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                id="lesson-files"
                accept=".pdf,.doc,.docx,.ppt,.pptx,.jpg,.jpeg,.png,.gif,.txt,.xls,.xlsx"
              />
              <label
                htmlFor="lesson-files"
                className="flex items-center px-4 py-2 bg-midnight-700 hover:bg-midnight-600 text-white rounded-md cursor-pointer transition-colors"
              >
                <Upload className="mr-2 h-4 w-4" />
                Choose Files
              </label>
              {selectedFiles.length > 0 && (
                <span className="text-gray-400 text-sm">
                  {selectedFiles.length} file(s) selected
                </span>
              )}
            </div>
            
            {selectedFiles.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm text-gray-400">Selected files:</p>
                {selectedFiles.map((file, index) => (
                  <div key={index} className="flex items-center space-x-2 text-sm text-gray-300">
                    <File className="h-4 w-4 text-gold-400" />
                    <span>{file.name}</span>
                    <span className="text-gray-500">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <Button 
            type="submit" 
            className="w-full bg-gold-600 hover:bg-gold-700 text-black"
            disabled={uploading}
          >
            {uploading ? 'Creating & Uploading...' : 'Create Lesson'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

const MessageDialog = ({ onSendMessage }) => {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [recipientId, setRecipientId] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    await onSendMessage({ message, recipient_id: recipientId });
    setMessage('');
    setRecipientId('');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-gold-600 hover:bg-gold-700 text-black">
          <Send className="mr-2 h-4 w-4" />
          New Message
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-midnight-800 border-midnight-700">
        <DialogHeader>
          <DialogTitle className="text-white">Send Message</DialogTitle>
          <DialogDescription className="text-gray-400">
            Send a message to students or other teachers.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Recipient ID"
            value={recipientId}
            onChange={(e) => setRecipientId(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
            required
          />
          <Textarea
            placeholder="Your message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
            required
          />
          <Button type="submit" className="w-full bg-gold-600 hover:bg-gold-700 text-black">
            Send Message
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default App;