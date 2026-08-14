import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import * as api from '../api/client';
import type { SkinPreviewResponse, SkinPreviewVideo } from '../types';
import { CloseIcon, PlayIcon } from './Icons';

interface SkinPreviewModalProps {
  skinUuid: string;
  skinName: string;
  tierColor: string;
  onClose: () => void;
}

function cleanLabel(value: string): string {
  return value.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
}

export default function SkinPreviewModal({ skinUuid, skinName, tierColor, onClose }: SkinPreviewModalProps) {
  const [preview, setPreview] = useState<SkinPreviewResponse | null>(null);
  const [active, setActive] = useState<SkinPreviewVideo | null>(null);
  const [error, setError] = useState('');
  const closeRef = useRef<HTMLButtonElement>(null);
  const modalRef = useRef<HTMLElement>(null);

  useEffect(() => {
    let mounted = true;
    void api.getSkinPreview(skinUuid)
      .then((result) => {
        if (!mounted) return;
        setPreview(result);
        setActive(result.levels[0] ?? result.chromas[0] ?? null);
      })
      .catch((reason: unknown) => {
        if (mounted) setError(reason instanceof Error ? reason.message : 'Preview unavailable.');
      });
    return () => { mounted = false; };
  }, [skinUuid]);

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeRef.current?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !modalRef.current) return;
      const focusable = Array.from(modalRef.current.querySelectorAll<HTMLElement>('button:not(:disabled), video[controls]'));
      const first = focusable[0];
      const last = focusable.at(-1);
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('keydown', handleKey);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [onClose]);

  const groups = useMemo(() => preview ? [
    { label: 'Upgrades', items: preview.levels },
    { label: 'Variants', items: preview.chromas },
  ].filter((group) => group.items.length > 0) : [], [preview]);

  return (
    <div className="preview-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section ref={modalRef} className="preview-modal" role="dialog" aria-modal="true" aria-labelledby="preview-title" style={{ '--tier-color': tierColor } as CSSProperties}>
        <header className="preview-header">
          <div><span>Skin showcase / Riot CDN</span><h2 id="preview-title">{skinName}</h2></div>
          <button ref={closeRef} type="button" className="preview-close" onClick={onClose} aria-label="Close preview"><CloseIcon /></button>
        </header>

        <div className="preview-layout">
          <div className="preview-stage">
            {active ? (
              <video key={active.uuid} src={active.streamed_video} poster={active.display_icon || preview?.display_icon} controls autoPlay muted playsInline preload="metadata" />
            ) : error ? (
              <div className="preview-status"><span>Preview unavailable</span><p>{error}</p></div>
            ) : preview ? (
              <div className="preview-status preview-empty">{preview.display_icon ? <img src={preview.display_icon} alt="" /> : null}<span>No video demonstration</span><p>Riot has not published a preview video for this skin.</p></div>
            ) : (
              <div className="preview-status preview-loading"><i /><span>Loading showcase</span><p>Preparing the highest-quality preview available.</p></div>
            )}
            <div className="preview-stage-meta"><span>{active ? cleanLabel(active.name) : skinName}</span><small>{active?.level_item ? cleanLabel(active.level_item).replace('EEquippableSkinLevelItem::', '') : 'Official in-game capture'}</small></div>
          </div>

          <aside className="preview-playlist" aria-label="Available skin demonstrations">
            <div className="preview-playlist-head"><span>Demonstrations</span><small>{groups.reduce((total, group) => total + group.items.length, 0).toString().padStart(2, '0')} clips</small></div>
            {groups.map((group) => (
              <div className="preview-group" key={group.label}>
                <h3>{group.label}</h3>
                {group.items.map((item) => (
                  <button type="button" key={item.uuid} className={active?.uuid === item.uuid ? 'preview-option is-active' : 'preview-option'} onClick={() => setActive(item)}>
                    <span className="preview-option-art">{item.swatch ? <img src={item.swatch} alt="" /> : <PlayIcon />}</span>
                    <span><b>{cleanLabel(item.name)}</b><small>{group.label === 'Upgrades' ? `Level ${item.ordinal}` : `Variant ${item.ordinal}`}</small></span>
                  </button>
                ))}
              </div>
            ))}
            <footer><i />Streamed directly from Riot’s content network</footer>
          </aside>
        </div>
      </section>
    </div>
  );
}
