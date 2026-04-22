import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

const BACKEND = __ENV.LOADTEST_BACKEND || 'http://localhost:8080';
const POLL_INTERVAL_MS = parseInt(__ENV.POLL_INTERVAL_MS || '3000', 10);
const POLL_MAX = parseInt(__ENV.POLL_MAX || '20', 10);
const ALGORITHM_BASE = __ENV.ALGORITHM || 'bubble-sort';

const tokens = new SharedArray('tokens', () =>
  JSON.parse(open('./tokens.json')).map((e) => e.token)
);

export const options = {
  stages: [
    { duration: '2m',  target: 100 },  // warmup
    { duration: '5m',  target: 100 },
    { duration: '30s', target: 200 },
    { duration: '5m',  target: 200 },
    { duration: '30s', target: 400 },
    { duration: '5m',  target: 400 },
    { duration: '30s', target: 800 },
    { duration: '5m',  target: 800 },
    { duration: '2m',  target: 0 },
  ],
  thresholds: {
    'http_req_failed{expected_response:true}': ['rate<0.05'],
    'http_req_duration{endpoint:status}': ['p(95)<2000'],
  },
};

export default function () {
  const token = tokens[Math.floor(Math.random() * tokens.length)];
  const headers = { Authorization: `Bearer ${token}` };

  // Force cache MISS: salt algorithm slug with VU + iteration.
  const slug = `${ALGORITHM_BASE}-${__VU}-${__ITER}`;
  const startRes = http.get(
    `${BACKEND}/api/v1/animate?algorithm=${slug}`,
    { headers, tags: { endpoint: 'animate' } }
  );

  if (startRes.status !== 202) {
    // Could be 200 cache HIT or error. Either way, skip polling.
    sleep(1);
    return;
  }

  let jobId;
  try { jobId = startRes.json('jobId'); } catch (e) { sleep(1); return; }
  if (!jobId) { sleep(1); return; }

  for (let i = 0; i < POLL_MAX; i++) {
    sleep(POLL_INTERVAL_MS / 1000);
    const r = http.get(
      `${BACKEND}/api/v1/animate/status/${jobId}`,
      { headers, tags: { endpoint: 'status' } }
    );
    check(r, { 'poll ok': (rr) => rr.status < 500 });
    if (r.status === 200) {
      const status = r.json('status');
      if (status === 'SUCCESS' || status === 'FAILED') break;
    }
  }
  sleep(1);
}

export function handleSummary(data) {
  return {
    [`${__ENV.LOADTEST_OUT || '.'}/k6_summary.json`]: JSON.stringify(data, null, 2),
    stdout: JSON.stringify({
      http_req_duration_p95: data.metrics.http_req_duration.values['p(95)'],
      http_reqs: data.metrics.http_reqs.values.count,
      iterations: data.metrics.iterations.values.count,
    }, null, 2),
  };
}
