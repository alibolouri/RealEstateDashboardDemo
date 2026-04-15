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
  onOpenSettings: () => void;
  onLogout: () => void;
  assistantBrand: string;
  brokerageName: string;
};

export function ConversationList({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onOpenSettings,
  onLogout,
  assistantBrand,
  brokerageName
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__eyebrow">Agent workspace</div>
        <div className="sidebar__title">{assistantBrand}</div>
        <div className="sidebar__brand-copy">
          <p className="sidebar__meta">{brokerageName}</p>
          <p className="sidebar__meta">Threads, runs, listing context, and routed handoff.</p>
        </div>
      </div>

      <button className="button button--primary" onClick={onNewConversation}>
        <span className="button__label">New conversation</span>
      </button>

      <section className="sidebar__section">
        <div className="sidebar__section-title">Threads</div>
        <div className="conversation-list">
          {conversations.length > 0 ? (
            conversations.map((conversation) => (
              <button
                key={conversation.id}
                className={`conversation-row${activeConversationId === conversation.id ? " is-active" : ""}`}
                onClick={() => onSelectConversation(conversation.id)}
                aria-label={conversation.title || "New conversation"}
                title={conversation.title || "New conversation"}
              >
                <div className="conversation-row__title">{conversation.title || "New conversation"}</div>
              </button>
            ))
          ) : (
            <div className="panel callout-note">Start a new conversation to create your first agent thread.</div>
          )}
        </div>
      </section>

      <div className="sidebar__footer">
        <button className="button button--secondary sidebar__logout" onClick={onOpenSettings} aria-label="Open runtime settings">
          <span className="button__label">Settings</span>
        </button>
        <button className="button button--secondary sidebar__logout" onClick={onLogout} aria-label="Clear active workspace">
          <span className="button__label">Log out</span>
        </button>
      </div>
    </aside>
  );
}
