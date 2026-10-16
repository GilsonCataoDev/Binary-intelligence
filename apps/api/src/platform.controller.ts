import { Controller, Get, Param, Post } from '@nestjs/common';
import { PlatformStateService } from './platform-state.service';
import { ForexCryptoMarketService } from './market/forex-crypto-market.service';

@Controller('v1')
export class PlatformController {
  constructor(
    private readonly platform: PlatformStateService,
    private readonly market: ForexCryptoMarketService,
  ) {}

  @Get('status') status(): Promise<object> { return this.platform.status(); }
  @Get('assets') assets(): object { return this.market.listAssets(); }
  @Get('market/candles/:symbol') candles(@Param('symbol') symbol: string): Promise<object> {
    return this.market.candles(symbol);
  }
  @Get('predictions') predictions(): object { return this.platform.predictions(); }
  @Get('news') news(): object { return { availability: 'unavailable', events: [], limitation: 'no authorized news feed configured' }; }
  @Get('metrics') metrics(): object { return { paper: null, backtest: null, live: null }; }
  @Get('paper-trades') trades(): object { return { trades: [], resultType: 'paper' }; }
  @Get('models') models(): object {
    return { active: null, candidates: ['logistic-v1', 'random-forest-v1', 'histogram-boosting-v1'], approved: [] };
  }
  @Get('integrations') integrations(): object {
    return {
      candidate: 'Research-only market-data adapters', officialApiDocumented: true,
      publicDiscoveryReady: true, demoTradingReady: false, realTradingReady: false,
      dataMode: 'read_only_reference_feeds',
      pending: ['venue selection', 'account-specific spread and commission history', 'paper-trading validation'],
    };
  }
  @Post('analysis/:asset') analyze(@Param('asset') asset: string): Promise<object> { return this.platform.analyze(asset); }
  @Post('control/start') start(): Promise<object> { return this.platform.start(); }
  @Post('control/pause') pause(): Promise<object> { return this.platform.pause(); }
  @Post('control/stop') stop(): Promise<object> { return this.platform.stop(); }
  @Post('control/emergency-stop') emergency(): Promise<object> { return this.platform.emergency(); }
}
