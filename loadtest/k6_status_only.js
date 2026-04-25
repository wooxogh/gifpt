import http from 'k6/http';
import { check } from 'k6';

const BACKEND = __ENV.LOADTEST_BACKEND || 'http://localhost:8080';
// Phase 1: shared token (first seeded user)
const TOKEN = __ENV.LOADTEST_TOKEN;  // required
const FAKE_JOB_ID = __ENV.LOADTEST_FAKE_JOB_ID || '999999999';

if (!TOKEN) throw new Error('LOADTEST_TOKEN env var required');

// Treat 4xx as expected so http_req_failed reflects real failures only
// (default is 200–399; without this, 404s inflate the failure rate).
http.setResponseCallback(http.expectedStatuses({ min: 200, max: 499 }));

export const options = {
  stages: [
    { duration: '2m',  target: 50 },   // warmup
    { duration: '3m',  target: 50 },
    { duration: '30s', target: 100 },
    { duration: '3m',  target: 100 },
    { duration: '30s', target: 200 },
    { duration: '3m',  target: 200 },
    { duration: '30s', target: 400 },
    { duration: '3m',  target: 400 },
    { duration: '30s', target: 800 },
    { duration: '3m',  target: 800 },
    { duration: '1m',  target: 0 },
  ],
  thresholds: {
    // 404 is expected (fake jobId) — not a failure for this test
    'http_req_failed': ['rate<0.05'],
    'http_req_duration': ['p(95)<2000'],
  },
};

export default function () {
  const res = http.get(
    `${BACKEND}/api/v1/animate/status/${FAKE_JOB_ID}`,
    {
      headers: { Authorization: `Bearer ${TOKEN}` },
      tags: { endpoint: 'status' },
    }
  );
  // 404 is the expected response for a nonexistent jobId
  check(res, {
    'status is 404 or 403': (r) => r.status === 404 || r.status === 403,
  });
}

export function handleSummary(data) {
  return {
    stdout: JSON.stringify(data.metrics.http_req_duration.values, null, 2),
    [`${__ENV.LOADTEST_OUT || '.'}/k6_summary.json`]: JSON.stringify(data, null, 2),
  };
}
