import { Controller, Get } from '@nestjs/common';
import { Public } from './auth/public.decorator';

@Controller('health')
export class HealthController {
  @Get()
  @Public()
  getHealth(): object {
    return {
      status: 'degraded', phase: 11, api: 'ok', marketData: 'not_configured',
      aiEngine: 'contract_only', execution: 'disabled',
    };
  }
}
