import { useMemo } from 'react';
import type { ArchitecturalStyle } from '../store/uiStore';

export interface ThemeTokens {
  bg: string;
  panel: string;
  line: string;
  muted: string;
  text: string;
  accent: string;
  accentDim: string;
  accentGlow: string;
  structure: string;
  structureLight: string;
  core: string;
  coreLight: string;
  floor: string;
  floorAlt: string;
  glass: string;
  glassOpacity: number;
  mullion: string;
  mullionLight: string;
  lobby: string;
  lobbyGlow: string;
  roof: string;
  roofDeck: string;
  ground: string;
  sky: string;
  fog: string;
  sun: string;
  fill: string;
  accentLight: string;
}

const themes: Record<ArchitecturalStyle, ThemeTokens> = {
  modern: {
    bg: '#0a0f14',
    panel: '#111920',
    line: '#1e2d36',
    muted: '#8b9ca8',
    text: '#e8eef3',
    accent: '#00d4aa',
    accentDim: '#00b894',
    accentGlow: 'rgba(0,212,170,0.4)',
    structure: '#1a2228',
    structureLight: '#243038',
    core: '#1e2a2a',
    coreLight: '#2a3a3a',
    floor: '#1a2a2a',
    floorAlt: '#223535',
    glass: '#00d4aa',
    glassOpacity: 0.06,
    mullion: '#2a3a44',
    mullionLight: '#3a4a54',
    lobby: '#00d4aa',
    lobbyGlow: 'rgba(0,212,170,0.5)',
    roof: '#0f141a',
    roofDeck: '#1a242a',
    ground: '#0f181f',
    sky: '#080f14',
    fog: '#060b10',
    sun: '#ffffee',
    fill: '#88aaff',
    accentLight: '#4affcc',
  },
  brutalist: {
    bg: '#141414',
    panel: '#1e1e1e',
    line: '#3a3a3a',
    muted: '#999',
    text: '#e8e8e8',
    accent: '#ff6b35',
    accentDim: '#e85a2a',
    accentGlow: 'rgba(255,107,53,0.3)',
    structure: '#2a2a2a',
    structureLight: '#3a3a3a',
    core: '#222222',
    coreLight: '#2a2a2a',
    floor: '#2a2a2a',
    floorAlt: '#333333',
    glass: '#3a3a3a',
    glassOpacity: 0.25,
    mullion: '#222222',
    mullionLight: '#333333',
    lobby: '#ff6b35',
    lobbyGlow: 'rgba(255,107,53,0.4)',
    roof: '#1a1a1a',
    roofDeck: '#222222',
    ground: '#1c1c1c',
    sky: '#141414',
    fog: '#0d0d0d',
    sun: '#ffccaa',
    fill: '#ffaa88',
    accentLight: '#ff9966',
  },
  warm: {
    bg: '#0f0d0a',
    panel: '#1a1610',
    line: '#3d3228',
    muted: '#b8a898',
    text: '#f0e8dd',
    accent: '#d4a550',
    accentDim: '#c49540',
    accentGlow: 'rgba(212,165,80,0.35)',
    structure: '#3d2814',
    structureLight: '#4d341a',
    core: '#2a2014',
    coreLight: '#352818',
    floor: '#2a2218',
    floorAlt: '#352a1e',
    glass: '#d4a550',
    glassOpacity: 0.08,
    mullion: '#2d1f10',
    mullionLight: '#3d2814',
    lobby: '#d4a550',
    lobbyGlow: 'rgba(212,165,80,0.5)',
    roof: '#12100a',
    roofDeck: '#1a1610',
    ground: '#16120c',
    sky: '#0f0d0a',
    fog: '#0c0a08',
    sun: '#ffe8cc',
    fill: '#ffddaa',
    accentLight: '#e8c58a',
  },
  cyber: {
    bg: '#010204',
    panel: '#040810',
    line: '#0a1a2a',
    muted: '#5a8a9a',
    text: '#e0f0ff',
    accent: '#00ffff',
    accentDim: '#00cccc',
    accentGlow: 'rgba(0,255,255,0.5)',
    structure: '#0a141e',
    structureLight: '#0e1e2e',
    core: '#122424',
    coreLight: '#1a2e2e',
    floor: '#102020',
    floorAlt: '#182828',
    glass: '#00ffff',
    glassOpacity: 0.04,
    mullion: '#003344',
    mullionLight: '#005577',
    lobby: '#00ffff',
    lobbyGlow: 'rgba(0,255,255,0.6)',
    roof: '#020408',
    roofDeck: '#040812',
    ground: '#03060a',
    sky: '#010204',
    fog: '#000102',
    sun: '#ffffaa',
    fill: '#00ffff',
    accentLight: '#80ffff',
  },
};

export function useTheme(style: ArchitecturalStyle): ThemeTokens {
  return useMemo(() => themes[style], [style]);
}

export function useCSSVariables(style: ArchitecturalStyle): React.CSSProperties {
  const theme = useTheme(style);
  return useMemo(() => ({
    '--bg': theme.bg,
    '--panel': theme.panel,
    '--line': theme.line,
    '--muted': theme.muted,
    '--text': theme.text,
    '--accent': theme.accent,
    '--accent-dim': theme.accentDim,
    '--accent-glow': theme.accentGlow,
    '--structure': theme.structure,
    '--structure-light': theme.structureLight,
    '--core': theme.core,
    '--core-light': theme.coreLight,
    '--floor': theme.floor,
    '--floor-alt': theme.floorAlt,
    '--glass': theme.glass,
    '--glass-opacity': theme.glassOpacity.toString(),
    '--mullion': theme.mullion,
    '--mullion-light': theme.mullionLight,
    '--lobby': theme.lobby,
    '--lobby-glow': theme.lobbyGlow,
    '--roof': theme.roof,
    '--roof-deck': theme.roofDeck,
    '--ground': theme.ground,
    '--sky': theme.sky,
    '--fog': theme.fog,
    '--sun': theme.sun,
    '--fill': theme.fill,
    '--accent-light': theme.accentLight,
  } as React.CSSProperties), [style]);
}