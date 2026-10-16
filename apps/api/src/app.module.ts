import { MiddlewareConsumer, Module, NestModule } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { HealthController } from './health.controller';
import { ApiKeyGuard } from './auth/api-key.guard';
import { PlatformController } from './platform.controller';
import { PlatformStateService } from './platform-state.service';
import { RequestContextMiddleware } from './request-context.middleware';
import { LocalRateLimitMiddleware } from './security/rate-limit.middleware';
import { ForexCryptoMarketService } from './market/forex-crypto-market.service';
import { EngineClientService } from './engine/engine-client.service';

@Module({
  controllers: [HealthController, PlatformController],
  providers: [PlatformStateService, ForexCryptoMarketService, EngineClientService, { provide: APP_GUARD, useClass: ApiKeyGuard }],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(RequestContextMiddleware, LocalRateLimitMiddleware).forRoutes('{*path}');
  }
}
