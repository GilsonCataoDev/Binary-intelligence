import { BadRequestException, Injectable, ServiceUnavailableException } from '@nestjs/common';
import WebSocket from 'ws';

type JsonObject = Record<string, unknown>;

@Injectable()
export class DerivPublicMarketService {
  private readonly endpoint = 'wss://api.derivws.com/trading/v1/options/ws/public';

  async probe(): Promise<{ connected: boolean; checkedAt: string }> {
    await this.request({ ping: 1 });
    return { connected: true, checkedAt: new Date().toISOString() };
  }

  async listAssets(): Promise<object> {
    const response = await this.request({ active_symbols: 'brief', contract_type: ['CALL', 'PUT'] });
    const records = Array.isArray(response.active_symbols) ? response.active_symbols : [];
    const assets = records.slice(0, 250).map((item) => {
      const record = item as JsonObject;
      return {
        symbol: String(record.underlying_symbol ?? ''),
        name: String(record.underlying_symbol_name ?? ''),
        pipSize: Number(record.pip_size ?? 0),
      };
    }).filter((item) => item.symbol);
    return {
      source: 'Deriv public Options API', mode: 'transient_read_only', assets,
      retentionLimit: 'cache only; maximum 24 hours under current API terms',
    };
  }

  async candles(symbol: string): Promise<object> {
    const safeSymbol = this.symbol(symbol);
    const response = await this.request({
      ticks_history: safeSymbol, end: 'latest', style: 'candles',
      granularity: 300, count: 100, adjust_start_time: 1,
    });
    const candles = Array.isArray(response.candles) ? response.candles : [];
    return {
      source: 'Deriv public Options API', symbol: safeSymbol, granularitySeconds: 300,
      fetchedAt: new Date().toISOString(), transient: true, candles,
    };
  }

  async fiveMinuteProposal(symbol: string): Promise<object> {
    const safeSymbol = this.symbol(symbol);
    const response = await this.request({
      proposal: 1, amount: 1, basis: 'stake', contract_type: 'CALL', currency: 'USD',
      duration: 5, duration_unit: 'm', underlying_symbol: safeSymbol,
    });
    const proposal = (response.proposal ?? {}) as JsonObject;
    return {
      source: 'Deriv public Options API', symbol: safeSymbol, contractType: 'CALL',
      durationMinutes: 5, fetchedAt: new Date().toISOString(), executable: false,
      quote: {
        askPrice: proposal.ask_price ?? null,
        payout: proposal.payout ?? null,
        spot: proposal.spot ?? null,
        proposalIdPresent: Boolean(proposal.id),
      },
      limitation: 'quotation only; no buy adapter or authenticated account is configured',
    };
  }

  private symbol(value: string): string {
    if (!/^[A-Za-z0-9_.-]{1,40}$/.test(value)) throw new BadRequestException('invalid market symbol');
    return value;
  }

  private request(payload: JsonObject): Promise<JsonObject> {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(this.endpoint, { handshakeTimeout: 5_000 });
      const timeout = setTimeout(() => {
        socket.terminate();
        reject(new ServiceUnavailableException('Deriv public API timed out'));
      }, 8_000);
      const finish = (callback: () => void): void => {
        clearTimeout(timeout);
        if (socket.readyState === WebSocket.OPEN) socket.close();
        callback();
      };
      socket.once('open', () => socket.send(JSON.stringify(payload)));
      socket.once('message', (raw) => {
        try {
          const response = JSON.parse(raw.toString()) as JsonObject;
          const error = response.error as JsonObject | undefined;
          if (error) {
            finish(() => reject(new ServiceUnavailableException({
              error: 'Deriv request rejected', message: String(error.message ?? 'unknown provider error'),
            })));
            return;
          }
          finish(() => resolve(response));
        } catch {
          finish(() => reject(new ServiceUnavailableException('Deriv returned an invalid response')));
        }
      });
      socket.once('error', () => finish(() => reject(new ServiceUnavailableException('Deriv public API is unavailable'))));
    });
  }
}
