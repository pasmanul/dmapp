import { useLibraryStore } from '../../store/libraryStore'
import { applyFilters, type FilterState } from './FilterBar'
import type { Card } from '../../domain/types'

const CIV_COLOR: Record<string, string> = {
  '光': '#ffe44d',
  '水': '#44aaff',
  '闇': '#aa44ff',
  '火': '#ff4444',
  '自然': '#44cc44',
  '無色': '#888888',
}

function LibraryCardTile({ card }: { card: Card }) {
  const { resolveImageUrl, cardBackUrl } = useLibraryStore(s => ({
    resolveImageUrl: s.resolveImageUrl,
    cardBackUrl: s.cardBackUrl,
  }))
  const imgUrl = resolveImageUrl(card.image_path) || cardBackUrl

  function onDragStart(e: React.DragEvent) {
    e.dataTransfer.setData('text/plain', JSON.stringify({ cardId: card.id }))
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div
      draggable
      onDragStart={onDragStart}
      title={card.name}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 3,
        cursor: 'grab',
        userSelect: 'none',
      }}
    >
      <div style={{
        width: 72,
        aspectRatio: '150/210',
        borderRadius: 4,
        overflow: 'hidden',
        border: '1px solid rgba(124,58,237,0.3)',
        background: '#0d1020',
        flexShrink: 0,
      }}>
        {imgUrl ? (
          <img src={imgUrl} alt={card.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        ) : (
          <div style={{ width: '100%', height: '100%', background: '#1a1a2e' }} />
        )}
      </div>

      <div style={{
        fontFamily: "'Chakra Petch', sans-serif",
        fontSize: 8,
        color: '#94A3B8',
        textAlign: 'center',
        width: 72,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        lineHeight: 1.2,
      }}>
        {card.name}
      </div>

      <div style={{ display: 'flex', gap: 3, alignItems: 'center' }}>
        <span style={{ fontFamily: "'Press Start 2P', monospace", fontSize: 6, color: '#44bbff' }}>
          M{card.mana}
        </span>
        {card.civilizations.map((civ, i) => (
          <span key={i} style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: CIV_COLOR[civ] ?? '#888',
          }} />
        ))}
      </div>
    </div>
  )
}

interface Props {
  filter: FilterState
}

export function LibraryGrid({ filter }: Props) {
  const cards = useLibraryStore(s => s.cards)
  const filtered = applyFilters(cards, filter)

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: 8,
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, 80px)',
      gap: 8,
      alignContent: 'start',
    }}>
      {filtered.length === 0 && (
        <div style={{
          gridColumn: '1 / -1',
          color: '#505c78',
          fontFamily: "'Chakra Petch', sans-serif",
          fontSize: 12,
          padding: 24,
          textAlign: 'center',
        }}>
          {cards.length === 0
            ? 'カードライブラリを読み込んでください'
            : '条件に一致するカードがありません'}
        </div>
      )}
      {filtered.map(card => (
        <LibraryCardTile key={card.id} card={card} />
      ))}
    </div>
  )
}
