import type { HandoffCard, ListingCard, SourceCitation } from "../lib/api";

type Props = {
  listings: ListingCard[];
  handoff: HandoffCard | null;
  sources: SourceCitation[];
  brokerageName: string;
};

function formatPrice(listing: ListingCard) {
  return listing.listing_type === "short_stay" ? `$${listing.price}/night` : `$${listing.price.toLocaleString()}`;
}

export function DetailPanel({ listings, handoff, sources, brokerageName }: Props) {
  return (
    <aside className="detail-panel">
      <section className="panel-block">
        <span className="eyebrow">Context</span>
        <h2>Matched listings</h2>
        {listings.length === 0 ? (
          <p className="muted">Relevant listings will appear here once the assistant finds matches.</p>
        ) : (
          listings.map((listing) => (
            <article className="property-card" key={listing.id}>
              <div>
                <strong>{listing.title}</strong>
                <span>{listing.city}, {listing.state}</span>
              </div>
              <p>
                {formatPrice(listing)} · {listing.bedrooms} bd · {listing.bathrooms} ba
              </p>
              <small>{listing.short_description}</small>
              <small className="meta-line">{listing.source} · {listing.data_status}</small>
            </article>
          ))
        )}
      </section>

      <section className="panel-block">
        <span className="eyebrow">Handoff</span>
        <h2>{brokerageName} routing</h2>
        {handoff ? (
          <article className="handoff-card">
            <p><strong>Brokerage:</strong> {handoff.fixed_contact_number}</p>
            <p><strong>Realtor:</strong> {handoff.recommended_realtor.name}</p>
            <p>{handoff.recommended_realtor.specialty}</p>
            <small>{handoff.reason}</small>
          </article>
        ) : (
          <p className="muted">When a user asks for human help, the routing card will appear here.</p>
        )}
      </section>

      <section className="panel-block">
        <span className="eyebrow">Sources</span>
        <h2>Grounding and provenance</h2>
        {sources.length === 0 ? (
          <p className="muted">Sources will appear once the assistant references listings, guidance documents, or routing policy.</p>
        ) : (
          <ul className="source-list">
            {sources.map((source, index) => (
              <li key={`${source.label}-${index}`}>
                <strong>{source.label}</strong>
                <span>{source.type.replace("_", " ")} · {source.data_status} · {Math.round(source.confidence * 100)}% confidence</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}
