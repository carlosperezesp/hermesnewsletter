// screens-current.jsx — Temporada Actual screen + Playoff bracket

function CurrentSeason({ onTeamClick, onPlayerClick, onOpenMethodology }) {
  const { TEAMS, PLAYERS, BRACKET } = window.NHL_DATA;
  const [conf, setConf] = useState("E");
  const [posFilter, setPosFilter] = useState("ALL");

  // Standings: filter by conf, default sorted by pts desc
  const standings = useMemo(() => {
    return TEAMS.filter(t => t.conf === conf);
  }, [TEAMS, conf]);

  // Top players: filter by position
  const topPlayers = useMemo(() => {
    const filtered = posFilter === "ALL"
      ? PLAYERS
      : posFilter === "W"
        ? PLAYERS.filter(p => p.pos === "LW" || p.pos === "RW")
        : PLAYERS.filter(p => p.pos === posFilter);
    return [...filtered].sort((a, b) => b.score - a.score);
  }, [PLAYERS, posFilter]);

  const standingsCols = [
    {
      key: "rank", label: "#", w: 28, numeric: true, sortable: false,
      render: (_r, i) => <span className="mono mono--muted">{String(i + 1).padStart(2, "0")}</span>,
    },
    {
      key: "city", label: "Team", w: "auto",
      render: r => (
        <span className="team-cell">
          <TeamSwatch colors={r.colors} code={r.code} />
          <span className="team-cell__text">
            <span className="team-cell__code">{r.code}</span>
            <span className="team-cell__city">{r.city}</span>
          </span>
        </span>
      ),
    },
    { key: "gp",  label: "GP",  numeric: true, w: 48 },
    {
      key: "rec", label: "W–L–OT", numeric: true, w: 84, sortable: false,
      render: r => <span className="mono">{r.w}–{r.l}–{r.ot}</span>,
      value: r => r.w,
    },
    {
      key: "pts", label: "PTS", numeric: true, w: 56,
      render: r => <span className="mono mono--bold">{r.pts}</span>,
    },
    {
      key: "gd",  label: "GF / GA", numeric: true, w: 96,
      render: r => <span className="mono mono--muted">{r.gf} <span className="gd-slash">/</span> {r.ga}</span>,
      value: r => r.gd,
    },
    {
      key: "score", label: "Team Score", numeric: true, w: 132,
      render: r => <ScoreBar value={r.score} width={64} />,
    },
  ];

  const playerCols = [
    {
      key: "rank", label: "#", w: 28, numeric: true, sortable: false,
      render: (_r, i) => <span className="mono mono--muted">{String(i + 1).padStart(2, "0")}</span>,
    },
    {
      key: "name", label: "Player", w: "auto",
      render: r => (
        <span className="player-cell">
          <span className="player-line">
            <TeamSwatch colors={r.colors} code={r.teamCode} />
            <span className="player-cell__name">{r.name}</span>
          </span>
          <span className="player-cell__meta">{r.teamCode}{r.country ? ` · ${r.country}` : ""}{r.age ? ` · age ${r.age}` : ""}</span>
        </span>
      ),
    },
    {
      key: "pos", label: "Pos", w: 52, sortable: false,
      render: r => <PosBadge pos={r.pos} />,
    },
    {
      key: "stat", label: "Headline stat", w: 120, sortable: false,
      render: r => r.pos === "G"
        ? <span className="mono mono--muted">{r.stats.svpct.toFixed(3)} SV%</span>
        : <span className="mono mono--muted">{r.stats.p} P · {r.stats.g} G</span>,
    },
    {
      key: "traj", label: "5-yr", w: 70, sortable: false,
      render: r => <Sparkline values={r.trajectory} width={56} height={16} />,
    },
    {
      key: "score", label: "Score", numeric: true, w: 124,
      render: r => <ScoreBar value={r.score} width={56} />,
    },
  ];

  return (
    <div className="screen screen--current">
      <SectionHead
        kicker="Screen 01 / Temporada actual"
        title="2025–26 season at a glance"
        sub="Real NHL standings, playoff bracket, and top performers ranked by a transparent position-adjusted tracker score."
        right={
          <button className="link-button" onClick={onOpenMethodology}>
            How is the score calculated? →
          </button>
        }
      />

      {/* ───── Playoff bracket ───── */}
      <section className="block">
        <div className="block__head">
          <WFLabel>PLAYOFF BRACKET — live from NHL</WFLabel>
          <span className="block__head-meta">First-to-4 series · best-of-7</span>
        </div>
        <Bracket bracket={BRACKET} onTeamClick={onTeamClick} />
      </section>

      {/* ───── Standings ───── */}
      <section className="block">
        <div className="block__head">
          <WFLabel>STANDINGS</WFLabel>
          <div className="seg">
            <button className={`seg__btn ${conf === "E" ? "seg__btn--on" : ""}`} onClick={() => setConf("E")}>Eastern</button>
            <button className={`seg__btn ${conf === "W" ? "seg__btn--on" : ""}`} onClick={() => setConf("W")}>Western</button>
          </div>
        </div>

        <div className="block__body block__body--rel">
          <SortableTable
            columns={standingsCols}
            rows={standings}
            defaultSort={{ key: "pts", dir: "desc" }}
            rowKey={r => r.code}
            onRowClick={onTeamClick}
          />
          <MarginNote side="right">
            Click a row → team detail<br />with full roster.
          </MarginNote>
        </div>
      </section>

      {/* ───── Top 10 players ───── */}
      <section className="block">
        <div className="block__head">
          <WFLabel>TOP PERFORMERS — position-adjusted</WFLabel>
          <div className="seg">
            {["ALL", "C", "W", "D", "G"].map(p => (
              <button
                key={p}
                className={`seg__btn ${posFilter === p ? "seg__btn--on" : ""}`}
                onClick={() => setPosFilter(p)}
              >
                {p === "ALL" ? "All" : p === "W" ? "Wingers" : p === "C" ? "Centers" : p === "D" ? "Defense" : "Goalies"}
              </button>
            ))}
          </div>
        </div>

        <div className="block__body block__body--rel">
          <div className="scroll-region" style={{ maxHeight: 440 }}>
            <SortableTable
              columns={playerCols}
              rows={topPlayers.slice(0, 80)}
              defaultSort={{ key: "score", dir: "desc" }}
              rowKey={r => r.id}
              onRowClick={onPlayerClick}
            />
          </div>
          <MarginNote side="right">
            Top 10 by default, scroll for more.<br />Score normalized within position.
          </MarginNote>
        </div>
      </section>
    </div>
  );
}

// ───────────────────────── Bracket ─────────────────────────
function Bracket({ bracket, onTeamClick }) {
  const { TEAMS } = window.NHL_DATA;
  const teamByCode = Object.fromEntries(TEAMS.map(t => [t.code, t]));

  function Match({ m, round }) {
    const hi = m.hi ? teamByCode[m.hi] : null;
    const lo = m.lo ? teamByCode[m.lo] : null;
    const [hiW, loW] = m.seriesScore.includes("-")
      ? m.seriesScore.split("-").map(n => parseInt(n, 10))
      : [null, null];

    function Row({ team, wins, isWinner, isLoser }) {
      if (!team) return (
        <div className="match__row match__row--empty">
          <span className="match__code">—</span>
          <span className="match__city">TBD</span>
          <span className="match__wins">·</span>
        </div>
      );
      return (
        <div
          className={`match__row ${isWinner ? "match__row--winner" : ""} ${isLoser ? "match__row--loser" : ""}`}
          onClick={() => onTeamClick(team)}
          role="button"
          tabIndex={0}
        >
          <span className="match__code">{team.code}</span>
          <span className="match__city">{team.city}</span>
          <span className="match__wins">{wins ?? "·"}</span>
        </div>
      );
    }

    const decided = !!m.winner;

    return (
      <div className={`match ${decided ? "match--decided" : "match--live"}`}>
        <Row team={hi} wins={hiW} isWinner={decided && m.winner === m.hi} isLoser={decided && m.winner !== m.hi} />
        <Row team={lo} wins={loW} isWinner={decided && m.winner === m.lo} isLoser={decided && m.winner !== m.lo} />
        {!decided && <div className="match__live">SERIES LIVE · {m.seriesScore}</div>}
      </div>
    );
  }

  return (
    <div className="bracket">
      <div className="bracket__conf bracket__conf--east">
        <div className="bracket__conf-label">Eastern conference</div>
        <div className="bracket__rounds">
          <BracketRound label="Round 1" matches={bracket.east.r1} render={m => <Match m={m} round="r1" />} />
          <BracketRound label="Conf. semis" matches={bracket.east.r2} render={m => <Match m={m} round="r2" />} />
          <BracketRound label="Conf. final" matches={bracket.east.conf} render={m => <Match m={m} round="conf" />} />
        </div>
      </div>

      <div className="bracket__center">
        <div className="bracket__final">
          <div className="bracket__final-label">Stanley Cup Final</div>
          <div className="bracket__final-box">
            <div className="bracket__final-row">— · TBD</div>
            <div className="bracket__final-row">— · TBD</div>
          </div>
        </div>
      </div>

      <div className="bracket__conf bracket__conf--west">
        <div className="bracket__conf-label">Western conference</div>
        <div className="bracket__rounds bracket__rounds--reverse">
          <BracketRound label="Conf. final" matches={bracket.west.conf} render={m => <Match m={m} round="conf" />} />
          <BracketRound label="Conf. semis" matches={bracket.west.r2} render={m => <Match m={m} round="r2" />} />
          <BracketRound label="Round 1" matches={bracket.west.r1} render={m => <Match m={m} round="r1" />} />
        </div>
      </div>
    </div>
  );
}

function BracketRound({ label, matches, render }) {
  return (
    <div className="bracket-round" data-count={matches.length}>
      <div className="bracket-round__label">{label}</div>
      <div className="bracket-round__matches">
        {matches.map((m, i) => <div key={i} className="bracket-round__match-wrap">{render(m)}</div>)}
      </div>
    </div>
  );
}

Object.assign(window, { CurrentSeason });
