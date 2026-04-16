import { create } from 'zustand'
import type { GameCard, ActionLogEntry } from '../domain/types'

export type DialogType = 'setup' | 'search' | 'dice' | 'save-load' | null

interface ContextMenuState {
  x: number
  y: number
  zoneId: string
  cardInstanceId: string
  card: GameCard
}

interface StackInfo {
  gc: GameCard
  zoneId: string
}

interface DeckDropInfo {
  fromZoneId: string
  instanceId: string
}

interface HoveredCardInfo {
  instanceId: string
  zoneId: string
  cardName: string
}

interface UIStore {
  selectedCardIds: Set<string>
  zoomCard: GameCard | null
  zoomPos: { x: number; y: number } | null
  contextMenu: ContextMenuState | null
  activeDialog: DialogType
  stackInfo: StackInfo | null
  deckDropInfo: DeckDropInfo | null
  actionLog: ActionLogEntry[]
  deckPanelOpen: boolean
  hoveredCard: HoveredCardInfo | null

  selectCard: (instanceId: string, multi: boolean) => void
  clearSelection: () => void
  setZoom: (card: GameCard | null, pos?: { x: number; y: number }) => void
  openContextMenu: (state: ContextMenuState) => void
  closeContextMenu: () => void
  openDialog: (name: DialogType) => void
  closeDialog: () => void
  openStackDialog: (gc: GameCard, zoneId: string) => void
  closeStackDialog: () => void
  setDeckDropInfo: (info: DeckDropInfo | null) => void
  addLog: (message: string) => void
  openDeckPanel: () => void
  closeDeckPanel: () => void
  setHoveredCard: (info: HoveredCardInfo | null) => void
}

export const useUIStore = create<UIStore>((set) => ({
  selectedCardIds: new Set(),
  zoomCard: null,
  zoomPos: null,
  contextMenu: null,
  activeDialog: null,
  stackInfo: null,
  deckDropInfo: null,
  actionLog: [],
  deckPanelOpen: false,
  hoveredCard: null,

  selectCard: (instanceId, multi) =>
    set((s) => {
      const next = multi ? new Set(s.selectedCardIds) : new Set<string>()
      if (next.has(instanceId)) {
        next.delete(instanceId)
      } else {
        next.add(instanceId)
      }
      return { selectedCardIds: next }
    }),

  clearSelection: () => set({ selectedCardIds: new Set() }),

  setZoom: (card, pos) => set({ zoomCard: card, zoomPos: pos ?? null }),

  openContextMenu: (state) => set({ contextMenu: state }),

  closeContextMenu: () => set({ contextMenu: null }),

  openDialog: (name) => set({ activeDialog: name }),

  closeDialog: () => set({ activeDialog: null }),

  openStackDialog: (gc, zoneId) => set({ stackInfo: { gc, zoneId } }),
  closeStackDialog: () => set({ stackInfo: null }),

  setDeckDropInfo: (info) => set({ deckDropInfo: info }),

  openDeckPanel: () => set({ deckPanelOpen: true }),
  closeDeckPanel: () => set({ deckPanelOpen: false }),

  setHoveredCard: (info) => set({ hoveredCard: info }),

  addLog: (message) =>
    set((s) => ({
      actionLog: [
        { id: crypto.randomUUID(), message, timestamp: Date.now() },
        ...s.actionLog,
      ].slice(0, 200),
    })),
}))
