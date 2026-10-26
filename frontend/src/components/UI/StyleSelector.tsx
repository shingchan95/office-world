import { useUIStore } from '../../store/uiStore';

export function StyleSelector() {
  const style = useUIStore((s) => s.architecturalStyle);
  const setStyle = useUIStore((s) => s.setArchitecturalStyle);

  const styles: Array<{ id: typeof style; label: string; icon: string }> = [
    { id: 'modern', label: 'Modern', icon: '🪞' },
    { id: 'brutalist', label: 'Brutalist', icon: ' 🧱' },
    { id: 'warm', label: 'Warm Wood', icon: '🪵' },
    { id: 'cyber', label: 'Cyberpunk', icon: '🌃' },
  ];

  return (
    <div style={{
      display: 'flex',
      gap: 4,
      background: 'rgba(0,0,0,0.5)',
      padding: '6px 10px',
      borderRadius: 8,
      border: '1px solid #333',
    }}>
      {styles.map((s) => (
        <button
          key={s.id}
          onClick={() => setStyle(s.id)}
          title={s.label}
          style={{
            padding: '6px 12px',
            background: style === s.id ? '#00d4aa' : 'rgba(255,255,255,0.1)',
            color: style === s.id ? '#000' : '#aaa',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <span>{s.icon}</span>
          <span>{s.label}</span>
        </button>
      ))}
    </div>
  );
}

export default StyleSelector;