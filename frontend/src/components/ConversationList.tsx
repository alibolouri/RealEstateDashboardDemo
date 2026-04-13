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
};

export function ConversationList({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  assistantBrand,
  brokerageName
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="eyebrow">White-label concierge</span>
        <h1>{assistantBrand}</h1>
        <p>{brokerageName} conversation workspace for listing search and routed human support.</p>
      </div>
      <button className="primary-button" onClick={onNewConversation}>
        New conversation
      </button>
      <div className="conversation-group">
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            className={`conversation-item${activeConversationId === conversation.id ? " active" : ""}`}
            onClick={() => onSelectConversation(conversation.id)}
          >
            <strong>{conversation.title || "New conversation"}</strong>
            <span>{new Date(conversation.updated_at).toLocaleString()}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
