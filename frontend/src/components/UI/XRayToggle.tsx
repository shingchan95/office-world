import { useUIStore } from '../../store/uiStore';

export function XRayToggle() {
  const xray = useUIStore((s) => s.xrayMode);
  const toggle = useUIStore((s) => s.toggleXray);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      background: 'rgba(0,0,0,0.5)',
      padding: '6px 12px',
      borderRadius: 8,
      border: '1px solid #333',
    }}>
      <span style={{ color: '#88aaff', fontSize: 14 }}>👁</span>
      <label style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        cursor: 'pointer',
        fontSize: 12,
        color: xray ? '#00d4aa' : '#aaa',
      }}>
        <input
          type="checkbox"
          checked={xray}
          onChange={toggle}
          style={{ width: 14, height: 14, cursor: 'pointer' }}
        />
        X-Ray
      </label>
    </div>
  );
}

export default XRayToggle;