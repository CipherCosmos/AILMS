import React, { useState, useEffect } from 'react';

const NotificationSystem = () => {
  const [notifications, setNotifications] = useState([]);

  const addNotification = (message, type = 'info', duration = 5000) => {
    const id = Date.now();
    const notification = {
      id,
      message,
      type,
      duration
    };

    setNotifications(prev => [...prev, notification]);

    // Auto-remove notification after duration
    if (duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, duration);
    }

    return id;
  };

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  // Global notification function
  useEffect(() => {
    window.showNotification = addNotification;
  }, []);

  const getNotificationStyle = (type) => {
    const baseStyle = {
      padding: '1rem 1.5rem',
      marginBottom: '0.5rem',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '500',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      animation: 'slideIn 0.3s ease-out'
    };

    switch (type) {
      case 'success':
        return { ...baseStyle, backgroundColor: '#28a745' };
      case 'error':
        return { ...baseStyle, backgroundColor: '#dc3545' };
      case 'warning':
        return { ...baseStyle, backgroundColor: '#ffc107', color: '#212529' };
      default:
        return { ...baseStyle, backgroundColor: '#007bff' };
    }
  };

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: '20px',
      zIndex: 1000,
      maxWidth: '400px'
    }}>
      {notifications.map(notification => (
        <div
          key={notification.id}
          style={getNotificationStyle(notification.type)}
        >
          <span>{notification.message}</span>
          <button
            onClick={() => removeNotification(notification.id)}
            style={{
              background: 'none',
              border: 'none',
              color: 'white',
              fontSize: '1.2rem',
              cursor: 'pointer',
              padding: '0',
              marginLeft: '1rem'
            }}
          >
            ×
          </button>
        </div>
      ))}

      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes slideIn {
            from {
              transform: translateX(100%);
              opacity: 0;
            }
            to {
              transform: translateX(0);
              opacity: 1;
            }
          }
        `
      }} />
    </div>
  );
};

// Export a function to show notifications from anywhere
export const showNotification = (message, type = 'info', duration = 5000) => {
  if (window.showNotification) {
    window.showNotification(message, type, duration);
  } else {
    // Fallback to alert if component isn't mounted
    alert(message);
  }
};

export default NotificationSystem;