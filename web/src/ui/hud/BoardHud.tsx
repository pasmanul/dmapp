import { useGameStore } from '../../store/gameStore'
import { useUIStore } from '../../store/uiStore'

export function BoardHud() {
  const undo = useGameStore(s => s.undo)
  const { openDialog, addLog } = useUIStore(s => ({
    openDialog: s.openDialog,
    addLog: s.addLog,
  }))

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
        style={{ ...btn, background: '#0e1440', color: '#a0b8ff', border: '1px solid #283880' }}
        onMouseEnter={e => (e.currentTarget.style.background = '#141c60')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0e1440')}
        onClick={() => {
          const n = Math.floor(Math.random() * 6) + 1
          addLog(`ダイス: ${n}`)
        }}
      >
        DICE
      </button>

      <button
        style={{ ...btn, background: '#1a0c0c', color: '#eea0a0', border: '1px solid #803030' }}
        onMouseEnter={e => (e.currentTarget.style.background = '#280e0e')}
        onMouseLeave={e => (e.currentTarget.style.background = '#1a0c0c')}
        onClick={undo}
      >
        UNDO
      </button>

      <a
        href="/deck.html"
        style={{
          ...btn,
          background: '#0c0c28',
          color: '#aa88dd',
          border: '1px solid #404080',
          textDecoration: 'none',
          display: 'inline-block',
          marginLeft: 'auto',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = '#141444')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0c0c28')}
      >
        DECK
      </a>

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
