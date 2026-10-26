import { create } from 'zustand';
import { useFloorPlanStore } from './floorPlanStore';
import { immer } from 'zustand/middleware/immer';

export interface Agent {
  id: string;
  name: string;
  profile: string;
  team: string;
  avatarStyle: 'blob' | 'geometric' | 'custom';
  avatarColor: string;
  avatarSeed: string;
  position: { x: number; z: number; floor: number; y?: number };
  targetPosition: { x: number; z: number; floor: number; y?: number } | null;
  state: 'working' | 'meeting' | 'break' | 'leisure' | 'moving' | 'idle';
  currentTask: string;
  schedule: ScheduleEntry[];
  deskId?: string;
  path: { x: number; z: number }[];
  pathProgress: number;
}

export interface ScheduleEntry {
  id: string;
  timeStart: string; // "09:00"
  timeEnd: string;   // "12:00"
  purpose: 'work' | 'meeting' | 'break' | 'leisure';
  zone: string;
  furnitureId?: string;
}

interface AgentState {
  agents: Agent[];
  time: string; // "09:00"
  timeScale: number; // 1 = real-time, 60 = 1 min/sec
  isPlaying: boolean;
  addAgent: (agent: Agent) => void;
  updateAgent: (id: string, updates: Partial<Agent>) => void;
  removeAgent: (id: string) => void;
  setAgentTarget: (id: string, target: { x: number; z: number; floor: number } | null) => void;
  setAgentPath: (id: string, path: { x: number; z: number }[]) => void;
  updateAgentProgress: (id: string, progress: number) => void;
  setTime: (time: string) => void;
  setTimeScale: (scale: number) => void;
  setPlaying: (playing: boolean) => void;
  toggleTimePlaying: () => void;
  tick: (deltaTime: number) => void;
  evaluateSchedules: () => void;
}

const TEAM_COLORS: Record<string, string> = {
  research: '#00d4aa',
  engineering: '#5a9fff',
  design: '#c084fc',
  ops: '#ffb86b',
};

function generateBlobColor(team: string): string {
  return TEAM_COLORS[team] || '#72e0b2';
}

function generateAgentPath(start: { x: number; z: number }, end: { x: number; z: number }): { x: number; z: number }[] {
  // Simple grid pathfinding (Manhattan)
  const path: { x: number; z: number }[] = [];
  let cx = start.x;
  let cz = start.z;
  const steps = Math.max(Math.abs(end.x - start.x), Math.abs(end.z - start.z)) * 2;
  
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    path.push({
      x: start.x + (end.x - start.x) * t,
      z: start.z + (end.z - start.z) * t,
    });
  }
  return path;
}

export const useAgentStore = create<AgentState>()(
  immer((set, get) => ({
    agents: [
      {
        id: 'alice',
        name: 'Alice',
        profile: 'researcher',
        team: 'research',
        avatarStyle: 'blob',
        avatarColor: '#00d4aa',
        avatarSeed: 'alice',
        position: { x: 2, y: 0, z: 2, floor: 0 },
        targetPosition: null,
        state: 'working',
        currentTask: 'Research paper review',
        schedule: [
          { id: '1', timeStart: '09:00', timeEnd: '12:00', purpose: 'work', zone: 'research', furnitureId: 'desk-1' },
          { id: '2', timeStart: '12:00', timeEnd: '13:00', purpose: 'break', zone: 'leisure', furnitureId: 'sofa-1' },
          { id: '3', timeStart: '13:00', timeEnd: '17:00', purpose: 'work', zone: 'research', furnitureId: 'desk-1' },
        ],
        deskId: 'desk-1',
        path: [],
        pathProgress: 0,
      },
      {
        id: 'bob',
        name: 'Bob',
        profile: 'engineer',
        team: 'engineering',
        avatarStyle: 'blob',
        avatarColor: '#5a9fff',
        avatarSeed: 'bob',
        position: { x: 2, y: 0, z: 4, floor: 0 },
        targetPosition: null,
        state: 'working',
        currentTask: 'API implementation',
        schedule: [
          { id: '1', timeStart: '10:00', timeEnd: '12:00', purpose: 'work', zone: 'engineering', furnitureId: 'desk-2' },
          { id: '2', timeStart: '12:00', timeEnd: '13:00', purpose: 'break', zone: 'leisure', furnitureId: 'sofa-1' },
          { id: '3', timeStart: '13:00', timeEnd: '18:00', purpose: 'work', zone: 'engineering', furnitureId: 'desk-2' },
        ],
        deskId: 'desk-2',
        path: [],
        pathProgress: 0,
      },
      {
        id: 'carol',
        name: 'Carol',
        profile: 'designer',
        team: 'design',
        avatarStyle: 'blob',
        avatarColor: '#c084fc',
        avatarSeed: 'carol',
        position: { x: 5, y: 0, z: 5, floor: 0 },
        targetPosition: null,
        state: 'meeting',
        currentTask: 'Sprint planning',
        schedule: [
          { id: '1', timeStart: '09:00', timeEnd: '11:00', purpose: 'work', zone: 'design', furnitureId: 'desk-3' },
          { id: '2', timeStart: '11:00', timeEnd: '12:00', purpose: 'meeting', zone: 'meeting', furnitureId: 'meeting-table-1' },
          { id: '3', timeStart: '12:00', timeEnd: '13:00', purpose: 'break', zone: 'leisure', furnitureId: 'sofa-1' },
          { id: '4', timeStart: '13:00', timeEnd: '17:00', purpose: 'work', zone: 'design', furnitureId: 'desk-3' },
        ],
        deskId: 'desk-3',
        path: [],
        pathProgress: 0,
      },
      {
        id: 'dave',
        name: 'Dave',
        profile: 'engineer',
        team: 'ops',
        avatarStyle: 'blob',
        avatarColor: '#ffb86b',
        avatarSeed: 'dave',
        position: { x: 6, y: 0, z: 5, floor: 0 },
        targetPosition: null,
        state: 'meeting',
        currentTask: 'Sprint planning',
        schedule: [
          { id: '1', timeStart: '10:00', timeEnd: '11:00', purpose: 'work', zone: 'ops', furnitureId: 'desk-4' },
          { id: '2', timeStart: '11:00', timeEnd: '12:00', purpose: 'meeting', zone: 'meeting', furnitureId: 'meeting-table-1' },
          { id: '3', timeStart: '12:00', timeEnd: '13:00', purpose: 'break', zone: 'leisure', furnitureId: 'sofa-1' },
        ],
        deskId: 'desk-4',
        path: [],
        pathProgress: 0,
      },
    ],
    time: '09:00',
    timeScale: 60,
    isPlaying: true,
    
    addAgent: (agent) => set((state) => {
      state.agents.push(agent);
    }),
    
    updateAgent: (id, updates) => set((state) => {
      const idx = state.agents.findIndex(a => a.id === id);
      if (idx !== -1) {
        Object.assign(state.agents[idx], updates);
      }
    }),
    
    removeAgent: (id) => set((state) => {
      state.agents = state.agents.filter(a => a.id !== id);
    }),
    
    setAgentTarget: (id, target) => set((state) => {
      const agent = state.agents.find(a => a.id === id);
      if (agent) {
        agent.targetPosition = target;
        if (target) {
          agent.path = generateAgentPath(agent.position, target);
          agent.pathProgress = 0;
          agent.state = 'moving';
        }
      }
    }),
    
    setAgentPath: (id, path) => set((state) => {
      const agent = state.agents.find(a => a.id === id);
      if (agent) {
        agent.path = path;
        agent.pathProgress = 0;
      }
    }),
    
    updateAgentProgress: (id, progress) => set((state) => {
      const agent = state.agents.find(a => a.id === id);
      if (agent && agent.path.length > 0) {
        agent.pathProgress = Math.min(1, progress);
        const pathIndex = Math.floor(agent.pathProgress * (agent.path.length - 1));
        const nextPoint = agent.path[Math.min(pathIndex + 1, agent.path.length - 1)];
        agent.position = { ...agent.position, ...nextPoint };
        
        if (agent.pathProgress >= 1) {
          agent.path = [];
          agent.pathProgress = 0;
          agent.targetPosition = null;
          // Restore previous state based on schedule
          agent.state = 'working';
        }
      }
    }),
    
    setTime: (time) => set((state) => {
      state.time = time;
    }),
    
    setTimeScale: (scale) => set((state) => {
      state.timeScale = scale;
    }),
    
    setPlaying: (playing) => set((state) => {
      state.isPlaying = playing;
    }),
    
    toggleTimePlaying: () => set((state) => {
      state.isPlaying = !state.isPlaying;
    }),
    
    tick: (deltaTime: number) => set((state) => {
      if (!state.isPlaying) return;
      
      // Update time
      const [hours, minutes] = state.time.split(':').map(Number);
      const totalMinutes = hours * 60 + minutes + deltaTime * state.timeScale;
      const newHours = Math.floor(totalMinutes / 60) % 24;
      const newMinutes = Math.floor(totalMinutes % 60);
      state.time = `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}`;
      
      // Move agents along paths
      state.agents.forEach(agent => {
        if (agent.path.length > 0 && agent.targetPosition) {
          const speed = 0.02 * state.timeScale; // tiles per tick
          agent.pathProgress = Math.min(1, agent.pathProgress + speed);
          const pathIndex = Math.floor(agent.pathProgress * (agent.path.length - 1));
          const nextPoint = agent.path[Math.min(pathIndex + 1, agent.path.length - 1)];
          agent.position = { ...agent.position, ...nextPoint };
          
          if (agent.pathProgress >= 1) {
            agent.path = [];
            agent.pathProgress = 0;
            agent.targetPosition = null;
            agent.state = 'working';
          }
        }
      });
      
      // Evaluate schedules every minute
      if (Math.floor(totalMinutes) !== Math.floor(totalMinutes - deltaTime * state.timeScale)) {
        get().evaluateSchedules();
      }
    }),
    
    evaluateSchedules: () => set((state) => {
      const [hours, minutes] = state.time.split(':').map(Number);
      const currentMinutes = hours * 60 + minutes;
      
      state.agents.forEach(agent => {
        const currentSchedule = agent.schedule.find(s => {
          const start = parseTime(s.timeStart);
          const end = parseTime(s.timeEnd);
          return currentMinutes >= start && currentMinutes < end;
        });
        
        if (currentSchedule) {
          agent.currentTask = getTaskName(currentSchedule.purpose);
          
          // If agent should be at furniture but isn't there
          if (currentSchedule.furnitureId && agent.targetPosition === null) {
            // In real app: look up furniture position from floor plan store
            // For now, set a target based on purpose
            const target = getFurnitureTarget(currentSchedule.furnitureId, agent.deskId);
            if (target && (agent.position.x !== target.x || agent.position.z !== target.z)) {
              agent.targetPosition = { ...target, floor: agent.position.floor };
              agent.path = generateAgentPath(agent.position, agent.targetPosition);
              agent.pathProgress = 0;
              agent.state = 'moving';
            }
          }
          
          // Update state based on purpose
          switch (currentSchedule.purpose) {
            case 'work':
              agent.state = 'working';
              break;
            case 'meeting':
              agent.state = 'meeting';
              break;
            case 'break':
            case 'leisure':
              agent.state = 'break';
              break;
          }
        }
      });
    }),
  }))
);

function parseTime(time: string): number {
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
}

function getTaskName(purpose: string): string {
  switch (purpose) {
    case 'work': return 'Working at desk';
    case 'meeting': return 'In meeting';
    case 'break': return 'On break';
    case 'leisure': return 'Leisure time';
    default: return 'Idle';
  }
}

function getFurnitureTarget(furnitureId: string, deskId?: string): { x: number; z: number } | null {
  // Use the same draft furniture coordinates that FloorPlan renders.
  const targets: Record<string, { x: number; z: number }> = {
    ...Object.fromEntries((useFloorPlanStore.getState().floors[0]?.furniture || []).map(item => [item.id, { x: item.x, z: item.z }])),
  };
  return targets[furnitureId] || (deskId ? targets[deskId] : null);
}