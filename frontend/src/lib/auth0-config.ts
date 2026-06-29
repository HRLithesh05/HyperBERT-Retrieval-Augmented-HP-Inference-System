/**
 * Auth0 configuration for HyperBERT.
 *
 * To set up Auth0:
 * 1. Go to https://auth0.com → Create Application → Single Page Web Application
 * 2. Set Allowed Callback URLs: http://localhost:5173
 * 3. Set Allowed Logout URLs: http://localhost:5173
 * 4. Set Allowed Web Origins: http://localhost:5173
 * 5. Copy the Domain and Client ID to your .env file
 *
 * Create a .env file in the frontend/ directory with:
 *   VITE_AUTH0_DOMAIN=your-tenant.us.auth0.com
 *   VITE_AUTH0_CLIENT_ID=your-client-id
 */

export const auth0Config = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN || '',
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID || '',
  authorizationParams: {
    redirect_uri: typeof window !== 'undefined' ? window.location.origin : '',
  },
};

/** Whether Auth0 is configured (domain + clientId provided) */
export const isAuthConfigured =
  !!auth0Config.domain && !!auth0Config.clientId;
