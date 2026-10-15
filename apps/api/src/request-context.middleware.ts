import { Injectable, Logger, NestMiddleware } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import { NextFunction, Request, Response } from 'express';

@Injectable()
export class RequestContextMiddleware implements NestMiddleware {
  private readonly logger = new Logger('HTTP');

  use(request: Request, response: Response, next: NextFunction): void {
    const requestId = request.header('x-request-id') ?? randomUUID();
    response.setHeader('x-request-id', requestId);
    const started = Date.now();
    response.on('finish', () => this.logger.log(JSON.stringify({
      requestId, method: request.method, path: request.path, status: response.statusCode,
      durationMs: Date.now() - started,
    })));
    next();
  }
}
