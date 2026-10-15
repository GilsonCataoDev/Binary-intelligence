export type SecurityConfiguration = {
  apiKey: string;
  dashboardOrigin: string;
  rateLimitPerMinute: number;
};

export function loadSecurityConfiguration(
  environment: NodeJS.ProcessEnv = process.env,
): SecurityConfiguration {
  const apiKey = environment.API_KEY ?? '';
  if (apiKey.length < 32 || apiKey === 'replace_with_a_long_random_local_secret') {
    throw new Error('API_KEY must be a non-placeholder secret with at least 32 characters');
  }
  if ((environment.EXECUTION_MODE ?? 'simulation') !== 'simulation') {
    throw new Error('only EXECUTION_MODE=simulation is supported');
  }
  if ((environment.REAL_EXECUTION_ENABLED ?? 'false').toLowerCase() !== 'false') {
    throw new Error('REAL_EXECUTION_ENABLED must remain false');
  }

  const dashboardOrigin = environment.DASHBOARD_ORIGIN ?? 'http://127.0.0.1:5173';
  const origin = new URL(dashboardOrigin);
  if (!['http:', 'https:'].includes(origin.protocol) || !['127.0.0.1', 'localhost', '::1'].includes(origin.hostname)) {
    throw new Error('DASHBOARD_ORIGIN must use HTTP(S) on a loopback host in this release');
  }

  const rateLimitPerMinute = Number(environment.API_RATE_LIMIT_PER_MINUTE ?? 120);
  if (!Number.isInteger(rateLimitPerMinute) || rateLimitPerMinute < 1 || rateLimitPerMinute > 10_000) {
    throw new Error('API_RATE_LIMIT_PER_MINUTE must be an integer between 1 and 10000');
  }
  return { apiKey, dashboardOrigin: origin.origin, rateLimitPerMinute };
}
