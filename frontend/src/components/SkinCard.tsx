import type { CSSProperties } from 'react';
import type { SkinOffer } from '../types';
import { getContentTierColor } from '../utils/contentTier';
import { PlayIcon, VPIcon } from './Icons';
import * as api from '../api/client';

export default function SkinCard({ skin, index = 0, onPreview }: { skin: SkinOffer; index?: number; onPreview: () => void }) {
  const tierColor = getContentTierColor(skin.content_tier_name, skin.content_tier_color);

  return (
    <article className="skin-card group" style={{ '--tier-color': tierColor, '--card-index': index } as CSSProperties}>
      <div className="skin-media">
        <span className="offer-number">0{index + 1}</span>
        {skin.display_icon ? (
          <img src={skin.display_icon} alt={skin.name} loading="eager" decoding="async" fetchPriority={index < 2 ? 'high' : 'auto'} />
        ) : (
          <span className="image-fallback">Artwork unavailable</span>
        )}
        <span className="tier-bar" aria-hidden="true" />
        <button type="button" className="preview-trigger" onClick={onPreview} onPointerEnter={() => api.preloadSkinPreview(skin.uuid)} onFocus={() => api.preloadSkinPreview(skin.uuid)} aria-label={`Preview ${skin.name}`}><PlayIcon className="h-4 w-4" />Preview</button>
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
