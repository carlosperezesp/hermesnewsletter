// screens-history.jsx — All-time history screen

function History({ onOpenMethodology }) {
  const { HISTORY_TEAMS, HISTORY_PLAYERS } = window.NHL_DATA;
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
