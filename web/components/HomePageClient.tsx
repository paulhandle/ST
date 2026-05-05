'use client'

import Link from 'next/link'
import type { ReactNode } from 'react'
import BrandLogo from '@/components/BrandLogo'
import LanguageToggle from '@/components/LanguageToggle'
import { useI18n } from '@/lib/i18n/I18nProvider'

const WEEK_DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
const WEEK_BLOCKS = [46, 22, 58, 74, 18, 88, 54]

const COPY = {
  en: {
    navWorkflow: 'Workflow',
    navMethodology: 'Methodology',
    navEvidence: 'Evidence',
    login: 'Login',
    heroKicker: 'Endurance Performance System',
    heroText: 'Precision instrumentation for endurance training execution, integrating device history, methodology, recovery signals, and weekly adjustments into one cycle.',
    start: 'Start Training',
    viewMethodology: 'View Methodology',
    evidenceKicker: 'Data-Driven Execution',
    evidenceTitle: 'Total accountability from plan to completed work.',
    historyFirst: 'History First',
    executableCycle: 'Executable Cycle',
    adaptiveControl: 'Adaptive Control',
    phaseBase: 'Base Building',
    phasePrep: 'Specific Prep',
    phaseTaper: 'Taper',
    workflowKicker: 'Closed Loop',
    workflowTitle: 'One workflow from COROS import to weekly plan adjustment.',
    methodologyKicker: 'Methodology Layer',
    methodologyTitle: 'Training skills stay coherent across the entire cycle.',
    methodologyText: 'Built-in and extracted skills define the rules, safety constraints, and workout vocabulary. The platform handles data, sync, execution tracking, and adjustment mechanics.',
    finalTitle: 'Build your next training cycle.',
    footer: 'Precision instrumentation for human performance.',
    dashboard: 'Dashboard Overview',
    sync: 'COROS Sync Active',
    readiness: 'Readiness Score',
    volume: 'Training Volume 7D',
    schedule: 'Weekly Schedule',
    workflowSteps: [
      ['01', 'Connect COROS', 'Import history, training load, predictions, and readiness signals.'],
      ['02', 'Assess Fitness', 'Convert raw data into current capability and safe training bounds.'],
      ['03', 'Choose Skill', 'Generate the cycle from a coherent methodology, not a random workout mix.'],
      ['04', 'Execute + Adapt', 'Sync workouts, compare completion, and adjust the future plan.'],
    ],
  },
  zh: {
    navWorkflow: '流程',
    navMethodology: '方法论',
    navEvidence: '证据',
    login: '登录',
    heroKicker: '耐力表现系统',
    heroText: '把设备历史、训练方法、恢复信号和每周调整整合到一个可执行训练周期里。',
    start: '开始训练',
    viewMethodology: '查看方法论',
    evidenceKicker: '数据驱动执行',
    evidenceTitle: '从计划到完成训练，每一步都有记录和反馈。',
    historyFirst: '历史优先',
    executableCycle: '可执行周期',
    adaptiveControl: '动态控制',
    phaseBase: '基础建设',
    phasePrep: '专项准备',
    phaseTaper: '减量调整',
    workflowKicker: '闭环流程',
    workflowTitle: '从 COROS 导入到每周计划调整，一条完整链路。',
    methodologyKicker: '方法论层',
    methodologyTitle: '训练 skill 在整个周期内保持一致。',
    methodologyText: '内置和提取的 skill 定义规则、安全约束和训练词汇；平台负责数据、同步、执行追踪和调整机制。',
    finalTitle: '创建你的下一个训练周期。',
    footer: '面向运动表现的精密训练系统。',
    dashboard: '仪表盘概览',
    sync: 'COROS 同步已连接',
    readiness: '准备度评分',
    volume: '7 日训练量',
    schedule: '每周安排',
    workflowSteps: [
      ['01', '连接 COROS', '导入历史、训练负荷、预测和恢复信号。'],
      ['02', '评估能力', '把原始数据转成当前能力和安全训练边界。'],
      ['03', '选择 Skill', '用一致的方法论生成周期，不随机混合训练。'],
      ['04', '执行 + 调整', '同步训练、对比完成情况，并调整未来计划。'],
    ],
  },
}

export default function HomePageClient() {
  const { language, setLanguage } = useI18n()
  const t = COPY[language]

  return (
    <main className="homepage">
      <header className="home-nav">
        <BrandLogo href="/" />
        <nav className="home-nav-links" aria-label="Homepage navigation">
          <a href="#workflow">{t.navWorkflow}</a>
          <a href="#methodology">{t.navMethodology}</a>
          <a href="#evidence">{t.navEvidence}</a>
        </nav>
        <div className="home-nav-actions">
          <LanguageToggle language={language} onChange={setLanguage} />
          <Link href="/login" className="home-login">{t.login}</Link>
        </div>
      </header>

      <section className="home-hero">
        <div className="home-hero-copy">
          <div className="home-kicker">{t.heroKicker}</div>
          <h1>PerformanceProtocol</h1>
          <p>{t.heroText}</p>
          <div className="home-actions">
            <Link href="/login" className="home-button home-button-primary">
              {t.start}
            </Link>
            <a href="#methodology" className="home-button home-button-ghost">
              {t.viewMethodology}
            </a>
          </div>
        </div>

        <ProductPreview copy={t} />
      </section>

      <section id="evidence" className="home-section">
        <div className="home-section-heading">
          <div className="home-kicker">{t.evidenceKicker}</div>
          <h2>{t.evidenceTitle}</h2>
        </div>
        <div className="home-bento">
          <DataPanel title={t.historyFirst} className="home-panel-bars">
            <div className="home-bars" aria-label="Training history bars">
              {[34, 52, 43, 70, 86].map((h, index) => (
                <span key={index} style={{ height: `${h}%` }} />
              ))}
            </div>
          </DataPanel>

          <DataPanel title={t.executableCycle} className="home-panel-cycle">
            <div className="phase-row">
              <span>Phase 01</span>
              <strong>{t.phaseBase}</strong>
            </div>
            <div className="phase-row active">
              <span>Phase 02</span>
              <strong>{t.phasePrep}</strong>
            </div>
            <div className="phase-row">
              <span>Phase 03</span>
              <strong>{t.phaseTaper}</strong>
            </div>
          </DataPanel>

          <DataPanel title={t.adaptiveControl} className="home-panel-score">
            <div className="score-ring">
              <span>92%</span>
            </div>
          </DataPanel>
        </div>
      </section>

      <section id="workflow" className="home-section">
        <div className="home-section-heading">
          <div className="home-kicker">{t.workflowKicker}</div>
          <h2>{t.workflowTitle}</h2>
        </div>
        <div className="workflow-grid">
          {t.workflowSteps.map(([index, title, text]) => (
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
          <div className="home-kicker">{t.methodologyKicker}</div>
          <h2>{t.methodologyTitle}</h2>
        </div>
        <p>{t.methodologyText}</p>
      </section>

      <section className="home-final">
        <h2>{t.finalTitle}</h2>
        <Link href="/login" className="home-button home-button-primary">
          {t.start}
        </Link>
      </section>

      <footer className="home-footer">
        <BrandLogo compact />
        <span>{t.footer}</span>
      </footer>
    </main>
  )
}

function ProductPreview({ copy }: { copy: typeof COPY.en }) {
  return (
    <div className="product-preview" aria-label="Product dashboard preview">
      <div className="preview-header">
        <span>{copy.dashboard}</span>
        <span className="sync-state">
          <i />
          {copy.sync}
        </span>
      </div>

      <div className="preview-metrics">
        <MetricCard label={copy.readiness} value="84" unit="Optimal" accent="blue" />
        <MetricCard label={copy.volume} value="12.4" unit="hrs" />
      </div>

      <div className="schedule-panel">
        <div className="panel-label">{copy.schedule}</div>
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
