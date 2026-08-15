import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';
import * as api from '../api/client';
import type { SkinOffer, UserNotification, Wallet, WishlistItem } from '../types';
import WalletDisplay from './WalletDisplay';
import ThemeToggle from './ThemeToggle';
import Brand from './Brand';
import { BellIcon, BundleIcon, ChevronRightIcon, HeartIcon, HistoryIcon, LogoutIcon, NightMarketIcon, SettingsIcon, ShopIcon } from './Icons';

const navigation = [
  { to: '/shop', label: 'Shop', mobileLabel: 'Shop', icon: ShopIcon },
  { to: '/bundles', label: 'Bundles', mobileLabel: 'Bundles', icon: BundleIcon },
  { to: '/wishlist', label: 'Wishlist', mobileLabel: 'Wishlist', icon: HeartIcon },
  { to: '/history', label: 'History', mobileLabel: 'History', icon: HistoryIcon },
  { to: '/settings', label: 'Settings', mobileLabel: 'Settings', icon: SettingsIcon },
  { to: '/night-market', label: 'Night Market', mobileLabel: 'Market', icon: NightMarketIcon },
];

interface AppShellProps {
  children: ReactNode;
  wallet: Wallet | null;
  puuid: string | null;
  offers: SkinOffer[];
  onLogout: () => void;
}

export default function AppShell({ children, wallet, puuid, offers, onLogout }: AppShellProps) {
  const [notifications, setNotifications] = useState<UserNotification[]>([]);
  const [wishlist, setWishlist] = useState<WishlistItem[]>([]);
  const wishlistIds = useMemo(() => new Set(wishlist.map((item) => item.skin_uuid)), [wishlist]);
  const matches = useMemo(
    () => offers.filter((offer) => wishlistIds.has(offer.uuid)),
    [offers, wishlistIds],
  );
  const unread = notifications.filter((item) => !item.read_at).length;

  useEffect(() => {
    let active = true;
    void Promise.all([api.getNotifications(), api.getWishlist()]).then(([items, wanted]) => {
      if (!active) return;
      setNotifications(items);
      setWishlist(wanted);
    }).catch(() => undefined);
    return () => { active = false; };
  }, [offers]);

  async function markRead(item: UserNotification) {
    if (item.read_at) return;
    setNotifications((current) => current.map((entry) => (
      entry.id === item.id ? { ...entry, read_at: new Date().toISOString() } : entry
    )));
    await api.readNotification(item.id).catch(() => undefined);
  }

  async function markAllRead() {
    const readAt = new Date().toISOString();
    setNotifications((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? readAt })));
    await api.readAllNotifications().catch(() => undefined);
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="app-header">
        <div className="app-header-inner">
          <NavLink to="/shop" className="brand-link"><Brand /></NavLink>

          <nav className="desktop-nav" aria-label="Primary navigation">
            {navigation.map(({ to, label }, index) => (
              <NavLink key={to} to={to} data-index={`${index + 1}`.padStart(2, '0')} className={({ isActive }) => `desktop-nav-link ${isActive ? 'is-active' : ''}`}>{label}</NavLink>
            ))}
          </nav>

          <div className="header-account">
            {wallet ? <WalletDisplay wallet={wallet} /> : <div className="wallet-loading" aria-hidden="true" />}
            <span className="header-divider" aria-hidden="true" />
            <ThemeToggle />
            <details className="notification-menu">
              <summary className="icon-button" aria-label={`${unread} unread notifications`} title="Notifications">
                <BellIcon />{unread > 0 && <b>{unread > 9 ? '9+' : unread}</b>}
              </summary>
              <section className="notification-panel" aria-label="Notifications">
                <header><div><span>Activity</span><h2>Notifications</h2></div>{unread > 0 && <button type="button" onClick={() => void markAllRead()}>Mark all read</button>}</header>
                {notifications.length === 0 ? <p className="notification-empty">Wishlist matches will appear here.</p> : <div className="notification-list">
                  {notifications.map((item) => <Link key={item.id} to={item.target_url} className={item.read_at ? 'is-read' : ''} onClick={() => void markRead(item)}>
                    <div>{item.display_icon && <img src={item.display_icon} alt="" />}</div>
                    <span><strong>{item.title}</strong><small>{item.body}</small><time>{new Date(item.created_at).toLocaleString()}</time></span>
                  </Link>)}
                </div>}
              </section>
            </details>
            <div className="account-copy">
              <span>Connected</span>
              <small>{puuid ? puuid.slice(0, 8) : 'Riot account'}</small>
            </div>
            <button type="button" onClick={onLogout} className="icon-button" aria-label="Log out of VALSHOP" title="Log out"><LogoutIcon className="h-[17px] w-[17px]" /></button>
          </div>
        </div>
      </header>

      <main id="main-content" className="app-main">
        <div className="interface-rail" aria-hidden="true"><span>VALSHOP</span><i /><span>STORE INTELLIGENCE</span><i /><span>LIVE ACCOUNT</span></div>
        {matches.length > 0 && <section className="wishlist-hit" role="alert" aria-live="polite">
          <div className="wishlist-hit-art">{matches[0].display_icon && <img src={matches[0].display_icon} alt="" />}</div>
          <div className="wishlist-hit-copy"><span>Wishlist match · Live now</span><h2>{matches[0].name} is in your Daily Shop</h2><p>{matches[0].cost.toLocaleString()} VP{matches.length > 1 ? ` · Plus ${matches.length - 1} more saved ${matches.length === 2 ? 'skin' : 'skins'}.` : ' · Available until the next rotation.'}</p></div>
          <Link className="wishlist-hit-action" to={`/shop#skin-${matches[0].uuid}`}>View offer <ChevronRightIcon /></Link>
        </section>}
        {children}
      </main>
      <footer className="app-footer">Made by yb</footer>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        {navigation.map(({ to, label, mobileLabel, icon: Icon }) => (
          <NavLink key={to} to={to} aria-label={label} className={({ isActive }) => `mobile-nav-item ${isActive ? 'is-active' : ''}`}>
            <Icon className="h-[19px] w-[19px]" /><span>{mobileLabel}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
