import { FormEvent, useState } from "react";

import { loginAdmin } from "../lib/api";

type Props = {
  assistantBrand: string;
  brokerageName: string;
  onAuthenticated: (assistantBrand: string, brokerageName: string) => Promise<void> | void;
};

export function AuthScreen({ assistantBrand, brokerageName, onAuthenticated }: Props) {
  const [values, setValues] = useState({ username: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const session = await loginAdmin(values.username, values.password);
      if (!session.authenticated) {
        throw new Error("Authentication failed");
      }
      await onAuthenticated(assistantBrand, brokerageName);
      setValues({ username: "", password: "" });
    } catch {
      setError("Sign-in failed. Check the configured admin credentials and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-shell">
      <section className="panel auth-panel">
        <div className="auth-panel__eyebrow">Admin access</div>
        <h1 className="auth-panel__title">{assistantBrand}</h1>
        <p className="auth-panel__body">
          Sign in to access conversations, settings, and the full brokerage workspace for {brokerageName}.
        </p>

        <form className="auth-panel__form" onSubmit={handleSubmit}>
          <label className="settings-field">
            <span className="settings-field__label">Username</span>
            <input
              className="settings-field__input"
              type="text"
              value={values.username}
              onChange={(event) => setValues((current) => ({ ...current, username: event.target.value }))}
              autoComplete="username"
              required
            />
          </label>

          <label className="settings-field">
            <span className="settings-field__label">Password</span>
            <input
              className="settings-field__input"
              type="password"
              value={values.password}
              onChange={(event) => setValues((current) => ({ ...current, password: event.target.value }))}
              autoComplete="current-password"
              required
            />
          </label>

          {error ? <div className="callout-note settings-notice settings-notice--danger">{error}</div> : null}

          <button className="button button--primary auth-panel__submit" type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
