/**
 * AuthContext — Auth0 Authentication provider with guest limits.
 * 
 * Guest limits (like ChatGPT):
 *   - 5 papers can be analyzed without signing in
 *   - Notebook launch and analysis history require sign-in
 *
 * Auth flow: Uses loginWithPopup for inline sign-in (no page redirect).
 * This keeps the user on the current page after signing in.
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
  isGuest: boolean;
  canAnalyze: boolean;
  remainingFree: number;
  /** Opens a popup for Google sign-in (stays on current page) */
  loginWithGoogle: () => Promise<void>;
  /** Opens a popup for any sign-in method */
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
  loginWithGoogle: async () => {},
  loginWithPopup: async () => {},
  logout: () => {},
  getAccessToken: async () => '',
});

export function isAuthConfigured(): boolean {
  return !!(domain && clientId);
}

function AuthContextBridge({ children }: { children: ReactNode }) {
  const {
    user,
    isAuthenticated,
    isLoading,
    loginWithPopup: auth0Popup,
    logout: auth0Logout,
    getAccessTokenSilently,
  } = useAuth0();

  const { guestUsageCount } = useSession();

  const isGuest = !isAuthenticated;
  const remainingFree = Math.max(0, GUEST_PAPER_LIMIT - guestUsageCount);
  const canAnalyze = isAuthenticated || guestUsageCount < GUEST_PAPER_LIMIT;

  // Use POPUP for Google sign-in — user stays on the current page
  const loginWithGoogle = async () => {
    try {
      await auth0Popup({
        authorizationParams: {
          connection: 'google-oauth2',
        },
      });
    } catch (e) {
      console.error('Auth0 Google login error:', e);
    }
  };

  // Generic popup login
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
          loginWithGoogle: async () => console.warn('Auth0 not configured'),
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
