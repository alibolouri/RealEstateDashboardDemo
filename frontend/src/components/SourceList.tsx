import type { SourceCitation } from "../lib/api";

export function SourceList({ sources }: { sources: SourceCitation[] }) {
  return (
    <div className="source-stack">
      {sources.map((source, index) => (
        <article className="source-card" key={`${source.label}-${index}`}>
          <div>
            <div className="source-card__title">{source.label}</div>
            <div className="source-card__meta">
              {source.type.replace("_", " ")} · {source.data_status}
              {source.timestamp ? ` · ${new Date(source.timestamp).toLocaleString()}` : ""}
            </div>
          </div>
          <div className="source-card__confidence">{Math.round(source.confidence * 100)}%</div>
        </article>
      ))}
    </div>
  );
}
