import type { HandoffCard as HandoffCardType, ListingCard as ListingCardType, SourceCitation } from "../lib/api";
import { HandoffCard } from "./HandoffCard";
import { ListingCard } from "./ListingCard";
import { SourceList } from "./SourceList";

type Mode = "all" | "listings" | "handoff" | "sources";

type Props = {
  listings: ListingCardType[];
  handoff: HandoffCardType | null;
  sources: SourceCitation[];
  brokerageName: string;
  mode?: Mode;
};

function shouldShow(section: Exclude<Mode, "all">, mode: Mode) {
  return mode === "all" || mode === section;
}

export function DetailPanel({ listings, handoff, sources, brokerageName, mode = "all" }: Props) {
  return (
    <div className="context-panel">
      {shouldShow("listings", mode) ? (
        <section className="context-panel__section">
          <div>
            <div className="run-section__title">Listings</div>
            <div className="context-panel__section-title">Matched listings</div>
            <div className="context-panel__section-copy">
              Structured results from the active listing source appear here as the agent resolves the run.
            </div>
          </div>

          {listings.length > 0 ? (
            <div className="listing-stack">
              {listings.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          ) : (
            <div className="panel run-block">
              <div className="run-block__body">No listing context yet. Ask for a city, budget, beds, or listing type.</div>
            </div>
          )}
        </section>
      ) : null}

      {shouldShow("handoff", mode) ? (
        <section className="context-panel__section">
          <div>
            <div className="run-section__title">Routing</div>
            <div className="context-panel__section-title">{brokerageName} handoff</div>
            <div className="context-panel__section-copy">
              When the user requests human help, the fixed brokerage line and recommended realtor are elevated here.
            </div>
          </div>
          {handoff ? (
            <HandoffCard handoff={handoff} />
          ) : (
            <div className="panel run-block">
              <div className="run-block__body">Handoff remains idle until the user asks to connect with a human specialist.</div>
            </div>
          )}
        </section>
      ) : null}

      {shouldShow("sources", mode) ? (
        <section className="context-panel__section">
          <div>
            <div className="run-section__title">Provenance</div>
            <div className="context-panel__section-title">Sources and confidence</div>
            <div className="context-panel__section-copy">
              Every run can expose listing source provenance, routing policy, and knowledge confidence.
            </div>
          </div>
          {sources.length > 0 ? (
            <SourceList sources={sources} />
          ) : (
            <div className="panel run-block">
              <div className="run-block__body">No source metadata yet. Guidance, listings, and routing will appear here when used.</div>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
