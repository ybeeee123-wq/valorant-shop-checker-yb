import type { SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement>;

const baseProps: IconProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
};

export function ShopIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M4 8.5h16l-1 11H5l-1-11Z" /><path d="M8.5 8.5V7a3.5 3.5 0 0 1 7 0v1.5" /></svg>;
}

export function BundleIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" /><path d="m4.3 7.7 7.7 4.4 7.7-4.4M12 12.1V21" /></svg>;
}

export function NightMarketIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M20 15.2A8.7 8.7 0 0 1 8.8 4a8.7 8.7 0 1 0 11.2 11.2Z" /><path d="m15.5 4 .5 1.5 1.5.5-1.5.5-.5 1.5-.5-1.5-1.5-.5 1.5-.5.5-1.5Z" /></svg>;
}

export function SettingsIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M4 7h10M18 7h2M4 12h2M10 12h10M4 17h7M15 17h5" /><circle cx="16" cy="7" r="2" /><circle cx="8" cy="12" r="2" /><circle cx="13" cy="17" r="2" /></svg>;
}

export function HeartIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M20.8 4.8a5.5 5.5 0 0 0-7.8 0L12 5.9l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.3 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z" /></svg>;
}

export function HistoryIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 7v5l3 2" /></svg>;
}

export function RefreshIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M20 6v5h-5M4 18v-5h5" /><path d="M18.1 9A7 7 0 0 0 6.4 6.4L4 8m16 8-2.4 1.6A7 7 0 0 1 5.9 15" /></svg>;
}

export function LogoutIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M10 17l5-5-5-5M15 12H3M14 4h5a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-5" /></svg>;
}

export function ShieldIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-4" /></svg>;
}

export function ClockIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
}

export function ChevronRightIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="m9 18 6-6-6-6" /></svg>;
}

export function AlertIcon(props: IconProps) {
  return <svg {...baseProps} {...props}><path d="M10.3 3.8 2.2 18a2 2 0 0 0 1.7 3h16.2a2 2 0 0 0 1.7-3L13.7 3.8a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></svg>;
}

export function VPIcon(props: IconProps) {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}><path d="M3 5.5 10.1 19h3.8L21 5.5h-4.2L12 15 7.2 5.5H3Z" fill="currentColor" /></svg>;
}

export function RadianiteIcon(props: IconProps) {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}><path d="m12 2 8.7 5v10L12 22l-8.7-5V7L12 2Z" stroke="currentColor" strokeWidth="2" /><path d="m8.2 8.1 7.6 7.8M15.8 8.1l-7.6 7.8" stroke="currentColor" strokeWidth="2" /></svg>;
}
