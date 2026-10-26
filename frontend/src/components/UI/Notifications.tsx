import { useUIStore } from '../../store/uiStore';

export function Notifications() {
  const notifications = useUIStore((s) => s.notifications);
  const removeNotification = useUIStore((s) => s.removeNotification);

  if (notifications.length === 0) return null;

  const icons = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '❌',
  };

  return (
    <div style={{
      position: 'fixed',
      top: 16,
      right: 16,
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      zIndex: 1000,
    }}>
      {notifications.map((notification) => (
        <div
          key={notification.id}
          style={{
            padding: '10px 14px',
            background: 'rgba(0,0,0,0.85)',
            border: `1px solid ${notification.type === 'error' ? '#ff6b6b' : notification.type === 'warning' ? '#ffb86b' : '#00d4aa'}`,
            borderRadius: 6,
            fontSize: 12,
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            minWidth: 200,
            boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
          }}
        >
          <span>{icons[notification.type]}</span>
          <span>{notification.message}</span>
          <button
            onClick={() => removeNotification(notification.id)}
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: 'none',
              color: '#666',
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}

export default Notifications;