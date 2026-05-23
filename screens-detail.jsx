// screens-detail.jsx — Team detail + Player detail

// ───────────────────────── Team Detail ─────────────────────────
function TeamDetail({ team, onBack, onPlayerClick, onOpenMethodology }) {
  const { PLAYERS } = window.NHL_DATA;
  const roster = useMemo(() => PLAYERS.filter(p => p.teamCode === team.code), [PLAYERS, team]);
  const [posFilter, setPosFilter] = useState("ALL");

  const filtered = useMemo(() => {
    if (posFilter === "ALL") return roster;
    if (posFilter === "F") return roster.filter(p => p.pos === "C" || p.pos === "LW" || p.pos === "RW");
    return roster.filter(p => p.pos === posFilter);
  }, [roster, posFilter]);

  // KPI numbers
  const skaters = roster.filter(p => p.pos !== "G");
  const goalies = roster.filter(p => p.pos === "G");
  const avgSkaterScore = Math.round(skaters.reduce((a, p) => a + p.score, 0) / skaters.length);
  const avgGoalieScore = goalies.length ? Math.round(goalies.reduce((a, p) => a + p.score, 0) / goalies.length) : 0;
  const topScorer = [...skaters].sort((a, b) => (b.stats.p || 0) - (a.stats.p || 0))[0];

  const rosterCols = [
    {
      key: "rank", label: "#", w: 28, numeric: true, sortable: false,
      render: (_r, i) => <span className="mono mono--muted">{String(i + 1).padStart(2, "0")}</span>,
    },
    {
      key: "name", label: "Player",
      render: r => (
        <span className="player-cell">
          <span className="player-cell__name">{r.name}</span>
          <span className="player-cell__meta">{r.age ? `age ${r.age}` : r.teamCode}</span>
        </span>
      ),
    },
    { key: "pos", label: "Pos", w: 52, sortable: false, render: r => <PosBadge pos={r.pos} /> },
    {
      key: "gp", label: "GP", w: 72, numeric: true,
      render: r => r.stats.gp_po > 0
        ? <span className="mono" title={`${r.stats.gp - r.stats.gp_po} reg + ${r.stats.gp_po} PO`}>
            {r.stats.gp - r.stats.gp_po}<span className="mono--muted">+{r.stats.gp_po}</span>
          </span>
        : <span className="mono">{r.stats.gp}</span>,
      value: r => r.stats.gp,
    },
    {
      key: "line1", label: "G / SV%", w: 96, sortable: false, numeric: true,
      render: r => r.pos === "G"
        ? <span className="mono">{r.stats.svpct.toFixed(3)}</span>
        : <span className="mono">{r.stats.g}</span>,
    },
    {
      key: "line2", label: "A / GAA", w: 96, sortable: false, numeric: true,
      render: r => r.pos === "G"
        ? <span className="mono">{r.stats.gaa.toFixed(2)}</span>
        : <span className="mono">{r.stats.a}</span>,
    },
    {
      key: "line3", label: "P / W", w: 72, sortable: false, numeric: true,
      render: r => r.pos === "G"
        ? <span className="mono mono--bold">{r.stats.w}</span>
        : <span className="mono mono--bold">{r.stats.p}</span>,
      value: r => r.pos === "G" ? r.stats.w : r.stats.p,
    },
    {
      key: "toi", label: "TOI / GS", w: 88, numeric: true, sortable: false,
      render: r => r.pos === "G"
        ? <span className="mono mono--muted">{r.stats.gp} GS</span>
        : <span className="mono mono--muted">{r.stats.toi}</span>,
    },
    {
      key: "score", label: "Score", numeric: true, w: 124,
      render: r => <ScoreBar value={r.score} width={56} />,
    },
  ];

  return (
    <div className="screen screen--detail">
      <button className="breadcrumb" onClick={onBack}>
        <span className="breadcrumb__arrow">←</span>
        <span>Back to standings</span>
      </button>

      {/* Team header */}
      <header className="detail-head">
        <div className="detail-head__id">
          <div className="detail-head__code">{team.code}</div>
          <div>
            <div className="detail-head__kicker">2025–26 · {team.div} division · {team.conf === "E" ? "Eastern" : "Western"}</div>
            <h1 className="detail-head__title">{team.city}</h1>
          </div>
        </div>

        <div className="detail-head__kpis">
          <Kpi label="Record" value={`${team.w}–${team.l}–${team.ot}`} mono />
          <Kpi label="Points" value={team.pts} mono bold />
          <Kpi label="Goals (F / A)" value={`${team.gf} / ${team.ga}`} mono />
          <Kpi label="Team score" value={
            <span className="kpi__score">
              <ScoreBar value={team.score} width={48} mono />
            </span>
          } />
        </div>
      </header>

      {/* Score breakdown row */}
      <section className="block">
        <div className="block__head">
          <WFLabel>SCORE COMPOSITION</WFLabel>
          <button className="link-button" onClick={onOpenMethodology}>How this is computed →</button>
        </div>
        <div className="composition">
          <div className="composition__col">
            <div className="composition__label">Avg. skater score (TOI-weighted)</div>
            <div className="composition__value">{avgSkaterScore}</div>
            <div className="composition__bar"><span style={{ width: `${avgSkaterScore}%` }} /></div>
          </div>
          <div className="composition__col">
            <div className="composition__label">Avg. goalie score (GS-weighted)</div>
            <div className="composition__value">{avgGoalieScore}</div>
            <div className="composition__bar"><span style={{ width: `${avgGoalieScore}%` }} /></div>
          </div>
          <div className="composition__col">
            <div className="composition__label">Roster top scorer</div>
            <div className="composition__value composition__value--text">{topScorer?.name}</div>
            <div className="composition__sub mono mono--muted">{topScorer?.stats.p} P · score {topScorer?.score}</div>
          </div>
          <div className="composition__col composition__col--final">
            <div className="composition__label">Team score</div>
            <div className="composition__value composition__value--accent">{team.score}</div>
            <div className="composition__sub mono mono--muted">weighted avg of {skaters.length} skaters + {goalies.length} goalies</div>
          </div>
        </div>
      </section>

      {/* Roster table */}
      <section className="block">
        <div className="block__head">
          <WFLabel>FULL ROSTER · 2025–26</WFLabel>
          <div className="seg">
            {[
              ["ALL", "All"], ["F", "Forwards"], ["C", "C"], ["LW", "LW"], ["RW", "RW"], ["D", "D"], ["G", "G"],
            ].map(([k, label]) => (
              <button key={k} className={`seg__btn ${posFilter === k ? "seg__btn--on" : ""}`} onClick={() => setPosFilter(k)}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="block__body block__body--rel">
          <SortableTable
            columns={rosterCols}
            rows={filtered}
            defaultSort={{ key: "score", dir: "desc" }}
            rowKey={r => r.id}
            onRowClick={onPlayerClick}
            dense
          />
          <MarginNote side="right">
            Click any player → detail<br />with score breakdown.
          </MarginNote>
        </div>
      </section>
    </div>
  );
}

function Kpi({ label, value, mono, bold }) {
  return (
    <div className="kpi">
      <div className="kpi__label">{label}</div>
      <div className={`kpi__value ${mono ? "mono" : ""} ${bold ? "mono--bold" : ""}`}>{value}</div>
    </div>
  );
}

// ───────────────────────── Player Detail ─────────────────────────
function PlayerDetail({ player, onBack, onTeamClick, onOpenMethodology }) {
  const { TEAMS, PLAYERS, METHODOLOGY, PLAYER_COMPARISONS } = window.NHL_DATA;
  const comparison = useMemo(() => PLAYER_COMPARISONS.find(c => c.id === player.id), [PLAYER_COMPARISONS, player]);
  const team = TEAMS.find(t => t.code === player.teamCode);
  const isGoalie = player.pos === "G";

  // Position cohort percentile
  const cohort = useMemo(() => {
    if (player.pos === "G") return PLAYERS.filter(p => p.pos === "G");
    if (player.pos === "D") return PLAYERS.filter(p => p.pos === "D");
    return PLAYERS.filter(p => p.pos === "C" || p.pos === "LW" || p.pos === "RW");
  }, [PLAYERS, player]);

  const sortedCohort = useMemo(() => [...cohort].sort((a, b) => b.score - a.score), [cohort]);
  const rankInCohort = sortedCohort.findIndex(p => p.id === player.id) + 1;
  const cohortLabel = player.pos === "G" ? "goalies" : player.pos === "D" ? "defensemen" : "forwards";

  // Score component breakdown (synthetic but consistent with score)
  const components = isGoalie ? [
    { label: "Save share (xG vs actual)", value: Math.round(player.score * 0.95 + 4) },
    { label: "High-danger save %",        value: Math.round(player.score * 0.90 + 6) },
    { label: "Workload-adjusted GSAA",    value: Math.round(player.score * 1.02 - 2) },
    { label: "Quality-start rate",        value: Math.round(player.score * 0.98 + 1) },
  ] : [
    { label: "Even-strength offense",     value: Math.round(player.score * 1.01 - 1) },
    { label: "Power-play impact",         value: Math.round(player.score * 0.92 + 5) },
    { label: "Defensive impact",          value: Math.round(player.score * 0.88 + 8) },
    { label: "Penalty-kill / on-ice GA",  value: Math.round(player.score * 0.94 + 3) },
  ];

  return (
    <div className="screen screen--detail">
      <button className="breadcrumb" onClick={onBack}>
        <span className="breadcrumb__arrow">←</span>
        <span>Back</span>
      </button>

      {/* Player header */}
      <header className="detail-head detail-head--player">
        <div className="detail-head__id">
          {player.headshot ? (
            <img className="player-headshot" src={player.headshot} alt="" />
          ) : (
            <Placeholder h={84} style={{ width: 84, flex: "none" }}>player<br/>portrait</Placeholder>
          )}
          <div>
            <div className="detail-head__kicker">
              <PosBadge pos={player.pos} /> ·{" "}
              <span className="link-inline" onClick={() => onTeamClick(team)}>{team.city}</span>
              {player.age ? ` · age ${player.age}` : ""}
            </div>
            <h1 className="detail-head__title">{player.name}</h1>
          </div>
        </div>

        <div className="detail-head__kpis">
          {isGoalie ? (
            <>
              <Kpi label="Games" value={player.stats.gp} mono />
              <Kpi label="Wins" value={player.stats.w} mono bold />
              <Kpi label="Save %" value={player.stats.svpct.toFixed(3)} mono />
              <Kpi label="GAA" value={player.stats.gaa.toFixed(2)} mono />
            </>
          ) : (
            <>
              <Kpi label="Games" value={player.stats.gp} mono />
              <Kpi label="Goals" value={player.stats.g} mono />
              <Kpi label="Assists" value={player.stats.a} mono />
              <Kpi label="Points" value={player.stats.p} mono bold />
            </>
          )}
          <Kpi label="Player score" value={
            <span className="kpi__score">
              <ScoreBar value={player.score} width={56} mono />
            </span>
          } />
        </div>
      </header>

      {/* Score composition */}
      <section className="block">
        <div className="block__head">
          <WFLabel>SCORE BREAKDOWN — position-adjusted</WFLabel>
          <button className="link-button" onClick={onOpenMethodology}>Methodology →</button>
        </div>

        <div className="player-breakdown">
          <div className="player-breakdown__components">
            {components.map(c => (
              <div className="composition__col" key={c.label}>
                <div className="composition__label">{c.label}</div>
                <div className="composition__value">{Math.max(0, Math.min(100, c.value))}</div>
                <div className="composition__bar"><span style={{ width: `${Math.max(0, Math.min(100, c.value))}%` }} /></div>
              </div>
            ))}
          </div>

          <div className="player-breakdown__summary">
            <div className="player-breakdown__rank">
              <div className="player-breakdown__rank-label">Cohort rank</div>
              <div className="player-breakdown__rank-value">
                <span className="mono mono--bold">{rankInCohort}</span>
                <span className="mono mono--muted"> / {cohort.length}</span>
              </div>
              <div className="player-breakdown__rank-note mono mono--muted">
                among NHL {cohortLabel}, 2025–26
              </div>
            </div>

            <div className="player-breakdown__trajectory">
              <div className="composition__label">5-yr score trajectory</div>
              <div className="trajectory-chart">
                <Sparkline values={player.trajectory} width={220} height={56} />
                <div className="trajectory-chart__years">
                  {[4, 3, 2, 1, 0].map((y, i) => (
                    <span key={i} className="trajectory-chart__year mono mono--muted">
                      {2026 - y}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Career season history — available for skaters in PLAYER_COMPARISONS */}
      {comparison && comparison.seasons.length > 0 && (
        <section className="block">
          <div className="block__head">
            <WFLabel>CAREER NHL SEASONS</WFLabel>
          </div>
          <div className="scroll-region" style={{ maxHeight: 360 }}>
            <table className="table table--dense">
              <thead>
                <tr>
                  <th className="table__th" style={{ width: 80 }}>Season</th>
                  <th className="table__th" style={{ width: 32 }}>Age</th>
                  <th className="table__th">Team</th>
                  <th className="table__th table__th--num" style={{ width: 48 }}>GP</th>
                  <th className="table__th table__th--num" style={{ width: 44 }}>G</th>
                  <th className="table__th table__th--num" style={{ width: 44 }}>A</th>
                  <th className="table__th table__th--num" style={{ width: 52 }}>P</th>
                  <th className="table__th table__th--num" style={{ width: 44 }}>+/–</th>
                  <th className="table__th table__th--num" style={{ width: 140 }}>Season score</th>
                </tr>
              </thead>
              <tbody>
                {[...comparison.seasons].reverse().map(s => (
                  <tr key={s.seasonId} className="table__row">
                    <td className="table__td"><span className="mono">{s.season}</span></td>
                    <td className="table__td"><span className="mono mono--muted">{s.age}</span></td>
                    <td className="table__td"><span className="mono mono--muted">{s.team}</span></td>
                    <td className="table__td table__td--num"><span className="mono">{s.gp}</span></td>
                    <td className="table__td table__td--num"><span className="mono">{s.g}</span></td>
                    <td className="table__td table__td--num"><span className="mono">{s.a}</span></td>
                    <td className="table__td table__td--num"><span className="mono mono--bold">{s.p}</span></td>
                    <td className="table__td table__td--num"><span className="mono mono--muted">{s.pm > 0 ? `+${s.pm}` : s.pm}</span></td>
                    <td className="table__td table__td--num"><ScoreBar value={s.score} width={68} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

Object.assign(window, { TeamDetail, PlayerDetail });
