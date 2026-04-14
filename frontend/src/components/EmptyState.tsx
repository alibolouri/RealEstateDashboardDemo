type Props = {
  prompts: string[];
  onPrompt: (prompt: string) => void;
};

export function EmptyState({ prompts, onPrompt }: Props) {
  return (
    <section className="panel starter-panel">
      <div>
        <div className="starter-panel__title">Start with a specific request</div>
        <p className="starter-panel__body">
          Ask for listings, financing guidance, neighborhood help, or a routed human handoff. The workspace will organize results, provenance, and next steps as the run progresses.
        </p>
      </div>

      <div className="starter-grid">
        {prompts.map((prompt) => (
          <button key={prompt} className="button button--secondary" onClick={() => onPrompt(prompt)}>
            {prompt}
          </button>
        ))}
      </div>
    </section>
  );
}
