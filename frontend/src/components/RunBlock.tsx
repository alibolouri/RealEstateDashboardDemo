import type { HandoffCard as HandoffCardType, ListingCard as ListingCardType, SourceCitation } from "../lib/api";
import { HandoffCard } from "./HandoffCard";
import { ListingCard } from "./ListingCard";
import { SourceList } from "./SourceList";

type Props = {
  role: "user" | "assistant";
  label: string;
  content: string;
  listingResults?: ListingCardType[];
  handoff?: HandoffCardType | null;
  sources?: SourceCitation[];
  isStreaming?: boolean;
};

export function RunBlock({
  role,
  label,
  content,
  listingResults = [],
  handoff,
  sources = [],
  isStreaming = false
}: Props) {
  const bodyContent = content.trim().length > 0 ? content : isStreaming ? "Running the current request against the active workspace context." : "No response content.";

  return (
    <article className={`panel run-block run-block--${role}${isStreaming ? " run-block--streaming" : ""}`}>
      <div className="run-block__header">
        <div>
          <div className="run-block__role">{label}</div>
          <div className="run-block__summary">{role === "user" ? "Requested task" : "Agent response"}</div>
        </div>
        <div className="run-block__meta-row">
          {isStreaming ? <span className="micro-pill">running</span> : null}
          {listingResults.length > 0 ? <span className="micro-pill">{listingResults.length} listings</span> : null}
          {handoff ? <span className="micro-pill">handoff ready</span> : null}
          {sources.length > 0 ? <span className="micro-pill">{sources.length} sources</span> : null}
        </div>
      </div>

      <div className={`run-block__body${content.trim().length === 0 ? " run-block__body--placeholder" : ""}`}>{bodyContent}</div>

      {listingResults.length > 0 ? (
        <section className="run-section">
          <div className="run-section__title">Listings</div>
          <div className="listing-stack">
            {listingResults.slice(0, 3).map((listing) => (
              <ListingCard key={listing.id} listing={listing} compact />
            ))}
          </div>
        </section>
      ) : null}

      {handoff ? (
        <section className="run-section">
          <HandoffCard handoff={handoff} />
        </section>
      ) : null}

      {sources.length > 0 ? (
        <section className="run-section">
          <div className="run-section__title">Provenance</div>
          <SourceList sources={sources} />
        </section>
      ) : null}
    </article>
  );
}
