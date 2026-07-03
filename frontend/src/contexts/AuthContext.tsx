/**
 * AuthContext — Auth0 Authentication provider.
 * Wraps the app in Auth0Provider and exposes auth state + helpers.
 *
 * Credentials in frontend/.env:
 *   VITE_AUTH0_DOMAIN=dev-iutbwvtqrluinf71.us.auth0.com
 *   VITE_AUTH0_CLIENT_ID=m345VQTMFb82eJDZ2SEPxY4nEab8Z8oy
 */
import { createContext, useContext, type ReactNode } from 'react';
import { Auth0Provider, useAuth0, type User } from '@auth0/auth0-react';

interface AuthState {
  user: User | undefined;
  isAuthenticated: boolean;
  isLoading: boolean;
  loginWithGoogle: () => void;
  logout: () => void;
  getAccessToken: () => Promise<string>;
}

const AuthContext = createContext<AuthState>({
  user: undefined,
  isAuthenticated: false,
  isLoading: true,
  loginWithGoogle: () => {},
  logout: () => {},
  getAccessToken: async () => '',
});

const domain = import.meta.env.VITE_AUTH0_DOMAIN || '';
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID || '';

/** Check if Auth0 is configured (credentials present) */
export function isAuthConfigured(): boolean {
  return !!(domain && clientId);
}

function AuthContextBridge({ children }: { children: ReactNode }) {
  const {
    user,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout: auth0Logout,
    getAccessTokenSilently,
  } = useAuth0();

  const loginWithGoogle = () => {
    loginWithRedirect({
      authorizationParams: {
        connection: 'google-oauth2',
      },
    });
  };

  const logout = () => {
    auth0Logout({
      logoutParams: {
        returnTo: window.location.origin,
      },
    });
  };

  const getAccessToken = async () => {
    try {
      return await getAccessTokenSilently();
    } catch {
      return '';
    }
  };

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated, isLoading, loginWithGoogle, logout, getAccessToken }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // If Auth0 isn't configured, render children directly (dev mode — no gating)
  if (!isAuthConfigured()) {
    return (
      <AuthContext.Provider
        value={{
          user: undefined,
          isAuthenticated: false,
          isLoading: false,
          loginWithGoogle: () => console.warn('Auth0 not configured'),
          logout: () => {},
          getAccessToken: async () => '',
        }}
      >
        {children}
      </AuthContext.Provider>
    );
  }

  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
      }}
    >
      <AuthContextBridge>{children}</AuthContextBridge>
    </Auth0Provider>
  );
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
