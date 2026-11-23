export function PageHeading({ title, description, actions }: { title: string; description: string; actions?: React.ReactNode }) {
  return (
    <header className="page-heading">
      <div>
        <h2>{title}</h2>
        <p className="muted">{description}</p>
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="error-banner" role="alert">
      {message}
    </div>
  );
}

export function Notice({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="notice" role="status">
      {message}
    </div>
  );
}

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return <p className="muted">{label}</p>;
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return <p className="muted empty-state">{children}</p>;
}

export function StatusBadge({ value }: { value: unknown }) {
  const status = value == null ? "unknown" : String(value);
  const tone = ["published", "approved", "issued", "valid", "active", "open"].includes(status)
    ? "positive"
    : ["rejected", "revoked", "absent", "invalid", "superseded", "returned"].includes(status)
      ? "negative"
      : "neutral";
  return <span className={`badge badge-${tone}`}>{status.replace(/_/g, " ")}</span>;
}
