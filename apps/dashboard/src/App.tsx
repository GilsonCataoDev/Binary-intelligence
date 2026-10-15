import { useEffect, useState } from 'react';

type Status = { state: string; emergencyStop: boolean; connection: string; dataQuality: string; liveExecutionEnabled: boolean; engine?: { configured: boolean; reachable: boolean }; model: { version: string | null; approved: boolean }; news: { availability: string }; risk: { status: string; openExposure: number } };
type Analysis = {
  asset: string; analyzed_at: string; decision: string; reasons: string[]; data_usage: string;
  data_quality: { status: string; candle_count: number; issues: { code: string; message: string }[] };
  market_state: { regime: string; volatility: string; trend_strength: number | null; regime_changed: boolean } | null;
  input?: { candlesReceived: number; openCandlesDiscarded: number };
};
const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:3000/api';
const SYMBOL = /^[A-Za-z0-9_.-]{1,40}$/;

export function App() {
  const [key, setKey] = useState(() => sessionStorage.getItem('binary-ai-key') ?? '');
  const [status, setStatus] = useState<Status | null>(null);
  const [asset, setAsset] = useState('frxEURUSD');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [history, setHistory] = useState<Analysis[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Informe a chave local para consultar a API.');

  async function api<T>(path: string, method = 'GET'): Promise<T> {
    sessionStorage.setItem('binary-ai-key', key);
    const response = await fetch(`${API}${path}`, { method, headers: { 'x-api-key': key } });
    const body = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(body.reasons) ? `: ${body.reasons.join('; ')}` : '';
      throw new Error(`${body.message ?? body.error ?? 'Falha na API'}${detail}`);
    }
    return body as T;
  }
  async function refresh() {
    try {
      setStatus(await api<Status>('/v1/status'));
      setHistory((await api<{ predictions: Analysis[] }>('/v1/predictions')).predictions);
      setMessage('Estado atualizado.');
    } catch (error) { setMessage(String(error)); }
  }
  async function action(name: string) {
    try { setStatus(await api<Status>(`/v1/control/${name}`, 'POST')); setMessage('Estado atualizado.'); } catch (error) { setMessage(String(error)); }
  }
  async function analyze() {
    if (!SYMBOL.test(asset)) { setMessage('Símbolo inválido.'); return; }
    setBusy(true);
    try {
      const result = await api<Analysis>(`/v1/analysis/${encodeURIComponent(asset)}`, 'POST');
      setAnalysis(result);
      setHistory(previous => [result, ...previous].slice(0, 20));
      setMessage('Análise concluída.');
    } catch (error) { setMessage(String(error)); } finally { setBusy(false); }
  }
  useEffect(() => { if (key) void refresh(); }, []);

  const engineLabel = !status?.engine ? 'não verificado' : !status.engine.configured ? 'não configurado' : status.engine.reachable ? 'conectado' : 'inacessível';

  return <main>
    <header><div><p className="eyebrow">AMBIENTE EXPERIMENTAL</p><h1>Binary Intelligence</h1><p>Paper trading • horizonte de 5 minutos</p></div><span className={`pill ${status?.state ?? 'offline'}`}>{status?.state ?? 'desconectado'}</span></header>
    <section className="access"><label>Chave local<input type="password" value={key} onChange={e => setKey(e.target.value)} placeholder="API_KEY" /></label><button onClick={() => void refresh()}>Conectar</button><span>{message}</span></section>
    <section className="access"><label>Ativo (símbolo Deriv)<input value={asset} onChange={e => setAsset(e.target.value)} maxLength={40} /></label><button onClick={() => void analyze()} disabled={busy}>{busy ? 'Analisando…' : 'Analisar'}</button><span>Dados públicos transitórios; a análise não gera ordem.</span></section>
    <section className="grid">
      <article><h2>Decisão atual</h2><strong>{analysis ? (analysis.decision === 'ABSTAIN' ? 'ABSTER-SE' : analysis.decision) : 'ABSTER-SE'}</strong>
        {analysis ? <ul className="reasons">{analysis.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul> : <p>Nenhuma análise executada nesta sessão.</p>}</article>
      <article><h2>Mercado {analysis ? `• ${analysis.asset}` : ''}</h2><strong>{analysis?.market_state?.regime ?? 'sem análise'}</strong>
        <p>Volatilidade: {analysis?.market_state?.volatility ?? '—'}<br />ADX: {analysis?.market_state?.trend_strength?.toFixed(1) ?? '—'}{analysis?.market_state?.regime_changed ? ' • regime mudou' : ''}</p></article>
      <article><h2>Qualidade dos dados</h2><strong>{analysis?.data_quality.status ?? status?.dataQuality ?? 'indisponível'}</strong>
        <p>{analysis ? `${analysis.data_quality.candle_count} candles fechados${analysis.input ? `, ${analysis.input.openCandlesDiscarded} em formação descartado(s)` : ''}${analysis.data_quality.issues.length ? ` • ${analysis.data_quality.issues.map(i => i.code).join(', ')}` : ''}` : `Conexão: ${status?.connection ?? 'não verificada'}`}</p></article>
      <article><h2>Motor de IA</h2><strong>{engineLabel}</strong><p>Modelo: {status?.model.version ?? 'nenhum ativo'} • aprovado: {status?.model.approved ? 'sim' : 'não'}</p></article>
      <article><h2>Risco</h2><strong>{status?.risk.status ?? 'sem estado'}</strong><p>Exposição aberta: {status?.risk.openExposure ?? 0} unidade</p></article>
      <article><h2>Notícias</h2><strong>{status?.news.availability ?? 'indisponível'}</strong><p>Eventos não são presumidos quando não há cobertura.</p></article>
      <article><h2>Execução real</h2><strong>{status?.liveExecutionEnabled ? 'habilitada' : 'desabilitada'}</strong><p>Este painel controla somente simulação.</p></article>
    </section>
    <section className="controls"><h2>Análises recentes (memória da API)</h2>
      {history.length ? <table><thead><tr><th>Horário</th><th>Ativo</th><th>Decisão</th><th>Qualidade</th><th>Regime</th></tr></thead><tbody>
        {history.map(item => <tr key={`${item.asset}-${item.analyzed_at}`}><td>{new Date(item.analyzed_at).toLocaleTimeString('pt-BR')}</td><td>{item.asset}</td><td>{item.decision}</td><td>{item.data_quality.status}</td><td>{item.market_state?.regime ?? '—'}</td></tr>)}
      </tbody></table> : <p className="muted">Nenhuma análise registrada desde o último reinício da API.</p>}
    </section>
    <section className="controls"><h2>Controle da simulação</h2><div><button onClick={() => action('start')}>Iniciar</button><button className="secondary" onClick={() => action('pause')}>Pausar</button><button className="secondary" onClick={() => action('stop')}>Parar</button><button className="danger" onClick={() => confirm('Ativar parada de emergência?') && action('emergency-stop')}>PARADA DE EMERGÊNCIA</button></div></section>
    <footer>Nenhum resultado exibido representa promessa de rentabilidade.</footer>
  </main>;
}
