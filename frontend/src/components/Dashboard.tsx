import { useEffect, useMemo, useRef, useState } from "react";

import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";
import { ConversationList } from "./ConversationList";
import { DetailPanel } from "./DetailPanel";
import {
  createConversation,
  fetchConversations,
  fetchHealth,
  getHistory,
  sendMessageStream,
  type HandoffCard,
  type ListingCard,
  type Message,
  type SourceCitation
} from "../lib/api";

type Conversation = {
  id: string;
  title: string;
  updated_at: string;
};

const STARTER_PROMPTS = [
  "Find 3-bedroom homes in Houston under $500000",
  "What should I know before renting in Austin?",
  "Show me short stays in Miami Beach",
  "Connect me to a realtor for Austin condos"
];

export function Dashboard() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [panelListings, setPanelListings] = useState<ListingCard[]>([]);
  const [panelHandoff, setPanelHandoff] = useState<HandoffCard | null>(null);
  const [panelSources, setPanelSources] = useState<SourceCitation[]>([]);
  const [assistantBrand, setAssistantBrand] = useState("Real Estate Concierge");
  const [brokerageName, setBrokerageName] = useState("Summit Realty Group");
  const [sourceMode, setSourceMode] = useState("demo_json");
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void fetchHealth().then((payload) => {
      setAssistantBrand(payload.assistant_brand);
      setBrokerageName(payload.brokerage_name);
      setSourceMode(payload.listing_source_mode);
    }).catch(() => undefined);
    void fetchConversations().then((rows) => {
      setConversations(rows);
      if (rows.length > 0) {
        setActiveConversationId(rows[0].id);
      }
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!activeConversationId) return;
    void getHistory(activeConversationId).then((history) => {
      setMessages(history);
      const lastAssistant = [...history].reverse().find((row) => row.role === "assistant");
      setPanelListings(lastAssistant?.listing_results || []);
      setPanelHandoff(lastAssistant?.handoff || null);
      setPanelSources(lastAssistant?.sources || []);
    }).catch(() => setMessages([]));
  }, [activeConversationId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewConversation = async () => {
    const conversationId = await createConversation();
    const conversation = {
      id: conversationId,
      title: "New conversation",
      updated_at: new Date().toISOString()
    };
    setConversations((current) => [conversation, ...current]);
    setActiveConversationId(conversationId);
    setMessages([]);
    setPanelListings([]);
    setPanelHandoff(null);
    setPanelSources([]);
  };

  const handleSendMessage = async (content: string) => {
    let conversationId = activeConversationId;
    if (!conversationId) {
      conversationId = await createConversation();
      const conversation = {
        id: conversationId,
        title: content.slice(0, 48),
        updated_at: new Date().toISOString()
      };
      setConversations((current) => [conversation, ...current]);
      setActiveConversationId(conversationId);
    }

    const userMessage: Message = { role: "user", content, created_at: new Date().toISOString() };
    const assistantPlaceholder: Message = {
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
      listing_results: [],
      sources: [],
      handoff: null
    };
    setMessages((current) => [...current, userMessage, assistantPlaceholder]);
    setIsLoading(true);

    await sendMessageStream(
      conversationId,
      content,
      (chunk) => {
        setMessages((current) => {
          const next = [...current];
          const last = next[next.length - 1];
          if (last && last.role === "assistant") {
            next[next.length - 1] = { ...last, content: `${last.content}${chunk}` };
          }
          return next;
        });
      },
      (meta) => {
        setPanelListings(meta.listing_results || []);
        setPanelHandoff(meta.handoff || null);
        setPanelSources(meta.sources || []);
        setMessages((current) => {
          const next = [...current];
          const last = next[next.length - 1];
          if (last && last.role === "assistant") {
            next[next.length - 1] = { ...last, ...meta };
          }
          return next;
        });
      },
      () => {
        setIsLoading(false);
        setConversations((current) =>
          current.map((conversation) =>
            conversation.id === conversationId
              ? { ...conversation, title: conversation.title === "New conversation" ? content.slice(0, 48) : conversation.title, updated_at: new Date().toISOString() }
              : conversation
          )
        );
      },
      (error) => {
        setIsLoading(false);
        setMessages((current) => {
          const next = [...current];
          const last = next[next.length - 1];
          if (last && last.role === "assistant") {
            next[next.length - 1] = { ...last, content: `Sorry, something failed while generating the response: ${error}` };
          }
          return next;
        });
      }
    );
  };

  const activePlaceholder = useMemo(() => messages.length === 0, [messages.length]);

  return (
    <div className="app-shell">
      <ConversationList
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewConversation={handleNewConversation}
        assistantBrand={assistantBrand}
        brokerageName={brokerageName}
      />

      <main className="chat-shell">
        <header className="hero">
          <span className="eyebrow">Standalone trial console</span>
          <h1>{assistantBrand}</h1>
          <p>Ask about listings, neighborhoods, buying, renting, short stays, or request a brokerage handoff.</p>
          <div className="hero-meta">
            <span>{brokerageName}</span>
            <span>Listing source mode: {sourceMode}</span>
          </div>
        </header>

        <section className="chat-thread">
          {activePlaceholder ? (
            <div className="starter-state">
              <h2>Start with a natural question</h2>
              <div className="starter-grid">
                {STARTER_PROMPTS.map((prompt) => (
                  <button key={prompt} className="secondary-button" onClick={() => void handleSendMessage(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <ChatMessage key={`${message.created_at}-${index}`} message={message} assistantLabel={assistantBrand} />
            ))
          )}
          {isLoading && <div className="thinking-indicator">{assistantBrand} is thinking...</div>}
          <div ref={endRef} />
        </section>

        <ChatInput onSend={(value) => void handleSendMessage(value)} disabled={isLoading} />
      </main>

      <DetailPanel
        listings={panelListings}
        handoff={panelHandoff}
        sources={panelSources}
        brokerageName={brokerageName}
      />
    </div>
  );
}
