import { MiddlewareConsumer, Module, NestModule } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { HealthController } from './health.controller';
import { ApiKeyGuard } from './auth/api-key.guard';
import { PlatformController } from './platform.controller';
import { PlatformStateService } from './platform-state.service';
import { RequestContextMiddleware } from './request-context.middleware';
import { LocalRateLimitMiddleware } from './security/rate-limit.middleware';
import { DerivPublicMarketService } from './market/deriv-public-market.service';

@Module({
  controllers: [HealthController, PlatformController],
  providers: [PlatformStateService, DerivPublicMarketService, { provide: APP_GUARD, useClass: ApiKeyGuard }],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(RequestContextMiddleware, LocalRateLimitMiddleware).forRoutes('{*path}');
  }
}
