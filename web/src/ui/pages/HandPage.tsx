import { useTabSync } from '../../sync/useTabSync'
import { useCardHotkeys } from '../hooks/useCardHotkeys'
import { HandStage } from '../stage/HandStage'
import { HandHud } from '../hud/HandHud'
import { ContextMenu } from '../overlays/ContextMenu'
import { SetupDialog } from '../overlays/SetupDialog'

const CRT_STYLE: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.04) 2px, rgba(0,0,0,0.04) 4px)',
  pointerEvents: 'none',
  zIndex: 9999,
}

export function HandPage() {
  useTabSync('hand')
  useCardHotkeys()

  // initZones は呼ばない — ボードウィンドウが initZones + ダミーデータを管理し
  // BroadcastChannel (PING/PONG) で状態を同期する

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      width: '100vw',
      background: '#0F0F23',
      overflow: 'hidden',
    }}>
      <div style={CRT_STYLE} />
      <HandHud />
      <HandStage />
      <ContextMenu />
      <SetupDialog />
    </div>
  )
}
