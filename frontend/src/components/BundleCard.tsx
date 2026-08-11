import { useEffect, useState, type CSSProperties } from 'react';
import type { Bundle } from '../types';
import { ClockIcon, VPIcon } from './Icons';

function formatTime(totalSecs: number): string {
  const days = Math.floor(totalSecs / 86400);
  const hours = Math.floor((totalSecs % 86400) / 3600);
  const minutes = Math.floor((totalSecs % 3600) / 60);
  return days > 0 ? `${days}d ${hours}h ${minutes}m` : `${hours}h ${minutes}m`;
}

export default function BundleCard({ bundle }: { bundle: Bundle }) {
  const [remaining, setRemaining] = useState(bundle.duration_remaining_secs);

  useEffect(() => {
    if (remaining <= 0) return;
    const timeout = window.setTimeout(() => setRemaining((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(timeout);
  }, [remaining]);

  const hasDiscount = bundle.total_discounted_price < bundle.total_base_price;

  return (
    <article className="bundle-card">
      <div className="bundle-feature">
        <div className="bundle-summary">
          <div>
            <p className="bundle-kicker">Featured collection</p>
            <h2>{bundle.name}</h2>
          </div>
          <div className="bundle-meta">
            <span><ClockIcon className="h-4 w-4" />{formatTime(remaining)}</span>
            <span className="bundle-total"><VPIcon className="h-4 w-4" />{bundle.total_discounted_price.toLocaleString()}</span>
            {hasDiscount && <span className="bundle-original">{bundle.total_base_price.toLocaleString()} VP</span>}
          </div>
        </div>
        <div className="bundle-art">
          {bundle.display_icon ? <img src={bundle.display_icon} alt={bundle.name} /> : <span>Collection artwork unavailable</span>}
        </div>
      </div>

      <div className="bundle-items-section">
        <div className="bundle-items-heading"><span>Included items</span><span>{bundle.items.length} total</span></div>
        <div className="bundle-items">
          {bundle.items.map((item, index) => (
            <div key={item.uuid} className="bundle-item group" style={{ '--item-index': index } as CSSProperties}>
              <div className="bundle-item-art">
                {item.display_icon ? <img src={item.display_icon} alt={item.name} /> : <span>No artwork</span>}
              </div>
              <div className="bundle-item-copy">
                <p>{item.name}</p>
                <span><VPIcon className="h-3 w-3" />{item.discounted_price.toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}
