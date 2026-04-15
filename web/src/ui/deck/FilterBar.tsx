import type { Card } from '../../domain/types'

export interface FilterState {
  query: string
  sort: 'mana_asc' | 'mana_desc' | 'name' | 'type'
  mana: string   // 'すべて' | '1' | ... | '12+'
  civ: string    // 'すべて' | 動的
  type: string   // 'すべて' | 動的
}

export const DEFAULT_FILTER: FilterState = {
  query: '',
  sort: 'mana_asc',
  mana: 'すべて',
  civ: 'すべて',
  type: 'すべて',
}

/** カード一覧をフィルタ＆ソートして返す純粋関数 */
export function applyFilters(cards: Card[], filter: FilterState): Card[] {
  let result = cards.filter(c => {
    if (filter.query && !c.name.toLowerCase().includes(filter.query.toLowerCase())) return false
    if (filter.mana !== 'すべて') {
      if (filter.mana === '12+') { if (c.mana < 12) return false }
      else { if (c.mana !== Number(filter.mana)) return false }
    }
    if (filter.civ !== 'すべて' && !c.civilizations.includes(filter.civ)) return false
    if (filter.type !== 'すべて' && c.card_type !== filter.type) return false
    return true
  })

  switch (filter.sort) {
    case 'mana_asc':  result = result.sort((a, b) => a.mana - b.mana || a.name.localeCompare(b.name)); break
    case 'mana_desc': result = result.sort((a, b) => b.mana - a.mana || a.name.localeCompare(b.name)); break
    case 'name':      result = result.sort((a, b) => a.name.localeCompare(b.name)); break
    case 'type':      result = result.sort((a, b) => (a.card_type ?? '').localeCompare(b.card_type ?? '') || a.mana - b.mana); break
  }
  return result
}

/** cards から重複なく文明・タイプを収集する */
export function collectOptions(cards: Card[]): { civs: string[]; types: string[] } {
  const civSet = new Set<string>()
  const typeSet = new Set<string>()
  for (const c of cards) {
    c.civilizations.forEach(v => civSet.add(v))
    if (c.card_type) typeSet.add(c.card_type)
  }
  return {
    civs: [...civSet].sort(),
    types: [...typeSet].sort(),
  }
}

interface Props {
  cards: Card[]
  filter: FilterState
  onChange: (f: FilterState) => void
}

const sel: React.CSSProperties = {
  background: '#0e1228',
  color: '#A78BFA',
  border: '1px solid rgba(124,58,237,0.4)',
  borderRadius: 4,
  padding: '3px 6px',
  fontFamily: "'Chakra Petch', sans-serif",
  fontSize: 11,
  cursor: 'pointer',
}

export function FilterBar({ cards, filter, onChange }: Props) {
  const { civs, types } = collectOptions(cards)
  const set = (partial: Partial<FilterState>) => onChange({ ...filter, ...partial })

  return (
    <div style={{
      display: 'flex',
      gap: 6,
      padding: '6px 8px',
      background: '#060810',
      borderBottom: '1px solid rgba(124,58,237,0.15)',
      flexWrap: 'wrap',
      alignItems: 'center',
      flexShrink: 0,
    }}>
      <input
        type="text"
        placeholder="カード名で検索..."
        value={filter.query}
        onChange={e => set({ query: e.target.value })}
        style={{ ...sel, color: '#E2E8F0', width: 140 }}
      />

      <select value={filter.sort} onChange={e => set({ sort: e.target.value as FilterState['sort'] })} style={sel}>
        <option value="mana_asc">マナ↑</option>
        <option value="mana_desc">マナ↓</option>
        <option value="name">名前順</option>
        <option value="type">タイプ順</option>
      </select>

      <select value={filter.mana} onChange={e => set({ mana: e.target.value })} style={sel}>
        <option value="すべて">マナ:全</option>
        {Array.from({ length: 11 }, (_, i) => i + 1).map(n => (
          <option key={n} value={String(n)}>{n}</option>
        ))}
        <option value="12+">12+</option>
      </select>

      <select value={filter.civ} onChange={e => set({ civ: e.target.value })} style={sel}>
        <option value="すべて">文明:全</option>
        {civs.map(c => <option key={c} value={c}>{c}</option>)}
      </select>

      <select value={filter.type} onChange={e => set({ type: e.target.value })} style={sel}>
        <option value="すべて">タイプ:全</option>
        {types.map(t => <option key={t} value={t}>{t}</option>)}
      </select>

      <button
        onClick={() => onChange(DEFAULT_FILTER)}
        style={{ ...sel, color: '#94A3B8', border: '1px solid rgba(255,255,255,0.1)' }}
      >
        リセット
      </button>
    </div>
  )
}
