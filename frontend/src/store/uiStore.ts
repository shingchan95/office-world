import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export type CameraView = 'perspective' | 'isometric' | 'top' | 'section';
export type ArchitecturalStyle = 'modern' | 'brutalist' | 'warm' | 'cyber';
export type AgentAvatarStyle = 'blob' | 'geometric' | 'custom';

export interface UIState {
  // View
  cameraView: CameraView;
  setCameraView: (view: CameraView) => void;
  
  // Style
  architecturalStyle: ArchitecturalStyle;
  setArchitecturalStyle: (style: ArchitecturalStyle) => void;
  
  // Display options
  xrayMode: boolean;
  toggleXray: () => void;
  wireframeMode: boolean;
  toggleWireframe: () => void;
  showGrid: boolean;
  toggleGrid: () => void;
  showZones: boolean;
  toggleZones: () => void;
  
  // Sidebar
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  activeSidebarTab: 'design' | 'agents' | 'schedule' | 'teams' | 'settings';
  setActiveSidebarTab: (tab: UIState['activeSidebarTab']) => void;
  
  // Agent avatars
  agentAvatarStyle: AgentAvatarStyle;
  setAgentAvatarStyle: (style: AgentAvatarStyle) => void;
  
  // Time
  timeScale: number;
  setTimeScale: (scale: number) => void;
  isTimePlaying: boolean;
  toggleTimePlaying: () => void;
  
  // Notifications
  notifications: { id: string; message: string; type: 'info' | 'success' | 'warning' | 'error' }[];
  addNotification: (message: string, type: UIState['notifications'][0]['type']) => void;
  removeNotification: (id: string) => void;
}

export const useUIStore = create<UIState>()(
  immer((set) => ({
    cameraView: 'isometric',
    setCameraView: (view) => set((state) => { state.cameraView = view; }),
    
    architecturalStyle: 'modern',
    setArchitecturalStyle: (style) => set((state) => { state.architecturalStyle = style; }),
    
    xrayMode: false,
    toggleXray: () => set((state) => { state.xrayMode = !state.xrayMode; }),
    
    wireframeMode: false,
    toggleWireframe: () => set((state) => { state.wireframeMode = !state.wireframeMode; }),
    
    showGrid: true,
    toggleGrid: () => set((state) => { state.showGrid = !state.showGrid; }),
    
    showZones: true,
    toggleZones: () => set((state) => { state.showZones = !state.showZones; }),
    
    sidebarOpen: false,
    toggleSidebar: () => set((state) => { state.sidebarOpen = !state.sidebarOpen; }),
    
    activeSidebarTab: 'design',
    setActiveSidebarTab: (tab) => set((state) => { state.activeSidebarTab = tab; }),
    
    agentAvatarStyle: 'blob',
    setAgentAvatarStyle: (style) => set((state) => { state.agentAvatarStyle = style; }),
    
    timeScale: 60,
    setTimeScale: (scale) => set((state) => { state.timeScale = Math.max(1, Math.min(3600, scale)); }),
    
    isTimePlaying: true,
    toggleTimePlaying: () => set((state) => { state.isTimePlaying = !state.isTimePlaying; }),
    
    notifications: [],
    addNotification: (message, type) => set((state) => {
      state.notifications.push({
        id: Date.now().toString(),
        message,
        type,
      });
      // Keep only last 5
      if (state.notifications.length > 5) {
        state.notifications.shift();
      }
    }),
    removeNotification: (id) => set((state) => {
      state.notifications = state.notifications.filter(n => n.id !== id);
    }),
  }))
);