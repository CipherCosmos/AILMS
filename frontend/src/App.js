import React, { useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate, useParams } from "react-router-dom";
import "./App.css";
import Auth from "./components/Auth";
import ProfileDropdown from "./components/ProfileDropdown";
import InstructorDashboard from "./pages/InstructorDashboard";
import CourseEditor from "./pages/CourseEditor";
import CourseAnalytics from "./pages/CourseAnalytics";
import CourseReviews from "./pages/CourseReviews";
import StudentDashboard from "./pages/StudentDashboard";
import AuditorDashboard from "./pages/AuditorDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import WellbeingDashboard from "./pages/WellbeingDashboard";
import Marketplace from "./pages/Marketplace";
import AssessmentCenter from "./pages/AssessmentCenter";
import GamificationHub from "./pages/GamificationHub";
import ParentPortal from "./pages/ParentPortal";
import NotificationsPage from "./pages/NotificationsPage";
import SettingsPage from "./pages/SettingsPage";
import { useWebSocket } from "./components/WebSocketManager";
import NotificationSystem from "./components/NotificationSystem";

function AppContent() {
  const [me, setMe] = useState(null);
  const navigate = useNavigate();
  const { addListener } = useWebSocket(me?.id);

  useEffect(()=>{
    const cached = localStorage.getItem("me");
    if (cached) setMe(JSON.parse(cached));
  },[]);

  // Set up WebSocket listeners for real-time notifications
  useEffect(() => {
    if (me?.id) {
      addListener('notification', (data) => {
        // Handle real-time notifications
        console.log('Real-time notification:', data);

        // Show user-friendly notifications
        if (data.type === 'notification') {
          if (data.notification_type === 'assignment_due') {
            window.showNotification(`📚 Assignment due: ${data.data.title}`, 'warning');
          } else if (data.notification_type === 'course_completed') {
            window.showNotification(`🎉 Congratulations! You completed: ${data.data.course_title}`, 'success');
          } else if (data.notification_type === 'new_announcement') {
            window.showNotification(`📢 New announcement: ${data.data.title}`, 'info');
          } else if (data.notification_type === 'grade_received') {
            window.showNotification(`📊 New grade received for: ${data.data.assignment_title}`, 'info');
          }
        } else if (data.type === 'connected') {
          console.log('WebSocket connected:', data.message);
          window.showNotification('🔗 Connected to real-time updates', 'success', 3000);
        } else if (data.type === 'subscribed') {
          console.log('WebSocket subscribed for user:', data.user_id);
        } else if (data.type === 'echo') {
          console.log('WebSocket echo:', data.message);
        }
      });

      // Add connection status listener
      addListener('connection', (data) => {
        if (data.status === 'connected') {
          console.log('Real-time connection established');
        } else if (data.status === 'disconnected') {
          console.warn('Real-time connection lost - some features may be limited');
        }
      });
    }
  }, [me?.id, addListener]);

  const logout = () => {
    localStorage.clear();
    setMe(null);
    navigate("/");
  };

  const getNavigationItems = () => {
    if (!me) return [];

    const commonItems = [
      { id: "dashboard", label: "Dashboard", icon: "📊" },
      { id: "notifications", label: "Notifications", icon: "🔔" },
      { id: "wellbeing", label: "Well-being", icon: "🧘‍♀️" },
      { id: "marketplace", label: "Marketplace", icon: "🛒" },
      { id: "gamification", label: "Gamification", icon: "🎮" },
      { id: "settings", label: "Settings", icon: "⚙️" }
    ];

    const roleSpecificItems = {
      admin: [
        { id: "assessment", label: "Assessment", icon: "📝" }
      ],
      instructor: [
        { id: "assessment", label: "Assessment", icon: "📝" }
      ],
      student: [
        { id: "assessment", label: "Assessment", icon: "📝" }
      ],
      auditor: [
        { id: "assessment", label: "Assessment", icon: "📝" }
      ],
      parent: [
        { id: "parent", label: "Parent Portal", icon: "👨‍👩‍👧‍👦" }
      ]
    };

    return [...commonItems, ...(roleSpecificItems[me.role] || [])];
  };

  if (!me) {
    return <Auth onAuthed={setMe} />;
  }

  return (
    <div className="App">
      <nav className="main-navigation">
        <div className="nav-container">
          <div className="nav-brand">
            <h1 className="logo">AI LMS</h1>
          </div>

          <div className="nav-items">
            {getNavigationItems().map(item => (
              <button
                key={item.id}
                className="nav-item"
                onClick={() => navigate(`/${item.id}`)}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </button>
            ))}
          </div>

          <div className="nav-user">
            <ProfileDropdown user={me} onLogout={logout} onNavigate={(page) => navigate(`/${page}`)} />
          </div>
        </div>
      </nav>

      <main className="main-content">
        <Routes>
          <Route path="/" element={
            me.role === "admin" ? <AdminDashboard /> :
            me.role === "instructor" ? <InstructorDashboard me={me} /> :
            me.role === "student" ? <StudentDashboard me={me} /> :
            me.role === "auditor" ? <AuditorDashboard /> :
            me.role === "parent" ? <ParentPortal /> :
            <StudentDashboard me={me} />
          } />
          <Route path="/dashboard" element={
            me.role === "admin" ? <AdminDashboard /> :
            me.role === "instructor" ? <InstructorDashboard me={me} /> :
            me.role === "student" ? <StudentDashboard me={me} /> :
            me.role === "auditor" ? <AuditorDashboard /> :
            me.role === "parent" ? <ParentPortal /> :
            <StudentDashboard me={me} />
          } />
          <Route path="/instructor" element={<InstructorDashboard me={me} />} />
          <Route path="/instructor/course/:courseId/edit" element={<CourseEditor me={me} />} />
          <Route path="/instructor/course/:courseId/analytics" element={<CourseAnalytics me={me} />} />
          <Route path="/instructor/course/:courseId/reviews" element={<CourseReviews me={me} />} />
          <Route path="/wellbeing" element={<WellbeingDashboard />} />
          <Route path="/marketplace" element={<Marketplace />} />
          <Route path="/assessment" element={<AssessmentCenter />} />
          <Route path="/gamification" element={<GamificationHub />} />
          <Route path="/parent" element={<ParentPortal />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/settings" element={<SettingsPage me={me} onProfileUpdate={setMe} />} />
        </Routes>
      </main>

      <NotificationSystem />
      <footer className="foot">
        Backend via REACT_APP_BACKEND_URL • All API routes under /api
      </footer>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;