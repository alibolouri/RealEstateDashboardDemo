import type { HandoffCard, PropertyCard, SourceCitation } from "../lib/api";

type Props = {
  properties: PropertyCard[];
  handoff: HandoffCard | null;
  sources: SourceCitation[];
};

export function DetailPanel({ properties, handoff, sources }: Props) {
  return (
    <aside className="detail-panel">
      <section className="panel-block">
        <span className="eyebrow">Context</span>
        <h2>Active results</h2>
        {properties.length === 0 ? (
          <p className="muted">Relevant properties will appear here once the assistant finds matches.</p>
        ) : (
          properties.map((property) => (
            <article className="property-card" key={property.id}>
              <div>
                <strong>{property.title}</strong>
                <span>{property.city}, {property.state}</span>
              </div>
              <p>
                {property.listing_type === "short_stay" ? `$${property.price}/night` : `$${property.price.toLocaleString()}`} · {property.bedrooms} bd · {property.bathrooms} ba
              </p>
              <small>{property.short_description}</small>
            </article>
          ))
        )}
      </section>

      <section className="panel-block">
        <span className="eyebrow">Handoff</span>
        <h2>Doorviser routing</h2>
        {handoff ? (
          <article className="handoff-card">
            <p><strong>Doorviser:</strong> {handoff.fixed_contact_number}</p>
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
        <h2>Grounding</h2>
        {sources.length === 0 ? (
          <p className="muted">Sources will appear once the assistant references property data or Doorviser knowledge.</p>
        ) : (
          <ul className="source-list">
            {sources.map((source, index) => (
              <li key={`${source.label}-${index}`}>{source.label}</li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}

