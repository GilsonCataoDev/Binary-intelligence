import { useEffect, useState } from 'react';

type Status = { state: string; emergencyStop: boolean; connection: string; dataQuality: string; liveExecutionEnabled: boolean; model: { version: string | null; approved: boolean }; news: { availability: string }; risk: { status: string; openExposure: number } };
const API = 'http://127.0.0.1:3000/api';

export function App() {
  const [key, setKey] = useState(() => sessionStorage.getItem('binary-ai-key') ?? '');
  const [status, setStatus] = useState<Status | null>(null);
  const [message, setMessage] = useState('Informe a chave local para consultar a API.');

  async function request(path: string, method = 'GET') {
    sessionStorage.setItem('binary-ai-key', key);
    const response = await fetch(`${API}${path}`, { method, headers: { 'x-api-key': key } });
    const body = await response.json();
    if (!response.ok) throw new Error(body.message ?? body.error ?? 'Falha na API');
    setStatus(body); setMessage('Estado atualizado.');
  }
  async function action(name: string) {
    try { await request(`/v1/control/${name}`, 'POST'); } catch (error) { setMessage(String(error)); }
  }
  useEffect(() => { if (key) request('/v1/status').catch(error => setMessage(String(error))); }, []);

  return <main>
    <header><div><p className="eyebrow">AMBIENTE EXPERIMENTAL</p><h1>Binary Intelligence</h1><p>Paper trading • horizonte de 5 minutos</p></div><span className={`pill ${status?.state ?? 'offline'}`}>{status?.state ?? 'desconectado'}</span></header>
    <section className="access"><label>Chave local<input type="password" value={key} onChange={e => setKey(e.target.value)} placeholder="API_KEY" /></label><button onClick={() => request('/v1/status').catch(error => setMessage(String(error)))}>Conectar</button><span>{message}</span></section>
    <section className="grid">
      <article><h2>Decisão atual</h2><strong>ABSTER-SE</strong><p>Sem fonte de mercado autorizada e sem modelo promovido.</p></article>
      <article><h2>Qualidade dos dados</h2><strong>{status?.dataQuality ?? 'indisponível'}</strong><p>Conexão: {status?.connection ?? 'não verificada'}</p></article>
      <article><h2>Risco</h2><strong>{status?.risk.status ?? 'sem estado'}</strong><p>Exposição aberta: {status?.risk.openExposure ?? 0} unidade</p></article>
      <article><h2>Modelo</h2><strong>{status?.model.version ?? 'nenhum ativo'}</strong><p>Aprovado: {status?.model.approved ? 'sim' : 'não'}</p></article>
      <article><h2>Notícias</h2><strong>{status?.news.availability ?? 'indisponível'}</strong><p>Eventos não são presumidos quando não há cobertura.</p></article>
      <article><h2>Execução real</h2><strong>{status?.liveExecutionEnabled ? 'habilitada' : 'desabilitada'}</strong><p>Este painel controla somente simulação.</p></article>
    </section>
    <section className="controls"><h2>Controle da simulação</h2><div><button onClick={() => action('start')}>Iniciar</button><button className="secondary" onClick={() => action('pause')}>Pausar</button><button className="secondary" onClick={() => action('stop')}>Parar</button><button className="danger" onClick={() => confirm('Ativar parada de emergência?') && action('emergency-stop')}>PARADA DE EMERGÊNCIA</button></div></section>
    <footer>Nenhum resultado exibido representa promessa de rentabilidade.</footer>
  </main>;
}
