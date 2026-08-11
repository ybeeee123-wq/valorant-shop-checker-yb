import { NavLink } from 'react-router-dom';
import type { ReactNode } from 'react';
import type { Wallet } from '../types';
import WalletDisplay from './WalletDisplay';
import ThemeToggle from './ThemeToggle';
import Brand from './Brand';
import { BundleIcon, HeartIcon, HistoryIcon, LogoutIcon, NightMarketIcon, SettingsIcon, ShopIcon } from './Icons';

const navigation = [
  { to: '/shop', label: 'Shop', icon: ShopIcon },
  { to: '/bundles', label: 'Bundles', icon: BundleIcon },
  { to: '/wishlist', label: 'Wishlist', icon: HeartIcon },
  { to: '/history', label: 'History', icon: HistoryIcon },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
  { to: '/night-market', label: 'Night Market', icon: NightMarketIcon },
];

interface AppShellProps {
  children: ReactNode;
  wallet: Wallet | null;
  puuid: string | null;
  onLogout: () => void;
}

export default function AppShell({ children, wallet, puuid, onLogout }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <NavLink to="/shop" className="brand-link"><Brand /></NavLink>

          <nav className="desktop-nav" aria-label="Primary navigation">
            {navigation.map(({ to, label }) => (
              <NavLink key={to} to={to} className={({ isActive }) => `desktop-nav-link ${isActive ? 'is-active' : ''}`}>{label}</NavLink>
            ))}
          </nav>

          <div className="header-account">
            {wallet ? <WalletDisplay wallet={wallet} /> : <div className="wallet-loading" aria-hidden="true" />}
            <span className="header-divider" aria-hidden="true" />
            <ThemeToggle />
            <div className="account-copy">
              <span>Connected</span>
              <small>{puuid ? puuid.slice(0, 8) : 'Riot account'}</small>
            </div>
            <button type="button" onClick={onLogout} className="icon-button" aria-label="Log out of VALSHOP" title="Log out"><LogoutIcon className="h-[17px] w-[17px]" /></button>
          </div>
        </div>
      </header>

      <main className="app-main">{children}</main>
      <footer className="app-footer">Made by yb</footer>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        {navigation.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `mobile-nav-item ${isActive ? 'is-active' : ''}`}>
            <Icon className="h-[19px] w-[19px]" /><span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
