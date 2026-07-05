import axios from 'axios';

// In development VITE_API_BASE_URL is empty and the Vite dev server proxies
// /api to the Flask app. In production it is set to the deployed API origin.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
});

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
    message: 'Could not reach the EduSense service. Please try again in a moment.',
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

export function getHealth() {
  return request(client.get('/health'));
}

export function predictStudent(profile) {
  return request(client.post('/predict', profile));
}

// modifications is a list of { feature, new_value }, applied together so the
// caller can see the combined effect of several changes at once.
export function whatIf(student, modifications) {
  return request(client.post('/what-if', { student, modifications }));
}

export function getClusterProfiles() {
  return request(client.get('/cluster-profiles'));
}

export default client;
