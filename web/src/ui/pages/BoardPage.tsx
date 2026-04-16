import { useEffect } from 'react'
import { useGameStore } from '../../store/gameStore'
import { useLayoutStore } from '../../store/layoutStore'
import { useUIStore } from '../../store/uiStore'
import { useLibraryStore } from '../../store/libraryStore'
import { useTabSync } from '../../sync/useTabSync'
import { useCardHotkeys } from '../hooks/useCardHotkeys'
import type { GameCard, Card } from '../../domain/types'
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

function makeDummyCard(index: number): GameCard {
  const card: Card = {
    id: `dummy-${index}`,
    name: `ダミー ${index + 1}`,
    image_path: '',
    mana: (index % 10) + 1,
    civilizations: ['light'],
    card_type: 'creature',
    count: 1,
  }
  return {
    instanceId: crypto.randomUUID(),
    card,
    tapped: false,
    face_down: false,
    revealed: false,
    row: 0,
    marker: null,
    under_cards: [],
  }
}

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
  useCardHotkeys()

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

    // カードライブラリ未ロード時はダミーデッキで動作確認できるよう初期配置
    if (useLibraryStore.getState().cards.length === 0) {
      const dummy = Array.from({ length: 40 }, (_, i) => makeDummyCard(i))
      useGameStore.setState(s => ({
        zones: {
          ...s.zones,
          deck:   { zoneId: 'deck',   cards: dummy.slice(0, 30) },
          hand:   { zoneId: 'hand',   cards: dummy.slice(30, 35) },
          shield: { zoneId: 'shield', cards: dummy.slice(35, 40).map(c => ({ ...c, face_down: true })) },
        },
      }))
    }
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
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 500,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(0,0,0,0.6)',
        }}>
          <div style={{
            width: '88vw',
            height: '88vh',
            borderRadius: 10,
            overflow: 'hidden',
            boxShadow: '0 0 40px rgba(124,58,237,0.4)',
            border: '1px solid rgba(124,58,237,0.5)',
          }}>
            <DeckPage />
          </div>
        </div>
      )}
    </div>
  )
}
