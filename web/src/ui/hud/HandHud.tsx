import { useGameStore } from '../../store/gameStore'
import { useUIStore } from '../../store/uiStore'
import { useLibraryStore } from '../../store/libraryStore'
import { newGameCard } from '../../domain/gameLogic'
import type { GameCard } from '../../domain/types'

export function HandHud() {
  const { initializeField, undo, zones } = useGameStore(s => ({
    initializeField: s.initializeField,
    undo: s.undo,
    zones: s.zones,
  }))
  const { openDialog, addLog } = useUIStore(s => ({
    openDialog: s.openDialog,
    addLog: s.addLog,
  }))
  const { cards, currentDeck, deckName } = useLibraryStore(s => ({
    cards: s.cards,
    currentDeck: s.currentDeck,
    deckName: s.deckName,
  }))

  function flattenCards(gcs: GameCard[]): GameCard[] {
    return gcs.flatMap(gc => [gc, ...flattenCards(gc.under_cards)])
  }

  function handleInit() {
    let deckCards: GameCard[]

    if (cards.length === 0) {
      // ライブラリ未ロード（ダミーモード）: 全ゾーンのカードを集めて使う
      deckCards = Object.values(zones).flatMap(zone => flattenCards(zone.cards))
    } else {
      const cardMap = new Map(cards.map(c => [c.id, c]))
      deckCards = currentDeck.flatMap(entry => {
        const card = cardMap.get(entry.cardId)
        if (!card) return []
        return Array.from({ length: entry.count }, () => newGameCard(card))
      })
    }

    if (deckCards.length === 0) {
      addLog('デッキが空です')
      return
    }
    initializeField(deckCards)
    addLog(`フィールド初期化 — ${deckCards.length}枚`)
  }

  const btn: React.CSSProperties = {
    fontFamily: "'Press Start 2P', monospace",
    fontSize: 8,
    padding: '7px 12px',
    borderRadius: 6,
    cursor: 'pointer',
    transition: 'all 150ms',
  }

  return (
    <div style={{
      display: 'flex',
      gap: 8,
      padding: '6px 12px',
      background: '#08091a',
      borderBottom: '1px solid rgba(32,168,176,0.2)',
      alignItems: 'center',
      flexWrap: 'wrap',
    }}>
      <span style={{
        fontFamily: "'VT323', monospace",
        fontSize: 16,
        color: '#55ddee',
        textShadow: '0 0 10px rgba(0,255,255,0.4)',
        marginRight: 4,
      }}>
        手札 {deckName && `— ${deckName}`}
      </span>

      <button
        style={{ ...btn, background: 'linear-gradient(135deg, #7C3AED, #5B21B6)', color: '#fff', border: 'none' }}
        onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
        onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
        onClick={handleInit}
      >
        INIT FIELD
      </button>

      <button
        style={{ ...btn, background: '#1a0c0c', color: '#eea0a0', border: '1px solid #803030' }}
        onMouseEnter={e => (e.currentTarget.style.background = '#280e0e')}
        onMouseLeave={e => (e.currentTarget.style.background = '#1a0c0c')}
        onClick={undo}
      >
        UNDO
      </button>

      <button
        style={{ ...btn, background: '#0c1828', color: '#88aade', border: '1px solid #284060', marginLeft: 'auto' }}
        onMouseEnter={e => (e.currentTarget.style.background = '#102238')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0c1828')}
        onClick={() => openDialog('setup')}
      >
        LOAD CARDS
      </button>
    </div>
  )
}
