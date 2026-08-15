import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import * as api from '../api/client';
import { ChevronRightIcon, DownloadIcon, ShieldIcon } from '../components/Icons';
import ThemeToggle from '../components/ThemeToggle';
import Brand from '../components/Brand';

type Stage = 'start' | 'paste';

const INSTALLER_URL = import.meta.env.VITE_INSTALLER_URL
  ?? 'https://github.com/ybeeee123-wq/valorant-shop-checker-yb/releases/latest/download/VALSHOP-Setup.exe';

export default function LoginPage() {
  const { state, dispatch } = useAuth();
  const navigate = useNavigate();
  const [stage, setStage] = useState<Stage>(() => (sessionStorage.getItem('login_stage') === 'paste' ? 'paste' : 'start'));
  const [pastedUrl, setPastedUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { document.title = 'VALSHOP — Daily Store Checker'; }, []);

  if (state.status === 'authenticated') return <Navigate to={sessionStorage.getItem('post_login_path') ?? '/shop'} replace />;
  if (state.status === 'checking') return <div className="route-loader" role="status" aria-live="polite"><span aria-hidden="true" />Checking your session</div>;

  async function handleOpenLogin() {
    setLoading(true);
    setError(null);
    try {
      const { auth_url } = await api.getAuthUrl();
      window.open(auth_url, '_blank', 'noopener');
      sessionStorage.setItem('login_stage', 'paste');
      setStage('paste');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start login');
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitUrl(event: React.FormEvent) {
    event.preventDefault();
    if (!pastedUrl.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.submitToken(pastedUrl.trim());
      if (res.status === 'success' && res.puuid && res.session_token) {
        sessionStorage.removeItem('login_stage');
        api.storeToken(res.session_token);
        dispatch({ type: 'LOGIN_SUCCESS', puuid: res.puuid });
        const destination = sessionStorage.getItem('post_login_path') ?? '/shop';
        sessionStorage.removeItem('post_login_path');
        navigate(destination);
      } else {
        setError(res.error ?? 'Authentication failed');
        setLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to authenticate');
      setLoading(false);
    }
  }

  function handleBack() {
    sessionStorage.removeItem('login_stage');
    setStage('start');
    setPastedUrl('');
    setError(null);
  }

  return (
    <div className="login-page">
      <header className="login-header">
        <Brand />
        <div className="login-header-actions"><span className="login-header-note"><i />Independent companion</span><ThemeToggle /></div>
      </header>

      <main className="login-main">
        <section className="login-panel">
          <p className="login-eyebrow">The VALORANT shop companion</p>
          <h1>Your shop.<br />Always within reach.</h1>
          <p className="login-intro">See your daily offers, Night Market, bundles, wishlist, and balance from any browser. Connect Riot once to get started.</p>

          {stage === 'start' ? (
            <div className="login-action-block">
              <button type="button" onClick={handleOpenLogin} disabled={loading} className="primary-button login-button" aria-busy={loading}>
                {loading ? <Spinner /> : <span className="button-dot" />}
                <span>Sign in with Riot</span>
                {!loading && <ChevronRightIcon className="h-4 w-4" />}
              </button>
              <a className="installer-button" href={INSTALLER_URL}>
                <DownloadIcon className="h-4 w-4" />
                <span><strong>Install for Windows</strong><small>Background checks and native alerts</small></span>
                <span className="installer-meta">Windows 10/11</span>
              </a>
              <div className="security-note">
                <ShieldIcon className="h-[18px] w-[18px]" />
                <p><strong>Private by design.</strong> Authentication happens on Riot’s official page. VALSHOP never sees your password.</p>
              </div>
              {error && <p role="alert" className="login-error">{error}</p>}
            </div>
          ) : (
            <div className="login-action-block stage-enter">
              <div className="fallback-intro">
                <span>Fallback sign-in</span>
                <p>After signing in with Riot, the callback usually returns automatically. If it didn’t, paste the full localhost URL below.</p>
              </div>
              <form onSubmit={handleSubmitUrl} className="callback-form">
                <label htmlFor="riot-callback-url">Riot callback URL</label>
                <textarea id="riot-callback-url" value={pastedUrl} onChange={(event) => setPastedUrl(event.target.value)} placeholder="http://localhost/redirect#..." rows={3} className="login-input" />
                <button type="submit" disabled={loading || !pastedUrl.trim()} className="primary-button login-button" aria-busy={loading}>
                  {loading && <Spinner />}Complete sign in<ChevronRightIcon className="h-4 w-4" />
                </button>
              </form>
              {error && <p role="alert" className="login-error">{error}</p>}
              <button type="button" onClick={handleBack} className="text-button">Start over</button>
            </div>
          )}
        </section>

        <aside className="login-preview" aria-label="How to start using VALSHOP">
          <div className="preview-topline"><span>Get started</span><span>About 2 minutes</span></div>
          <ol className="onboarding-steps">
            <li><i>01</i><div><strong>Sign in through Riot</strong><p>Use Riot’s official login page. Your password never passes through VALSHOP.</p></div></li>
            <li><i>02</i><div><strong>Open your shop anywhere</strong><p>Your daily offers, bundles, wishlist, and Night Market live on this website.</p></div></li>
            <li><i>03</i><div><strong>Install the companion</strong><p>Optional, but recommended for automatic checks and Windows notifications.</p></div></li>
          </ol>
          <div className="preview-trust"><ShieldIcon className="h-5 w-5" /><span><strong>Built for privacy</strong>Independent, password-free Riot connection.</span></div>
        </aside>
      </main>

      <footer className="login-footer">
        <span>Made by yb</span>
      </footer>
    </div>
  );
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.4 0 0 5.4 0 12h4Z" />
    </svg>
  );
}
