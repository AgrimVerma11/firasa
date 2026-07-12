import axios from 'axios';

// In development VITE_API_BASE_URL is empty and the Vite dev server proxies
// /api to the Flask app. In production it is set to the deployed API origin.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// The API runs on a free tier that spins down when idle. A cold instance
// tends to fail fast (a 502 from the platform's edge while the container is
// still booting) rather than hang until a timeout, so a single long timeout
// does not actually buy a visitor anything. Calls that may land on a cold
// instance retry across this whole window instead, so the "could not reach
// the service" message only appears after genuinely giving the free tier a
// chance to wake up.
const COLD_START_BUDGET_MS = 40000;
const COLD_START_ATTEMPT_TIMEOUT_MS = 12000;
const RETRY_DELAY_MS = 4000;

// A generous, invisible timeout for the fire-and-forget wake-up ping. Nothing
// in the UI waits on it, so there is no harm in giving it plenty of room.
const WAKE_TIMEOUT_MS = 60000;

// Only retry a failure that plausibly means "the instance is still waking
// up": no response at all (network drop, timeout, CORS failure while the
// container is not yet listening) or a gateway-level error from the
// platform's edge. A real validation error or an application error surfaces
// immediately instead of being retried for 40 seconds.
function isRetryable(error) {
  if (!error.response) return true;
  return [502, 503, 504].includes(error.response.status);
}

// Turn any failure into a plain object the UI can render, whether it came back
// as one of our structured API errors, a network drop, or a timeout. We never
// surface raw stack traces or axios internals to the student.
function normalizeError(error) {
  if (error.response?.data && typeof error.response.data === 'object') {
    const { message, error_code, field } = error.response.data;
    return {
      message: message || 'The request could not be completed.',
      code: error_code || 'error',
      field: field || null,
      status: error.response.status,
    };
  }
  if (error.code === 'ECONNABORTED') {
    return {
      message: 'The request took too long. Please check your connection and try again.',
      code: 'timeout',
      field: null,
      status: null,
    };
  }
  return {
    message: 'Could not reach the Firasa service. Please try again in a moment.',
    code: 'network_error',
    field: null,
    status: null,
  };
}

async function request(promise) {
  try {
    const { data } = await promise;
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

// Retries a cold-start-prone call across a fixed time budget rather than
// waiting longer on a single attempt, since a spinning-up instance tends to
// fail fast instead of hanging. makeRequest is a factory (not a promise) so
// each retry actually fires a new request.
async function requestWithRetry(makeRequest) {
  const start = Date.now();
  for (;;) {
    try {
      const { data } = await makeRequest();
      return data;
    } catch (error) {
      const elapsed = Date.now() - start;
      if (!isRetryable(error) || elapsed >= COLD_START_BUDGET_MS) {
        throw normalizeError(error);
      }
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
    }
  }
}

export function getHealth() {
  return request(client.get('/health'));
}

// Fire-and-forget warm-up. Called when the app first loads so the free-tier API
// is waking while the student fills in the form, not when they hit submit. Never
// throws and is not awaited by the UI.
export function wakeApi() {
  return client
    .get('/health', { timeout: WAKE_TIMEOUT_MS })
    .then(() => true)
    .catch(() => false);
}

export function predictStudent(profile) {
  return requestWithRetry(() =>
    client.post('/predict', profile, { timeout: COLD_START_ATTEMPT_TIMEOUT_MS })
  );
}

// modifications is a list of { feature, new_value }, applied together so the
// caller can see the combined effect of several changes at once.
export function whatIf(student, modifications) {
  return requestWithRetry(() =>
    client.post(
      '/what-if',
      { student, modifications },
      { timeout: COLD_START_ATTEMPT_TIMEOUT_MS }
    )
  );
}

export function getClusterProfiles() {
  return requestWithRetry(() =>
    client.get('/cluster-profiles', { timeout: COLD_START_ATTEMPT_TIMEOUT_MS })
  );
}

export default client;
