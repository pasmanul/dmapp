import { useEffect } from 'react'
import { useUIStore } from '../../store/uiStore'
import { useGameStore } from '../../store/gameStore'
import { useLayoutStore } from '../../store/layoutStore'

// キー → 移動先ゾーンID（ローカル版と同じデフォルト）
const KEY_ZONE: Record<string, string> = {
  b: 'battle',
  m: 'mana',
  g: 'graveyard',
  h: 'hand',
  s: 'shield',
}

export function useCardHotkeys() {
  const hoveredCard = useUIStore(s => s.hoveredCard)
  const moveCard = useGameStore(s => s.moveCard)
  const addLog = useUIStore(s => s.addLog)
  const zones = useLayoutStore(s => s.zones)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // input/textarea フォーカス中はスキップ
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (!hoveredCard) return

      const destZoneId = KEY_ZONE[e.key.toLowerCase()]
      if (!destZoneId) return
      if (destZoneId === hoveredCard.zoneId) return

      e.preventDefault()
      const destZone = zones.find(z => z.id === destZoneId)
      moveCard(hoveredCard.zoneId, hoveredCard.instanceId, destZoneId)
      addLog(`${hoveredCard.cardName} → ${destZone?.name ?? destZoneId}`)
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [hoveredCard, moveCard, addLog, zones])
}
