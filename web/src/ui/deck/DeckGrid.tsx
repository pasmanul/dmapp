import { useState } from 'react'
import { useLibraryStore } from '../../store/libraryStore'

function useToast() {
  const [msg, setMsg] = useState<string | null>(null)
  function show(text: string) {
    setMsg(text)
    setTimeout(() => setMsg(null), 2500)
  }
  return { msg, show }
}

interface Props {
  selectedCardId: string | null
  onSelect: (cardId: string | null) => void
}

export function DeckGrid({ selectedCardId, onSelect }: Props) {
  const { currentDeck, cards, resolveImageUrl, cardBackUrl, loadDeck } = useLibraryStore(s => ({
    currentDeck: s.currentDeck,
    cards: s.cards,
    resolveImageUrl: s.resolveImageUrl,
    cardBackUrl: s.cardBackUrl,
    loadDeck: s.loadDeck,
  }))
  const deckName = useLibraryStore(s => s.deckName)
  const { msg: toastMsg, show: showToast } = useToast()
  const [isDragOver, setIsDragOver] = useState(false)

  const cardMap = new Map(cards.map(c => [c.id, c]))
  const totalCount = currentDeck.reduce((s, e) => s + e.count, 0)

  function addCard(cardId: string) {
    const existing = currentDeck.find(e => e.cardId === cardId)
    if (existing && existing.count >= 4) {
      showToast('同じカードは4枚まで')
      return
    }
    if (totalCount >= 40) {
      showToast('デッキは40枚まで')
      return
    }
    const next = existing
      ? currentDeck.map(e => e.cardId === cardId ? { ...e, count: e.count + 1 } : e)
      : [...currentDeck, { cardId, count: 1 }]
    loadDeck({ cards: next, name: deckName })
  }

  function decCard(cardId: string) {
    const entry = currentDeck.find(e => e.cardId === cardId)
    if (!entry) return
    const next = entry.count > 1
      ? currentDeck.map(e => e.cardId === cardId ? { ...e, count: e.count - 1 } : e)
      : currentDeck.filter(e => e.cardId !== cardId)
    if (entry.count === 1) onSelect(null)
    loadDeck({ cards: next, name: deckName })
  }

  function removeCard(cardId: string) {
    const next = currentDeck.filter(e => e.cardId !== cardId)
    onSelect(null)
    loadDeck({ cards: next, name: deckName })
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(false)
    const raw = e.dataTransfer.getData('text/plain')
    if (!raw) return
    try {
      const parsed = JSON.parse(raw)
      if (parsed.cardId) addCard(parsed.cardId)
    } catch {
      // ignore
    }
  }

  const actionBtn: React.CSSProperties = {
    fontFamily: "'Press Start 2P', monospace",
    fontSize: 8,
    padding: '6px 12px',
    borderRadius: 5,
    transition: 'all 150ms',
    flex: 1,
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* ドロップ領域 */}
      <div
        onDragOver={e => { e.preventDefault(); setIsDragOver(true) }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 8,
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, 80px)',
          gap: 8,
          alignContent: 'start',
          background: isDragOver ? 'rgba(0,255,255,0.04)' : 'transparent',
          border: isDragOver ? '2px dashed rgba(0,255,255,0.4)' : '2px dashed transparent',
          borderRadius: 8,
          transition: 'all 150ms',
          minHeight: 120,
        }}
      >
        {currentDeck.length === 0 && !isDragOver && (
          <div style={{
            gridColumn: '1 / -1',
            color: '#2a3550',
            fontFamily: "'Chakra Petch', sans-serif",
            fontSize: 12,
            padding: 24,
            textAlign: 'center',
          }}>
            ← 左からカードをドロップ
          </div>
        )}
        {currentDeck.map(entry => {
          const card = cardMap.get(entry.cardId)
          if (!card) return null
          const imgUrl = resolveImageUrl(card.image_path) || cardBackUrl
          const isSelected = entry.cardId === selectedCardId
          return (
            <div
              key={entry.cardId}
              onClick={() => onSelect(isSelected ? null : entry.cardId)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 3,
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              <div style={{
                position: 'relative',
                width: 72,
                aspectRatio: '150/210',
                borderRadius: 4,
                overflow: 'visible',
                border: isSelected ? '2px solid #00FFFF' : '1px solid rgba(0,255,255,0.2)',
                background: '#0d1020',
                flexShrink: 0,
                boxShadow: isSelected ? '0 0 8px rgba(0,255,255,0.5)' : 'none',
              }}>
                <div style={{ width: '100%', height: '100%', overflow: 'hidden', borderRadius: 3 }}>
                  {imgUrl ? (
                    <img src={imgUrl} alt={card.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  ) : (
                    <div style={{ width: '100%', height: '100%', background: '#1a1a2e' }} />
                  )}
                </div>
                <div style={{
                  position: 'absolute',
                  bottom: -6,
                  right: -6,
                  background: '#0a0e1a',
                  border: '1px solid rgba(0,255,255,0.4)',
                  color: '#ffdd66',
                  fontSize: 9,
                  fontFamily: "'Press Start 2P', monospace",
                  padding: '1px 4px',
                  borderRadius: 3,
                  lineHeight: 1.4,
                }}>
                  ×{entry.count}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* +1 / -1 / 削除 */}
      <div style={{
        display: 'flex',
        gap: 6,
        padding: '8px',
        borderTop: '1px solid rgba(124,58,237,0.15)',
        flexShrink: 0,
      }}>
        {([
          { action: 'inc', label: '+1', bg: '#0c280c', fg: '#88dd88', border: '#285028' },
          { action: 'dec', label: '-1', bg: '#1a1020', fg: '#ddaa88', border: '#503828' },
          { action: 'del', label: '削除', bg: '#200c0c', fg: '#dd8888', border: '#502828' },
        ] as const).map(({ action, label, bg, fg, border }) => (
          <button
            key={action}
            disabled={!selectedCardId}
            onClick={() => {
              if (!selectedCardId) return
              if (action === 'inc') addCard(selectedCardId)
              else if (action === 'dec') decCard(selectedCardId)
              else removeCard(selectedCardId)
            }}
            style={{
              ...actionBtn,
              cursor: selectedCardId ? 'pointer' : 'not-allowed',
              background: selectedCardId ? bg : '#111',
              color: selectedCardId ? fg : '#333',
              border: `1px solid ${selectedCardId ? border : '#222'}`,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* トースト */}
      {toastMsg && (
        <div style={{
          position: 'fixed',
          bottom: 24,
          left: '50%',
          transform: 'translateX(-50%)',
          background: '#1a0a0a',
          border: '1px solid #cc3333',
          color: '#ff8888',
          padding: '8px 20px',
          borderRadius: 8,
          fontFamily: "'Chakra Petch', sans-serif",
          fontSize: 13,
          zIndex: 9000,
          pointerEvents: 'none',
          boxShadow: '0 0 20px rgba(255,0,0,0.2)',
        }}>
          {toastMsg}
        </div>
      )}
    </div>
  )
}
