import { useEffect, useRef } from 'react'
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'
import { useStore } from './store'

const TICKS_PER_WHOLE = 1920

export function ScoreView() {
  const containerRef = useRef<HTMLDivElement>(null)
  const osmdRef = useRef<OpenSheetMusicDisplay | null>(null)
  const lastTickRef = useRef<number>(-1)
  const musicxml = useStore((s) => s.arrangement?.musicxml ?? null)
  const currentTick = useStore((s) => s.currentTick)
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
        followCursor: true,
      })
    }
    if (!musicxml) return
    let cancelled = false
    osmdRef.current
      .load(musicxml)
      .then(() => {
        if (cancelled) return
        osmdRef.current!.render()
        lastTickRef.current = -1
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

  // moving playback cursor: advance OSMD's cursor to the sounding tick
  useEffect(() => {
    const osmd = osmdRef.current
    if (!osmd || !osmd.cursor) return
    const cursor = osmd.cursor
    if (currentTick === null) {
      cursor.reset()
      cursor.hide()
      lastTickRef.current = -1
      return
    }
    if (currentTick <= lastTickRef.current) {
      cursor.reset()
    }
    cursor.show()
    const target = currentTick / TICKS_PER_WHOLE
    let guard = 10000
    while (
      !cursor.iterator.EndReached &&
      cursor.iterator.currentTimeStamp.RealValue < target - 1e-6 &&
      guard-- > 0
    ) {
      cursor.next()
    }
    lastTickRef.current = currentTick
  }, [currentTick])

  return <div className="score-sheet" data-empty={musicxml === null} ref={containerRef} />
}
