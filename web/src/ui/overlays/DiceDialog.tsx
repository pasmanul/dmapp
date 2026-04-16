import { useState, useCallback, useEffect, useRef } from 'react'
import { useUIStore } from '../../store/uiStore'

const DICE_TYPES = [4, 6, 8, 10, 12, 20]

interface HistoryEntry { sides: number; result: number }

export function DiceDialog() {
  const { activeDialog, closeDialog, addLog } = useUIStore(s => ({
    activeDialog: s.activeDialog,
    closeDialog: s.closeDialog,
    addLog: s.addLog,
  }))

  const [sides, setSides] = useState(6)
  const [display, setDisplay] = useState<number | null>(null)
  const [rolling, setRolling] = useState(false)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ダイアログを閉じた時にロール中のintervalをキャンセル
  useEffect(() => {
    if (activeDialog !== 'dice' && intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
      setRolling(false)
    }
  }, [activeDialog])

  const roll = useCallback(() => {
    if (rolling) return
    setRolling(true)
    const final = Math.floor(Math.random() * sides) + 1
    let count = 0
    intervalRef.current = setInterval(() => {
      setDisplay(Math.floor(Math.random() * sides) + 1)
      count++
      if (count >= 14) {
        clearInterval(intervalRef.current!)
        intervalRef.current = null
        setDisplay(final)
        setRolling(false)
        setHistory(h => [{ sides, result: final }, ...h].slice(0, 10))
        addLog(`ダイス d${sides}: ${final}`)
      }
    }, 30)
  }, [rolling, sides, addLog])

  // Enter / Space キーでロール（ダイアログが開いている間のみ）
  useEffect(() => {
    if (activeDialog !== 'dice') return
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        roll()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [activeDialog, roll])

  if (activeDialog !== 'dice') return null

  const overlay: React.CSSProperties = {
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.7)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 2000,
  }
  const dialog: React.CSSProperties = {
    background: '#080c1c',
    border: '1px solid rgba(124,58,237,0.4)',
    borderRadius: 12,
    padding: 24,
    width: 360,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
    boxShadow: '0 16px 48px rgba(0,0,0,0.8)',
    fontFamily: "'Chakra Petch', sans-serif",
  }

  return (
    <div style={overlay} onClick={closeDialog}>
      <div style={dialog} onClick={e => e.stopPropagation()}>
        <div style={{
          fontFamily: "'Press Start 2P', monospace",
          fontSize: 11,
          color: '#00FFFF',
          textShadow: '0 0 10px rgba(0,255,255,0.5)',
        }}>
          DICE ROLLER
        </div>

        {/* ダイス種選択 */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {DICE_TYPES.map(d => (
            <button
              key={d}
              onClick={() => setSides(d)}
              style={{
                fontFamily: "'Press Start 2P', monospace",
                fontSize: 9,
                padding: '6px 10px',
                borderRadius: 6,
                cursor: 'pointer',
                border: `1px solid ${sides === d ? '#7C3AED' : 'rgba(124,58,237,0.3)'}`,
                background: sides === d ? '#4c1d95' : '#0e1228',
                color: sides === d ? '#c4b5fd' : '#6672a0',
                transition: 'all 150ms',
              }}
            >
              d{d}
            </button>
          ))}
        </div>

        {/* 結果表示 */}
        <div style={{
          textAlign: 'center',
          padding: '24px 0',
          borderRadius: 8,
          background: '#0e1228',
          border: '1px solid rgba(124,58,237,0.2)',
        }}>
          <div style={{
            fontFamily: "'Press Start 2P', monospace",
            fontSize: display !== null ? 56 : 32,
            color: rolling ? '#7C3AED' : '#00FFFF',
            textShadow: rolling
              ? '0 0 20px rgba(124,58,237,0.8)'
              : display !== null ? '0 0 20px rgba(0,255,255,0.8)' : 'none',
            minHeight: 80,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: rolling ? 'none' : 'color 300ms, text-shadow 300ms',
          }}>
            {display !== null ? display : '?'}
          </div>
          <div style={{ color: '#505c78', fontSize: 11, marginTop: 4 }}>
            d{sides}
          </div>
        </div>

        {/* ロールボタン */}
        <button
          onClick={roll}
          disabled={rolling}
          style={{
            fontFamily: "'Press Start 2P', monospace",
            fontSize: 11,
            padding: '12px 0',
            borderRadius: 8,
            cursor: rolling ? 'not-allowed' : 'pointer',
            border: 'none',
            background: rolling ? '#1a1a2e' : '#4c1d95',
            color: rolling ? '#505c78' : '#c4b5fd',
            transition: 'all 150ms',
            boxShadow: rolling ? 'none' : '0 0 16px rgba(124,58,237,0.4)',
          }}
          onMouseEnter={e => { if (!rolling) e.currentTarget.style.background = '#5b21b6' }}
          onMouseLeave={e => { if (!rolling) e.currentTarget.style.background = '#4c1d95' }}
        >
          {rolling ? 'ROLLING...' : 'ROLL'}
        </button>

        {/* 履歴 */}
        {history.length > 0 && (
          <div>
            <div style={{ color: '#505c78', fontSize: 10, fontFamily: "'Press Start 2P', monospace", marginBottom: 6 }}>
              HISTORY
            </div>
            <div style={{
              display: 'flex', flexDirection: 'column', gap: 2,
              maxHeight: 160, overflowY: 'auto',
            }}>
              {history.map((h, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '3px 8px',
                  borderRadius: 4,
                  background: i === 0 ? 'rgba(124,58,237,0.1)' : 'transparent',
                  color: i === 0 ? '#a78bfa' : '#505c78',
                  fontSize: 12,
                }}>
                  <span>d{h.sides}</span>
                  <span style={{ fontFamily: "'Press Start 2P', monospace", fontSize: 11 }}>
                    {h.result}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={closeDialog}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#505c78',
            cursor: 'pointer',
            fontSize: 11,
            fontFamily: "'Chakra Petch', sans-serif",
            alignSelf: 'flex-end',
          }}
        >
          閉じる
        </button>
      </div>
    </div>
  )
}
