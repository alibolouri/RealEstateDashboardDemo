import type { Message } from "../lib/api";
import { ChatMessage } from "./ChatMessage";

type Props = {
  messages: Message[];
  assistantLabel: string;
  isLoading: boolean;
};

export function ThreadView({ messages, assistantLabel, isLoading }: Props) {
  return (
    <section className="thread">
      {messages.map((message, index) => {
        const isStreamingMessage = isLoading && index === messages.length - 1 && message.role === "assistant";
        return (
          <ChatMessage
            key={`${message.created_at}-${index}`}
            message={message}
            assistantLabel={assistantLabel}
            isStreaming={isStreamingMessage}
          />
        );
      })}
    </section>
  );
}
