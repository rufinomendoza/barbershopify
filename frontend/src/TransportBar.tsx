import { useStore } from './store'
import { VOICE_ORDER } from './playback/engine'

const VOICE_LABELS: Record<string, string> = {
  tenor: 'Tenor',
  lead: 'Lead',
  bari: 'Bari',
  bass: 'Bass',
}

export function TransportBar() {
  const { playing, tempoBpm, voiceSettings, stage } = useStore()
  const { play, pause, stop, setTempo, toggleMute, toggleSolo, setVolume } = useStore()

  if (stage !== 'ready') return null

  return (
    <div className="transport">
      <div className="transport-buttons">
        <button
          className="transport-btn"
          aria-label={playing ? 'Pause' : 'Play'}
          onClick={() => void (playing ? pause() : play())}
        >
          {playing ? '❚❚' : '▶'}
        </button>
        <button className="transport-btn" aria-label="Stop" onClick={stop}>
          ■
        </button>
      </div>

      <label className="tempo">
        <span className="tempo-label">♩ = {Math.round(tempoBpm)}</span>
        <input
          type="range"
          min={50}
          max={180}
          value={tempoBpm}
          onChange={(e) => setTempo(Number(e.target.value))}
          aria-label="Tempo"
        />
      </label>

      <div className="mixer">
        {VOICE_ORDER.map((voice) => {
          const s = voiceSettings[voice]
          return (
            <div className="strip" key={voice}>
              <span className="strip-name">{VOICE_LABELS[voice]}</span>
              <span className="strip-buttons">
                <button
                  className={s.mute ? 'chip active' : 'chip'}
                  title={`Mute ${voice}`}
                  onClick={() => toggleMute(voice)}
                >
                  M
                </button>
                <button
                  className={s.solo ? 'chip active solo' : 'chip'}
                  title={`Solo ${voice}`}
                  onClick={() => toggleSolo(voice)}
                >
                  S
                </button>
              </span>
              <input
                type="range"
                min={-30}
                max={0}
                value={s.volume}
                onChange={(e) => setVolume(voice, Number(e.target.value))}
                aria-label={`${voice} volume`}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
