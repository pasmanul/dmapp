import { useLibraryStore } from '../../store/libraryStore'
import { useUIStore } from '../../store/uiStore'

export function DeckHud() {
  const {
    deckFiles,
    currentDeck,
    deckName,
    dirHandle,
    loadDeckFile,
    saveDeckFile,
    loadDeck,
    newDeck,
  } = useLibraryStore(s => ({
    deckFiles: s.deckFiles,
    currentDeck: s.currentDeck,
    deckName: s.deckName,
    dirHandle: s.dirHandle,
    loadDeckFile: s.loadDeckFile,
    saveDeckFile: s.saveDeckFile,
    loadDeck: s.loadDeck,
    newDeck: s.newDeck,
  }))
  const openDialog = useUIStore(s => s.openDialog)

  const totalCount = currentDeck.reduce((s, e) => s + e.count, 0)
  const overLimit = totalCount > 40

  const btn: React.CSSProperties = {
    fontFamily: "'Press Start 2P', monospace",
    fontSize: 8,
    padding: '7px 12px',
    borderRadius: 6,
    cursor: 'pointer',
    transition: 'all 150ms',
    whiteSpace: 'nowrap',
  }

  async function handleSave() {
    if (!dirHandle) {
      alert('先にカードライブラリを読み込んでください')
      return
    }
    if (!deckName.trim()) {
      alert('デッキ名を入力してください')
      return
    }
    await saveDeckFile()
  }

  async function handleSelectDeck(filename: string) {
    if (!filename) {
      newDeck()
      return
    }
    await loadDeckFile(filename)
  }

  return (
    <div style={{
      display: 'flex',
      gap: 8,
      padding: '6px 12px',
      background: '#08091a',
      borderBottom: '1px solid rgba(124,58,237,0.2)',
      alignItems: 'center',
      flexShrink: 0,
    }}>
      <span style={{
        fontFamily: "'Press Start 2P', monospace",
        fontSize: 9,
        color: '#00FFFF',
        textShadow: '0 0 12px rgba(0,255,255,0.6)',
        marginRight: 4,
      }}>
        DECK
      </span>

      {/* デッキ選択 */}
      <select
        value={deckName}
        onChange={e => handleSelectDeck(e.target.value)}
        style={{
          background: '#0e1228',
          color: '#A78BFA',
          border: '1px solid rgba(124,58,237,0.5)',
          borderRadius: 4,
          padding: '4px 8px',
          fontFamily: "'Chakra Petch', sans-serif",
          fontSize: 11,
          cursor: 'pointer',
          maxWidth: 160,
        }}
      >
        <option value="">— 新規 —</option>
        {deckFiles.map(f => (
          <option key={f} value={f}>{f}</option>
        ))}
      </select>

      {/* デッキ名入力 */}
      <input
        type="text"
        placeholder="デッキ名"
        value={deckName}
        onChange={e => loadDeck({ cards: currentDeck, name: e.target.value })}
        style={{
          background: '#0e1228',
          color: '#E2E8F0',
          border: '1px solid rgba(124,58,237,0.4)',
          borderRadius: 4,
          padding: '4px 8px',
          fontFamily: "'Chakra Petch', sans-serif",
          fontSize: 12,
          width: 160,
        }}
      />

      {/* 枚数 */}
      <span style={{
        fontFamily: "'Press Start 2P', monospace",
        fontSize: 9,
        color: overLimit ? '#ff4444' : '#94A3B8',
        minWidth: 52,
      }}>
        {totalCount}/40
      </span>

      {/* SAVE */}
      <button
        style={{
          ...btn,
          background: '#0c280c',
          color: '#88dd88',
          border: '1px solid #285028',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = '#103810')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0c280c')}
        onClick={handleSave}
      >
        SAVE
      </button>

      {/* LOAD CARDS */}
      <button
        style={{
          ...btn,
          background: '#0c1828',
          color: '#88aade',
          border: '1px solid #284060',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = '#102238')}
        onMouseLeave={e => (e.currentTarget.style.background = '#0c1828')}
        onClick={() => openDialog('setup')}
      >
        LOAD CARDS
      </button>

      {/* BOARD リンク */}
      <a
        href="/index.html"
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
        ▶ BOARD
      </a>
    </div>
  )
}
