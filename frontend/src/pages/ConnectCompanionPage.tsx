import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import * as api from '../api/client';
import Brand from '../components/Brand';
import ThemeToggle from '../components/ThemeToggle';

export default function ConnectCompanionPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const challenge = params.get('challenge') ?? '';
  const [device, setDevice] = useState('Windows PC');
  const [status, setStatus] = useState<'loading' | 'ready' | 'approved' | 'expired' | 'error'>(challenge ? 'loading' : 'expired');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!challenge) return;
    void api.getPairingStatus(challenge).then((result) => {
      setDevice(result.device_name || 'Windows PC');
      setStatus(result.status === 'expired' ? 'expired' : 'ready');
    }).catch((reason: Error) => { setError(reason.message); setStatus('error'); });
  }, [challenge]);

  async function approve() {
    try { await api.approvePairing(challenge); setStatus('approved'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Pairing failed'); setStatus('error'); }
  }

  return <div className="login-page"><header className="login-header"><Brand /><ThemeToggle /></header><main className="pairing-main"><section className="pairing-card"><p className="login-eyebrow">Secure device pairing</p><h1>Connect this PC?</h1>
    {status === 'loading' && <p>Checking the pairing request…</p>}
    {status === 'ready' && <><div className="pairing-device"><span>Requesting device</span><strong>{device}</strong></div><p>Only approve if VALSHOP is open on this computer. The permanent device credential is delivered directly to the desktop app and never placed in this URL.</p><div className="pairing-actions"><button className="primary-button" onClick={() => void approve()}>Connect this PC</button><button className="secondary-button" onClick={() => navigate('/shop')}>Cancel</button></div></>}
    {status === 'approved' && <><div className="pairing-success">Connected securely</div><p>You can close this browser tab. VALSHOP will finish setup automatically.</p></>}
    {status === 'expired' && <><h2>This pairing request expired</h2><p>Return to VALSHOP and start device connection again.</p></>}
    {status === 'error' && <><h2>Pairing could not be completed</h2><p>{error}</p></>}
  </section></main><footer className="login-footer"><span>Made by yb</span><span>Independent companion</span></footer></div>;
}
