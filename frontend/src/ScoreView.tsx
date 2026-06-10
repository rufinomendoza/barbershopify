import { useEffect, useRef, useState } from 'react'
import { OpenSheetMusicDisplay, PointF2D } from 'opensheetmusicdisplay'
import { useStore, type Selection } from './store'
import type { VoiceName } from './types'

const TICKS_PER_WHOLE = 1920

// our MusicXML layout is fixed: P1 voice1=tenor voice2=lead, P2 voice1=bari voice2=bass
const VOICE_BY_INSTRUMENT_AND_ID: Record<string, VoiceName> = {
  '0:1': 'tenor',
  '0:2': 'lead',
  '1:1': 'bari',
  '1:2': 'bass',
}

/* eslint-disable @typescript-eslint/no-explicit-any */

function selectionOfGraphicalNote(osmd: OpenSheetMusicDisplay, gn: any): Selection | null {
  const sn = gn?.sourceNote
  if (!sn || sn.isRest()) return null
  const voice = sn.ParentVoiceEntry?.ParentVoice
  if (!voice) return null
  const instruments = (osmd as any).Sheet?.Instruments ?? []
  const instrIdx = instruments.indexOf(voice.Parent)
  const name = VOICE_BY_INSTRUMENT_AND_ID[`${instrIdx}:${voice.VoiceId}`]
  if (!name) return null
  const onset = Math.round(sn.getAbsoluteTimestamp().RealValue * TICKS_PER_WHOLE)
  return { voice: name, onset }
}

function* graphicalNotes(osmd: OpenSheetMusicDisplay): Generator<any> {
  const measureList = (osmd as any).GraphicSheet?.MeasureList ?? []
  for (const measureRow of measureList) {
    for (const measure of measureRow ?? []) {
      for (const staffEntry of measure?.staffEntries ?? []) {
        for (const voiceEntry of staffEntry?.graphicalVoiceEntries ?? []) {
          for (const note of voiceEntry?.notes ?? []) {
            yield note
          }
        }
      }
    }
  }
}

function findGraphicalNote(osmd: OpenSheetMusicDisplay, sel: Selection): any | null {
  for (const gn of graphicalNotes(osmd)) {
    const got = selectionOfGraphicalNote(osmd, gn)
    if (got && got.voice === sel.voice && got.onset === sel.onset) return gn
  }
  return null
}

function paintNote(gn: any, color: string | null) {
  const el: SVGGElement | undefined = gn?.getSVGGElement?.()
  if (!el) return
  for (const p of el.querySelectorAll('path, rect, ellipse')) {
    const shape = p as SVGElement
    if (color) {
      shape.style.fill = color
      shape.style.stroke = color
    } else {
      shape.style.fill = ''
      shape.style.stroke = ''
    }
  }
}

const DURATION_KEYS: Record<string, number> = {
  '3': 120,
  '4': 240,
  '5': 480,
  '6': 960,
  '7': 1920,
}

export function ScoreView() {
  const containerRef = useRef<HTMLDivElement>(null)
  const osmdRef = useRef<OpenSheetMusicDisplay | null>(null)
  const lastTickRef = useRef<number>(-1)
  const highlightedRef = useRef<any | null>(null)
  const [renderEpoch, setRenderEpoch] = useState(0)

  const musicxml = useStore((s) => s.arrangement?.musicxml ?? null)
  const currentTick = useStore((s) => s.currentTick)
  const selected = useStore((s) => s.selected)
  const stage = useStore((s) => s.stage)
  const { setStage, selectNote, nudgePitch, setDuration, deleteSelected, undo, redo } = useStore()

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
        highlightedRef.current = null
        setRenderEpoch((n) => n + 1)
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

  // selection highlight (re-applied after each render)
  useEffect(() => {
    const osmd = osmdRef.current
    if (!osmd) return
    if (highlightedRef.current) {
      paintNote(highlightedRef.current, null)
      highlightedRef.current = null
    }
    if (selected) {
      const gn = findGraphicalNote(osmd, selected)
      if (gn) {
        paintNote(gn, '#a8262a')
        highlightedRef.current = gn
      }
    }
  }, [selected, renderEpoch])

  // click -> select nearest note
  useEffect(() => {
    const container = containerRef.current
    const osmd = osmdRef.current
    if (!container || !osmd) return
    const onClick = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      const zoom = (osmd as any).zoom ?? 1
      const x = (e.clientX - rect.left) / 10 / zoom
      const y = (e.clientY - rect.top) / 10 / zoom
      const sheet = (osmd as any).GraphicSheet
      const gn = sheet?.GetNearestNote?.(new PointF2D(x, y), new PointF2D(5, 5))
      selectNote(gn ? selectionOfGraphicalNote(osmd, gn) : null)
    }
    container.addEventListener('click', onClick)
    return () => container.removeEventListener('click', onClick)
  }, [selectNote, renderEpoch])

  // keyboard editing
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        void (e.shiftKey ? redo() : undo())
        return
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault()
        void redo()
        return
      }
      if (!useStore.getState().selected) return
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault()
        const step = (e.key === 'ArrowUp' ? 1 : -1) * (e.shiftKey ? 12 : 1)
        void nudgePitch(step)
      } else if (e.key in DURATION_KEYS) {
        e.preventDefault()
        void setDuration(DURATION_KEYS[e.key])
      } else if (e.key === '.') {
        e.preventDefault()
        const state = useStore.getState()
        const sel = state.selected
        const note = sel
          ? state.arrangement?.score.voices[sel.voice].find((n) => n.onset === sel.onset)
          : null
        if (note) void setDuration(Math.round(note.duration * 1.5))
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault()
        void deleteSelected()
      } else if (e.key === 'Escape') {
        selectNote(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [nudgePitch, setDuration, deleteSelected, undo, redo, selectNote])

  // moving playback cursor
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

  return (
    <div>
      {stage === 'ready' && (
        <p className="edit-hint">
          Click a note to select · ↑↓ pitch (⇧ = octave) · 3–7 duration · «.» dot · Del remove ·
          Ctrl-Z undo
        </p>
      )}
      <div className="score-sheet" data-empty={musicxml === null} ref={containerRef} />
    </div>
  )
}
