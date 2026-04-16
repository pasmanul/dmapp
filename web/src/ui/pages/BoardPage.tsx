import { useEffect } from 'react'
import { useGameStore } from '../../store/gameStore'
import { useLayoutStore } from '../../store/layoutStore'
import { useUIStore } from '../../store/uiStore'
import { useTabSync } from '../../sync/useTabSync'
import { BoardStage } from '../stage/BoardStage'
import { BoardHud } from '../hud/BoardHud'
import { ActionLog } from '../overlays/ActionLog'
import { ContextMenu } from '../overlays/ContextMenu'
import { SetupDialog } from '../overlays/SetupDialog'
import { SearchDialog } from '../overlays/SearchDialog'
import { DiceDialog } from '../overlays/DiceDialog'
import { StackDialog } from '../overlays/StackDialog'
import { SaveLoadDialog } from '../overlays/SaveLoadDialog'
import { DeckDropDialog } from '../overlays/DeckDropDialog'
import { DeckPage } from './DeckPage'

// CRT scanline overlay style
const CRT_STYLE: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.04) 2px, rgba(0,0,0,0.04) 4px)',
  pointerEvents: 'none',
  zIndex: 9999,
}

export function BoardPage() {
  useTabSync('board')

  const initZones = useGameStore(s => s.initZones)
  const zones = useLayoutStore(s => s.zones)
  const deckPanelOpen = useUIStore(s => s.deckPanelOpen)

  useEffect(() => {
    const realZoneIds = zones
      .filter(z => z.window_id === 'board' && !z.source_zone_id && !z.ui_widget)
      .map(z => z.id)
    // Also include zones from hand window that need state
    const handZoneIds = zones
      .filter(z => !z.source_zone_id && !z.ui_widget)
      .map(z => z.id)
    initZones([...new Set([...realZoneIds, ...handZoneIds])])
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      width: '100vw',
      background: '#0F0F23',
      overflow: 'hidden',
    }}>
      {/* CRT overlay */}
      <div style={CRT_STYLE} />

      {/* HUD bar */}
      <BoardHud />

      {/* Main content: stage + action log */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <BoardStage />

        {/* Action log sidebar */}
        <div style={{ width: 200, flexShrink: 0, borderLeft: '1px solid rgba(124,58,237,0.2)' }}>
          <ActionLog />
        </div>
      </div>

      {/* Overlays */}
      <ContextMenu />
      <SetupDialog />
      <SearchDialog />
      <DiceDialog />
      <StackDialog />
      <SaveLoadDialog />
      <DeckDropDialog />

      {/* デッキビルダーパネル */}
      {deckPanelOpen && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 500 }}>
          <DeckPage />
        </div>
      )}
    </div>
  )
}
