import type { CSSProperties } from 'react';
import type { NightMarketOffer } from '../types';
import { getContentTierColor } from '../utils/contentTier';
import { VPIcon } from './Icons';

export default function NightMarketCard({ offer, index }: { offer: NightMarketOffer; index: number }) {
  const tierColor = getContentTierColor(offer.content_tier_name, offer.content_tier_color);

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
