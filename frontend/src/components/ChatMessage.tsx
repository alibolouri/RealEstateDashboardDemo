import type { Message } from "../lib/api";
import { RunBlock } from "./RunBlock";

export function ChatMessage({ message, assistantLabel }: { message: Message; assistantLabel: string }) {
  return (
    <RunBlock
      role={message.role === "user" ? "user" : "assistant"}
      label={message.role === "user" ? "User request" : assistantLabel}
      content={message.content}
      listingResults={message.listing_results}
      handoff={message.handoff}
      sources={message.sources}
    />
  );
}
