import { Controller, Get, Param, Post } from '@nestjs/common';
import { PlatformStateService } from './platform-state.service';

@Controller('v1')
export class PlatformController {
  constructor(private readonly platform: PlatformStateService) {}

  @Get('status') status(): object { return this.platform.status(); }
  @Get('assets') assets(): object { return { assets: [], limitation: 'no authorized market provider configured' }; }
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
      publicDiscoveryReady: false, demoTradingReady: false, realTradingReady: false,
      pending: ['app registration', 'account and regional eligibility', 'contract verification', 'demo integration tests'],
    };
  }
  @Post('analysis/:asset') analyze(@Param('asset') asset: string): never { return this.platform.unavailableAnalysis(asset); }
  @Post('control/start') start(): object { return this.platform.start(); }
  @Post('control/pause') pause(): object { return this.platform.pause(); }
  @Post('control/stop') stop(): object { return this.platform.stop(); }
  @Post('control/emergency-stop') emergency(): object { return this.platform.emergency(); }
}
