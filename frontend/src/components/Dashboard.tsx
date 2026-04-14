import { useEffect, useMemo, useRef, useState } from "react";

import { ChatInput } from "./ChatInput";
import { ConversationList } from "./ConversationList";
import { EmptyState } from "./EmptyState";
import { SettingsPage } from "./SettingsPage";
import { ThreadView } from "./ThreadView";
import { TopBar } from "./TopBar";
import {
  createConversation,
  fetchConversations,
  fetchHealth,
  getHistory,
  logoutAdmin,
  sendMessageStream,
  type Message,
} from "../lib/api";

type Conversation = {
  id: string;
  title: string;
  updated_at: string;
};

const STARTER_PROMPTS = [
  "Build me a Houston family-home shortlist under $600k and ask the right follow-up questions first.",
  "Help me compare Austin rentals for a hybrid commute, pet policy, parking, and total move-in cost.",
  "Walk me through Dallas monthly-payment trade-offs around a $400k purchase before recommending listings.",
  "Give me a seller-ready prep checklist for Houston, then route me to the right agent."
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
  const initialView = window.location.pathname === "/settings" ? "settings" : "workspace";
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [assistantBrand, setAssistantBrand] = useState("Real Estate Concierge");
  const [brokerageName, setBrokerageName] = useState("Summit Realty Group");
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [view, setView] = useState<"workspace" | "settings">(initialView);
  const endRef = useRef<HTMLDivElement | null>(null);
  const streamQueueRef = useRef("");
  const streamMetaRef = useRef<Partial<Message> | null>(null);
  const streamFinalizeRef = useRef<(() => void) | null>(null);
  const streamTimerRef = useRef<number | null>(null);
  const isMobile = useMobileLayout();

  const stopStreamAnimator = () => {
    if (streamTimerRef.current !== null) {
      window.clearInterval(streamTimerRef.current);
      streamTimerRef.current = null;
    }
  };

  const appendAssistantContent = (chunk: string) => {
    if (!chunk) return;
    setMessages((current) => {
      const next = [...current];
      const last = next[next.length - 1];
      if (last && last.role === "assistant") {
        next[next.length - 1] = { ...last, content: `${last.content}${chunk}` };
      }
      return next;
    });
  };

  const applyPendingMeta = () => {
    if (!streamMetaRef.current) return;
    const meta = streamMetaRef.current;
    streamMetaRef.current = null;
    setMessages((current) => {
      const next = [...current];
      const last = next[next.length - 1];
      if (last && last.role === "assistant") {
        next[next.length - 1] = { ...last, ...meta };
      }
      return next;
    });
  };

  const finalizeStreaming = () => {
    applyPendingMeta();
    if (streamFinalizeRef.current) {
      const finalize = streamFinalizeRef.current;
      streamFinalizeRef.current = null;
      finalize();
    }
  };

  const flushStreamQueue = () => {
    if (!streamQueueRef.current.length) {
      stopStreamAnimator();
      finalizeStreaming();
      return;
    }

    const chunk = streamQueueRef.current.slice(0, 2);
    streamQueueRef.current = streamQueueRef.current.slice(2);
    appendAssistantContent(chunk);
  };

  const ensureStreamAnimator = () => {
    if (streamTimerRef.current === null) {
      streamTimerRef.current = window.setInterval(flushStreamQueue, 18);
    }
  };

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

  useEffect(() => {
    const handlePopState = () => {
      setView(window.location.pathname === "/settings" ? "settings" : "workspace");
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    return () => {
      stopStreamAnimator();
    };
  }, []);

  const navigateTo = (nextView: "workspace" | "settings") => {
    const path = nextView === "settings" ? "/settings" : "/";
    window.history.pushState({}, "", path);
    setView(nextView);
    setMobileDrawerOpen(false);
  };

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
    if (view !== "workspace") {
      window.history.pushState({}, "", "/");
      setView("workspace");
    }
    setMobileDrawerOpen(false);
  };

  const handleSelectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId);
    if (view !== "workspace") {
      window.history.pushState({}, "", "/");
      setView("workspace");
    }
    setMobileDrawerOpen(false);
  };

  const handleLogout = () => {
    void logoutAdmin().catch(() => undefined);
    setActiveConversationId(null);
    setMessages([]);
    navigateTo("workspace");
    setMobileDrawerOpen(false);
  };

  const handleSendMessage = async (content: string) => {
    stopStreamAnimator();
    streamQueueRef.current = "";
    streamMetaRef.current = null;
    streamFinalizeRef.current = null;
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
        streamQueueRef.current += chunk;
        ensureStreamAnimator();
      },
      (meta) => {
        streamMetaRef.current = meta;
        if (!streamQueueRef.current.length && streamTimerRef.current === null) {
          applyPendingMeta();
        }
      },
      () => {
        streamFinalizeRef.current = () => {
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
        };
        if (!streamQueueRef.current.length && streamTimerRef.current === null) {
          finalizeStreaming();
        }
      },
      (error) => {
        stopStreamAnimator();
        streamQueueRef.current = "";
        streamMetaRef.current = null;
        streamFinalizeRef.current = null;
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
      <div className={`app-shell${sidebarCollapsed ? " app-shell--sidebar-collapsed" : ""}`}>
        <aside className="shell-sidebar">
          <ConversationList
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelectConversation={handleSelectConversation}
            onNewConversation={() => void handleNewConversation()}
            onOpenSettings={() => navigateTo("settings")}
            onLogout={handleLogout}
            onToggleCollapse={() => setSidebarCollapsed((current) => !current)}
            assistantBrand={assistantBrand}
            brokerageName={brokerageName}
            collapsed={sidebarCollapsed}
          />
        </aside>

        <main className="shell-main">
          <TopBar
            assistantBrand={assistantBrand}
            brokerageName={brokerageName}
            onOpenDrawer={() => setMobileDrawerOpen(true)}
            mobile={isMobile}
          />

          <section className="workspace">
            <div className="workspace-scroll">
              <div className="workspace-inner">
                {view === "settings" ? (
                  <SettingsPage
                    onRuntimeBrandingChange={(nextAssistantBrand, nextBrokerageName) => {
                      setAssistantBrand(nextAssistantBrand);
                      setBrokerageName(nextBrokerageName);
                    }}
                  />
                ) : (
                  workspaceContent
                )}
              </div>
            </div>

            {view === "workspace" ? <ChatInput onSend={(value) => void handleSendMessage(value)} disabled={isLoading} /> : null}
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
              onOpenSettings={() => navigateTo("settings")}
              onLogout={handleLogout}
              assistantBrand={assistantBrand}
              brokerageName={brokerageName}
              collapsed={false}
            />
          </div>
        </>
      ) : null}
    </>
  );
}
