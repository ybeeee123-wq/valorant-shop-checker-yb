import { useEffect, useMemo, useState } from 'react';
import * as api from '../api/client';
import type { CompanionStatus, HistorySnapshot, NotificationPreferences, SkinCatalogItem, SkinOffer, WishlistItem } from '../types';
import { HeartIcon, HistoryIcon, VPIcon } from './Icons';
import EmptyState from './EmptyState';
import PageHeader from './PageHeader';
import Reveal from './Reveal';

export function WishlistView({ today }: { today: SkinOffer[] }) {
  const [query, setQuery] = useState('');
  const [skins, setSkins] = useState<SkinCatalogItem[]>([]);
  const [wishlist, setWishlist] = useState<WishlistItem[]>([]);
  const [catalogError, setCatalogError] = useState('');
  const [wishlistError, setWishlistError] = useState('');
  const [mutationError, setMutationError] = useState('');
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<Set<string>>(() => new Set());
  const wanted = useMemo(() => new Set(wishlist.map((item) => item.skin_uuid)), [wishlist]);
  const todayIds = useMemo(() => new Set(today.map((item) => item.uuid)), [today]);

  useEffect(() => {
    let active = true;
    void api.getWishlist()
      .then((items) => { if (active) setWishlist(items); })
      .catch((e: Error) => { if (active) setWishlistError(e.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      setLoading(true);
      setCatalogError('');
      void api.getSkins(query, '', controller.signal)
        .then(setSkins)
        .catch((e: Error) => { if (e.name !== 'AbortError') setCatalogError(e.message); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 220);
    return () => { window.clearTimeout(timeout); controller.abort(); };
  }, [query]);

  async function toggle(skin: SkinCatalogItem) {
    if (pending.has(skin.uuid)) return;
    setPending((items) => new Set(items).add(skin.uuid));
    setMutationError('');
    try {
      if (wanted.has(skin.uuid)) {
        await api.removeWishlist(skin.uuid);
        setWishlist((items) => items.filter((item) => item.skin_uuid !== skin.uuid));
      } else {
        const item = await api.addWishlist(skin.uuid);
        setWishlist((items) => [item, ...items]);
      }
    } catch (e) {
      setMutationError(e instanceof Error ? e.message : 'Could not update your wishlist.');
    } finally {
      setPending((items) => {
        const next = new Set(items);
        next.delete(skin.uuid);
        return next;
      });
    }
  }

  return (
    <>
      <Reveal direction="none"><PageHeader eyebrow="Persistent tracking" title="Wishlist" description="Search the collection and get notified when a saved skin reaches your daily shop." /></Reveal>
      <div className="feature-toolbar"><input className="feature-input" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search skins by name" aria-label="Search skins" autoComplete="off" /><span aria-live="polite">{wishlist.length} saved</span></div>
      {(mutationError || wishlistError || catalogError) && <p className="feature-error" role="alert">{mutationError || wishlistError || catalogError}</p>}
      {wishlist.some((item) => todayIds.has(item.skin_uuid)) && <div className="match-banner"><HeartIcon className="h-5 w-5" /><span>A wishlist skin is in today’s shop.</span></div>}
      {loading ? <CatalogSkeleton /> : skins.length === 0 ? <EmptyState icon={<HeartIcon className="h-7 w-7" />} label="No matching skins" title="Try another search" description="No collection items match that name." /> : <section className="catalog-grid" aria-label="Skin collection">
        {skins.map((skin, index) => (
          <Reveal key={skin.uuid} delay={Math.min(index * 25, 250)} className="h-full"><article className={`catalog-card ${todayIds.has(skin.uuid) ? 'is-match' : ''}`}>
            <div className="catalog-art">{skin.display_icon ? <img src={skin.display_icon} alt={skin.name} loading="lazy" /> : <span>Artwork unavailable</span>}</div>
            <div className="catalog-copy"><span>{skin.content_tier_name} · {skin.weapon}</span><h2>{skin.name}</h2>{todayIds.has(skin.uuid) && <b>In your shop</b>}</div>
            <button type="button" className={wanted.has(skin.uuid) ? 'wishlist-button is-saved' : 'wishlist-button'} onClick={() => void toggle(skin)} disabled={pending.has(skin.uuid)} aria-pressed={wanted.has(skin.uuid)} aria-label={`${wanted.has(skin.uuid) ? 'Remove' : 'Add'} ${skin.name}`}><HeartIcon className="h-4 w-4" />{pending.has(skin.uuid) ? 'Updating' : wanted.has(skin.uuid) ? 'Saved' : 'Save'}</button>
          </article></Reveal>
        ))}
      </section>}
    </>
  );
}

export function HistoryView() {
  const [history, setHistory] = useState<HistorySnapshot[] | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    void api.getHistory()
      .then((snapshots) => { if (active) setHistory(snapshots); })
      .catch((e: Error) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  return (
    <>
      <Reveal direction="none"><PageHeader eyebrow="Persistent archive" title="Shop History" description="Every successful daily rotation sync, saved with the artwork and price seen at the time." /></Reveal>
      {error ? <p className="feature-error" role="alert">{error}</p> : history === null ? <HistorySkeleton /> : history.length === 0 ? <EmptyState icon={<HistoryIcon className="h-7 w-7" />} label="No snapshots yet" title="Your first sync will appear here" description="Open the daily shop or run the companion to save the current rotation." /> : <div className="history-list">
        {history.map((snapshot) => <Reveal key={snapshot.rotation_key}><section className="history-snapshot"><header><div><span>Daily rotation</span><h2>{new Date(snapshot.fetched_at).toLocaleString()}</h2></div><small>{snapshot.offers.length} offers</small></header><div className="history-offers">{snapshot.offers.map((offer) => <article key={offer.skin_uuid}><div>{offer.display_icon ? <img src={offer.display_icon} alt="" loading="lazy" /> : null}</div><span>{offer.skin_name}</span><strong><VPIcon className="h-3 w-3" />{offer.vp_cost.toLocaleString()}</strong></article>)}</div></section></Reveal>)}
      </div>}
    </>
  );
}

function CatalogSkeleton() {
  return <div className="catalog-grid" aria-label="Loading skin collection" aria-busy="true">{[0, 1, 2, 3, 4, 5, 6, 7].map((item) => <div key={item} className="catalog-card catalog-skeleton" aria-hidden="true"><div /><span /></div>)}</div>;
}

function HistorySkeleton() {
  return <div className="history-skeleton" role="status" aria-label="Loading shop history"><span /><div /></div>;
}

function applicationServerKey(value: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - value.length % 4) % 4);
  const raw = atob((value + padding).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(raw, (character) => character.charCodeAt(0));
}

export function SettingsView() {
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);
  const [status, setStatus] = useState<CompanionStatus | null>(null);
  const [webhook, setWebhook] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    void Promise.all([api.getNotificationPreferences(), api.getCompanionStatus()])
      .then(([preferences, companion]) => {
        if (!active) return;
        setPrefs(preferences);
        setStatus(companion);
      })
      .catch((e: Error) => { if (active) setMessage(e.message); });
    return () => { active = false; };
  }, []);

  async function runAction(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setMessage('');
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'That action could not be completed.');
    } finally {
      setBusy(false);
    }
  }

  async function save(overrides: Partial<NotificationPreferences> = {}) {
    if (!prefs) return;
    const next = { ...prefs, ...overrides };
    const updated = await api.updateNotificationPreferences({ web_push_enabled: next.web_push_enabled, discord_enabled: next.discord_enabled, discord_webhook_url: webhook || null, notify_only_wishlist_matches: true });
    setPrefs(updated); setWebhook(''); setMessage('Preferences saved.');
  }

  async function enablePush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) { setMessage('Web Push is not supported in this browser.'); return; }
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') { setMessage('Notification permission was not granted.'); return; }
    const registration = await navigator.serviceWorker.ready;
    const { public_key } = await api.getVapidPublicKey();
    if (!public_key) { setMessage('VAPID is not configured on the backend.'); return; }
    const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: applicationServerKey(public_key) });
    await api.subscribePush(subscription.toJSON()); await save({ web_push_enabled: true });
  }

  async function disablePush() {
    const registration = await navigator.serviceWorker?.ready;
    const subscription = await registration?.pushManager.getSubscription();
    if (subscription) {
      await api.unsubscribePush(subscription.endpoint);
      await subscription.unsubscribe();
    }
    await save({ web_push_enabled: false });
  }

  async function removeDiscord() {
    if (!prefs) return;
    const updated = await api.updateNotificationPreferences({
      web_push_enabled: prefs.web_push_enabled, discord_enabled: false,
      remove_discord_webhook: true, notify_only_wishlist_matches: true,
    });
    setPrefs(updated); setMessage('Discord webhook removed.');
  }

  async function revokeCompanion() {
    await api.revokeCompanion();
    setStatus({ registered: false, online: false, device_name: null, last_seen_at: null, last_successful_sync_at: null, reauth_required: false });
    setMessage('All companion access revoked.');
  }

  async function sendTest(channel: 'web_push' | 'discord') {
    await api.testNotification(channel);
    setMessage(channel === 'web_push' ? 'Test push sent.' : 'Discord test sent.');
  }

  return (
    <>
      <Reveal direction="none"><PageHeader eyebrow="Delivery & background sync" title="Notifications" description="Choose how VALSHOP reaches you and connect the optional Windows companion." /></Reveal>
      {message && <div className="settings-message" role="status" aria-live="polite">{message}</div>}
      <div className="settings-grid">
        <section className="settings-card"><span>Web Push</span><h2>Browser notifications</h2><p>Works when the site is closed, provided your browser allows background notifications.</p><div className="settings-actions"><button className="secondary-button" type="button" disabled={!prefs || busy} onClick={() => void runAction(enablePush)}>{busy ? 'Working' : prefs?.web_push_enabled ? 'Refresh subscription' : 'Enable Web Push'}</button>{prefs?.web_push_enabled && <button className="text-button" type="button" disabled={busy} onClick={() => void runAction(disablePush)}>Disable</button>}<button className="text-button" type="button" disabled={!prefs?.web_push_enabled || busy} onClick={() => void runAction(() => sendTest('web_push'))}>Send test</button></div></section>
        <section className="settings-card"><span>Discord</span><h2>Private webhook</h2><p>The webhook is encrypted before storage and is never returned to the browser.</p><label className="sr-only" htmlFor="discord-webhook">Discord webhook URL</label><input id="discord-webhook" className="feature-input" type="url" value={webhook} onChange={(e) => setWebhook(e.target.value)} placeholder={prefs?.discord_configured ? 'Webhook configured — paste to replace' : 'https://discord.com/api/webhooks/...'} autoComplete="off" /><div className="settings-actions"><button className="secondary-button" type="button" disabled={!prefs || !webhook.trim() || busy} onClick={() => void runAction(() => save({ discord_enabled: true }))}>Save & enable</button>{prefs?.discord_configured && <button className="text-button" type="button" disabled={busy} onClick={() => void runAction(removeDiscord)}>Remove</button>}<button className="text-button" type="button" disabled={!prefs?.discord_configured || busy} onClick={() => void runAction(() => sendTest('discord'))}>Send test</button></div></section>
        <section className="settings-card companion-card"><span>Windows companion</span><h2>{status === null ? 'Checking connection' : status.online ? 'Online' : status.registered ? 'Currently offline' : 'Not connected'}</h2><p>{status?.reauth_required ? 'Riot authentication is required again.' : status?.last_successful_sync_at ? `Last synced ${new Date(status.last_successful_sync_at).toLocaleString()}.` : 'Open the installed VALSHOP app and choose Connect cloud account. Pairing never asks you to copy a token.'}</p>{status?.registered && <button className="text-button" type="button" disabled={busy} onClick={() => void runAction(revokeCompanion)}>Revoke all companion devices</button>}</section>
      </div>
    </>
  );
}
