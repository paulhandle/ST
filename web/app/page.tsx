import Link from 'next/link'
import type { ReactNode } from 'react'
import BrandLogo from '@/components/BrandLogo'

const WEEK_DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
const WEEK_BLOCKS = [46, 22, 58, 74, 18, 88, 54]

export default function HomePage() {
  return (
    <main className="homepage">
      <header className="home-nav">
        <BrandLogo href="/" />
        <nav className="home-nav-links" aria-label="Homepage navigation">
          <a href="#workflow">Workflow</a>
          <a href="#methodology">Methodology</a>
          <a href="#evidence">Evidence</a>
        </nav>
        <Link href="/login" className="home-login">Login</Link>
      </header>

      <section className="home-hero">
        <div className="home-hero-copy">
          <div className="home-kicker">Endurance Performance System</div>
          <h1>PerformanceProtocol</h1>
          <p>
            Precision instrumentation for endurance training execution, integrating device
            history, methodology, recovery signals, and weekly adjustments into one cycle.
          </p>
          <div className="home-actions">
            <Link href="/login" className="home-button home-button-primary">
              Start Training
            </Link>
            <a href="#methodology" className="home-button home-button-ghost">
              View Methodology
            </a>
          </div>
        </div>

        <ProductPreview />
      </section>

      <section id="evidence" className="home-section">
        <div className="home-section-heading">
          <div className="home-kicker">Data-Driven Execution</div>
          <h2>Total accountability from plan to completed work.</h2>
        </div>
        <div className="home-bento">
          <DataPanel title="History First" className="home-panel-bars">
            <div className="home-bars" aria-label="Training history bars">
              {[34, 52, 43, 70, 86].map((h, index) => (
                <span key={index} style={{ height: `${h}%` }} />
              ))}
            </div>
          </DataPanel>

          <DataPanel title="Executable Cycle" className="home-panel-cycle">
            <div className="phase-row">
              <span>Phase 01</span>
              <strong>Base Building</strong>
            </div>
            <div className="phase-row active">
              <span>Phase 02</span>
              <strong>Specific Prep</strong>
            </div>
            <div className="phase-row">
              <span>Phase 03</span>
              <strong>Taper</strong>
            </div>
          </DataPanel>

          <DataPanel title="Adaptive Control" className="home-panel-score">
            <div className="score-ring">
              <span>92%</span>
            </div>
          </DataPanel>
        </div>
      </section>

      <section id="workflow" className="home-section">
        <div className="home-section-heading">
          <div className="home-kicker">Closed Loop</div>
          <h2>One workflow from COROS import to weekly plan adjustment.</h2>
        </div>
        <div className="workflow-grid">
          {[
            ['01', 'Connect COROS', 'Import history, training load, predictions, and readiness signals.'],
            ['02', 'Assess Fitness', 'Convert raw data into current capability and safe training bounds.'],
            ['03', 'Choose Skill', 'Generate the cycle from a coherent methodology, not a random workout mix.'],
            ['04', 'Execute + Adapt', 'Sync workouts, compare completion, and adjust the future plan.'],
          ].map(([index, title, text]) => (
            <div className="workflow-step" key={index}>
              <span>{index}</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="methodology" className="home-methodology">
        <div>
          <div className="home-kicker">Methodology Layer</div>
          <h2>Training skills stay coherent across the entire cycle.</h2>
        </div>
        <p>
          Built-in and extracted skills define the rules, safety constraints, and workout vocabulary.
          The platform handles data, sync, execution tracking, and adjustment mechanics.
        </p>
      </section>

      <section className="home-final">
        <h2>Build your next training cycle.</h2>
        <Link href="/login" className="home-button home-button-primary">
          Get Started
        </Link>
      </section>

      <footer className="home-footer">
        <BrandLogo compact />
        <span>Precision instrumentation for human performance.</span>
      </footer>
    </main>
  )
}

function ProductPreview() {
  return (
    <div className="product-preview" aria-label="Product dashboard preview">
      <div className="preview-header">
        <span>Dashboard Overview</span>
        <span className="sync-state">
          <i />
          COROS Sync Active
        </span>
      </div>

      <div className="preview-metrics">
        <MetricCard label="Readiness Score" value="84" unit="Optimal" accent="blue" />
        <MetricCard label="Training Volume 7D" value="12.4" unit="hrs" />
      </div>

      <div className="schedule-panel">
        <div className="panel-label">Weekly Schedule</div>
        <div className="week-grid">
          {WEEK_DAYS.map((day, index) => (
            <span key={`${day}-${index}`} className={index === 3 ? 'active' : ''}>{day}</span>
          ))}
          {WEEK_BLOCKS.map((height, index) => (
            <div key={index} className={index === 3 ? 'today' : ''}>
              <i style={{ height: `${height}%` }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, unit, accent }: { label: string; value: string; unit: string; accent?: 'blue' }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <div>
        <strong>{value}</strong>
        <em className={accent === 'blue' ? 'blue' : ''}>{unit}</em>
      </div>
    </div>
  )
}

function DataPanel({ title, className, children }: { title: string; className?: string; children: ReactNode }) {
  return (
    <div className={`home-data-panel${className ? ` ${className}` : ''}`}>
      <div className="panel-label">{title}</div>
      {children}
    </div>
  )
}
