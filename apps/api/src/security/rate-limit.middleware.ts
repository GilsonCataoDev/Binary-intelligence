import { Injectable, NestMiddleware } from '@nestjs/common';
import { NextFunction, Request, Response } from 'express';

type WindowState = { startedAt: number; requests: number };

@Injectable()
export class LocalRateLimitMiddleware implements NestMiddleware {
  private readonly windows = new Map<string, WindowState>();

  use(request: Request, response: Response, next: NextFunction): void {
    const now = Date.now();
    const windowMs = 60_000;
    const limit = Number(process.env.API_RATE_LIMIT_PER_MINUTE ?? 120);
    const key = request.ip || request.socket.remoteAddress || 'local';
    let state = this.windows.get(key);
    if (!state || now - state.startedAt >= windowMs) {
      state = { startedAt: now, requests: 0 };
      this.windows.set(key, state);
    }
    state.requests += 1;
    response.setHeader('x-rate-limit-limit', limit);
    response.setHeader('x-rate-limit-remaining', Math.max(0, limit - state.requests));
    if (state.requests > limit) {
      response.status(429).json({ statusCode: 429, error: 'Too Many Requests' });
      return;
    }
    next();
  }
}
