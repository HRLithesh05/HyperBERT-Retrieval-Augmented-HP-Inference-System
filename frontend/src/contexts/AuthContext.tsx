/**
 * AuthContext — Auth0 Authentication provider with guest limits.
 * 
 * Guest limits (like ChatGPT):
 *   - 5 papers can be analyzed without signing in
 *   - Notebook launch and analysis history require sign-in
 *
 * Credentials in frontend/.env:
 *   VITE_AUTH0_DOMAIN=dev-iutbwvtqrluinf71.us.auth0.com
 *   VITE_AUTH0_CLIENT_ID=m345VQTMFb82eJDZ2SEPxY4nEab8Z8oy
 */
import { createContext, useContext, type ReactNode } from 'react';
import { Auth0Provider, useAuth0, type User } from '@auth0/auth0-react';
import { useSession } from './SessionContext';

const domain = import.meta.env.VITE_AUTH0_DOMAIN || '';
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID || '';
export const GUEST_PAPER_LIMIT = 5;

interface AuthState {
  user: User | undefined;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** true when user is not signed in */
  isGuest: boolean;
  /** true when guest still has free papers remaining, or is authenticated */
  canAnalyze: boolean;
  /** number of free papers remaining for guest */
  remainingFree: number;
  loginWithGoogle: () => void;
  loginWithPopup: () => Promise<void>;
  logout: () => void;
  getAccessToken: () => Promise<string>;
}

const AuthContext = createContext<AuthState>({
  user: undefined,
  isAuthenticated: false,
  isLoading: true,
  isGuest: true,
  canAnalyze: true,
  remainingFree: GUEST_PAPER_LIMIT,
  loginWithGoogle: () => {},
  loginWithPopup: async () => {},
  logout: () => {},
  getAccessToken: async () => '',
});

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
    loginWithPopup: auth0Popup,
    logout: auth0Logout,
    getAccessTokenSilently,
  } = useAuth0();

  const { guestUsageCount } = useSession();

  const isGuest = !isAuthenticated;
  const remainingFree = Math.max(0, GUEST_PAPER_LIMIT - guestUsageCount);
  const canAnalyze = isAuthenticated || guestUsageCount < GUEST_PAPER_LIMIT;

  const loginWithGoogle = () => {
    loginWithRedirect({
      authorizationParams: {
        connection: 'google-oauth2',
      },
    });
  };

  const loginWithPopup = async () => {
    try {
      await auth0Popup();
    } catch (e) {
      console.error('Auth0 popup login error:', e);
    }
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
      value={{
        user, isAuthenticated, isLoading, isGuest, canAnalyze, remainingFree,
        loginWithGoogle, loginWithPopup, logout, getAccessToken,
      }}
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
          isGuest: true,
          canAnalyze: true,
          remainingFree: GUEST_PAPER_LIMIT,
          loginWithGoogle: () => console.warn('Auth0 not configured'),
          loginWithPopup: async () => console.warn('Auth0 not configured'),
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
