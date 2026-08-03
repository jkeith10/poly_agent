"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Market = {
  id: string;
  question: string;
  description: string;
  yes_price: string;
  no_price: string;
  liquidity: string;
  volume: string;
  closes_at: string | null;
};

type Recommendation = {
  prediction_id: string;
  question: string;
  action: string;
  market_probability: string;
  oracle_probability: string;
  expected_value: string;
  suggested_position: string;
};

const apiUrl = process.env.NEXT_PUBLIC_ORACLE_API_URL ?? "http://localhost:8000";

function percentage(value: string): string {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

export default function Home() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMarkets = useCallback(async () => {
    setLoading(true);
    try {
      const [marketResponse, recommendationResponse] = await Promise.all([
        fetch(`${apiUrl}/api/v1/markets?limit=100`, { cache: "no-store" }),
        fetch(`${apiUrl}/api/v1/recommendations?limit=20`, { cache: "no-store" }),
      ]);
      if (!marketResponse.ok) throw new Error(`API returned ${marketResponse.status}`);
      if (!recommendationResponse.ok) {
        throw new Error(`Recommendation API returned ${recommendationResponse.status}`);
      }
      setMarkets((await marketResponse.json()) as Market[]);
      setRecommendations((await recommendationResponse.json()) as Recommendation[]);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load markets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => void loadMarkets(), [loadMarkets]);

  async function scanMarkets() {
    setScanning(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/markets/scan`, { method: "POST" });
      if (!response.ok) throw new Error(`Scan failed with ${response.status}`);
      await loadMarkets();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to scan markets");
    } finally {
      setScanning(false);
    }
  }

  const totalLiquidity = useMemo(
    () => markets.reduce((total, market) => total + Number(market.liquidity), 0),
    [markets],
  );

  return (
    <>
      <header>
        <div>
          <p className="eyebrow">PREDICTION MARKET INTELLIGENCE</p>
          <h1>Decision edge, quantified.</h1>
          <p className="subtitle">Bayesian research and disciplined position sizing—not certainty.</p>
        </div>
        <button disabled={scanning} onClick={scanMarkets}>
          {scanning ? "Scanning…" : "Scan markets"}
        </button>
      </header>
      {error && <div className="error" role="alert">{error}</div>}
      <section className="metrics">
        <article><label>Positive EV analyses</label><strong>{loading ? "—" : recommendations.length}</strong><small>Latest persisted recommendations</small></article>
        <article><label>Visible liquidity</label><strong className="green">${totalLiquidity.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong><small>Across loaded markets</small></article>
        <article><label>Forecast Brier score</label><strong>—</strong><small>Available after resolutions</small></article>
        <article><label>Data connection</label><strong>{error ? "Offline" : "Live"}</strong><small>{error ? "Retry or check API" : "Backed by ORACLE API"}</small></article>
      </section>
      <section id="markets" className="panel">
        <div className="panelHead"><div><p className="eyebrow">MARKET RADAR</p><h2>Active markets</h2></div><span className="live">● {error ? "DISCONNECTED" : "LIVE"}</span></div>
        <div className="table">
          <div className="row headings"><span>Market</span><span>YES</span><span>NO</span><span>Liquidity</span><span>Volume</span><span>Closes</span></div>
          {!loading && markets.length === 0 && <p className="empty">No markets are stored. Run a scan to begin ingestion.</p>}
          {markets.map((market) => (
            <div className="row" key={market.id}>
              <span><b>{market.question}</b><small>{market.description.slice(0, 100)}</small></span>
              <span className="oracle">{percentage(market.yes_price)}</span>
              <span>{percentage(market.no_price)}</span>
              <span>${Number(market.liquidity).toLocaleString()}</span>
              <span>${Number(market.volume).toLocaleString()}</span>
              <span>{market.closes_at ? new Date(market.closes_at).toLocaleDateString() : "Open"}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="panel recommendations">
        <div className="panelHead"><div><p className="eyebrow">ORACLE ANALYSIS</p><h2>Positive expected value</h2></div></div>
        {!loading && recommendations.length === 0 && <p className="empty">No positive-EV analyses have been persisted yet.</p>}
        {recommendations.map((item) => (
          <div className="row" key={item.prediction_id}>
            <span><b>{item.question}</b><small>{item.action}</small></span>
            <span>{percentage(item.market_probability)}</span>
            <span className="oracle">{percentage(item.oracle_probability)}</span>
            <span className="green">{percentage(item.expected_value)} EV</span>
            <span>${Number(item.suggested_position).toLocaleString()}</span>
            <span>Audited</span>
          </div>
        ))}
      </section>
      <section className="lower">
        <article id="portfolio" className="panel"><p className="eyebrow">PORTFOLIO</p><h2>Risk at a glance</h2><p className="subtitle">Portfolio metrics appear after positions are recorded. ORACLE never fabricates performance history.</p></article>
        <article id="research" className="panel"><p className="eyebrow">MODEL DISCIPLINE</p><h2>Evidence quality</h2><p className="subtitle">Every analysis request requires explicit citations and returns a persisted, reproducible recommendation.</p></article>
      </section>
      <footer>ORACLE provides probabilistic decision support. It does not guarantee outcomes or execute trades.</footer>
    </>
  );
}
