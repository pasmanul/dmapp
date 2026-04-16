import { useRef, useEffect, useCallback } from 'react'
import { Stage, Layer } from 'react-konva'
import { useLayoutStore } from '../../store/layoutStore'
import { useGameStore } from '../../store/gameStore'
import { useUIStore } from '../../store/uiStore'
import { useStageSize, gridToPixel } from '../hooks/useStageSize'
import { calcCardPositions } from '../hooks/useCardLayout'
import { ZoneGroup } from '../zones/ZoneGroup'
import { ZoneOverlayButtons } from '../zones/ZoneOverlayButtons'
import { TOKENS, CARD_W, CARD_H } from '../../theme'

export function BoardStage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const size = useStageSize(containerRef)

  const zoneDefs = useLayoutStore(s => s.getWindowZones('board'))
  const winDef = useLayoutStore(s => s.getWindow('board'))
  const zones = useGameStore(s => s.zones)
  const moveCard = useGameStore(s => s.moveCard)
  const stackCard = useGameStore(s => s.stackCard)
  const addLog = useUIStore(s => s.addLog)
  const setDeckDropInfo = useUIStore(s => s.setDeckDropInfo)
  const closeContextMenu = useUIStore(s => s.closeContextMenu)

  // Handle card-drop events from ZoneGroup dragging
  const handleCardDrop = useCallback((e: Event) => {
    const { fromZoneId, instanceId, dropX, dropY } = (e as CustomEvent).detail

    if (!winDef || size.width === 0) return

    const cellW = size.width / winDef.grid_cols
    const cellH = size.height / winDef.grid_rows

    // Find which zone contains the drop point
    let targetZoneId: string | null = null
    for (const zd of zoneDefs) {
      if (zd.source_zone_id || zd.ui_widget) continue
      const r = {
        x: zd.grid_pos.col * cellW,
        y: zd.grid_pos.row * cellH,
        w: zd.grid_pos.col_span * cellW,
        h: zd.grid_pos.row_span * cellH,
      }
      if (dropX >= r.x && dropX <= r.x + r.w && dropY >= r.y && dropY <= r.y + r.h) {
        targetZoneId = zd.id
        break
      }
    }

    if (!targetZoneId) return

    const TITLE_H = 22
    const targetZone = zoneDefs.find(z => z.id === targetZoneId)
    const targetCards = zones[targetZoneId]?.cards ?? []

    // Check if the drop point lands on a specific card → stack/evolve
    if (targetZone && !targetZone.pile_mode && targetCards.length > 0) {
      const r = {
        x: targetZone.grid_pos.col * cellW,
        y: targetZone.grid_pos.row * cellH,
        w: targetZone.grid_pos.col_span * cellW,
        h: targetZone.grid_pos.row_span * cellH,
      }
      const cardScale = targetZone.card_scale ?? 1.0
      const cardW = Math.round(CARD_W * cardScale)
      const cardH = Math.round(CARD_H * cardScale)
      const positions = calcCardPositions(
        targetCards,
        r.x, r.y + TITLE_H,
        r.w, r.h - TITLE_H,
        cardW, cardH,
        !!targetZone.two_row,
      )
      for (const pos of positions) {
        if (pos.instanceId === instanceId) continue
        if (dropX >= pos.x && dropX <= pos.x + pos.cardW &&
            dropY >= pos.y && dropY <= pos.y + pos.cardH) {
          stackCard(fromZoneId, instanceId, targetZoneId, pos.instanceId)
          addLog(`進化スタック → ${targetZone.name}`)
          return
        }
      }
    }

    // 山札へのドロップは上/下選択ダイアログへ委譲
    if (targetZoneId === 'deck' && fromZoneId !== 'deck') {
      setDeckDropInfo({ fromZoneId, instanceId })
      return
    }

    // Regular zone move
    if (targetZoneId !== fromZoneId) {
      moveCard(fromZoneId, instanceId, targetZoneId)
      addLog(`カード移動 → ${targetZone?.name}`)
    }
  }, [zoneDefs, winDef, size, zones, moveCard, stackCard, addLog, setDeckDropInfo])

  useEffect(() => {
    window.addEventListener('card-drop', handleCardDrop)
    return () => window.removeEventListener('card-drop', handleCardDrop)
  }, [handleCardDrop])

  if (!winDef) return null

  const zoneRects = zoneDefs
    .filter(zd => !zd.ui_widget)
    .map(zd => ({
      zd,
      rect: size.width > 0
        ? gridToPixel(zd.grid_pos, winDef.grid_cols, winDef.grid_rows, size.width, size.height)
        : null,
    }))

  return (
    <div
      ref={containerRef}
      style={{ flex: 1, background: TOKENS.bg, position: 'relative' }}
      onClick={() => closeContextMenu()}
    >
      {size.width > 0 && (
        <>
          <Stage width={size.width} height={size.height}>
            <Layer>
              {zoneRects.map(({ zd, rect }) => rect && (
                <ZoneGroup
                  key={zd.id}
                  zoneDef={zd}
                  x={rect.x}
                  y={rect.y}
                  width={rect.width}
                  height={rect.height}
                />
              ))}
            </Layer>
          </Stage>

          {/* Zone overlay buttons (DOM layer over canvas) */}
          <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
            {zoneRects.map(({ zd, rect }) => rect && (
              <ZoneOverlayButtons
                key={zd.id}
                zoneDef={zd}
                x={rect.x}
                y={rect.y}
                width={rect.width}
                height={rect.height}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
