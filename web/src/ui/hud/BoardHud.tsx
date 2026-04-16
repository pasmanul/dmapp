import { useGameStore } from '../../store/gameStore'
import { useUIStore } from '../../store/uiStore'
import { useLibraryStore } from '../../store/libraryStore'
import { newGameCard } from '../../domain/gameLogic'
import type { GameCard } from '../../domain/types'

export function BoardHud() {
  const { undo, initializeField, zones } = useGameStore(s => ({
    undo: s.undo,
    initializeField: s.initializeField,
    zones: s.zones,
  }))
  const { openDialog, openDeckPanel, addLog } = useUIStore(s => ({
    openDialog: s.openDialog,
    openDeckPanel: s.openDeckPanel,
    addLog: s.addLog,
  }))
  const { cards, currentDeck } = useLibraryStore(s => ({
    cards: s.cards,
    currentDeck: s.currentDeck,
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
    whiteSpace: 'nowrap' as const,
  }

  return (
    <div style={{
      display: 'flex',
      gap: 8,
      padding: '6px 12px',
      background: '#08091a',
      borderBottom: '1px solid rgba(124,58,237,0.2)',
      alignItems: 'center',
    }}>
      <span style={{
        fontFamily: "'Press Start 2P', monospace",
        fontSize: 10,
        color: '#00FFFF',
        textShadow: '0 0 12px rgba(0,255,255,0.6)',
        marginRight: 8,
      }}>
        TCG SIM
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
        style={{ ...btn, background: '#0e1440', color: '#a0b8ff', border: '1px solid #283880' }}
        onMouseEnter={e => (e.currentTarget.style.background = '#141c60')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0e1440')}
        onClick={() => openDialog('dice')}
      >
        DICE
      </button>

      <button
        style={{ ...btn, background: '#0c1820', color: '#88c4aa', border: '1px solid #204040' }}
        onMouseEnter={e => (e.currentTarget.style.background = '#0f2030')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0c1820')}
        onClick={() => openDialog('save-load')}
      >
        SAVE/LOAD
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
        style={{ ...btn, background: '#0c1c14', color: '#66ddaa', border: '1px solid #225040', marginLeft: 'auto' }}
        onMouseEnter={e => (e.currentTarget.style.background = '#102618')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0c1c14')}
        onClick={() => window.open('/hand.html', 'hand', 'width=540,height=720')}
      >
        HAND
      </button>

      <button
        style={{ ...btn, background: '#0c0c28', color: '#aa88dd', border: '1px solid #404080' }}
        onMouseEnter={e => (e.currentTarget.style.background = '#141444')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0c0c28')}
        onClick={openDeckPanel}
      >
        DECK
      </button>

      <button
        style={{ ...btn, background: '#0c1828', color: '#88aade', border: '1px solid #284060' }}
        onMouseEnter={e => (e.currentTarget.style.background = '#102238')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0c1828')}
        onClick={() => openDialog('setup')}
      >
        LOAD CARDS
      </button>
    </div>
  )
}
