import { useEffect } from 'react'
import { ScoreView } from './ScoreView'
import { TransportBar } from './TransportBar'
import { useStore } from './store'

const SPICE_LABELS: Record<number, string> = {
  1: 'faithful',
  2: 'gentle',
  3: 'classic',
  4: 'adventurous',
  5: 'contest showpiece',
}

const STAGE_COPY: Record<string, string> = {
  idle: 'Select a number from the programme to begin.',
  arranging: 'Arranging four parts…',
  rendering: 'Engraving the score…',
  ready: '',
  error: 'Something went wrong.',
}

export default function App() {
  const { demos, selectedDemo, spice, stage, error, arrangement } = useStore()
  const { loadDemos, setSpice, arrange } = useStore()

  useEffect(() => {
    void loadDemos()
  }, [loadDemos])

  return (
    <div className="hall">
      <header className="marquee">
        <h1>Barbershopify</h1>
        <p className="tagline">Four-part harmony, freshly lathered</p>
        <div className="pole-stripe" aria-hidden="true" />
      </header>

      <div className="floor">
        <aside className="programme">
          <h2>Programme</h2>
          <ul className="bill">
            {demos.map((d) => (
              <li key={d.id}>
                <button
                  className={d.id === selectedDemo ? 'act selected' : 'act'}
                  onClick={() => void arrange(d.id)}
                >
                  {d.title}
                </button>
              </li>
            ))}
          </ul>

          <h2>Spice</h2>
          <div className="spice-control">
            <input
              type="range"
              min={1}
              max={5}
              step={1}
              value={spice}
              onChange={(e) => setSpice(Number(e.target.value))}
              aria-label="Spice level"
            />
            <div className="spice-readout">
              <span className="spice-number">{spice}</span>
              <span className="spice-label">{SPICE_LABELS[spice]}</span>
            </div>
          </div>
          <button
            className="rearrange"
            disabled={!selectedDemo || stage === 'arranging'}
            onClick={() => void arrange()}
          >
            Re-arrange
          </button>

          {arrangement && stage === 'ready' && (
            <dl className="fine-print">
              <dt>Dominant 7th share</dt>
              <dd>{Math.round(arrangement.metrics.dom7_family_share * 100)}%</dd>
              <dt>Bass on root/5th</dt>
              <dd>{Math.round(arrangement.metrics.bass_root_fifth_share * 100)}%</dd>
              <dt>Final chord rings</dt>
              <dd>{arrangement.metrics.final_chord_ring ? 'yes' : 'no'}</dd>
              <dt>Legality</dt>
              <dd>
                {arrangement.violations.length === 0
                  ? 'clean'
                  : `${arrangement.violations.length} violations`}
              </dd>
            </dl>
          )}
        </aside>

        <main className="stage">
          {stage !== 'ready' && (
            <p className={stage === 'error' ? 'status error' : 'status'}>
              {stage === 'error' && error ? `${STAGE_COPY.error} ${error}` : STAGE_COPY[stage]}
            </p>
          )}
          <TransportBar />
          <ScoreView />
        </main>
      </div>
    </div>
  )
}
