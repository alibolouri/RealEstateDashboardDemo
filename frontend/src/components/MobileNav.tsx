export type MobileView = "threads" | "workspace" | "listings" | "handoff" | "sources";

type Props = {
  activeView: MobileView;
  onChange: (view: MobileView) => void;
};

const ITEMS: Array<{ id: MobileView; label: string }> = [
  { id: "threads", label: "Threads" },
  { id: "workspace", label: "Workspace" },
  { id: "listings", label: "Listings" },
  { id: "handoff", label: "Handoff" },
  { id: "sources", label: "Sources" }
];

export function MobileNav({ activeView, onChange }: Props) {
  return (
    <nav className="mobile-nav" aria-label="Mobile workspace navigation">
      {ITEMS.map((item) => (
        <button
          key={item.id}
          className={`mobile-nav__item${item.id === activeView ? " is-active" : ""}`}
          onClick={() => onChange(item.id)}
        >
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
