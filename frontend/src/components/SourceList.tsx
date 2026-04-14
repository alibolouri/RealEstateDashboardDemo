import type { SourceCitation } from "../lib/api";

function formatSourceType(type: SourceCitation["type"]) {
  switch (type) {
    case "listing_source":
      return "Listing source";
    case "knowledge_source":
      return "Guidance source";
    case "routing_source":
      return "Routing policy";
  }
}

function formatDataStatus(status: SourceCitation["data_status"]) {
  switch (status) {
    case "live":
      return "Live";
    case "cached":
      return "Cached";
    case "demo":
    default:
      return "Sample";
  }
}

export function SourceList({ sources }: { sources: SourceCitation[] }) {
  return (
    <div className="source-stack">
      {sources.map((source, index) => (
        <article className="source-card" key={`${source.label}-${index}`}>
          <div>
            <div className="source-card__title">{source.label}</div>
            <div className="source-card__meta">
              {formatSourceType(source.type)} · {formatDataStatus(source.data_status)}
              {source.timestamp ? ` · ${new Date(source.timestamp).toLocaleString()}` : ""}
            </div>
            {source.url ? (
              <a className="source-card__link" href={source.url} target="_blank" rel="noreferrer">
                Open source
              </a>
            ) : null}
          </div>
          <div className="source-card__confidence">{Math.round(source.confidence * 100)}%</div>
        </article>
      ))}
    </div>
  );
}
