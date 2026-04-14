const API_BASE_URL = import.meta.env.VITE_API_URL || window.location.origin || "http://localhost:8000";

export type DataStatus = "live" | "cached" | "demo";

export type SourceCitation = {
  type: "listing_source" | "knowledge_source" | "routing_source";
  label: string;
  url?: string | null;
  timestamp?: string | null;
  confidence: number;
  data_status: DataStatus;
};

export type RealtorCard = {
  id: string;
  name: string;
  phone: string;
  email: string;
  specialty: string;
  cities_covered: string[];
  brokerage: string;
};

export type ListingCard = {
  id: string;
  source: string;
  external_id: string;
  title: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  price: number;
  listing_type: string;
  property_type: string;
  status: string;
  bedrooms: number;
  bathrooms: number;
  square_feet?: number | null;
  short_description: string;
  image_url?: string | null;
  brokerage?: string | null;
  url?: string | null;
  last_synced_at?: string | null;
  provenance: string;
  data_status: DataStatus;
};

export type HandoffCard = {
  fixed_contact_number: string;
  recommended_realtor: RealtorCard;
  reason: string;
  next_step_message: string;
};

export type Message = {
  role: string;
  content: string;
  created_at: string;
  sources?: SourceCitation[];
  listing_results?: ListingCard[];
  handoff?: HandoffCard | null;
  data_status?: DataStatus | null;
};

export type SettingOption = {
  value: string;
  label: string;
};

export type SettingField = {
  key: string;
  label: string;
  group: string;
  kind: "text" | "password" | "url" | "number" | "select";
  required: boolean;
  secret: boolean;
  placeholder?: string | null;
  help_text?: string | null;
  options?: SettingOption[];
};

export type SettingGroup = {
  id: string;
  label: string;
  description?: string | null;
  fields: SettingField[];
};

export type SettingValue = {
  key: string;
  value?: string | null;
  is_set: boolean;
  is_secret: boolean;
};

export type SettingsPayload = {
  groups: SettingGroup[];
  values: SettingValue[];
};

export type AdminSession = {
  authenticated: boolean;
  username?: string | null;
};

async function apiFetch(path: string, init?: RequestInit, includeCredentials = false): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: includeCredentials ? "include" : init?.credentials,
    headers: {
      ...(init?.headers || {}),
    }
  });
}

export async function createConversation(): Promise<string> {
  const response = await apiFetch("/conversations", { method: "POST" });
  if (!response.ok) throw new Error("Failed to create conversation");
  const payload = await response.json();
  return payload.conversation_id;
}

export async function fetchConversations(): Promise<Array<{ id: string; title: string; updated_at: string }>> {
  const response = await apiFetch("/conversations");
  const payload = await response.json();
  return payload.conversations;
}

export async function getHistory(conversationId: string): Promise<Message[]> {
  const response = await apiFetch(`/conversations/${conversationId}/history`);
  if (!response.ok) throw new Error("Failed to fetch history");
  const payload = await response.json();
  return payload.messages;
}

export async function fetchHealth(): Promise<{ assistant_brand: string; brokerage_name: string; listing_source_mode: string }> {
  const response = await apiFetch("/health");
  if (!response.ok) throw new Error("Failed to fetch health metadata");
  return response.json();
}

export async function fetchAdminSession(): Promise<AdminSession> {
  const response = await apiFetch("/admin/session", undefined, true);
  if (!response.ok) throw new Error("Failed to fetch admin session");
  return response.json();
}

export async function loginAdmin(username: string, password: string): Promise<AdminSession> {
  const response = await apiFetch(
    "/admin/login",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    },
    true
  );
  if (!response.ok) throw new Error("Invalid admin credentials");
  return response.json();
}

export async function logoutAdmin(): Promise<void> {
  await apiFetch("/admin/logout", { method: "POST" }, true);
}

export async function fetchSettings(): Promise<SettingsPayload> {
  const response = await apiFetch("/settings", undefined, true);
  if (!response.ok) {
    if (response.status === 401) throw new Error("unauthorized");
    throw new Error("Failed to fetch settings");
  }
  return response.json();
}

export async function saveSettings(values: Record<string, string | null>): Promise<SettingsPayload> {
  const response = await apiFetch(
    "/settings",
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values })
    },
    true
  );
  if (!response.ok) {
    if (response.status === 401) throw new Error("unauthorized");
    throw new Error("Failed to save settings");
  }
  return response.json();
}

export async function sendMessageStream(
  conversationId: string,
  message: string,
  onChunk: (chunk: string) => void,
  onMeta: (meta: { sources?: SourceCitation[]; listing_results?: ListingCard[]; handoff?: HandoffCard | null; data_status?: DataStatus | null }) => void,
  onComplete: () => void,
  onError: (error: string) => void
): Promise<void> {
  const response = await apiFetch(`/conversations/${conversationId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  if (!response.ok || !response.body) {
    onError(`HTTP ${response.status}`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      onComplete();
      return;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const event of events) {
      const line = event.split("\n").find((candidate) => candidate.startsWith("data: "));
      if (!line) continue;
      try {
        const payload = JSON.parse(line.slice(6));
        if (payload.chunk) onChunk(payload.chunk);
        if (payload.meta) onMeta(payload.meta);
        if (payload.error) {
          onError(payload.error);
          return;
        }
        if (payload.done) {
          onComplete();
          return;
        }
      } catch {
        onError("Failed to parse streaming payload");
        return;
      }
    }
  }
}
