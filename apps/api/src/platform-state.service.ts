import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import { DerivPublicMarketService } from './market/deriv-public-market.service';
import { EngineClientService } from './engine/engine-client.service';

type BotState = 'stopped' | 'running' | 'paused' | 'emergency_stopped';

@Injectable()
export class PlatformStateService {
  private state: BotState = 'stopped';
  private emergencyStop = false;
  private recentAnalyses: object[] = [];

  constructor(
    private readonly market: DerivPublicMarketService,
    private readonly engine: EngineClientService,
  ) {}

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
    const engine = await this.engine.health();
    return {
      mode: 'paper', state: this.state, emergencyStop: this.emergencyStop,
      liveExecutionEnabled: false, connection, dataQuality,
      marketSource: { name: 'Deriv public Options API', mode: 'transient_read_only', checkedAt },
      engine: { configured: this.engine.configured, reachable: engine.reachable },
      model: { version: engine.modelVersion, approved: false }, news: { availability: 'unavailable' },
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

  async analyze(asset: string): Promise<object> {
    const result = await this.engine.analyze(asset);
    if (result.decision !== 'ABSTAIN') {
      throw new ServiceUnavailableException({ error: 'engine returned a non-ABSTAIN decision in simulation-only release', decision: 'ABSTAIN' });
    }
    this.recentAnalyses = [result, ...this.recentAnalyses].slice(0, 20);
    return result;
  }

  predictions(): object {
    return { predictions: this.recentAnalyses, resultType: 'analysis_only', retention: 'in-memory, last 20, cleared on restart' };
  }
}
