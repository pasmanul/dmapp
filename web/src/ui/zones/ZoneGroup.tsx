import { useRef } from 'react'
import { Group, Rect, Text } from 'react-konva'
import type Konva from 'konva'
import type { ZoneDefinition } from '../../domain/types'
import { useGameStore } from '../../store/gameStore'
import { useUIStore } from '../../store/uiStore'
import { zoneColors, CARD_W, CARD_H } from '../../theme'
import { calcCardPositions } from '../hooks/useCardLayout'
import { CardShape } from '../cards/CardShape'

interface Props {
  zoneDef: ZoneDefinition
  x: number
  y: number
  width: number
  height: number
  // Source zone override (for hand_view)
  sourceZoneId?: string
}

function hexToRgb(hex: string) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return [r, g, b] as const
}

export function ZoneGroup({ zoneDef, x, y, width, height, sourceZoneId }: Props) {
  const zoneId = sourceZoneId ?? zoneDef.id
  const effectiveZoneId = zoneDef.source_zone_id ?? zoneDef.id

  const cards = useGameStore(s => s.zones[effectiveZoneId]?.cards ?? [])
  const moveCard = useGameStore(s => s.moveCard)
  const tapCard = useGameStore(s => s.tapCard)
  const { selectedCardIds, selectCard, clearSelection, openContextMenu, openStackDialog, addLog, setHoveredCard } = useUIStore(s => ({
    selectedCardIds: s.selectedCardIds,
    selectCard: s.selectCard,
    clearSelection: s.clearSelection,
    openContextMenu: s.openContextMenu,
    openStackDialog: s.openStackDialog,
    addLog: s.addLog,
    setHoveredCard: s.setHoveredCard,
  }))

  const colors = zoneColors(zoneDef.id)
  const cardScale = zoneDef.card_scale ?? 1.0

  const TITLE_H = 22
  const contentY = y + TITLE_H
  const contentH = height - TITLE_H

  // ゾーン高さに収まるようにカードをスケールダウン（アスペクト比維持）
  // two_row の場合は行の高さ（contentH/2）を基準にする
  const baseCardW = CARD_W * cardScale
  const baseCardH = CARD_H * cardScale
  const rowH = zoneDef.two_row ? contentH / 2 : contentH
  const fitScale = Math.min(1, rowH / baseCardH)
  const cardW = Math.round(baseCardW * fitScale)
  const cardH = Math.round(baseCardH * fitScale)

  const positions = calcCardPositions(
    cards,
    x, contentY,
    width, contentH,
    cardW, cardH,
    zoneDef.two_row,
  )

  const [bgR, bgG, bgB] = hexToRgb(colors.bgTop)

  // Find which zone contains a point (used for drop target detection)
  const groupRef = useRef<Konva.Group>(null)

  function handleDragStart() {
    // ZoneGroup 全体を Layer の最前面に移動してドラッグ中のカードが他ゾーンに隠れないようにする
    groupRef.current?.moveToTop()
    clearSelection()
  }

  function handleDragEnd(gc: import('../../domain/types').GameCard, dropX: number, dropY: number) {
    // The stage will call findDropTarget — we use a global event
    const event = new CustomEvent('card-drop', {
      detail: { fromZoneId: zoneDef.id, instanceId: gc.instanceId, dropX, dropY },
    })
    window.dispatchEvent(event)
    addLog(`${zoneDef.name}から移動: ${gc.card.name}`)
  }

  function handleTap(gc: import('../../domain/types').GameCard) {
    if (zoneDef.tappable) {
      tapCard(zoneDef.id, gc.instanceId)
      addLog(`${gc.card.name} をタップ/アンタップ`)
    } else {
      selectCard(gc.instanceId, false)
    }
  }

  function handleHover(gc: import('../../domain/types').GameCard | null) {
    setHoveredCard(gc ? { instanceId: gc.instanceId, zoneId: zoneDef.id, cardName: gc.card.name } : null)
  }

  function handleContextMenu(
    gc: import('../../domain/types').GameCard,
    cx: number,
    cy: number,
  ) {
    openContextMenu({ x: cx, y: cy, zoneId: zoneDef.id, cardInstanceId: gc.instanceId, card: gc })
  }

  return (
    <Group ref={groupRef} id={`zone-${zoneDef.id}`}>
      {/* Zone background */}
      <Rect
        x={x} y={y} width={width} height={height}
        fillLinearGradientStartPoint={{ x: 0, y: 0 }}
        fillLinearGradientEndPoint={{ x: 0, y: height }}
        fillLinearGradientColorStops={[
          0, colors.bgTop,
          1, colors.bgBottom,
        ]}
        stroke={colors.border}
        strokeWidth={1}
        cornerRadius={8}
      />

      {/* Top accent line */}
      <Rect
        x={x + 1} y={y + 1}
        width={width - 2} height={3}
        fillLinearGradientStartPoint={{ x: 0, y: 0 }}
        fillLinearGradientEndPoint={{ x: width, y: 0 }}
        fillLinearGradientColorStops={[
          0, 'transparent',
          0.3, colors.border,
          0.7, colors.border,
          1, 'transparent',
        ]}
        cornerRadius={[8, 8, 0, 0]}
      />

      {/* Title bar */}
      <Rect
        x={x} y={y} width={width} height={TITLE_H}
        fill={colors.titleBar}
        cornerRadius={[8, 8, 0, 0]}
      />

      {/* Zone name + card count */}
      <Text
        x={x + 8} y={y + 4}
        text={`${zoneDef.name}  (${cards.length})`}
        fontSize={11}
        fill={colors.titleFg}
        fontFamily="'VT323', monospace"
        letterSpacing={0.5}
      />

      {/* Drop target overlay — transparent but captures events */}
      <Rect
        x={x} y={contentY}
        width={width} height={contentH}
        fill="transparent"
        id={`droptarget-${zoneDef.id}`}
      />

      {/* Pile mode: show count only */}
      {zoneDef.pile_mode && cards.length > 0 && (
        <>
          <Rect
            x={x + width / 2 - cardW / 2}
            y={contentY + contentH / 2 - cardH / 2}
            width={cardW} height={cardH}
            fill="#061420"
            stroke={colors.border}
            strokeWidth={2}
            cornerRadius={6}
          />
          <Text
            x={x + width / 2 - 24}
            y={contentY + contentH / 2 - 14}
            text={String(cards.length)}
            fontSize={28}
            fill={colors.titleFg}
            fontFamily="'Press Start 2P', monospace"
          />
        </>
      )}

      {/* Cards */}
      {!zoneDef.pile_mode && positions.map((pos) => {
        const gc = cards.find(c => c.instanceId === pos.instanceId)
        if (!gc) return null
        return (
          <CardShape
            key={gc.instanceId}
            gc={gc}
            x={pos.x}
            y={pos.y}
            cardW={pos.cardW}
            cardH={pos.cardH}
            masked={zoneDef.masked}
            selected={selectedCardIds.has(gc.instanceId)}
            draggable={!zoneDef.masked}
            onTap={handleTap}
            onContextMenu={handleContextMenu}
            onBadgeClick={(gc) => openStackDialog(gc, zoneDef.id)}
            onHover={handleHover}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          />
        )
      })}

      {/* Neon glow border on hover (simulated with shadow) */}
      <Rect
        x={x} y={y} width={width} height={height}
        fill="transparent"
        stroke="transparent"
        cornerRadius={8}
        shadowColor={colors.border}
        shadowBlur={12}
        shadowOpacity={0.4}
        listening={false}
      />
    </Group>
  )
}
