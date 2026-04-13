import type { Message } from "../lib/api";

export function ChatMessage({ message, assistantLabel }: { message: Message; assistantLabel: string }) {
  return (
    <article className={`message ${message.role}`}>
      <div className="message-label">{message.role === "user" ? "You" : assistantLabel}</div>
      <div className="message-body">{message.content}</div>
    </article>
  );
}
