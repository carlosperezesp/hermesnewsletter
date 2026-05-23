// screens-history.jsx — All-time history screen

function RoadToGlory({ data, onPlayerClick }) {
  const [tab, setTab] = useState("players");
  if (!data) return null;
  const { players, teams, playerThreshold, teamThreshold } = data;

  function handlePlayerClick(playerId) {
    const player = window.NHL_DATA.PLAYERS.find(p => p.id === playerId);
    if (player && onPlayerClick) onPlayerClick(player);
  }

  return (
    <div className="block">
      <div className="block__head">
        <div>
          <WFLabel>HALL OF FAME WATCH</WFLabel>
          <h3 className="rtg-title">Road to glory</h3>
          <p className="rtg-sub">
            Active players and current franchises tracking toward the all-time top 10.
            Same 0–100 scale — the red line marks the minimum score to enter.
          </p>
        </div>
        <div className="seg">
          <button className={`seg__btn ${tab === "players" ? "seg__btn--on" : ""}`} onClick={() => setTab("players")}>Players</button>
          <button className={`seg__btn ${tab === "teams" ? "seg__btn--on" : ""}`} onClick={() => setTab("teams")}>Franchises</button>
        </div>
      </div>

      <div className="rtg-threshold-note mono--muted">
        {tab === "players"
          ? <><span className="rtg-threshold-num">{playerThreshold}</span> = top-10 threshold · Dominik Hasek (1990–08)</>
          : <><span className="rtg-threshold-num">{teamThreshold}</span> = top-10 threshold · Pittsburgh Penguins (1991–92)</>
        }
      </div>

      <div className="rtg-list">
        {tab === "players" ? players.map((p, i) => (
          <div
            className="rtg-row rtg-row--clickable"
            key={p.id}
            onClick={() => handlePlayerClick(p.id)}
            title={`Ver detalle de ${p.name}`}
          >
            <span className="rtg-row__rank">{String(i + 1).padStart(2, "0")}</span>
            <span className="rtg-row__identity">
              <TeamSwatch colors={p.colors} code={p.teamCode} />
              <span className="rtg-row__info">
                <span className="rtg-row__name">{p.name}</span>
                <span className="rtg-row__meta">
                  {p.country} · <span className={`pos-badge pos-badge--${p.pos}`}>{p.pos}</span>
                  {p.age ? ` · ${p.age} años` : ""}
                  {` · ${p.seasons} temporadas`}
                  {p.cups > 0 ? ` · ${p.cups} Cup${p.cups > 1 ? "s" : ""}` : ""}
                </span>
              </span>
            </span>
            <span className="rtg-row__bar-col">
              <ThresholdBar value={p.careerScore} threshold={playerThreshold} width={160} />
              <span className="rtg-row__score mono mono--bold">{p.careerScore}</span>
            </span>
            <span className="rtg-row__gap">+{p.gap} to enter</span>
            <span className="rtg-row__note">{p.note}</span>
          </div>
        )) : teams.map((t, i) => (
          <div className="rtg-row" key={t.teamCode + t.era}>
            <span className="rtg-row__rank">{String(i + 1).padStart(2, "0")}</span>
            <span className="rtg-row__identity">
              <TeamSwatch colors={t.colors} code={t.teamCode} />
              <span className="rtg-row__info">
                <span className="rtg-row__name">{t.city}</span>
                <span className="rtg-row__meta">{t.era} · {t.cups} Cup{t.cups !== 1 ? "s" : ""} · {t.note}</span>
              </span>
            </span>
            <span className="rtg-row__bar-col">
              <ThresholdBar value={t.dynastyScore} threshold={teamThreshold} width={160} />
              <span className="rtg-row__score mono mono--bold">{t.dynastyScore}</span>
            </span>
            <span className="rtg-row__gap">+{t.gap} to enter</span>
            <span className="rtg-row__note">{t.needs}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function YoungGuns({ data, onPlayerClick }) {
  if (!data) return null;
  const { youngProspects, playerThreshold } = data;
  if (!youngProspects || youngProspects.length === 0) return null;

  function handleClick(playerId) {
    const player = window.NHL_DATA.PLAYERS.find(p => p.id === playerId);
    if (player && onPlayerClick) onPlayerClick(player);
  }

  return (
    <div className="block">
      <div className="block__head">
        <div>
          <WFLabel>JÓVENES EN CAMINO</WFLabel>
          <h3 className="rtg-title">Jóvenes on the road to glory</h3>
          <p className="rtg-sub">
            25 años o menos con estadísticas que apuntan al top 10 histórico.
            Score proyectado: si mantienen su nivel actual hasta los 38 años.
            La línea roja marca el mínimo para entrar.
          </p>
        </div>
      </div>

      <div className="rtg-threshold-note mono--muted">
        <span className="rtg-threshold-num">{playerThreshold}</span> = umbral top-10 · Dominik Hasek
      </div>

      <div className="rtg-list">
        {youngProspects.map((p, i) => (
          <div
            className="rtg-row rtg-row--clickable"
            key={p.id}
            onClick={() => handleClick(p.id)}
          >
            <span className="rtg-row__rank">{String(i + 1).padStart(2, "0")}</span>
            <span className="rtg-row__identity">
              <TeamSwatch colors={p.colors} code={p.teamCode} />
              <span className="rtg-row__info">
                <span className="rtg-row__name">{p.name}</span>
                <span className="rtg-row__meta">
                  {p.country} · <span className={`pos-badge pos-badge--${p.pos}`}>{p.pos}</span>
                  {p.age ? ` · ${p.age} años` : ""}
                  {" · score actual "}
                  <span className="mono mono--bold">{p.currentScore}</span>
                </span>
              </span>
            </span>
            <span className="rtg-row__bar-col">
              <ThresholdBar value={p.projectedScore} threshold={playerThreshold} width={160} />
              <span className="rtg-row__score mono mono--bold">{p.projectedScore}</span>
            </span>
            <span className="rtg-row__gap">+{p.gap} to enter</span>
            <span className="rtg-row__note">{p.note}</span>
          </div>
        ))}
      </div>

      <div className="rtg-projection-note mono mono--muted">
        Proyección basada en nivel actual sostenido hasta los 38 años + potencial de Cups.
        No es una predicción — es un escenario optimista.
      </div>
    </div>
  );
}

function History({ onOpenMethodology, onPlayerClick }) {
  const { HISTORY_TEAMS, HISTORY_PLAYERS, ROAD_TO_GLORY } = window.NHL_DATA;
  const [tab, setTab] = useState("teams"); // 'teams' | 'players'

  const teamCols = [
    {
      key: "rank", label: "#", w: 36, numeric: true, sortable: false,
      render: r => <span className="rank-num">{String(r.rank).padStart(2, "0")}</span>,
    },
    {
      key: "city", label: "Franchise / era",
      render: r => (
        <span className="hist-cell">
          <span className="player-line">
            <TeamSwatch colors={r.colors} code={r.teamCode} />
            <span className="hist-cell__name">{r.city}</span>
          </span>
          <span className="hist-cell__meta">{r.country} · peak era · {r.era}</span>
        </span>
      ),
    },
    { key: "conf", label: "Era league", w: 132, render: r => <span className="mono mono--muted">{r.conf}</span> },
    {
      key: "titles", label: "Cups in run", w: 100, numeric: true,
      render: r => <span className="mono mono--bold">{r.titles}</span>,
    },
    {
      key: "conf_tier", label: "Conf.", w: 64, numeric: true, sortable: false,
      render: r => <TierBadge tier={r.conf_tier} />,
    },
    {
      key: "score", label: "All-time score", numeric: true, w: 152,
      render: r => <ScoreBar value={r.score} width={72} />,
    },
  ];

  const playerCols = [
    {
      key: "rank", label: "#", w: 36, numeric: true, sortable: false,
      render: r => <span className="rank-num">{String(r.rank).padStart(2, "0")}</span>,
    },
    {
      key: "name", label: "Player",
      render: r => (
        <span className="hist-cell">
          <span className="player-line">
            <TeamSwatch colors={r.colors} code={r.teamCode} />
            <span className="hist-cell__name">{r.name}</span>
          </span>
          <span className="hist-cell__meta">{r.country} · {r.note}</span>
        </span>
      ),
    },
    {
      key: "pos", label: "Pos", w: 56, sortable: false,
      render: r => <PosBadge pos={r.pos} />,
    },
    {
      key: "era", label: "Era", w: 128, render: r => <span className="mono mono--muted">{r.era}</span>,
    },
    {
      key: "tier", label: "Conf.", w: 64, numeric: true, sortable: false,
      render: r => <TierBadge tier={r.tier} />,
    },
    {
      key: "score", label: "All-time score", numeric: true, w: 152,
      render: r => <ScoreBar value={r.score} width={72} />,
    },
  ];

  return (
    <div className="screen screen--history">
      <SectionHead
        kicker="Screen 02 / All-time"
        title="The top 10 since 1917"
        sub="Cross-era, position-adjusted rankings. Pre-expansion seasons rely on regressed box-score approximations — confidence tier is shown for every row."
        right={
          <button className="link-button" onClick={onOpenMethodology}>
            Methodology &amp; data tiers →
          </button>
        }
      />

      <div className="block">
        <div className="block__head">
          <WFLabel>HISTORICAL TOPS</WFLabel>
          <div className="seg">
            <button className={`seg__btn ${tab === "teams" ? "seg__btn--on" : ""}`} onClick={() => setTab("teams")}>Top 10 teams</button>
            <button className={`seg__btn ${tab === "players" ? "seg__btn--on" : ""}`} onClick={() => setTab("players")}>Top 10 players</button>
          </div>
        </div>

        <div className="block__body block__body--rel">
          {tab === "teams" ? (
            <SortableTable
              columns={teamCols}
              rows={HISTORY_TEAMS}
              defaultSort={{ key: "score", dir: "desc" }}
              rowKey={r => `${r.city}-${r.era}`}
            />
          ) : (
            <SortableTable
              columns={playerCols}
              rows={HISTORY_PLAYERS}
              defaultSort={{ key: "score", dir: "desc" }}
              rowKey={r => r.name}
            />
          )}
          <MarginNote side="right">
            Tier badges A–D indicate<br />
            data confidence by era.<br />
            D = boxscore approximation.
          </MarginNote>
        </div>
      </div>

      <RoadToGlory data={ROAD_TO_GLORY} onPlayerClick={onPlayerClick} />
      <YoungGuns data={ROAD_TO_GLORY} onPlayerClick={onPlayerClick} />

      {/* Era timeline footnote */}
      <div className="era-strip">
        <WFLabel>ERA TIMELINE</WFLabel>
        <div className="era-strip__bar">
          <div className="era-strip__segment era-strip__segment--d" style={{ flex: 24 }}>
            <span className="era-strip__label">1917–41 · tier D</span>
          </div>
          <div className="era-strip__segment era-strip__segment--c" style={{ flex: 24 }}>
            <span className="era-strip__label">1942–66 · tier C · Original Six</span>
          </div>
          <div className="era-strip__segment era-strip__segment--b" style={{ flex: 12 }}>
            <span className="era-strip__label">1967–79 · tier B</span>
          </div>
          <div className="era-strip__segment era-strip__segment--a" style={{ flex: 46 }}>
            <span className="era-strip__label">1980 → present · tier A</span>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { History });
