import { FormEvent, KeyboardEvent, useMemo, useState } from "react";

type Props = {
  onSend: (text: string) => void;
  disabled: boolean;
  sourceMode: string;
};

export function ChatInput({ onSend, disabled, sourceMode }: Props) {
  const [value, setValue] = useState("");

  const trimmed = value.trim();
  const canSend = trimmed.length > 0 && !disabled;

  const statusText = useMemo(() => {
    if (disabled) return "Agent run in progress";
    return "Ready";
  }, [disabled]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!canSend) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSend) {
        onSend(trimmed);
        setValue("");
      }
    }
  };

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <div className="composer__shell">
        <textarea
          className="composer__textarea"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask for listings, financing guidance, neighborhood trade-offs, or a human handoff."
          rows={3}
        />

        <div className="composer__actions">
          <div className="composer__meta">
            <span className="micro-pill">{sourceMode}</span>
            <span className="composer__status">{statusText}</span>
            {disabled ? (
              <span className="streaming-indicator">
                <span className="streaming-indicator__dots" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </span>
                running
              </span>
            ) : null}
          </div>

          <button className="button button--primary" type="submit" disabled={!canSend}>
            {disabled ? "Running..." : "Send"}
          </button>
        </div>
      </div>
    </form>
  );
}
