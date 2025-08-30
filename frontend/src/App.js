import React, { useEffect, useState } from "react";
import "./App.css";
import Auth from "./components/Auth";
import ProfileDropdown from "./components/ProfileDropdown";
import InstructorDashboard from "./pages/InstructorDashboard";
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

function App() {
  const [me, setMe] = useState(null);
  const [currentPage, setCurrentPage] = useState("dashboard");
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
    setCurrentPage("dashboard");
  };

  const renderCurrentPage = () => {
    if (!me) return <Auth onAuthed={setMe} />;

    switch (currentPage) {
      case "dashboard":
        if (me.role === "admin") return <AdminDashboard />;
        if (me.role === "instructor") return <InstructorDashboard me={me} />;
        if (me.role === "student") return <StudentDashboard me={me} />;
        if (me.role === "auditor") return <AuditorDashboard />;
        if (me.role === "parent") return <ParentPortal />;
        return <StudentDashboard me={me} />;

      case "wellbeing":
        return <WellbeingDashboard />;

      case "marketplace":
        return <Marketplace />;

      case "assessment":
        return <AssessmentCenter />;

      case "gamification":
        return <GamificationHub />;

      case "parent":
        return <ParentPortal />;

      case "notifications":
        return <NotificationsPage />;

      case "settings":
        return <SettingsPage me={me} onProfileUpdate={setMe} />;

      default:
        return <StudentDashboard me={me} />;
    }
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

  return (
    <div className="App">
      {me && (
        <nav className="main-navigation">
          <div className="nav-container">
            <div className="nav-brand">
              <h1 className="logo">AI LMS</h1>
            </div>

            <div className="nav-items">
              {getNavigationItems().map(item => (
                <button
                  key={item.id}
                  className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
                  onClick={() => setCurrentPage(item.id)}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                </button>
              ))}
            </div>

            <div className="nav-user">
              <ProfileDropdown user={me} onLogout={logout} onNavigate={setCurrentPage} />
            </div>
          </div>
        </nav>
      )}

      <main className="main-content">
        {renderCurrentPage()}
      </main>

      <NotificationSystem />
      <footer className="foot">
        Backend via REACT_APP_BACKEND_URL • All API routes under /api
      </footer>
    </div>
  );
}

export default App;