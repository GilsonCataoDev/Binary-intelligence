import { Controller, Get } from '@nestjs/common';

@Controller('health')
export class HealthController {
  @Get()
  getHealth(): { status: 'ok'; phase: 5 } {
    return { status: 'ok', phase: 5 };
  }
}
