import React, { useEffect, useState } from "react";
import api from "../services/api";

function NotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all"); // all, unread, read

  useEffect(() => {
    loadNotifications();
  }, []);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const response = await api.get("/notifications");
      setNotifications(response.data);
    } catch (error) {
      console.error("Error loading notifications:", error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await api.post(`/notifications/${notificationId}/read`);
      setNotifications(prev =>
        prev.map(n =>
          n.id === notificationId ? { ...n, read: true } : n
        )
      );
    } catch (error) {
      console.error("Error marking notification as read:", error);
    }
  };

  const deleteNotification = async (notificationId) => {
    if (!confirm("Delete this notification?")) return;

    try {
      await api.delete(`/notifications/${notificationId}`);
      setNotifications(prev => prev.filter(n => n.id !== notificationId));
    } catch (error) {
      console.error("Error deleting notification:", error);
    }
  };

  const markAllAsRead = async () => {
    try {
      const unreadNotifications = notifications.filter(n => !n.read);
      await Promise.all(
        unreadNotifications.map(n => api.post(`/notifications/${n.id}/read`))
      );
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch (error) {
      console.error("Error marking all as read:", error);
    }
  };

  const filteredNotifications = notifications.filter(notification => {
    if (filter === "unread") return !notification.read;
    if (filter === "read") return notification.read;
    return true;
  });

  const unreadCount = notifications.filter(n => !n.read).length;

  if (loading) {
    return (
      <div className="notifications-page">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading notifications...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="notifications-page">
      <div className="notifications-header">
        <div className="header-content">
          <h1>Notifications</h1>
          <p>Stay updated with your learning activities</p>
        </div>
        <div className="header-actions">
          {unreadCount > 0 && (
            <button className="btn secondary" onClick={markAllAsRead}>
              Mark All as Read ({unreadCount})
            </button>
          )}
        </div>
      </div>

      <div className="notifications-controls">
        <div className="filter-tabs">
          <button
            className={filter === "all" ? "active" : ""}
            onClick={() => setFilter("all")}
          >
            All ({notifications.length})
          </button>
          <button
            className={filter === "unread" ? "active" : ""}
            onClick={() => setFilter("unread")}
          >
            Unread ({unreadCount})
          </button>
          <button
            className={filter === "read" ? "active" : ""}
            onClick={() => setFilter("read")}
          >
            Read ({notifications.filter(n => n.read).length})
          </button>
        </div>
      </div>

      <div className="notifications-content">
        {filteredNotifications.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🔔</div>
            <h3>No notifications</h3>
            <p>
              {filter === "unread"
                ? "You've read all your notifications!"
                : filter === "read"
                ? "No read notifications yet"
                : "You're all caught up!"}
            </p>
          </div>
        ) : (
          <div className="notifications-list">
            {filteredNotifications.map(notification => (
              <div
                key={notification.id}
                className={`notification-item ${notification.read ? 'read' : 'unread'}`}
              >
                <div className="notification-icon">
                  {notification.type === "assignment" && "📝"}
                  {notification.type === "quiz" && "🧠"}
                  {notification.type === "course" && "📚"}
                  {notification.type === "system" && "⚙️"}
                  {!["assignment", "quiz", "course", "system"].includes(notification.type) && "📢"}
                </div>

                <div className="notification-content">
                  <div className="notification-header">
                    <h4 className="notification-title">{notification.title}</h4>
                    <span className="notification-time">
                      {new Date(notification.created_at).toLocaleDateString()} at{" "}
                      {new Date(notification.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="notification-message">{notification.message}</p>
                </div>

                <div className="notification-actions">
                  {!notification.read && (
                    <button
                      className="btn small"
                      onClick={() => markAsRead(notification.id)}
                    >
                      Mark as Read
                    </button>
                  )}
                  <button
                    className="btn small danger"
                    onClick={() => deleteNotification(notification.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .notifications-page {
          min-height: 100vh;
          background: #f8f9fa;
          padding: 2rem;
        }

        .notifications-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 2rem;
          border-radius: 12px;
          margin-bottom: 2rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .header-content h1 {
          margin: 0 0 0.5rem 0;
          font-size: 2rem;
        }

        .header-content p {
          margin: 0;
          opacity: 0.9;
        }

        .notifications-controls {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          margin-bottom: 2rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .filter-tabs {
          display: flex;
          gap: 1rem;
        }

        .filter-tabs button {
          padding: 0.75rem 1.5rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          border-radius: 6px;
          transition: all 0.3s;
        }

        .filter-tabs button.active {
          background: #667eea;
          color: white;
        }

        .filter-tabs button:hover {
          background: #f8f9fa;
        }

        .notifications-content {
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          overflow: hidden;
        }

        .notifications-list {
          max-height: 70vh;
          overflow-y: auto;
        }

        .notification-item {
          display: flex;
          align-items: flex-start;
          padding: 1.5rem;
          border-bottom: 1px solid #eee;
          transition: background-color 0.3s;
        }

        .notification-item:hover {
          background: #f8f9fa;
        }

        .notification-item.unread {
          background: #f0f8ff;
          border-left: 4px solid #667eea;
        }

        .notification-icon {
          font-size: 1.5rem;
          margin-right: 1rem;
          margin-top: 0.25rem;
        }

        .notification-content {
          flex: 1;
        }

        .notification-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 0.5rem;
        }

        .notification-title {
          margin: 0;
          color: #2c3e50;
          font-size: 1.1rem;
        }

        .notification-time {
          color: #6c757d;
          font-size: 0.9rem;
          white-space: nowrap;
          margin-left: 1rem;
        }

        .notification-message {
          margin: 0;
          color: #6c757d;
          line-height: 1.5;
        }

        .notification-actions {
          display: flex;
          gap: 0.5rem;
          margin-left: 1rem;
        }

        .empty-state {
          text-align: center;
          padding: 4rem 2rem;
          color: #6c757d;
        }

        .empty-icon {
          font-size: 4rem;
          margin-bottom: 1rem;
          opacity: 0.5;
        }

        .empty-state h3 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .empty-state p {
          margin: 0;
        }

        .loading-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 4rem;
          color: #6c757d;
        }

        .spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #f3f3f3;
          border-top: 4px solid #667eea;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 1rem;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .btn {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s;
        }

        .btn.secondary {
          background: #6c757d;
          color: white;
        }

        .btn.secondary:hover {
          background: #5a6268;
        }

        .btn.small {
          padding: 0.375rem 0.75rem;
          font-size: 0.875rem;
        }

        .btn.danger {
          background: #dc3545;
          color: white;
        }

        .btn.danger:hover {
          background: #c82333;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
          .notifications-page {
            padding: 1rem;
          }

          .notifications-header {
            flex-direction: column;
            text-align: center;
            gap: 1rem;
          }

          .filter-tabs {
            flex-direction: column;
          }

          .filter-tabs button {
            text-align: center;
          }

          .notification-item {
            flex-direction: column;
            gap: 1rem;
          }

          .notification-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }

          .notification-time {
            margin-left: 0;
          }

          .notification-actions {
            margin-left: 0;
            justify-content: center;
          }
        }

        @media (max-width: 480px) {
          .notifications-header {
            padding: 1.5rem;
          }

          .header-content h1 {
            font-size: 1.5rem;
          }

          .notifications-controls {
            padding: 1rem;
          }

          .notification-item {
            padding: 1rem;
          }

          .notification-icon {
            font-size: 1.25rem;
          }

          .notification-title {
            font-size: 1rem;
          }
        }
      `}</style>
    </div>
  );
}

export default NotificationsPage;