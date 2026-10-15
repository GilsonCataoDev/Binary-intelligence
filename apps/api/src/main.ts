import 'reflect-metadata';
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import helmet from 'helmet';
import { AppModule } from './app.module';
import { loadSecurityConfiguration } from './security/config';

async function bootstrap(): Promise<void> {
  const security = loadSecurityConfiguration();
  const app = await NestFactory.create(AppModule);
  app.use(helmet());
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true }));
  app.enableCors({ origin: security.dashboardOrigin });
  app.setGlobalPrefix('api');
  const port = Number(process.env.APP_PORT ?? 3000);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('APP_PORT must be an integer between 1 and 65535');
  }
  await app.listen(port, '127.0.0.1');
}

void bootstrap();
