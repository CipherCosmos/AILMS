import { useEffect, useRef } from 'react';

class WebSocketManager {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 3000;
  }

  connect(userId) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    // Clear any existing connection
    if (this.ws) {
      this.ws.close();
    }

    // Try different WebSocket URLs for better compatibility
    const wsUrls = [
      `ws://localhost:8000/ws/${userId}`,
      `ws://127.0.0.1:8000/ws/${userId}`
    ];

    const tryConnect = (urlIndex = 0) => {
      if (urlIndex >= wsUrls.length) {
        console.error('Failed to connect to any WebSocket URL');
        this.notifyListeners('connection', { status: 'failed', userId });
        this.attemptReconnect(userId);
        return;
      }

      const wsUrl = wsUrls[urlIndex];
      console.log(`Attempting WebSocket connection to: ${wsUrl}`);

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected successfully to:', wsUrl);
        this.reconnectAttempts = 0;
        this.notifyListeners('connection', { status: 'connected', userId });

        // Send initial subscription message
        this.sendMessage({
          type: 'subscribe',
          userId: userId,
          timestamp: new Date().toISOString()
        });
      };

      this.ws.onmessage = (event) => {
        console.log('WebSocket message received:', event.data);
        try {
          const data = JSON.parse(event.data);
          this.notifyListeners(data.type || 'message', data);
        } catch (error) {
          // Handle connection messages and other non-JSON messages gracefully
          if (event.data?.startsWith('Connected to LMS WebSocket')) {
            // This is a connection confirmation message
            this.notifyListeners('connection', {
              status: 'connected',
              message: event.data,
              timestamp: new Date().toISOString()
            });
          } else {
            console.warn('Unexpected non-JSON message (first 100 chars):', event.data?.substring(0, 100));
            // Handle other non-JSON messages gracefully
            this.notifyListeners('raw_message', {
              type: 'raw_message',
              data: event.data,
              timestamp: new Date().toISOString()
            });
          }
        }
      };

      this.ws.onclose = (event) => {
        console.log(`WebSocket disconnected (code: ${event.code}, reason: ${event.reason})`);
        this.notifyListeners('connection', { status: 'disconnected', userId, code: event.code, reason: event.reason });

        // Only attempt reconnection if it wasn't a clean close
        if (event.code !== 1000) {
          this.attemptReconnect(userId);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        // Try next URL if current one fails
        if (urlIndex < wsUrls.length - 1) {
          console.log('Trying next WebSocket URL...');
          setTimeout(() => tryConnect(urlIndex + 1), 1000);
        } else {
          this.notifyListeners('connection', { status: 'error', userId, error });
          this.attemptReconnect(userId);
        }
      };
    };

    tryConnect();
  }

  sendMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
      console.log('Sending WebSocket message:', messageStr);
      this.ws.send(messageStr);
      return true;
    } else {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  addListener(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType).push(callback);
  }

  removeListener(eventType, callback) {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  notifyListeners(eventType, data) {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      listeners.forEach(callback => callback(data));
    }
  }

  attemptReconnect(userId) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        this.connect(userId);
      }, this.reconnectInterval);
    }
  }
}

// Singleton instance
const wsManager = new WebSocketManager();

// React hook for using WebSocket
export const useWebSocket = (userId) => {
  const managerRef = useRef(wsManager);

  useEffect(() => {
    if (userId) {
      managerRef.current.connect(userId);
    }

    return () => {
      // Don't disconnect on unmount, let it persist
    };
  }, [userId]);

  const addListener = (eventType, callback) => {
    managerRef.current.addListener(eventType, callback);
  };

  const removeListener = (eventType, callback) => {
    managerRef.current.removeListener(eventType, callback);
  };

  const send = (message) => {
    managerRef.current.send(message);
  };

  return { addListener, removeListener, send };
};

export default wsManager;