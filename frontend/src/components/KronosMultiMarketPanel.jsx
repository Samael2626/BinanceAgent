import { useEffect, useState } from 'react'
import './KronosMultiMarketPanel.css'

const money = (value) => value == null ? 'Valoración no disponible' : `${Number(value).toFixed(4)} USDT`
const percent = (value) => value == null ? 'No disponible' : `${Number(value).toFixed(5)} %`

function usePolling(path, token, intervalMs) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  useEffect(() => {
    const controller = new AbortController()
    let busy = false
    const load = async () => {
      if (busy) return
      busy = true
      try {
        const response = await fetch(path, { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json()
        if (!controller.signal.aborted) setState({ data, loading: false, error: null })
      } catch (error) {
        if (!controller.signal.aborted) setState(previous => ({ ...previous, loading: false, error: 'Conexión temporalmente perdida' }))
      } finally { busy = false }
    }
    load()
    const timer = setInterval(load, intervalMs)
    return () => { controller.abort(); clearInterval(timer) }
  }, [path, token, intervalMs])
  return state
}

export default function KronosMultiMarketPanel({ token }) {
  const report = usePolling('/api/paper/futures/report', token, 10000)
  const scan = usePolling('/api/markets/multi-scan', token, 60000)
  const position = report.data?.position
  const poly = scan.data?.polymarket
  const light = poly?.status === 'available' ? 'green' : poly?.status === 'partial' ? 'yellow' : 'gray'
  return <section className="kronos-panel" aria-label="Panel PAPER Futuros">
    <header><h2>PAPER Futuros · multiactivo</h2><span>Solo consulta · capital virtual</span></header>
    {report.loading && <p>Cargando cartera virtual…</p>}
    {report.error && <p role="alert">Cartera: {report.error}{report.data && ' · Último dato conservado'}</p>}
    {report.data && <div className="kronos-grid">
      <article><small>Saldo virtual libre</small><strong>{money(report.data.wallet_balance_usdt)}</strong></article>
      <article><small>Patrimonio virtual</small><strong>{money(report.data.total_equity_usdt)}</strong></article>
      <article><small>Posición</small><strong>{position ? `${position.side} · ${position.symbol}` : 'Sin posición'}</strong><span>{position ? `${position.qty} · ${position.leverage}x` : `${report.data.leverage}x configurado`}</span></article>
      <article><small>PnL no realizado</small><strong>{money(report.data.unrealized_pnl_usdt)}</strong><span>{position && report.data.mark_price ? `Mark: ${report.data.mark_price}` : position ? 'Valoración no disponible' : 'Sin posición'}</span></article>
      <article><small>Funding neto</small><strong>{money(report.data.funding_net_usdt)}</strong><span>Cobrado (+) / pagado (−)</span></article>
    </div>}
    <h3>Funding Binance ↔ Hyperliquid</h3>
    {scan.loading && <p>Cargando mercados…</p>}
    {scan.error && <p role="alert">Mercados: {scan.error}{scan.data && ' · Último dato conservado'}</p>}
    {scan.data && <><div className="kronos-funding">
      {scan.data.funding.map(row => <article key={row.symbol}><strong>{row.symbol}</strong><span>Binance: {percent(row.binance_8h_pct)}</span><span>Hyperliquid: {percent(row.hyperliquid_8h_pct)}</span><span>Diferencia 8 h: {percent(row.spread_8h_pct)}</span><span>Indicativo bruto anualizado: {row.annualized_gross_indicative_pct == null ? 'No disponible' : `${row.annualized_gross_indicative_pct} %`}</span>{row.status !== 'available' && <em>Datos parciales</em>}</article>)}
    </div><div className="kronos-poly"><h3><span className={`kronos-light ${light}`} /> Polymarket · {poly?.status === 'available' ? 'Datos disponibles' : poly?.status === 'partial' ? 'Datos parciales' : 'Sin datos'}</h3>
      {poly?.events?.length ? poly.events.map((event, index) => <article key={`${event.question}-${index}`}><strong>{event.question}</strong><span>Sí: {event.yes_prob_pct} % · No: {event.no_prob_pct} %</span></article>) : <p>Sin eventos válidos.</p>}
    </div><small>Consulta: {new Date(scan.data.queried_at).toLocaleString('es-CO')} · El rendimiento anualizado es indicativo bruto, no beneficio realizable.</small></>}
  </section>
}
