import { Link } from 'react-router-dom'
import { BarChart2, Zap, Bot, TrendingUp, Check, ChevronRight } from 'lucide-react'

const PILLARS = [
  {
    icon: TrendingUp,
    title: 'Gap Fill Engine',
    subtitle: 'Statistical truth on 10+ years',
    desc: 'Master fill rate tables by opening location, gap size, VIX regime, and time-of-day. Probability calculator with sample sizes for every filter combination.',
    color: '#10D982',
  },
  {
    icon: BarChart2,
    title: 'A Period Analytics',
    subtitle: 'Dalton/Steidlmayer in real-time',
    desc: '7-type A Period classification (Open-Drive, Open-Auction, Rejection-Reverse…) plus live day-type probability model updating every 5 minutes from 09:30–10:00 ET.',
    color: '#4D9FFF',
  },
  {
    icon: Zap,
    title: 'Dealer GEX Intelligence',
    subtitle: 'Call Wall · Put Wall · Zero Gamma',
    desc: 'Black-Scholes GEX computed from live SPY options chain. Long vs Short Gamma regime classification tells you whether dealers are suppressing or amplifying volatility right now.',
    color: '#FFB800',
  },
  {
    icon: Bot,
    title: 'ATLAS AI Copilot',
    subtitle: 'Claude-powered · Zero hallucination',
    desc: 'Daily pre-market briefing synthesizing all four pillars. Live intraday alerts at key levels. Ad-hoc chat backed entirely by computed statistics — no invented numbers.',
    color: '#A855F7',
  },
]

const TIERS = [
  {
    name: 'Free',
    price: '$0',
    period: '',
    features: ['Live ES price + gap status', '1-year gap statistics', 'Daily P/C ratio', '1 AI alert per day'],
    cta: 'Get Started',
    highlight: false,
  },
  {
    name: 'Pro',
    price: '$99',
    period: '/mo',
    features: [
      '10+ year gap history',
      'Full A Period tracker + day-type model',
      'Live GEX dashboard',
      '50 AI alerts per day',
      'Daily pre-market briefing',
      'Probability calculator',
      'CSV export',
    ],
    cta: 'Start Pro Trial',
    highlight: true,
  },
  {
    name: 'Elite',
    price: '$299',
    period: '/mo',
    features: [
      'Everything in Pro',
      'Unlimited AI alerts',
      'Atlas chat unlimited queries',
      'Webhook alerts (Discord/Telegram)',
      'API access',
      'Priority 5-min options refresh',
      'Custom alert rules',
    ],
    cta: 'Go Elite',
    highlight: false,
  },
]

const FAQS = [
  { q: 'Is this financial advice?', a: 'No. ATLAS is an educational and research platform providing statistical context and AI-powered analysis. It does not provide trade recommendations, signals, or investment advice. All trading decisions are solely your responsibility.' },
  { q: 'What data sources do you use?', a: 'All data comes from free public APIs: Yahoo Finance (price data), CBOE public files (P/C ratio), CFTC public API (COT), FRED API (macro), and Yahoo/Tradier sandbox (options). No paid data subscriptions required.' },
  { q: 'How accurate are the gap fill statistics?', a: 'Statistics are computed from 10+ years of ES futures daily and intraday data using precise gap fill definitions (Gap Up filled only if Day Low ≤ Prior Close). Every statistic displays its sample size (N=) and confidence level so you can judge reliability yourself.' },
  { q: 'What is GEX and why does it matter for ES traders?', a: 'Gamma Exposure (GEX) measures how much SPY/SPX options dealers must buy or sell as price moves to stay delta-neutral. Since ES tracks SPX, dealer hedging flows directly move ES intraday — sometimes more than fundamentals. Knowing the regime (Long Gamma = suppressed vol, Short Gamma = amplified vol) gives traders a structural edge.' },
  { q: 'Can I cancel anytime?', a: 'Yes. All subscriptions are monthly and can be cancelled at any time from your account settings with no fees.' },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-bg text-text-primary">
      {/* Navbar */}
      <nav className="border-b border-border px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue flex items-center justify-center text-bg font-bold text-sm">A</div>
          <span className="font-semibold text-lg tracking-tight">ATLAS</span>
        </div>
        <div className="flex items-center gap-4">
          <a href="#pricing" className="text-sm text-text-secondary hover:text-text-primary transition-colors">Pricing</a>
          <Link
            to="/live"
            className="flex items-center gap-1.5 bg-blue text-bg text-sm font-semibold px-4 py-2 rounded-xl hover:bg-blue/90 transition-colors"
          >
            Launch App <ChevronRight size={14} />
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-6 py-20 text-center max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 bg-surface border border-border rounded-full px-4 py-1.5 text-xs text-text-secondary mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-bull live-indicator" />
          Free tier available · No credit card required
        </div>
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight leading-tight mb-6">
          The Bloomberg Terminal
          <br />
          <span className="text-blue">for ES Futures Day Traders</span>
        </h1>
        <p className="text-lg text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed">
          Institutional-grade gap statistics, market profile analytics, dealer gamma intelligence, and an AI trading
          copilot — in one platform. Built on free data. Priced for serious traders.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to="/live"
            className="bg-blue text-bg font-semibold px-8 py-3.5 rounded-2xl text-base hover:bg-blue/90 transition-colors"
          >
            Open ATLAS Free →
          </Link>
          <a
            href="#pricing"
            className="border border-border text-text-primary font-medium px-8 py-3.5 rounded-2xl text-base hover:border-blue transition-colors"
          >
            View Pricing
          </a>
        </div>

        {/* Metrics strip */}
        <div className="flex flex-wrap justify-center gap-6 mt-14 text-center">
          {[
            { val: '10+', label: 'Years of ES History' },
            { val: '7', label: 'A Period Types' },
            { val: 'Live', label: 'GEX Regime' },
            { val: 'AI', label: 'Pre-Market Briefing' },
          ].map(({ val, label }) => (
            <div key={label}>
              <div className="text-3xl font-mono font-bold text-blue">{val}</div>
              <div className="text-xs text-text-secondary mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Four Pillars */}
      <section className="px-6 py-16 max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold text-center mb-2">Four Analytical Pillars. One Platform.</h2>
        <p className="text-text-secondary text-center text-sm mb-10">
          Every feature is built on verifiable statistics, not opinions.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {PILLARS.map(({ icon: Icon, title, subtitle, desc, color }) => (
            <div key={title} className="atlas-card hover:border-blue/40 transition-colors">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: `${color}20`, border: `1px solid ${color}40` }}>
                  <Icon size={18} style={{ color }} />
                </div>
                <div>
                  <h3 className="font-semibold text-text-primary">{title}</h3>
                  <p className="text-xs font-mono mb-2" style={{ color }}>{subtitle}</p>
                  <p className="text-sm text-text-secondary leading-relaxed">{desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="px-6 py-16 max-w-5xl mx-auto">
        <h2 className="text-2xl font-bold text-center mb-2">Simple, Transparent Pricing</h2>
        <p className="text-text-secondary text-center text-sm mb-10">Cancel anytime. No contracts.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`rounded-2xl p-6 border transition-colors ${
                tier.highlight
                  ? 'border-blue bg-blue/5'
                  : 'border-border bg-surface'
              }`}
            >
              {tier.highlight && (
                <div className="text-[10px] uppercase tracking-widest text-blue font-semibold mb-3">Most Popular</div>
              )}
              <div className="mb-4">
                <span className="text-sm text-text-secondary">{tier.name}</span>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-3xl font-mono font-bold text-text-primary">{tier.price}</span>
                  <span className="text-text-secondary text-sm">{tier.period}</span>
                </div>
              </div>
              <ul className="space-y-2 mb-6">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-text-secondary">
                    <Check size={14} className="text-bull mt-0.5 flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                to="/live"
                className={`block text-center py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                  tier.highlight
                    ? 'bg-blue text-bg hover:bg-blue/90'
                    : 'border border-border text-text-primary hover:border-blue'
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="px-6 py-16 max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-center mb-10">Frequently Asked Questions</h2>
        <div className="space-y-4">
          {FAQS.map(({ q, a }) => (
            <details key={q} className="atlas-card group">
              <summary className="cursor-pointer text-sm font-medium text-text-primary list-none flex justify-between items-center">
                {q}
                <ChevronRight size={16} className="text-text-secondary group-open:rotate-90 transition-transform" />
              </summary>
              <p className="mt-3 text-sm text-text-secondary leading-relaxed">{a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* Compliance Footer */}
      <footer className="border-t border-border px-6 py-10 max-w-6xl mx-auto">
        <div className="rounded-2xl bg-surface border border-border p-4 mb-6">
          <p className="text-[10px] text-text-secondary leading-relaxed">
            ⚠️ ATLAS provides educational and research data only. All statistics are derived from historical free-tier
            data sources and are not guarantees of future performance. Market Profile classifications are algorithmic
            approximations. GEX and dealer positioning estimates are based on publicly available options data and may
            not reflect actual dealer books. AI-generated commentary is contextual analysis, not financial advice.
            ATLAS does not provide trade recommendations, brokerage services, or investment advice. Trade futures only
            with risk capital. Past performance does not guarantee future results. By using ATLAS, you acknowledge
            full responsibility for your trading decisions. © 2026 ATLAS Intelligence.
          </p>
        </div>
        <div className="flex flex-wrap justify-between items-center gap-4 text-xs text-text-secondary">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-blue/20 flex items-center justify-center text-blue text-xs font-bold">A</div>
            <span>ATLAS Intelligence</span>
          </div>
          <div className="flex gap-4">
            <a href="#" className="hover:text-text-primary transition-colors">Terms</a>
            <a href="#" className="hover:text-text-primary transition-colors">Privacy</a>
            <a href="#" className="hover:text-text-primary transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
