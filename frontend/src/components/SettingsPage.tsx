import { FormEvent, useEffect, useMemo, useState } from "react";

import { fetchSettings, saveSettings, type SettingsPayload } from "../lib/api";

type Props = {
  onRuntimeBrandingChange: (assistantBrand: string, brokerageName: string) => void;
};

function toFormValues(payload: SettingsPayload): Record<string, string> {
  return payload.values.reduce<Record<string, string>>((accumulator, item) => {
    accumulator[item.key] = item.is_secret ? "" : item.value || "";
    return accumulator;
  }, {});
}

function valueMap(payload: SettingsPayload | null): Record<string, string | null> {
  if (!payload) return {};
  return payload.values.reduce<Record<string, string | null>>((accumulator, item) => {
    accumulator[item.key] = item.value || null;
    return accumulator;
  }, {});
}

export function SettingsPage({ onRuntimeBrandingChange }: Props) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [payload, setPayload] = useState<SettingsPayload | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const currentValues = useMemo(() => valueMap(payload), [payload]);

  async function loadSettings() {
    const nextPayload = await fetchSettings();
    setPayload(nextPayload);
    setFormValues(toFormValues(nextPayload));
    const assistantBrand = nextPayload.values.find((item) => item.key === "ASSISTANT_BRAND_NAME")?.value || "Real Estate Concierge";
    const brokerageName = nextPayload.values.find((item) => item.key === "BROKERAGE_NAME")?.value || "Summit Realty Group";
    onRuntimeBrandingChange(assistantBrand, brokerageName);
  }

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        setLoading(true);
        await loadSettings();
      } catch {
        if (!cancelled) {
          setError("Settings are unavailable until an admin session is active.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [onRuntimeBrandingChange]);

  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    if (!payload) return;
    setSaving(true);
    setError(null);
    setNotice(null);

    const valuesToSave = payload.values.reduce<Record<string, string | null>>((accumulator, item) => {
      const nextValue = formValues[item.key] ?? "";
      if (item.is_secret) {
        if (nextValue.trim()) {
          accumulator[item.key] = nextValue.trim();
        }
      } else {
        accumulator[item.key] = nextValue.trim();
      }
      return accumulator;
    }, {});

    try {
      const nextPayload = await saveSettings(valuesToSave);
      setPayload(nextPayload);
      setFormValues(toFormValues(nextPayload));
      const assistantBrand = nextPayload.values.find((item) => item.key === "ASSISTANT_BRAND_NAME")?.value || "Real Estate Concierge";
      const brokerageName = nextPayload.values.find((item) => item.key === "BROKERAGE_NAME")?.value || "Summit Realty Group";
      onRuntimeBrandingChange(assistantBrand, brokerageName);
      setNotice("Settings saved. Runtime changes apply on the next request.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-page">
        <div className="settings-page__header">
          <div className="workspace-header__eyebrow">Settings</div>
          <div className="workspace-header__title">Runtime configuration</div>
          <p className="workspace-header__body">Loading current runtime settings and connector metadata.</p>
        </div>
        <div className="panel settings-panel">
          <div className="callout-note">Loading settings...</div>
        </div>
      </div>
    );
  }

  if (!payload) {
    return (
      <div className="settings-page">
        <div className="settings-page__header">
          <div className="workspace-header__eyebrow">Settings</div>
          <div className="workspace-header__title">Runtime configuration</div>
          <p className="workspace-header__body">An admin session is required before runtime settings can be loaded.</p>
        </div>
        {error ? <div className="callout-note settings-notice settings-notice--danger">{error}</div> : null}
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="settings-page__header">
        <div className="workspace-header__eyebrow">Settings</div>
        <div className="workspace-header__title">Runtime configuration</div>
        <p className="workspace-header__body">
          Configure the active brokerage identity, model runtime, and source credentials without redeploying the app.
        </p>
      </div>

      <form className="settings-stack" onSubmit={handleSave}>
        {payload.groups.map((group) => (
          <section className="panel settings-panel" key={group.id}>
            <div className="settings-panel__header">
              <div>
                <div className="settings-panel__title">{group.label}</div>
                {group.description ? <p className="settings-panel__description">{group.description}</p> : null}
              </div>
            </div>

            <div className="settings-grid">
              {group.fields.map((field) => {
                const hasStoredSecret = field.secret && payload.values.find((item) => item.key === field.key)?.is_set;
                return (
                  <label className="settings-field" key={field.key}>
                    <span className="settings-field__label">
                      {field.label}
                      {field.required ? <span className="settings-field__required">Required</span> : null}
                    </span>

                    {field.kind === "select" ? (
                      <select
                        className="settings-field__input"
                        value={formValues[field.key] ?? ""}
                        onChange={(event) => setFormValues((current) => ({ ...current, [field.key]: event.target.value }))}
                      >
                        {(field.options || []).map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        className="settings-field__input"
                        type={field.kind === "password" ? "password" : field.kind}
                        value={formValues[field.key] ?? ""}
                        placeholder={field.placeholder || ""}
                        onChange={(event) => setFormValues((current) => ({ ...current, [field.key]: event.target.value }))}
                        autoComplete="off"
                      />
                    )}

                    <div className="settings-field__footer">
                      {field.help_text ? <span className="settings-field__help">{field.help_text}</span> : null}
                      {field.secret && hasStoredSecret ? <span className="micro-pill">Configured</span> : null}
                      {!field.secret && currentValues[field.key] ? <span className="settings-field__value">Current: {currentValues[field.key]}</span> : null}
                    </div>
                  </label>
                );
              })}
            </div>
          </section>
        ))}

        {error ? <div className="callout-note settings-notice settings-notice--danger">{error}</div> : null}
        {notice ? <div className="callout-note settings-notice settings-notice--success">{notice}</div> : null}

        <div className="settings-actions">
          <button className="button button--primary" type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save settings"}
          </button>
        </div>
      </form>
    </div>
  );
}
