import { useUIStore } from '../../store/uiStore';

export function CameraControls() {
  const cameraView = useUIStore((s) => s.cameraView);
  const setCameraView = useUIStore((s) => s.setCameraView);

  const views: Array<{ id: typeof cameraView; label: string; icon: string }> = [
    { id: 'perspective', label: 'Perspective', icon: '📐' },
    { id: 'isometric', label: 'Isometric', icon: '🔺' },
    { id: 'top', label: 'Top Down', icon: '⬇️' },
    { id: 'section', label: 'Section', icon: '✂️' },
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
      {views.map((view) => (
        <button
          key={view.id}
          onClick={() => setCameraView(view.id)}
          title={view.label}
          style={{
            padding: '6px 10px',
            background: cameraView === view.id ? '#00d4aa' : 'rgba(255,255,255,0.1)',
            color: cameraView === view.id ? '#000' : '#aaa',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 12,
            transition: 'all 0.2s',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <span>{view.icon}</span>
          <span>{view.label}</span>
        </button>
      ))}
    </div>
  );
}

export default CameraControls;