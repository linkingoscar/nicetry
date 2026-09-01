import React, { type Key, type ReactNode } from 'react';

export interface MetadataItem {
  key: Key;
  label: ReactNode;
  value: ReactNode;
}

export interface EvidenceSectionProps {
  eyebrow?: string;
  title: string;
  statusChip?: {
    label: string;
    variant: 'pass' | 'fail' | 'info' | 'warning';
  };
  metadata?: MetadataItem[];
  methodNote?: ReactNode;
  children?: ReactNode;
  'aria-labelledby'?: string;
}

export const EvidenceSection = React.memo(function EvidenceSection({
  eyebrow,
  title,
  statusChip,
  metadata,
  methodNote,
  children,
  'aria-labelledby': ariaLabelledby
}: EvidenceSectionProps) {
  const chipClass = statusChip 
    ? `status-chip ${statusChip.variant === 'warning' || statusChip.variant === 'fail' ? 'is-warning' : ''}`
    : '';

  return (
    <section className="evidence-section" aria-labelledby={ariaLabelledby}>
      <div className="section-heading">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          {ariaLabelledby ? <h2 id={ariaLabelledby}>{title}</h2> : <h2>{title}</h2>}
        </div>
        {statusChip && (
          <span className={chipClass}>{statusChip.label}</span>
        )}
      </div>
      
      {metadata && metadata.length > 0 && (
        <dl className="run-meta factor-meta">
          {metadata.map((item) => (
            item.value != null ? (
              <div key={item.key}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ) : null
          ))}
        </dl>
      )}

      {methodNote && (
        <p className="method-note">{methodNote}</p>
      )}

      {children}
    </section>
  );
});
