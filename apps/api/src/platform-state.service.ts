import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import { DerivPublicMarketService } from './market/deriv-public-market.service';

type BotState = 'stopped' | 'running' | 'paused' | 'emergency_stopped';

@Injectable()
export class PlatformStateService {
  private state: BotState = 'stopped';
  private emergencyStop = false;

  constructor(private readonly market: DerivPublicMarketService) {}

  async status(): Promise<object> {
    let connection = 'deriv_public_unavailable';
    let dataQuality = 'unavailable';
    let checkedAt: string | null = null;
    try {
      const probe = await this.market.probe();
      connection = 'deriv_public_connected';
      dataQuality = 'transient_unvalidated';
      checkedAt = probe.checkedAt;
    } catch {
      // Safe degraded state is returned when the public provider cannot be reached.
    }
    return {
      mode: 'paper', state: this.state, emergencyStop: this.emergencyStop,
      liveExecutionEnabled: false, connection, dataQuality,
      marketSource: { name: 'Deriv public Options API', mode: 'transient_read_only', checkedAt },
      model: { version: null, approved: false }, news: { availability: 'unavailable' },
      risk: { status: this.emergencyStop ? 'blocked' : 'ready', openExposure: 0 },
    };
  }

  start(): Promise<object> {
    if (this.emergencyStop) throw new ServiceUnavailableException('emergency stop is latched');
    this.state = 'running';
    return this.status();
  }

  pause(): Promise<object> {
    if (this.state === 'running') this.state = 'paused';
    return this.status();
  }

  stop(): Promise<object> {
    this.state = 'stopped';
    return this.status();
  }

  emergency(): Promise<object> {
    this.emergencyStop = true;
    this.state = 'emergency_stopped';
    return this.status();
  }

  unavailableAnalysis(asset: string): never {
    throw new ServiceUnavailableException({
      statusCode: 503,
      error: 'Analysis unavailable',
      asset: asset.toUpperCase(),
      reasons: ['public transient data is not approved for model inference', 'no model has passed controlled promotion'],
      decision: 'ABSTAIN',
    });
  }
}
