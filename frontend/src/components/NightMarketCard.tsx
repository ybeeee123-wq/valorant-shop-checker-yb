import type { CSSProperties } from 'react';
import type { NightMarketOffer } from '../types';
import { VPIcon } from './Icons';

const TIER_COLOR_MAP: Record<string, string> = {
  select: '#4f88b8',
  deluxe: '#268e7d',
  premium: '#b84e7e',
  ultra: '#aa7e18',
  exclusive: '#c46432',
};

function getTierColor(tierName: string, apiColor: string): string {
  const key = tierName.toLowerCase().replace(/\s*edition$/i, '');
  const normalizedApiColor = apiColor.replace('#', '').slice(0, 6);
  return TIER_COLOR_MAP[key] || (/^[0-9a-f]{6}$/i.test(normalizedApiColor) ? `#${normalizedApiColor}` : '#6f756f');
}

export default function NightMarketCard({ offer, index }: { offer: NightMarketOffer; index: number }) {
  const tierColor = getTierColor(offer.content_tier_name, offer.content_tier_color);

  return (
    <article className="night-market-card" style={{ '--tier-color': tierColor } as CSSProperties}>
      <div className="night-market-media">
        <span className="offer-number">0{index + 1}</span>
        <span className="night-market-discount">-{offer.discount_percent}%</span>
        {offer.display_icon ? (
          <img src={offer.display_icon} alt={offer.name} loading="eager" />
        ) : (
          <span className="image-fallback">Artwork unavailable</span>
        )}
        <span className="tier-bar" aria-hidden="true" />
      </div>
      <div className="night-market-details">
        <div className="skin-copy">
          <span className="tier-label" style={{ color: tierColor }}>{offer.content_tier_name}</span>
          <h2>{offer.name}</h2>
        </div>
        <div className="night-market-pricing" aria-label={`${offer.discounted_cost.toLocaleString()} Valorant Points, discounted from ${offer.original_cost.toLocaleString()}`}>
          <span className="night-market-original"><VPIcon className="h-3 w-3" />{offer.original_cost.toLocaleString()}</span>
          <strong><VPIcon className="h-4 w-4" />{offer.discounted_cost.toLocaleString()}</strong>
        </div>
      </div>
    </article>
  );
}
