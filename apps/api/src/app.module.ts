import { MiddlewareConsumer, Module, NestModule } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { HealthController } from './health.controller';
import { ApiKeyGuard } from './auth/api-key.guard';
import { PlatformController } from './platform.controller';
import { PlatformStateService } from './platform-state.service';
import { RequestContextMiddleware } from './request-context.middleware';

@Module({
  controllers: [HealthController, PlatformController],
  providers: [PlatformStateService, { provide: APP_GUARD, useClass: ApiKeyGuard }],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(RequestContextMiddleware).forRoutes('{*path}');
  }
}
