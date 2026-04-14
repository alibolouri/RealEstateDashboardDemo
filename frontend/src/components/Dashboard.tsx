import { useEffect, useMemo, useRef, useState } from "react";

import { ChatInput } from "./ChatInput";
import { ConversationList } from "./ConversationList";
import { EmptyState } from "./EmptyState";
import { ThreadView } from "./ThreadView";
import { TopBar } from "./TopBar";
import {
  createConversation,
  fetchConversations,
  fetchHealth,
  getHistory,
  sendMessageStream,
  type Message,
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

function useMobileLayout() {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= 1100);

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 1100);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return isMobile;
}

export function Dashboard() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [assistantBrand, setAssistantBrand] = useState("Real Estate Concierge");
  const [brokerageName, setBrokerageName] = useState("Summit Realty Group");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);
  const isMobile = useMobileLayout();

  useEffect(() => {
    void fetchHealth()
      .then((payload) => {
        setAssistantBrand(payload.assistant_brand);
        setBrokerageName(payload.brokerage_name);
      })
      .catch(() => undefined);

    void fetchConversations()
      .then((rows) => {
        setConversations(rows);
        if (rows.length > 0) {
          setActiveConversationId(rows[0].id);
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!activeConversationId) return;
    void getHistory(activeConversationId)
      .then((history) => setMessages(history))
      .catch(() => setMessages([]));
  }, [activeConversationId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!isMobile) {
      setMobileDrawerOpen(false);
    }
  }, [isMobile]);

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
    setMobileDrawerOpen(false);
  };

  const handleSelectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId);
    setMobileDrawerOpen(false);
  };

  const handleLogout = () => {
    setActiveConversationId(null);
    setMessages([]);
    setMobileDrawerOpen(false);
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
              ? {
                  ...conversation,
                  title: conversation.title === "New conversation" ? content.slice(0, 48) : conversation.title,
                  updated_at: new Date().toISOString()
                }
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

  const workspaceContent = (
    <div className="workspace-header">
      <div className="workspace-header__intro">
        <div className="workspace-header__copy">
          <div className="workspace-header__eyebrow">Agent workspace</div>
          <div className="workspace-header__title">{assistantBrand}</div>
          <p className="workspace-header__body">
            {isMobile
              ? "A structured run surface for listing retrieval, guidance, provenance, and brokerage handoff."
              : "A calm, structured operator surface for listing runs, guidance, provenance, and routed handoff."}
          </p>
        </div>
      </div>

      {activePlaceholder ? (
        <EmptyState prompts={STARTER_PROMPTS} onPrompt={(prompt) => void handleSendMessage(prompt)} />
      ) : (
        <>
          <ThreadView messages={messages} assistantLabel={assistantBrand} isLoading={isLoading} />
          <div ref={endRef} />
        </>
      )}
    </div>
  );

  return (
    <>
      <div className={`app-shell${sidebarCollapsed ? " sidebar-collapsed" : ""}`}>
        <aside className="shell-sidebar">
          <ConversationList
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelectConversation={handleSelectConversation}
            onNewConversation={() => void handleNewConversation()}
            onLogout={handleLogout}
            assistantBrand={assistantBrand}
            brokerageName={brokerageName}
            collapsed={sidebarCollapsed}
          />
        </aside>

        <main className="shell-main">
          <TopBar
            assistantBrand={assistantBrand}
            brokerageName={brokerageName}
            onToggleSidebar={() => setSidebarCollapsed((current) => !current)}
            onOpenDrawer={() => setMobileDrawerOpen(true)}
            mobile={isMobile}
          />

          <section className="workspace">
            <div className="workspace-scroll">
              <div className="workspace-inner">{workspaceContent}</div>
            </div>

            <ChatInput onSend={(value) => void handleSendMessage(value)} disabled={isLoading} />
          </section>
        </main>
      </div>

      {isMobile && mobileDrawerOpen ? (
        <>
          <button className="drawer-overlay" onClick={() => setMobileDrawerOpen(false)} aria-label="Close thread drawer" />
          <div className="drawer">
            <ConversationList
              conversations={conversations}
              activeConversationId={activeConversationId}
              onSelectConversation={handleSelectConversation}
              onNewConversation={() => void handleNewConversation()}
              onLogout={handleLogout}
              assistantBrand={assistantBrand}
              brokerageName={brokerageName}
            />
          </div>
        </>
      ) : null}
    </>
  );
}
