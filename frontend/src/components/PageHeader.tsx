import type { ReactNode } from 'react';

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
  compact?: boolean;
}

export default function PageHeader({ eyebrow, title, description, action, compact = false }: PageHeaderProps) {
  const sectionCode = title.replace(/[^a-z0-9]/gi, '').slice(0, 3).toUpperCase();

  return (
    <header className={`page-header ${compact ? 'page-header-compact' : ''}`}>
      <div className="page-header-copy">
        <span className="page-code" aria-hidden="true">VS / {sectionCode}</span>
        <p className="page-eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {action && <div className="page-action">{action}</div>}
    </header>
  );
}
