import type { CSSProperties } from 'react';
import type { SkinOffer } from '../types';
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

export default function SkinCard({ skin, index = 0 }: { skin: SkinOffer; index?: number }) {
  const tierColor = getTierColor(skin.content_tier_name, skin.content_tier_color);

  return (
    <article className="skin-card group" style={{ '--tier-color': tierColor, '--card-index': index } as CSSProperties}>
      <div className="skin-media">
        <span className="offer-number">0{index + 1}</span>
        {skin.display_icon ? (
          <img src={skin.display_icon} alt={skin.name} loading="eager" />
        ) : (
          <span className="image-fallback">Artwork unavailable</span>
        )}
        <span className="tier-bar" aria-hidden="true" />
      </div>
      <div className="skin-details">
        <div className="skin-copy">
          <span className="tier-label" style={{ color: tierColor }}>{skin.content_tier_name}</span>
          <h2>{skin.name}</h2>
        </div>
        <div className="skin-price" aria-label={`${skin.cost.toLocaleString()} Valorant Points`}>
          <VPIcon className="h-3.5 w-3.5" /><strong>{skin.cost.toLocaleString()}</strong>
        </div>
      </div>
    </article>
  );
}
