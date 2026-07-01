import { createContext, useContext, useEffect, useState } from 'react'

// Global full-screen image viewer. Any component can call useLightbox()(url)
// to open an image full-screen; click / Escape / × closes it.
const LightboxContext = createContext(() => {})

export function useLightbox() {
  return useContext(LightboxContext)
}

export function LightboxProvider({ children }) {
  const [src, setSrc] = useState(null)

  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') setSrc(null) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    document.body.style.overflow = src ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [src])

  return (
    <LightboxContext.Provider value={setSrc}>
      {children}
      {src && (
        <div
          onClick={() => setSrc(null)}
          style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            background: 'rgba(24,16,8,0.93)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'zoom-out',
          }}
        >
          <img
            src={src}
            alt=""
            style={{ maxWidth: '95vw', maxHeight: '95vh', objectFit: 'contain', boxShadow: '0 6px 40px rgba(0,0,0,0.6)' }}
          />
          <button
            onClick={() => setSrc(null)}
            aria-label="Close"
            style={{
              position: 'fixed', top: 14, right: 20, fontSize: 30, lineHeight: 1,
              color: '#f4ecdc', background: 'none', border: 'none', cursor: 'pointer',
            }}
          >×</button>
          <a
            href={src} target="_blank" rel="noreferrer"
            onClick={e => e.stopPropagation()}
            style={{ position: 'fixed', bottom: 16, right: 22, color: '#e9dfca', fontSize: 13, fontFamily: 'sans-serif' }}
          >open original ↗</a>
        </div>
      )}
    </LightboxContext.Provider>
  )
}
