import type { HandoffCard as HandoffCardType } from "../lib/api";

export function HandoffCard({ handoff }: { handoff: HandoffCardType }) {
  return (
    <article className="handoff-card">
      <div className="run-section__title">Brokerage handoff</div>
      <div className="handoff-card__grid">
        <div>
          <div className="handoff-card__label">Primary line</div>
          <strong>{handoff.fixed_contact_number}</strong>
        </div>
        <div>
          <div className="handoff-card__label">Recommended realtor</div>
          <strong>{handoff.recommended_realtor.name}</strong>
        </div>
      </div>
      <div className="handoff-card__meta">
        <div className="u-muted">{handoff.recommended_realtor.specialty}</div>
        <div className="u-tertiary">{handoff.recommended_realtor.phone}</div>
      </div>
      <div className="handoff-card__reason">{handoff.reason}</div>
      <div className="callout-note">{handoff.next_step_message}</div>
    </article>
  );
}
