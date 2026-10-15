import { CanActivate, ExecutionContext, Injectable, ServiceUnavailableException, UnauthorizedException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { timingSafeEqual } from 'node:crypto';
import { IS_PUBLIC } from './public.decorator';

@Injectable()
export class ApiKeyGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    if (this.reflector.getAllAndOverride<boolean>(IS_PUBLIC, [context.getHandler(), context.getClass()])) return true;
    const configured = process.env.API_KEY;
    if (!configured) throw new ServiceUnavailableException('API_KEY is not configured');
    const supplied = context.switchToHttp().getRequest<{ headers: Record<string, string | undefined> }>().headers['x-api-key'];
    if (!supplied || !sameSecret(configured, supplied)) throw new UnauthorizedException('invalid API key');
    return true;
  }
}

function sameSecret(expected: string, supplied: string): boolean {
  const left = Buffer.from(expected);
  const right = Buffer.from(supplied);
  return left.length === right.length && timingSafeEqual(left, right);
}
