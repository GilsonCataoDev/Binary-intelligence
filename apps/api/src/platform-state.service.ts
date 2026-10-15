import { Injectable, ServiceUnavailableException } from '@nestjs/common';

type BotState = 'stopped' | 'running' | 'paused' | 'emergency_stopped';

@Injectable()
export class PlatformStateService {
  private state: BotState = 'stopped';
  private emergencyStop = false;

  status(): object {
    return {
      mode: 'paper', state: this.state, emergencyStop: this.emergencyStop,
      liveExecutionEnabled: false, connection: 'no_market_provider', dataQuality: 'unavailable',
      model: { version: null, approved: false }, news: { availability: 'unavailable' },
      risk: { status: this.emergencyStop ? 'blocked' : 'ready', openExposure: 0 },
    };
  }

  start(): object {
    if (this.emergencyStop) throw new ServiceUnavailableException('emergency stop is latched');
    this.state = 'running';
    return this.status();
  }

  pause(): object {
    if (this.state === 'running') this.state = 'paused';
    return this.status();
  }

  stop(): object {
    this.state = 'stopped';
    return this.status();
  }

  emergency(): object {
    this.emergencyStop = true;
    this.state = 'emergency_stopped';
    return this.status();
  }

  unavailableAnalysis(asset: string): never {
    throw new ServiceUnavailableException({
      statusCode: 503,
      error: 'Analysis unavailable',
      asset: asset.toUpperCase(),
      reasons: ['no authorized live market source configured', 'no model has passed controlled promotion'],
      decision: 'ABSTAIN',
    });
  }
}
