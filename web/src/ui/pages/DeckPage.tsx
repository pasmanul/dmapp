import { useState, useEffect } from 'react'
import { DeckHud } from '../deck/DeckHud'
import { FilterBar, DEFAULT_FILTER, type FilterState } from '../deck/FilterBar'
import { LibraryGrid } from '../deck/LibraryGrid'
import { DeckGrid } from '../deck/DeckGrid'
import { SetupDialog } from '../overlays/SetupDialog'
import { CardEditorDialog } from '../overlays/CardEditorDialog'
import { useLibraryStore } from '../../store/libraryStore'

const CRT_STYLE: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.04) 2px, rgba(0,0,0,0.04) 4px)',
  pointerEvents: 'none',
  zIndex: 9999,
}

export function DeckPage() {
  const [filter, setFilter] = useState<FilterState>(DEFAULT_FILTER)
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null)
  const [cardEditorOpen, setCardEditorOpen] = useState(false)
  const listDeckFiles = useLibraryStore(s => s.listDeckFiles)
  const allCards = useLibraryStore(s => s.cards)

  // カードライブラリが読み込まれたらデッキ一覧を更新
  useEffect(() => {
    listDeckFiles()
  }, [allCards]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      width: '100%',
      background: '#0F0F23',
      overflow: 'hidden',
    }}>
      <div style={CRT_STYLE} />

      <DeckHud />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* 左パネル: カードライブラリ */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          borderRight: '1px solid rgba(124,58,237,0.2)',
          overflow: 'hidden',
        }}>
          <FilterBar cards={allCards} filter={filter} onChange={setFilter} onAddCard={() => setCardEditorOpen(true)} />
          <LibraryGrid filter={filter} />
        </div>

        {/* 右パネル: デッキ内容 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{
            padding: '6px 12px',
            background: '#060810',
            borderBottom: '1px solid rgba(0,255,255,0.1)',
            fontFamily: "'VT323', monospace",
            color: '#00FFFF88',
            fontSize: 14,
            flexShrink: 0,
          }}>
            デッキ内容（ここへドロップ）
          </div>
          <DeckGrid selectedCardId={selectedCardId} onSelect={setSelectedCardId} />
        </div>
      </div>

      <SetupDialog />
      {cardEditorOpen && <CardEditorDialog onClose={() => setCardEditorOpen(false)} />}
    </div>
  )
}
