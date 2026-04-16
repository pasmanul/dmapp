import type { GameCard } from '../../domain/types'

export interface CardPosition {
  instanceId: string
  x: number
  y: number
  cardW: number
  cardH: number
}

const PADDING = 8

function layoutRow(
  cards: GameCard[],
  areaX: number,
  areaY: number,
  areaW: number,
  areaH: number,
  cardW: number,
  cardH: number,
): CardPosition[] {
  const n = cards.length
  if (n === 0) return []

  // Effective width accounts for tapped cards (90deg rotation → width becomes cardH)
  const totalNatural = cards.reduce((sum, gc) => sum + (gc.tapped ? cardH : cardW), 0)
  const availW = areaW - PADDING * 2

  // pos.x/pos.y はカード中央座標（CardShape の Group offset 設計に合わせる）
  // 収まる場合は中央揃え・隙間なし、収まらない場合は重なり
  let centers: number[]
  if (totalNatural <= availW) {
    // 中央揃え（間隔0）
    const startX = areaX + (areaW - totalNatural) / 2
    let x = startX
    centers = cards.map(gc => {
      const w = gc.tapped ? cardH : cardW
      const cx = x + w / 2
      x += w
      return cx
    })
  } else {
    // 収まらない場合：等間隔で重なり（最後のカードが右端に収まる）
    const lastW = cards[n - 1].tapped ? cardH : cardW
    const overlap = n > 1 ? (availW - lastW) / (n - 1) : availW
    let x = areaX + PADDING
    centers = cards.map((gc, i) => {
      const w = gc.tapped ? cardH : cardW
      const cx = x + w / 2
      if (i < n - 1) x += overlap
      else x += w
      return cx
    })
  }

  // カード中央をゾーンのコンテンツ領域中央に揃える
  const cy = areaY + areaH / 2

  return cards.map((gc, i) => ({
    instanceId: gc.instanceId,
    x: centers[i],
    y: cy,
    cardW,
    cardH,
  }))
}

export function calcCardPositions(
  cards: GameCard[],
  areaX: number,
  areaY: number,
  areaW: number,
  areaH: number,
  cardW: number,
  cardH: number,
  twoRow: boolean,
): CardPosition[] {
  if (cards.length === 0) return []

  if (!twoRow) {
    return layoutRow(cards, areaX, areaY, areaW, areaH, cardW, cardH)
  }

  // two_row: row=0 bottom, row=1 top
  const row0 = cards.filter(gc => gc.row === 0)
  const row1 = cards.filter(gc => gc.row === 1)
  const halfH = areaH / 2

  const bottom = layoutRow(row0, areaX, areaY + halfH, areaW, halfH, cardW, cardH)
  const top = layoutRow(row1, areaX, areaY, areaW, halfH, cardW, cardH)

  return [...top, ...bottom]
}
