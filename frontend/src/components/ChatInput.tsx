import { FormEvent, useState } from "react";

export function ChatInput({ onSend, disabled }: { onSend: (text: string) => void; disabled: boolean }) {
  const [value, setValue] = useState("");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Ask about listings, neighborhoods, buying, renting, or ask to be connected."
        rows={3}
      />
      <button className="primary-button" type="submit" disabled={disabled}>
        {disabled ? "Thinking..." : "Send"}
      </button>
    </form>
  );
}

