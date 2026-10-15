import { Injectable, Logger, ServiceUnavailableException } from '@nestjs/common';
import { DerivPublicMarketService } from '../market/deriv-public-market.service';

export type EngineConfiguration = { url: string; token: string };
type JsonObject = Record<string, unknown>;

const GRANULARITY_SECONDS = 300;
const PLACEHOLDER_TOKEN = 'replace_with_a_long_random_engine_secret';

export function loadEngineConfiguration(environment: NodeJS.ProcessEnv = process.env): EngineConfiguration | null {
  const token = environment.ENGINE_TOKEN ?? '';
  if (!token) return null;
  if (token.length < 32 || token === PLACEHOLDER_TOKEN) {
    throw new Error('ENGINE_TOKEN must be a non-placeholder secret with at least 32 characters');
  }
  const url = new URL(environment.AI_ENGINE_URL ?? 'http://127.0.0.1:8000');
  if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)) {
    throw new Error('AI_ENGINE_URL must use HTTP on a loopback host in this release');
  }
  return { url: url.origin, token };
}

@Injectable()
export class EngineClientService {
  private readonly logger = new Logger(EngineClientService.name);
  private readonly configuration = loadEngineConfiguration();

  constructor(private readonly market: DerivPublicMarketService) {}

  get configured(): boolean {
    return this.configuration !== null;
  }

  async health(): Promise<{ reachable: boolean; modelVersion: string | null }> {
    if (!this.configuration) return { reachable: false, modelVersion: null };
    try {
      const response = await fetch(`${this.configuration.url}/health`, { signal: AbortSignal.timeout(3_000) });
      if (!response.ok) return { reachable: false, modelVersion: null };
      const body = (await response.json()) as JsonObject;
      const model = (body.model ?? {}) as JsonObject;
      return { reachable: body.status === 'ok', modelVersion: typeof model.version === 'string' ? model.version : null };
    } catch {
      return { reachable: false, modelVersion: null };
    }
  }

  async analyze(symbol: string): Promise<JsonObject> {
    if (!this.configuration) {
      throw new ServiceUnavailableException({
        error: 'Analysis unavailable', decision: 'ABSTAIN',
        reasons: ['AI engine is not configured (ENGINE_TOKEN missing)'],
      });
    }
    const market = (await this.market.candles(symbol)) as JsonObject;
    const nowSeconds = Math.floor(Date.now() / 1000);
    const raw = Array.isArray(market.candles) ? (market.candles as JsonObject[]) : [];
    const closed = raw.filter((candle) => Number(candle.epoch) + GRANULARITY_SECONDS <= nowSeconds);

    const payload = {
      asset: String(market.symbol), timeframe: '5m', source: 'deriv_public', data_usage: 'transient_unvalidated',
      candles: closed.map((candle) => ({
        open_time: new Date(Number(candle.epoch) * 1000).toISOString(),
        open: String(candle.open), high: String(candle.high), low: String(candle.low), close: String(candle.close),
      })),
    };

    let response: Response;
    try {
      response = await fetch(`${this.configuration.url}/v1/analysis`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-engine-token': this.configuration.token },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(10_000),
      });
    } catch {
      throw new ServiceUnavailableException({ error: 'AI engine is unreachable', decision: 'ABSTAIN' });
    }
    const body = (await response.json().catch(() => ({}))) as JsonObject;
    if (!response.ok) {
      this.logger.warn(`engine rejected analysis with HTTP ${response.status}`);
      throw new ServiceUnavailableException({ error: 'AI engine rejected the analysis', decision: 'ABSTAIN', status: response.status });
    }
    return { ...body, input: { candlesReceived: raw.length, openCandlesDiscarded: raw.length - closed.length } };
  }
}
