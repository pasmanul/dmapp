import { useEffect, useRef } from 'react'
import { useUIStore } from '../../store/uiStore'
import { useGameStore } from '../../store/gameStore'

const ZONES = [
  { id: 'battle', label: 'バトルゾーン', toIndex: undefined as number | undefined },
  { id: 'mana', label: 'マナゾーン', toIndex: undefined },
  { id: 'graveyard', label: '墓地', toIndex: undefined },
  { id: 'shield', label: 'シールド', toIndex: undefined },
  { id: 'hand', label: '手札', toIndex: undefined },
  { id: 'temp', label: '保留', toIndex: undefined },
  { id: 'deck', label: '山札（上）', toIndex: 0 },
  { id: 'deck', label: '山札（下）', toIndex: undefined },
]

const MARKERS = [
  { id: 'red', label: '赤' },
  { id: 'blue', label: '青' },
  { id: 'green', label: '緑' },
  { id: 'yellow', label: '黄' },
  { id: null, label: 'なし' },
]

export function ContextMenu() {
  const { contextMenu, closeContextMenu, addLog, openDialog, openStackDialog } = useUIStore(s => ({
    contextMenu: s.contextMenu,
    closeContextMenu: s.closeContextMenu,
    addLog: s.addLog,
    openDialog: s.openDialog,
    openStackDialog: s.openStackDialog,
  }))
  const { tapCard, flipCard, setMarker, moveCard } = useGameStore(s => ({
    tapCard: s.tapCard,
    flipCard: s.flipCard,
    setMarker: s.setMarker,
    moveCard: s.moveCard,
  }))
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        closeContextMenu()
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [closeContextMenu])

  if (!contextMenu) return null

  const { x, y, zoneId, cardInstanceId, card } = contextMenu

  function action(fn: () => void) {
    fn()
    closeContextMenu()
  }

  const menuStyle: React.CSSProperties = {
    position: 'fixed',
    left: Math.min(x, window.innerWidth - 200),
    top: Math.min(y, window.innerHeight - 300),
    width: 190,
    background: '#0e1228',
    border: '1px solid rgba(124,58,237,0.4)',
    borderRadius: 8,
    zIndex: 1000,
    overflow: 'hidden',
    boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
    fontFamily: "'Chakra Petch', sans-serif",
    fontSize: 12,
  }

  const itemStyle: React.CSSProperties = {
    padding: '7px 14px',
    cursor: 'pointer',
    color: '#aabbd0',
    borderBottom: '1px solid rgba(255,255,255,0.04)',
    transition: 'background 150ms',
  }

  const headerStyle: React.CSSProperties = {
    padding: '6px 14px',
    background: '#080c1c',
    color: '#505c78',
    fontSize: 10,
    fontFamily: "'Press Start 2P', monospace",
    letterSpacing: 0.5,
    borderBottom: '1px solid rgba(255,255,255,0.06)',
  }

  const labelStyle: React.CSSProperties = {
    padding: '5px 14px 2px',
    color: '#505c78',
    fontSize: 10,
    letterSpacing: 0.5,
    textTransform: 'uppercase' as const,
  }

  return (
    <div ref={ref} style={menuStyle}>
      <div style={headerStyle}>{card.card.name.slice(0, 18)}</div>

      {/* スタック確認 — スタックカードがある場合のみ */}
      {card.under_cards.length > 0 && (
        <div
          style={{ ...itemStyle, color: '#e07020' }}
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(224,112,32,0.15)')}
          onMouseLeave={e => (e.currentTarget.style.background = '')}
          onClick={() => action(() => openStackDialog(card, zoneId))}
        >
          スタック確認 ({card.under_cards.length + 1})
        </div>
      )}

      {/* サーチ — 山札のみ */}
      {zoneId === 'deck' && (
        <div
          style={{ ...itemStyle, color: '#00FFFF' }}
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,255,255,0.1)')}
          onMouseLeave={e => (e.currentTarget.style.background = '')}
          onClick={() => action(() => openDialog('search'))}
        >
          サーチ
        </div>
      )}

      <div
        style={itemStyle}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(124,58,237,0.15)')}
        onMouseLeave={e => (e.currentTarget.style.background = '')}
        onClick={() => action(() => {
          tapCard(zoneId, cardInstanceId)
          addLog(`${card.card.name} タップ/アンタップ`)
        })}
      >
        {card.tapped ? 'アンタップ' : 'タップ'}
      </div>

      <div
        style={itemStyle}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(124,58,237,0.15)')}
        onMouseLeave={e => (e.currentTarget.style.background = '')}
        onClick={() => action(() => {
          flipCard(zoneId, cardInstanceId)
          addLog(`${card.card.name} 裏返し`)
        })}
      >
        {card.face_down ? '表向きにする' : '裏向きにする'}
      </div>

      <div style={labelStyle}>マーカー</div>
      {MARKERS.map(m => (
        <div
          key={String(m.id)}
          style={{ ...itemStyle, display: 'flex', alignItems: 'center', gap: 8 }}
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(124,58,237,0.15)')}
          onMouseLeave={e => (e.currentTarget.style.background = '')}
          onClick={() => action(() => setMarker(zoneId, cardInstanceId, m.id))}
        >
          {m.id && (
            <div style={{
              width: 10, height: 10, borderRadius: '50%',
              background: { red: '#ef4444', blue: '#3b82f6', green: '#22c55e', yellow: '#eab308' }[m.id] ?? '#fff',
            }} />
          )}
          {m.label}
          {card.marker === m.id && ' ✓'}
        </div>
      ))}

      <div style={labelStyle}>ゾーン移動</div>
      {ZONES.filter(z => z.id !== zoneId).map((z, i) => (
        <div
          key={`${z.id}-${i}`}
          style={itemStyle}
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(124,58,237,0.15)')}
          onMouseLeave={e => (e.currentTarget.style.background = '')}
          onClick={() => action(() => {
            moveCard(zoneId, cardInstanceId, z.id, z.toIndex)
            addLog(`${card.card.name} → ${z.label}`)
          })}
        >
          → {z.label}
        </div>
      ))}
    </div>
  )
}
