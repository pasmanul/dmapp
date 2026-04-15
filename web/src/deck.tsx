import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { DeckPage } from './ui/pages/DeckPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DeckPage />
  </StrictMode>,
)
