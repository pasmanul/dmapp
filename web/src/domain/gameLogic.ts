import type { Card, GameCard, Zone, GameStateSnapshot } from './types'

export function newGameCard(card: Card): GameCard {
  return {
    instanceId: crypto.randomUUID(),
    card,
    tapped: false,
    face_down: false,
    revealed: false,
    row: 0,
    marker: null,
    under_cards: [],
  }
}

export function shuffleArray<T>(arr: readonly T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export function cloneGameCard(gc: GameCard): GameCard {
  return {
    ...gc,
    under_cards: gc.under_cards.map(cloneGameCard),
  }
}

export function cloneZones(zones: Record<string, Zone>): Record<string, Zone> {
  const result: Record<string, Zone> = {}
  for (const [id, zone] of Object.entries(zones)) {
    result[id] = { zoneId: zone.zoneId, cards: zone.cards.map(cloneGameCard) }
  }
  return result
}

export function pushSnapshot(
  stack: GameStateSnapshot[],
  zones: Record<string, Zone>,
  maxLen = 50,
): GameStateSnapshot[] {
  const snap: GameStateSnapshot = { zones: cloneZones(zones) }
  const next = [...stack, snap]
  return next.length > maxLen ? next.slice(-maxLen) : next
}

export function moveCard(
  zones: Record<string, Zone>,
  fromZoneId: string,
  instanceId: string,
  toZoneId: string,
  toIndex?: number,
): Record<string, Zone> {
  const next = cloneZones(zones)
  const fromZone = next[fromZoneId]
  const toZone = next[toZoneId]
  if (!fromZone || !toZone) return zones

  const idx = fromZone.cards.findIndex(c => c.instanceId === instanceId)
  if (idx === -1) return zones

  const [card] = fromZone.cards.splice(idx, 1)
  if (toIndex !== undefined) {
    toZone.cards.splice(toIndex, 0, card)
  } else {
    toZone.cards.push(card)
  }
  return next
}

export function shuffleZone(zones: Record<string, Zone>, zoneId: string): Record<string, Zone> {
  const next = cloneZones(zones)
  const zone = next[zoneId]
  if (!zone) return zones
  zone.cards = shuffleArray(zone.cards)
  return next
}

export function initializeField(
  zones: Record<string, Zone>,
  deckCards: GameCard[],
): Record<string, Zone> {
  const next = cloneZones(zones)
  // Clear all zones
  for (const zone of Object.values(next)) {
    zone.cards = []
  }
  if (!next['deck']) return next

  // 全カードの状態をリセット（face_down, tapped, marker, スタック解除）してからシャッフル
  const reset = deckCards.map(gc => ({ ...gc, face_down: false, tapped: false, marker: null, under_cards: [] }))
  const shuffled = shuffleArray(reset)

  // 5 shields (face_down)
  const shieldCards = shuffled.splice(0, 5).map(gc => ({ ...gc, face_down: true }))
  if (next['shield']) next['shield'].cards = shieldCards

  // 5 hand cards
  const handCards = shuffled.splice(0, 5)
  if (next['hand']) next['hand'].cards = handCards

  // rest to deck
  next['deck'].cards = shuffled
  return next
}

/** ドラッグしたカードを別カードの上に重ねて進化スタックを形成する */
export function stackCard(
  zones: Record<string, Zone>,
  fromZoneId: string,
  instanceId: string,
  toZoneId: string,
  targetInstanceId: string,
): Record<string, Zone> {
  const next = cloneZones(zones)
  const fromZone = next[fromZoneId]
  const toZone = next[toZoneId]
  if (!fromZone || !toZone) return zones

  const fromIdx = fromZone.cards.findIndex(c => c.instanceId === instanceId)
  if (fromIdx === -1) return zones

  // splice前にtargetIdxを確定する（同ゾーン内でsplice後にインデックスがずれるのを防ぐ）
  const targetIdx = toZone.cards.findIndex(c => c.instanceId === targetInstanceId)
  if (targetIdx === -1) return zones

  const [card] = fromZone.cards.splice(fromIdx, 1)

  // 同ゾーン内かつfromIdx < targetIdxの場合、spliceにより1つずれる
  const adjustedTargetIdx = (fromZoneId === toZoneId && fromIdx < targetIdx)
    ? targetIdx - 1
    : targetIdx
  const target = toZone.cards[adjustedTargetIdx]

  // 新しいトップカードの under_cards = [旧トップ, ...旧トップの under_cards]
  toZone.cards[adjustedTargetIdx] = { ...card, under_cards: [{ ...target, under_cards: [] }, ...target.under_cards] }
  return next
}

/** スタック内の指定カードを切り離してゾーンに戻す */
export function unstackCard(
  zones: Record<string, Zone>,
  zoneId: string,
  topInstanceId: string,
  detachInstanceId: string,
): Record<string, Zone> {
  const next = cloneZones(zones)
  const zone = next[zoneId]
  if (!zone) return zones

  const topIdx = zone.cards.findIndex(c => c.instanceId === topInstanceId)
  if (topIdx === -1) return zones
  const top = { ...zone.cards[topIdx] }

  const detachIdx = top.under_cards.findIndex(c => c.instanceId === detachInstanceId)
  if (detachIdx === -1) return zones

  const detached = top.under_cards[detachIdx]
  top.under_cards = top.under_cards.filter(c => c.instanceId !== detachInstanceId)
  zone.cards[topIdx] = top
  zone.cards.push({ ...detached })
  return next
}

export function buildDeckFromLibrary(
  cards: Card[],
  deckList: { cardId: string; count: number }[],
): GameCard[] {
  const cardMap = new Map(cards.map(c => [c.id, c]))
  const result: GameCard[] = []
  for (const entry of deckList) {
    const card = cardMap.get(entry.cardId)
    if (!card) continue
    for (let i = 0; i < entry.count; i++) {
      result.push(newGameCard(card))
    }
  }
  return result
}
