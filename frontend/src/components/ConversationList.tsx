type Conversation = {
  id: string;
  title: string;
  updated_at: string;
};

type Props = {
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  assistantBrand: string;
  brokerageName: string;
  collapsed?: boolean;
};

export function ConversationList({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  assistantBrand,
  brokerageName,
  collapsed = false
}: Props) {
  return (
    <aside className={`sidebar${collapsed ? " sidebar--collapsed" : ""}`}>
      <div className="sidebar__brand">
        <div className="sidebar__eyebrow">Agent workspace</div>
        <div className="sidebar__title">{collapsed ? assistantBrand.slice(0, 2) : assistantBrand}</div>
        <div className="sidebar__brand-copy">
          <p className="sidebar__meta">{brokerageName}</p>
          <p className="sidebar__meta">Threads, runs, listing context, and routed handoff.</p>
        </div>
      </div>

      <button className="button button--primary" onClick={onNewConversation}>
        <span className="button__label">New conversation</span>
        {collapsed ? "+" : null}
      </button>

      <section className="sidebar__section">
        <div className="sidebar__section-title">Threads</div>
        <div className="conversation-list">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={`conversation-row${activeConversationId === conversation.id ? " is-active" : ""}`}
              onClick={() => onSelectConversation(conversation.id)}
              aria-label={conversation.title || "New conversation"}
            >
              <div className="conversation-row__title">{conversation.title || "New conversation"}</div>
              <div className="conversation-row__time">{new Date(conversation.updated_at).toLocaleString()}</div>
            </button>
          ))}
        </div>
      </section>
    </aside>
  );
}
