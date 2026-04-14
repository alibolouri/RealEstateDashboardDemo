type Props = {
  assistantBrand: string;
  brokerageName: string;
  onToggleSidebar: () => void;
  onOpenDrawer: () => void;
  mobile: boolean;
};

export function TopBar({ assistantBrand, brokerageName, onToggleSidebar, onOpenDrawer, mobile }: Props) {
  return (
    <header className="top-bar">
      <div className="top-bar__left">
        {mobile ? (
          <button className="button button--ghost mobile-only top-bar__menu-button" onClick={onOpenDrawer} aria-label="Open threads menu">
            <span className="top-bar__burger" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
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
    </header>
  );
}
