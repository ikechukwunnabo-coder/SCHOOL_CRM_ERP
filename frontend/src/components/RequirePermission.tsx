import { useAuth } from "../auth/AuthContext";
import { can, type ModuleKey } from "../auth/permissions";

export function RequirePermission({ module, children }: { module: ModuleKey; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!can(user, module, "view")) {
    return (
      <section className="card">
        <h2>Not available</h2>
        <p className="muted">Your role does not have access to this module.</p>
      </section>
    );
  }
  return <>{children}</>;
}
