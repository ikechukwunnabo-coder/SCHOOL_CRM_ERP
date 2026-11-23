export function Panel({ title, description, actions, children }: { title: string; description?: string; actions?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <section className="card panel">
      <div className="panel-head">
        <div>
          <h3>{title}</h3>
          {description ? <p className="muted small">{description}</p> : null}
        </div>
        {actions ? <div className="panel-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}
