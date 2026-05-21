// app.jsx — root app, top nav, screen router

function App() {
  const D = window.NHL_DATA;
  const [view, setView] = useState({ name: "current" }); // current | history | players | team | player
  const [methodOpen, setMethodOpen] = useState(false);

  function go(view) {
    setView(view);
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function onTeamClick(team) { go({ name: "team", team, from: view }); }
  function onPlayerClick(player) { go({ name: "player", player, from: view }); }
  function onBack() {
    if (view.from) go(view.from);
    else go({ name: "current" });
  }

  let screen = null;
  if (view.name === "current") {
    screen = <CurrentSeason onTeamClick={onTeamClick} onPlayerClick={onPlayerClick} onOpenMethodology={() => setMethodOpen(true)} />;
  } else if (view.name === "history") {
    screen = <History onOpenMethodology={() => setMethodOpen(true)} />;
  } else if (view.name === "players") {
    screen = <PlayersCompare onOpenMethodology={() => setMethodOpen(true)} />;
  } else if (view.name === "team") {
    screen = <TeamDetail team={view.team} onBack={onBack} onPlayerClick={onPlayerClick} onOpenMethodology={() => setMethodOpen(true)} />;
  } else if (view.name === "player") {
    screen = <PlayerDetail player={view.player} onBack={onBack} onTeamClick={onTeamClick} onOpenMethodology={() => setMethodOpen(true)} />;
  }

  const isDetail = view.name === "team" || view.name === "player";

  return (
    <div className="app">
      <TopNav
        active={view.name === "history" ? "history" : view.name === "players" ? "players" : "current"}
        onNav={name => go({ name })}
        season={D.SEASON}
        lastUpdate={D.LAST_UPDATE}
        showHomeOnly={!isDetail}
      />

      <main className="main">
        {screen}
      </main>

      <Footer />

      <MethodologyOverlay open={methodOpen} onClose={() => setMethodOpen(false)} data={D.METHODOLOGY} />
    </div>
  );
}

function TopNav({ active, onNav, season, lastUpdate }) {
  return (
    <header className="topnav">
      <div className="topnav__inner">
        <div className="topnav__brand">
          <span className="topnav__logo" aria-hidden="true">
            {/* abstract puck mark — original, no team IP */}
            <svg viewBox="0 0 24 24" width="22" height="22">
              <ellipse cx="12" cy="14" rx="9" ry="3.2" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <ellipse cx="12" cy="10" rx="9" ry="3.2" fill="currentColor" />
              <line x1="3" y1="10" x2="3" y2="14" stroke="currentColor" strokeWidth="1.5" />
              <line x1="21" y1="10" x2="21" y2="14" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </span>
          <div className="topnav__title-block">
            <div className="topnav__title">NHL Tracker</div>
            <div className="topnav__sub mono mono--muted">Live NHL data · local daily refresh</div>
          </div>
        </div>

        <nav className="topnav__tabs" aria-label="Primary">
          <button className={`tab ${active === "current" ? "tab--on" : ""}`} onClick={() => onNav("current")}>
            <span className="tab__num mono">01</span>
            <span>Temporada actual</span>
          </button>
          <button className={`tab ${active === "history" ? "tab--on" : ""}`} onClick={() => onNav("history")}>
            <span className="tab__num mono">02</span>
            <span>Historia</span>
          </button>
          <button className={`tab ${active === "players" ? "tab--on" : ""}`} onClick={() => onNav("players")}>
            <span className="tab__num mono">03</span>
            <span>Jugadores</span>
          </button>
        </nav>

        <div className="topnav__meta">
          <div className="topnav__season">
            <div className="topnav__season-label mono mono--muted">SEASON</div>
            <div className="topnav__season-value">{season}</div>
          </div>
          <div className="topnav__update mono mono--muted">
            Updated {lastUpdate}
          </div>
        </div>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner mono mono--muted">
        <span>NHL Tracker · live local dashboard</span>
        <span className="footer__dot">·</span>
        <span>Data generated from the public NHL web API</span>
        <span className="footer__dot">·</span>
        <span>Refresh with python3 scripts/update_data.py</span>
      </div>
    </footer>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
