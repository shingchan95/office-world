import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export interface Tile {
  x: number;
  z: number;
  teamZone: string | null;
}

export interface FurnitureItem {
  id: string;
  type: 'desk' | 'meeting-table' | 'sofa' | 'lectern' | 'laptop' | 'monitor' | 'whiteboard' | 'plant';
  purpose: 'work' | 'meeting' | 'leisure' | 'lecture' | 'prop';
  x: number;
  z: number;
  rotation: number;
  teamZone: string | null;
  capacity?: number;
  assignedAgents?: string[];
}

export interface Zone {
  id: string;
  name: string;
  color: string;
  tiles: [number, number][];
}

export interface Stairs {
  x: number;
  z: number;
  connectsTo: number;
}

export interface FloorPlan {
  floor: number;
  width: number;
  depth: number;
  tiles: Tile[];
  furniture: FurnitureItem[];
  zones: Zone[];
  stairs: Stairs[];
}

export interface Agent {
  id: string;
  name: string;
  profile: string;
  team: string;
  avatarStyle: 'blob' | 'geometric' | 'custom';
  avatarColor: string;
  position: { x: number; z: number; floor: number };
  targetPosition: { x: number; z: number; floor: number } | null;
  state: 'working' | 'meeting' | 'break' | 'moving' | 'idle';
  currentTask: string;
  schedule: ScheduleEntry[];
  deskId?: string;
}

export interface ScheduleEntry {
  time: string; // "09:00-12:00"
  purpose: 'work' | 'meeting' | 'break' | 'leisure';
  zone: string;
  furnitureId?: string;
}

interface FloorPlanState {
  floors: Record<number, FloorPlan>;
  currentFloor: number;
  selectedFurnitureId: string | null;
  setFloor: (floor: number) => void;
  setFloorPlan: (floor: number, plan: FloorPlan) => void;
  updateTile: (floor: number, x: number, z: number, teamZone: string | null) => void;
  addFurniture: (floor: number, furniture: FurnitureItem) => void;
  updateFurniture: (floor: number, id: string, updates: Partial<FurnitureItem>) => void;
  removeFurniture: (floor: number, id: string) => void;
  selectFurniture: (id: string | null) => void;
  addZone: (floor: number, zone: Zone) => void;
  updateZone: (floor: number, id: string, updates: Partial<Zone>) => void;
  removeZone: (floor: number, id: string) => void;
  addStairs: (floor: number, stairs: Stairs) => void;
}

export const useFloorPlanStore = create<FloorPlanState>()(
  immer((set) => ({
    floors: {},
    currentFloor: 0,
    selectedFurnitureId: null,
    
    setFloor: (floor) => set((state) => {
      state.currentFloor = floor;
    }),
    
    setFloorPlan: (floor, plan) => set((state) => {
      state.floors[floor] = plan;
    }),
    
    updateTile: (floor, x, z, teamZone) => set((state) => {
      if (!state.floors[floor]) {
        state.floors[floor] = {
          floor,
          width: 20,
          depth: 20,
          tiles: [],
          furniture: [],
          zones: [],
          stairs: [],
        };
      }
      const tile = state.floors[floor].tiles.find(t => t.x === x && t.z === z);
      if (tile) {
        tile.teamZone = teamZone;
      } else {
        state.floors[floor].tiles.push({ x, z, teamZone });
      }
    }),
    
    addFurniture: (floor, furniture) => set((state) => {
      if (!state.floors[floor]) {
        state.floors[floor] = {
          floor,
          width: 20,
          depth: 20,
          tiles: [],
          furniture: [],
          zones: [],
          stairs: [],
        };
      }
      state.floors[floor].furniture.push(furniture);
    }),
    
    updateFurniture: (floor, id, updates) => set((state) => {
      const plan = state.floors[floor];
      if (!plan) return;
      const idx = plan.furniture.findIndex(f => f.id === id);
      if (idx !== -1) {
        Object.assign(plan.furniture[idx], updates);
      }
    }),
    
    removeFurniture: (floor, id) => set((state) => {
      const plan = state.floors[floor];
      if (!plan) return;
      plan.furniture = plan.furniture.filter(f => f.id !== id);
      if (state.selectedFurnitureId === id) {
        state.selectedFurnitureId = null;
      }
    }),
    
    selectFurniture: (id) => set((state) => {
      state.selectedFurnitureId = id;
    }),
    
    addZone: (floor, zone) => set((state) => {
      if (!state.floors[floor]) {
        state.floors[floor] = {
          floor,
          width: 20,
          depth: 20,
          tiles: [],
          furniture: [],
          zones: [],
          stairs: [],
        };
      }
      state.floors[floor].zones.push(zone);
    }),
    
    updateZone: (floor, id, updates) => set((state) => {
      const plan = state.floors[floor];
      if (!plan) return;
      const idx = plan.zones.findIndex(z => z.id === id);
      if (idx !== -1) {
        Object.assign(plan.zones[idx], updates);
      }
    }),
    
    removeZone: (floor, id) => set((state) => {
      const plan = state.floors[floor];
      if (!plan) return;
      plan.zones = plan.zones.filter(z => z.id !== id);
    }),
    
    addStairs: (floor, stairs) => set((state) => {
      if (!state.floors[floor]) {
        state.floors[floor] = {
          floor,
          width: 20,
          depth: 20,
          tiles: [],
          furniture: [],
          zones: [],
          stairs: [],
        };
      }
      state.floors[floor].stairs.push(stairs);
    }),
  }))
);