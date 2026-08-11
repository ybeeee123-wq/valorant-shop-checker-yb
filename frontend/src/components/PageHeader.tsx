import type { ReactNode } from 'react';

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
  compact?: boolean;
}

export default function PageHeader({ eyebrow, title, description, action, compact = false }: PageHeaderProps) {
  return (
    <header className={`page-header ${compact ? 'page-header-compact' : ''}`}>
      <div>
        <p className="page-eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {action && <div className="page-action">{action}</div>}
    </header>
  );
}
