type Props = {
  assistantBrand: string;
  brokerageName: string;
  onOpenDrawer: () => void;
  mobile: boolean;
};

export function TopBar({ assistantBrand, brokerageName, onOpenDrawer, mobile }: Props) {
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
        ) : null}

        <div className="top-bar__heading">
          <div className="top-bar__title">{assistantBrand}</div>
          <div className="top-bar__subtitle">{brokerageName}</div>
        </div>
      </div>
    </header>
  );
}
