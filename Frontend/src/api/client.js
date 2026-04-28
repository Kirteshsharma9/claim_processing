const BASE_URL = 'http://0.0.0.0:8000/api/v1';

async function fetchAPI(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });
  
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error ${response.status}: ${errorBody}`);
  }
  
  return response.json();
}

export const api = {
  // Members
  getMembers: () => fetchAPI('/members'),
  createMember: (data) => fetchAPI('/members', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  
  // Policies
  getPolicies: () => fetchAPI('/policies'), // Note: API might not have list_policies endpoint natively if we check the openapi.json. Let's assume it doesn't or we mock fetching all policies from members if necessary. Wait, looking at openapi.json, there is NO `GET /api/v1/policies`. There is `POST /api/v1/policies`, `GET /api/v1/policies/{policy_id}`, and `GET /api/v1/members/{member_id}/policy`.
  // To handle PoliciesView listing, we might have to store them in Context when created or fetch per member if possible.
  createPolicy: (data) => fetchAPI('/policies', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  
  // Claims
  submitClaim: (data) => fetchAPI('/claims', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getClaimAdjudication: (claimId) => fetchAPI(`/claims/${claimId}/adjudication`),
  getClaimExplanation: (claimId) => fetchAPI(`/claims/${claimId}/explanation`),
  getMemberClaims: (memberId) => fetchAPI(`/members/${memberId}/claims`),
  
  // Disputes
  createDispute: (claimId, data) => fetchAPI(`/claims/${claimId}/disputes`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getClaimDisputes: (claimId) => fetchAPI(`/claims/${claimId}/disputes`),
};
