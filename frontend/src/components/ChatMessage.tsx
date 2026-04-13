import type { Message } from "../lib/api";

export function ChatMessage({ message }: { message: Message }) {
  return (
    <article className={`message ${message.role}`}>
      <div className="message-label">{message.role === "user" ? "You" : "Doorviser AI"}</div>
      <div className="message-body">{message.content}</div>
    </article>
  );
}

