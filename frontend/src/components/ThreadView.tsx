import type { Message } from "../lib/api";
import { ChatMessage } from "./ChatMessage";
import { RunBlock } from "./RunBlock";

type Props = {
  messages: Message[];
  assistantLabel: string;
  isLoading: boolean;
};

export function ThreadView({ messages, assistantLabel, isLoading }: Props) {
  return (
    <section className="thread">
      {messages.map((message, index) => (
        <ChatMessage key={`${message.created_at}-${index}`} message={message} assistantLabel={assistantLabel} />
      ))}

      {isLoading ? (
        <RunBlock
          role="assistant"
          label={assistantLabel}
          content="Running the current request against the active workspace context."
          isStreaming
        />
      ) : null}
    </section>
  );
}
