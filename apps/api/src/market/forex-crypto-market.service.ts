import { BadRequestException, Injectable, ServiceUnavailableException } from '@nestjs/common';

type JsonObject = Record<string, unknown>;
type Asset = 'BTCUSDT' | 'XAUUSD';

type MarketCandle = {
  epoch: number;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string | null;
};

@Injectable()
export class ForexCryptoMarketService {
  private readonly binanceKlines = 'https://api.binance.com/api/v3/klines';
  private readonly twelveDataSeries = 'https://api.twelvedata.com/time_series';

  async probe(): Promise<{ connected: boolean; checkedAt: string }> {
    const response = await fetch('https://api.binance.com/api/v3/ping', { signal: AbortSignal.timeout(5_000) });
    if (!response.ok) throw new ServiceUnavailableException('Binance public market data is unavailable');
    return { connected: true, checkedAt: new Date().toISOString() };
  }

  listAssets(): object {
    return {
      mode: 'research_read_only', executionEnabled: false,
      assets: [
        {
          symbol: 'BTCUSDT', displayName: 'Bitcoin / Tether', market: 'crypto_spot',
          source: 'Binance Spot public market data', timeframe: '5m', apiKeyRequired: false,
          limitation: 'BTC/USDT from one exchange; it is not a consolidated BTC/USD price or a broker fill.',
        },
        {
          symbol: 'XAUUSD', displayName: 'Gold / US Dollar', market: 'precious_metal_spot',
          source: 'Twelve Data Forex API', timeframe: '5m', apiKeyRequired: true,
          limitation: 'Reference feed only; spread, financing and broker-specific execution are not included.',
        },
      ],
    };
  }

  async candles(symbol: string): Promise<{ source: string; symbol: Asset; granularitySeconds: number; fetchedAt: string; candles: MarketCandle[]; dataUsage: string }> {
    const asset = this.asset(symbol);
    return asset === 'BTCUSDT' ? this.btcCandles() : this.goldCandles();
  }

  private async btcCandles(): Promise<{ source: string; symbol: Asset; granularitySeconds: number; fetchedAt: string; candles: MarketCandle[]; dataUsage: string }> {
    const url = new URL(this.binanceKlines);
    url.search = new URLSearchParams({ symbol: 'BTCUSDT', interval: '5m', limit: '100' }).toString();
    const response = await this.request(url, 'Binance');
    const payload: unknown = await response.json();
    if (!Array.isArray(payload)) throw new ServiceUnavailableException('Binance returned an invalid candle payload');
    const candles = payload.map((row): MarketCandle => {
      if (!Array.isArray(row) || row.length < 6 || !Number.isFinite(Number(row[0]))) {
        throw new ServiceUnavailableException('Binance returned a malformed candle');
      }
      return { epoch: Math.floor(Number(row[0]) / 1_000), open: String(row[1]), high: String(row[2]), low: String(row[3]), close: String(row[4]), volume: String(row[5]) };
    });
    return { source: 'binance_spot_public', symbol: 'BTCUSDT', granularitySeconds: 300, fetchedAt: new Date().toISOString(), candles, dataUsage: 'research_reference_feed' };
  }

  private async goldCandles(): Promise<{ source: string; symbol: Asset; granularitySeconds: number; fetchedAt: string; candles: MarketCandle[]; dataUsage: string }> {
    const apiKey = process.env.TWELVE_DATA_API_KEY?.trim();
    if (!apiKey || apiKey === 'replace_with_your_twelve_data_key') {
      throw new ServiceUnavailableException({ error: 'Gold data unavailable', decision: 'ABSTAIN', reasons: ['TWELVE_DATA_API_KEY is not configured'] });
    }
    const url = new URL(this.twelveDataSeries);
    url.search = new URLSearchParams({ symbol: 'XAU/USD', interval: '5min', timezone: 'UTC', outputsize: '100', apikey: apiKey }).toString();
    const response = await this.request(url, 'Twelve Data');
    const payload = await response.json() as JsonObject;
    if (payload.status === 'error' || !Array.isArray(payload.values)) {
      throw new ServiceUnavailableException({ error: 'Twelve Data request failed', decision: 'ABSTAIN', reasons: [String(payload.message ?? 'invalid provider response')] });
    }
    const candles = (payload.values as JsonObject[]).map((row): MarketCandle => {
      const stamp = String(row.datetime ?? '').replace(' ', 'T');
      const epoch = Math.floor(new Date(`${stamp}Z`).getTime() / 1_000);
      if (!Number.isFinite(epoch)) throw new ServiceUnavailableException('Twelve Data returned an invalid candle timestamp');
      return { epoch, open: String(row.open), high: String(row.high), low: String(row.low), close: String(row.close), volume: row.volume == null ? null : String(row.volume) };
    }).sort((left, right) => left.epoch - right.epoch);
    return { source: 'twelve_data_forex', symbol: 'XAUUSD', granularitySeconds: 300, fetchedAt: new Date().toISOString(), candles, dataUsage: 'research_reference_feed' };
  }

  private asset(value: string): Asset {
    const normalized = value.trim().toUpperCase();
    if (normalized === 'BTCUSDT' || normalized === 'XAUUSD') return normalized;
    throw new BadRequestException('asset must be BTCUSDT or XAUUSD');
  }

  private async request(url: URL, provider: string): Promise<Response> {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(8_000) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response;
    } catch {
      throw new ServiceUnavailableException(`${provider} market data is unavailable`);
    }
  }
}
