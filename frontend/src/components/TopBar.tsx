type Props = {
  assistantBrand: string;
  brokerageName: string;
  sourceModeLabel: string;
  onToggleSidebar: () => void;
  onOpenDrawer: () => void;
  onOpenSheet: () => void;
  onLogout: () => void;
  mobile: boolean;
};

export function TopBar({
  assistantBrand,
  brokerageName,
  sourceModeLabel,
  onToggleSidebar,
  onOpenDrawer,
  onOpenSheet,
  onLogout,
  mobile
}: Props) {
  return (
    <header className="top-bar">
      <div className="top-bar__left">
        {mobile ? (
          <button className="button button--ghost mobile-only" onClick={onOpenDrawer} aria-label="Open threads">
            Menu
          </button>
        ) : (
          <button className="button button--ghost" onClick={onToggleSidebar} aria-label="Toggle sidebar">
            Pane
          </button>
        )}

        <div className="top-bar__heading">
          <div className="top-bar__title">{assistantBrand}</div>
          <div className="top-bar__subtitle">{brokerageName}</div>
        </div>
      </div>

      <div className="top-bar__right">
        <span className="status-pill status-pill--healthy">healthy</span>
        {!mobile ? <span className="status-pill status-pill--demo">{sourceModeLabel}</span> : null}
        <button className="button button--ghost mobile-only" onClick={onOpenSheet}>
          Context
        </button>
        {!mobile ? (
          <button className="button button--secondary top-bar__logout" onClick={onLogout}>
            Log out
          </button>
        ) : null}
      </div>
    </header>
  );
}
