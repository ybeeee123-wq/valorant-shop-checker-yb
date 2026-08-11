import {
  createContext,
  useContext,
  useEffect,
  useReducer,
  type Dispatch,
  type ReactNode,
} from 'react';
import type { AuthAction, AuthState } from '../types';
import * as api from '../api/client';

const initialState: AuthState = {
  status: 'idle',
  sessionValid: false,
  puuid: null,
  error: null,
};

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN_START':
      return { ...state, status: 'loading', error: null };
    case 'LOGIN_SUCCESS':
      return {
        status: 'authenticated',
        sessionValid: true,
        puuid: action.puuid,
        error: null,
      };
    case 'LOGIN_ERROR':
      return { ...state, status: 'error', error: action.error };
    case 'LOGOUT':
      api.clearToken();
      return { ...initialState };
    case 'SESSION_RESTORED':
      return {
        status: 'authenticated',
        sessionValid: true,
        puuid: action.puuid,
        error: null,
      };
  }
}

const AuthContext = createContext<{
  state: AuthState;
  dispatch: Dispatch<AuthAction>;
}>({
  state: initialState,
  dispatch: () => undefined,
});

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  const callbackToken = params.get('session_token');

  if (callbackToken) {
    api.storeToken(callbackToken);

    // Remove the token from the visible URL
    window.history.replaceState({}, '', window.location.pathname);
  }

  const token = callbackToken ?? api.getStoredToken();

  if (!token) return;

  api.checkSession()
    .then((res) => {
      if (res.valid && res.puuid) {
        dispatch({
          type: 'SESSION_RESTORED',
          puuid: res.puuid,
        });
      } else {
        api.clearToken();
      }
    })
    .catch(() => {
      api.clearToken();
    });
}, []);

  return (
    <AuthContext.Provider value={{ state, dispatch }}>
      {children}
    </AuthContext.Provider>
  );
}
