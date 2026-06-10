import { useEffect, useRef } from 'react'
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'
import { useStore } from './store'

export function ScoreView() {
  const containerRef = useRef<HTMLDivElement>(null)
  const osmdRef = useRef<OpenSheetMusicDisplay | null>(null)
  const musicxml = useStore((s) => s.arrangement?.musicxml ?? null)
  const setStage = useStore((s) => s.setStage)

  useEffect(() => {
    if (!containerRef.current) return
    if (!osmdRef.current) {
      osmdRef.current = new OpenSheetMusicDisplay(containerRef.current, {
        autoResize: true,
        backend: 'svg',
        drawTitle: true,
        drawComposer: false,
        drawPartNames: true,
        drawingParameters: 'default',
      })
    }
    if (!musicxml) return
    let cancelled = false
    osmdRef.current
      .load(musicxml)
      .then(() => {
        if (cancelled) return
        osmdRef.current!.render()
        setStage('ready')
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          console.error('OSMD render failed', err)
          setStage('error')
        }
      })
    return () => {
      cancelled = true
    }
  }, [musicxml, setStage])

  return <div className="score-sheet" data-empty={musicxml === null} ref={containerRef} />
}
