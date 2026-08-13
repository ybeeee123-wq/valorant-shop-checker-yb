import { useCallback, useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import * as api from '../api/client';
import type { Bundle, NightMarketResponse, SkinOffer, Wallet } from '../types';
import AppShell from '../components/AppShell';
import BundleCard from '../components/BundleCard';
import CountdownTimer from '../components/CountdownTimer';
import EmptyState from '../components/EmptyState';
import { AlertIcon, RefreshIcon } from '../components/Icons';
import PageHeader from '../components/PageHeader';
import Reveal from '../components/Reveal';
import SkinCard from '../components/SkinCard';
import NightMarketCard from '../components/NightMarketCard';
import { HistoryView as PersistentHistoryView, SettingsView, WishlistView as PersistentWishlistView } from '../components/FeatureViews';

type View = 'shop' | 'bundles' | 'night-market' | 'wishlist' | 'history' | 'settings';

const viewFromPath: Record<string, View> = {
  '/shop': 'shop',
  '/bundles': 'bundles',
  '/night-market': 'night-market',
  '/wishlist': 'wishlist',
  '/history': 'history',
  '/settings': 'settings',
};

export default function ShopPage() {
  const { state, dispatch } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const view = viewFromPath[location.pathname];

  const [offers, setOffers] = useState<SkinOffer[]>([]);
  const [secondsRemaining, setSecondsRemaining] = useState(0);
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [nightMarket, setNightMarket] = useState<NightMarketResponse | null>(null);
  const [nightMarketLoading, setNightMarketLoading] = useState(true);
  const [nightMarketError, setNightMarketError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStoreData = useCallback(async (quiet = false) => {
    if (quiet) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const [dailyRes, bundleRes, walletRes] = await Promise.all([
        api.getDailyStore(),
        api.getBundles(),
        api.getWallet(),
      ]);
      setOffers(dailyRes.offers);
      setSecondsRemaining(dailyRes.seconds_remaining);
      setBundles(bundleRes.bundles);
      setWallet(walletRes);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load your storefront.';
      if (api.isAuthenticationError(err)) {
        dispatch({ type: 'LOGOUT' });
        navigate('/', { replace: true });
        return;
      }
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [dispatch, navigate]);

  const fetchNightMarket = useCallback(async () => {
    setNightMarketLoading(true);
    setNightMarketError(null);

    try {
      setNightMarket(await api.getNightMarket());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load the Night Market.';
      if (api.isAuthenticationError(err)) {
        dispatch({ type: 'LOGOUT' });
        navigate('/', { replace: true });
        return;
      }
      setNightMarketError(message);
    } finally {
      setNightMarketLoading(false);
    }
  }, [dispatch, navigate]);

  useEffect(() => { void fetchStoreData(); }, [fetchStoreData]);

  useEffect(() => {
    if (view === 'night-market') void fetchNightMarket();
  }, [fetchNightMarket, view]);

  useEffect(() => {
    if (!view) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reducedMotion ? 'auto' : 'smooth' });
    const title = view === 'night-market' ? 'Night Market' : `${view.charAt(0).toUpperCase()}${view.slice(1)}`;
    document.title = `${title} — VALSHOP`;
  }, [location.pathname, view]);

  async function handleLogout() {
    await api.logout().catch(() => undefined);
    dispatch({ type: 'LOGOUT' });
    navigate('/', { replace: true });
  }

  if (!view) return <Navigate to="/shop" replace />;

  return (
    <AppShell wallet={wallet} puuid={state.puuid} onLogout={handleLogout}>
      <div key={view} className="page-transition">
        {view === 'shop' && (
          <StoreView offers={offers} secondsRemaining={secondsRemaining} loading={loading} refreshing={refreshing} error={error} onRefresh={() => void fetchStoreData(true)} />
        )}
        {view === 'bundles' && <BundlesView bundles={bundles} loading={loading} error={error} onRetry={() => void fetchStoreData()} />}
        {view === 'night-market' && <NightMarketView nightMarket={nightMarket} loading={nightMarketLoading} error={nightMarketError} onRetry={() => void fetchNightMarket()} />}
        {view === 'wishlist' && <PersistentWishlistView today={offers} />}
        {view === 'history' && <PersistentHistoryView />}
        {view === 'settings' && <SettingsView />}
      </div>
    </AppShell>
  );
}

function NightMarketView({ nightMarket, loading, error, onRetry }: { nightMarket: NightMarketResponse | null; loading: boolean; error: string | null; onRetry: () => void }) {
  const active = nightMarket?.active ?? false;
  const offers = nightMarket?.offers ?? [];

  return (
    <>
      <Reveal direction="none"><PageHeader eyebrow="Personal offers" title="Night Market" description="A limited selection of skins, discounted just for you." /></Reveal>

      {!loading && !error && active && nightMarket && (
        <Reveal delay={60}><div className="timer-row"><CountdownTimer key={nightMarket.seconds_remaining} secondsRemaining={nightMarket.seconds_remaining} onExpire={onRetry} label="Market closes in" /></div></Reveal>
      )}

      {loading ? <NightMarketSkeleton /> : error ? <ErrorState message={error} onRetry={onRetry} /> : !active ? (
        <Reveal delay={100}><EmptyState icon={<AlertIcon className="h-7 w-7" />} label="Night Market" title="No Night Market is currently active" description="Your personalized Night Market will appear here when Riot opens the next event." /></Reveal>
      ) : offers.length === 0 ? (
        <Reveal delay={100}><EmptyState icon={<AlertIcon className="h-7 w-7" />} label="Night Market active" title="Offers are unavailable" description="Riot reports an active Night Market, but did not return any valid offers. Try again shortly." actionLabel="Try again" onAction={onRetry} /></Reveal>
      ) : (
        <section aria-label="Night Market offers" className="night-market-grid">
          {offers.map((offer, index) => <Reveal key={offer.bonus_offer_id} delay={100 + index * 70} className="h-full"><NightMarketCard offer={offer} index={index} /></Reveal>)}
        </section>
      )}
    </>
  );
}

interface StoreViewProps {
  offers: SkinOffer[];
  secondsRemaining: number;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  onRefresh: () => void;
}

function StoreView({ offers, secondsRemaining, loading, refreshing, error, onRefresh }: StoreViewProps) {
  return (
    <>
      <Reveal direction="none">
        <PageHeader
          eyebrow="Daily rotation"
          title="Your Daily Shop"
          description="Today’s four offers."
          compact
          action={<button type="button" onClick={onRefresh} disabled={loading || refreshing} className="secondary-button"><RefreshIcon className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />{refreshing ? 'Refreshing' : 'Refresh'}</button>}
        />
      </Reveal>

      {!loading && !error && <Reveal delay={60}><div className="timer-row"><CountdownTimer key={secondsRemaining} secondsRemaining={secondsRemaining} onExpire={onRefresh} /></div></Reveal>}

      {loading ? <StoreSkeleton /> : error ? <ErrorState message={error} onRetry={onRefresh} /> : offers.length === 0 ? (
        <EmptyState icon={<AlertIcon className="h-7 w-7" />} label="No offers returned" title="Your store is quiet" description="Riot did not return any daily offers. Refresh once, or check again after the next reset." actionLabel="Refresh store" onAction={onRefresh} />
      ) : (
        <section aria-label="Daily skin offers" className="skin-grid">
          {offers.map((skin, index) => <Reveal key={skin.uuid} delay={100 + index * 70} className="h-full"><SkinCard skin={skin} index={index} /></Reveal>)}
        </section>
      )}

    </>
  );
}

function BundlesView({ bundles, loading, error, onRetry }: { bundles: Bundle[]; loading: boolean; error: string | null; onRetry: () => void }) {
  return (
    <>
      <Reveal direction="none"><PageHeader eyebrow="Featured" title="Featured Bundles" description="Limited-time collections currently live in the VALORANT store." /></Reveal>
      {loading ? <BundleSkeleton /> : error ? <ErrorState message={error} onRetry={onRetry} /> : bundles.length === 0 ? (
        <EmptyState icon={<AlertIcon className="h-7 w-7" />} label="No featured collections" title="Nothing featured right now" description="There are no active bundles in the storefront. Check back after the next store update." />
      ) : (
        <section aria-label="Featured bundles" className="bundle-list">{bundles.map((bundle, index) => <Reveal key={`${bundle.uuid}-${bundle.duration_remaining_secs}`} delay={index * 100}><BundleCard bundle={bundle} /></Reveal>)}</section>
      )}
    </>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section className="error-state">
      <div>
        <AlertIcon className="h-7 w-7" />
        <h2>We couldn’t reach your store</h2>
        <p>{message}</p>
        <button type="button" onClick={onRetry} className="secondary-button"><RefreshIcon className="h-4 w-4" />Try again</button>
      </div>
    </section>
  );
}

function StoreSkeleton() {
  return (
    <div className="skeleton-wrap" aria-label="Loading daily offers">
      <div className="skeleton-timer" />
      <div className="skin-grid">
        {[0, 1, 2, 3].map((item) => <div key={item} className="skeleton-card"><div /><span /></div>)}
      </div>
    </div>
  );
}

function BundleSkeleton() {
  return <div className="bundle-skeleton" aria-label="Loading featured bundles" />;
}

function NightMarketSkeleton() {
  return (
    <div className="skeleton-wrap" aria-label="Loading Night Market offers">
      <div className="skeleton-timer" />
      <div className="night-market-grid">
        {[0, 1, 2, 3, 4, 5].map((item) => <div key={item} className="skeleton-card"><div /><span /></div>)}
      </div>
    </div>
  );
}
