import type { ReactNode } from 'react';
import { ChevronRightIcon } from './Icons';

interface EmptyStateProps {
  icon: ReactNode;
  label: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function EmptyState({ icon, label, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <section className="empty-state">
      <div className="empty-icon">{icon}</div>
      <div className="empty-copy">
        <p>{label}</p>
        <h2>{title}</h2>
        <span>{description}</span>
      </div>
      {actionLabel && (
        <button type="button" onClick={onAction} disabled={!onAction} className="secondary-button" aria-label={onAction ? actionLabel : `${actionLabel} (coming soon)`}>
          {actionLabel}<ChevronRightIcon className="h-4 w-4" />
        </button>
      )}
    </section>
  );
}
