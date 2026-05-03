export function ComplianceFooter() {
  return (
    <footer className="mt-8 pt-4 border-t border-border">
      <div className="rounded-2xl bg-surface border border-border/60 p-4 mb-4">
        <p className="text-[10px] text-text-secondary leading-relaxed">
          ⚠️ <strong className="text-text-primary">ATLAS provides educational and research data only.</strong> All
          statistics are derived from historical free-tier data sources and are not guarantees of future performance.
          Market Profile classifications are algorithmic approximations. GEX and dealer positioning estimates are based
          on publicly available options data and may not reflect actual dealer books. AI-generated commentary is
          contextual analysis, not financial advice. ATLAS does not provide trade recommendations, brokerage services,
          or investment advice. Trade futures only with risk capital. Past performance does not guarantee future
          results. By using ATLAS, you acknowledge full responsibility for your trading decisions.
        </p>
        <p className="text-[10px] text-text-secondary mt-2">
          Data sources: Yahoo Finance, CBOE (public), CFTC (public), FRED (Federal Reserve). © 2026 ATLAS Intelligence.
        </p>
      </div>
    </footer>
  )
}
