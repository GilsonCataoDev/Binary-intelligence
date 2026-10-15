import { Controller, Get, Param, Post } from '@nestjs/common';
import { PlatformStateService } from './platform-state.service';
import { DerivPublicMarketService } from './market/deriv-public-market.service';

@Controller('v1')
export class PlatformController {
  constructor(
    private readonly platform: PlatformStateService,
    private readonly market: DerivPublicMarketService,
  ) {}

  @Get('status') status(): Promise<object> { return this.platform.status(); }
  @Get('assets') assets(): Promise<object> { return this.market.listAssets(); }
  @Get('market/candles/:symbol') candles(@Param('symbol') symbol: string): Promise<object> {
    return this.market.candles(symbol);
  }
  @Get('market/proposal/:symbol') proposal(@Param('symbol') symbol: string): Promise<object> {
    return this.market.fiveMinuteProposal(symbol);
  }
  @Get('predictions') predictions(): object { return { predictions: [], resultType: 'paper' }; }
  @Get('news') news(): object { return { availability: 'unavailable', events: [], limitation: 'no authorized news feed configured' }; }
  @Get('metrics') metrics(): object { return { paper: null, backtest: null, live: null }; }
  @Get('paper-trades') trades(): object { return { trades: [], resultType: 'paper' }; }
  @Get('models') models(): object {
    return { active: null, candidates: ['logistic-v1', 'random-forest-v1', 'histogram-boosting-v1'], approved: [] };
  }
  @Get('integrations') integrations(): object {
    return {
      candidate: 'Deriv Options', officialApiDocumented: true,
      publicDiscoveryReady: true, demoTradingReady: false, realTradingReady: false,
      dataMode: 'transient_read_only',
      pending: ['app registration', 'account and regional eligibility', 'authenticated demo tests'],
    };
  }
  @Post('analysis/:asset') analyze(@Param('asset') asset: string): never { return this.platform.unavailableAnalysis(asset); }
  @Post('control/start') start(): Promise<object> { return this.platform.start(); }
  @Post('control/pause') pause(): Promise<object> { return this.platform.pause(); }
  @Post('control/stop') stop(): Promise<object> { return this.platform.stop(); }
  @Post('control/emergency-stop') emergency(): Promise<object> { return this.platform.emergency(); }
}
