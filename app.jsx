// app.jsx — single-page newsletter view

function getAlivePlayoffTeams(bracket) {
  const alive = new Set();
  const groups = [
    ...(bracket?.east?.r1 || []),
    ...(bracket?.east?.r2 || []),
    ...(bracket?.east?.conf || []),
    ...(bracket?.west?.r1 || []),
    ...(bracket?.west?.r2 || []),
    ...(bracket?.west?.conf || []),
    ...(bracket?.final || []),
  ];

  groups.forEach(match => {
    if (!match || match.winner) return;
    if (match.hi) alive.add(match.hi);
    if (match.lo) alive.add(match.lo);
  });

  return alive;
}

function NewsletterRankRow({ rank, item, alive, aliveKey = "teamCode", forceOut = false, score, scoreDisplay, scoreLabel, scoreDelta, meta, note, threshold, logo, scoreB, scoreBDisplay, scoreBLabel, scoreBThreshold, prevRank, rowClassName = "", legendActive = false }) {
  const aliveValue = item?.[aliveKey];
  const isAlive = !forceOut && (alive.size === 0 || alive.has(aliveValue));
  const displayed = scoreDisplay !== undefined ? scoreDisplay : score;
  
  // Indicador de cambio semanal:
  //   number  → subió/bajó en la lista
  //   null    → entrada nueva (no estaba la semana pasada)
  //   undefined → sin datos (no mostrar nada)
  let changeEl = null;
  if (typeof prevRank === "number") {
    const diff = prevRank - rank;
    if (diff > 0)
      changeEl = (
        <span style={{ display:"inline-flex", alignItems:"center", justifyContent:"center",
          fontSize: 10, fontWeight: 700, lineHeight: 1, color: "#fff",
          background: "#2a7a2a", borderRadius: 3, padding: "2px 4px", minWidth: 22 }}>
          ↑{diff}
        </span>
      );
    else if (diff < 0)
      changeEl = (
        <span style={{ display:"inline-flex", alignItems:"center", justifyContent:"center",
          fontSize: 10, fontWeight: 700, lineHeight: 1, color: "#fff",
          background: "#a02020", borderRadius: 3, padding: "2px 4px", minWidth: 22 }}>
          ↓{-diff}
        </span>
      );
  } else if (prevRank === null) {
    changeEl = (
      <span style={{ display:"inline-flex", alignItems:"center", justifyContent:"center",
        fontSize: 9, fontWeight: 700, lineHeight: 1, color: "#fff",
        background: "#1a5fa8", borderRadius: 3, padding: "2px 4px", letterSpacing: "0.04em" }}>
        NEW
      </span>
    );
  }

  // Chip de variación de score respecto a la semana pasada (verde sube / rojo baja).
  let deltaChip = null;
  if (typeof scoreDelta === "number" && Math.abs(scoreDelta) >= 0.1) {
    const up = scoreDelta > 0;
    deltaChip = (
      <span style={{ display:"inline-flex", alignItems:"center", gap:1,
        fontSize: 9, fontWeight: 700, lineHeight: 1, color: "#fff",
        background: up ? "#2a7a2a" : "#a02020", borderRadius: 3, padding: "2px 4px",
        fontFamily: "monospace" }}>
        {up ? "▲" : "▼"}{Math.abs(scoreDelta).toFixed(1)}
      </span>
    );
  }

  return (
    <div className={`newsletter-row ${scoreB !== undefined ? "newsletter-row--dual-score" : ""} ${!isAlive ? "newsletter-row--out" : ""} ${legendActive && isAlive ? "newsletter-row--legend-active" : ""} ${rowClassName}`}>
      <span className="newsletter-row__rank" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}>
        <span>{String(rank).padStart(2, "0")}</span>
        {changeEl}
      </span>
      <span className="newsletter-row__identity">
        <TeamSwatch colors={item.colors} code={item.teamCode} logo={logo} />
        <span className="newsletter-row__copy">
          <span className="newsletter-row__name">{item.name || item.city}</span>
          <span className="newsletter-row__meta">{meta}</span>
        </span>
      </span>
      <span className="newsletter-row__score" style={{ alignItems: "flex-end" }}>
        <span className="newsletter-row__score-label">{scoreLabel}</span>
        {threshold ? (
          <span className="newsletter-row__threshold">
            <ThresholdBar value={score} threshold={threshold} width={124} />
            <span className="newsletter-row__score-value">{displayed}</span>
            {deltaChip}
          </span>
        ) : (
          <span style={{ display: "inline-flex", alignItems: "baseline", gap: 5 }}>
            <span className="newsletter-row__score-value">{displayed}</span>
            {deltaChip}
          </span>
        )}
      </span>
      {scoreB !== undefined && (
        <span className="newsletter-row__score newsletter-row__score--secondary">
          <span className="newsletter-row__score-label">{scoreBLabel}</span>
          {scoreBThreshold !== undefined ? (
            <span className="newsletter-row__threshold">
              <ThresholdBar value={scoreB} threshold={scoreBThreshold} width={104} />
              <span className="newsletter-row__score-value">{scoreBDisplay !== undefined ? scoreBDisplay : (typeof scoreB === "number" ? scoreB.toFixed(1) : scoreB)}</span>
            </span>
          ) : (
            <span className="newsletter-row__score-value">{scoreBDisplay !== undefined ? scoreBDisplay : (typeof scoreB === "number" ? scoreB.toFixed(1) : scoreB)}</span>
          )}
        </span>
      )}
      {note && <span className="newsletter-row__note">{note}</span>}
    </div>
  );
}

function NewsletterSection({ kicker, title, sub, children }) {
  return (
    <section className="newsletter-section">
      <div className="newsletter-section__head">
        <WFLabel>{kicker}</WFLabel>
        <h2>{title}</h2>
        {sub && <p>{sub}</p>}
      </div>
      {children}
    </section>
  );
}

function SectionIcon({ type }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };
  const icons = {
    all: (
      <>
        <rect x="4" y="4" width="6" height="6" rx="1" {...common} />
        <rect x="14" y="4" width="6" height="6" rx="1" {...common} />
        <rect x="4" y="14" width="6" height="6" rx="1" {...common} />
        <rect x="14" y="14" width="6" height="6" rx="1" {...common} />
      </>
    ),
    nhl: <path d="M5 19 17 7m-5 12h7m-2-12 2 2" {...common} />,
    nba: (
      <>
        <circle cx="12" cy="12" r="8" {...common} />
        <path d="M4 12h16M12 4c2 2.4 3 5.1 3 8s-1 5.6-3 8M12 4c-2 2.4-3 5.1-3 8s1 5.6 3 8" {...common} />
      </>
    ),
    mlb: (
      <>
        <circle cx="12" cy="12" r="8" {...common} />
        <path d="M8 6c2.5 3.1 2.5 8.9 0 12M16 6c-2.5 3.1-2.5 8.9 0 12" {...common} />
      </>
    ),
    nfl: (
      <>
        <path d="M4 12c2.8-5.2 13.2-5.2 16 0-2.8 5.2-13.2 5.2-16 0Z" {...common} />
        <path d="M9 12h6m-4-2v4m2-4v4" {...common} />
      </>
    ),
    tennis: (
      <>
        <circle cx="11" cy="11" r="7" {...common} />
        <path d="M6 7c4 1 6 4 7 9M17 17l4 4" {...common} />
      </>
    ),
    cycling: (
      <>
        <circle cx="7" cy="16" r="4" {...common} />
        <circle cx="17" cy="16" r="4" {...common} />
        <path d="M7 16l4-7 3 7m-3-7h4m-5-3h3" {...common} />
      </>
    ),
    sumo: (
      <>
        <circle cx="12" cy="6" r="3" {...common} />
        <path d="M7 12c2-2 8-2 10 0m-9 6 4-6 4 6M6 15h12" {...common} />
      </>
    ),
    f1: (
      <>
        <path d="M5 19V5m0 1h12l-2.2 3L17 12H5" {...common} />
        <path d="M8 8h2m2 0h2M8 11h2m2 0h2" {...common} />
      </>
    ),
    indycar: (
      <>
        <path d="M4 14h16l-2-4H8l-4 4Z" {...common} />
        <circle cx="8" cy="16" r="2" {...common} />
        <circle cx="17" cy="16" r="2" {...common} />
      </>
    ),
    nascar: (
      <>
        <path d="M3 14h18l-3-5H8l-5 5Z" {...common} />
        <circle cx="8" cy="16" r="2" {...common} />
        <circle cx="17" cy="16" r="2" {...common} />
        <path d="M6 8h3m2 0h3" {...common} />
      </>
    ),
    afl: (
      <>
        <path d="M4 12c2.8-4.2 13.2-4.2 16 0-2.8 4.2-13.2 4.2-16 0Z" {...common} />
        <path d="M9 12h6" {...common} />
      </>
    ),
    golf: (
      <>
        <path d="M8 21V4l9 3-9 3" {...common} />
        <path d="M5 21h7" {...common} />
        <circle cx="16" cy="18" r="2" {...common} />
      </>
    ),
    motogp: (
      <>
        <circle cx="12" cy="11" r="7" {...common} />
        <path d="M5 12h14M9 16h6M15 6l3 3" {...common} />
      </>
    ),
    rugby: (
      <>
        <path d="M4 12c2.8-5.2 13.2-5.2 16 0-2.8 5.2-13.2 5.2-16 0Z" {...common} />
        <path d="M12 8v8" {...common} />
      </>
    ),
    football: (
      <>
        <circle cx="12" cy="12" r="8" {...common} />
        <path d="m12 8 4 3-1.5 5h-5L8 11l4-3Z" {...common} />
      </>
    ),
    cricket: (
      <>
        <path d="M6 20 17 9l2 2L8 22 6 20Z" {...common} />
        <path d="M14 6 18 2m-2 16 4 4" {...common} />
        <circle cx="6" cy="6" r="2" {...common} />
      </>
    ),
    athletics: (
      <>
        <path d="M4 9h16M4 15h16" {...common} />
        <path d="M4 9a4 4 0 0 0 0 6M20 9a4 4 0 0 1 0 6" {...common} />
      </>
    ),
  };

  return (
    <svg className="section-nav__icon" viewBox="0 0 24 24" aria-hidden="true">
      {icons[type] || icons.all}
    </svg>
  );
}

function FinalsShowdown({ teams, players, legendScores, legendThreshold, teamByCode, logoForTeam, playerMeta, scoreNote, title, kicker, sub }) {
  if (!teams || teams.length !== 2) return null;
  const valid = teams.every(code => code && code !== "TBD");
  if (!valid) return null;

  const rowsFor = code => players
    .filter(p => p.teamCode === code)
    .sort((a, b) => (b.score || 0) - (a.score || 0))
    .slice(0, 10);

  const teamTitle = code => teamByCode[code]?.city || teamByCode[code]?.commonName || code;

  return (
    <NewsletterSection kicker={kicker} title={title} sub={sub}>
      <div className="showdown-grid">
        {teams.map(code => (
          <div className="showdown-card" key={code}>
            <div className="showdown-card__head">
              <img src={logoForTeam(code)} alt={code} />
              <div>
                <h3>{teamTitle(code)}</h3>
                <span>{code}</span>
              </div>
            </div>
            <table className="showdown-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Jugador</th>
                  <th>Score</th>
                  <th>Leyenda</th>
                </tr>
              </thead>
              <tbody>
                {rowsFor(code).map((p, i) => {
                  const legendScore = p.legendScore ?? legendScores[p.id];
                  return (
                    <tr key={p.id}>
                      <td>{String(i + 1).padStart(2, "0")}</td>
                      <td>
                        <strong>{p.name}</strong>
                        <span>{playerMeta(p)} · {scoreNote(p)}</span>
                      </td>
                      <td>{p.score}</td>
                      <td>
                        {legendScore != null ? (
                          <span className="showdown-legend">
                            <ThresholdBar value={Number(legendScore)} threshold={legendThreshold} width={72} />
                            <strong>{Number(legendScore).toFixed(1)}</strong>
                          </span>
                        ) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </NewsletterSection>
  );
}

function NewsletterApp() {
  const D = window.NHL_DATA;
  const NBA = window.NBA_DATA;
  const { TEAMS, PLAYERS, BRACKET, ROAD_TO_GLORY } = D;
  const nhlSeasonShort = D.SEASON ? D.SEASON.replace(/^(\d{2})(\d{2})-/, "$2-") : "";
  const teamByCode = useMemo(() => Object.fromEntries(TEAMS.map(t => [t.code, t])), [TEAMS]);
  const alive = useMemo(() => getAlivePlayoffTeams(BRACKET), [BRACKET]);
  const aliveLabel = [...alive].sort().join(" · ");

  const topPerformers = useMemo(() => [...PLAYERS].sort((a, b) => b.score - a.score).slice(0, 10), [PLAYERS]);
  const roadPlayers = (ROAD_TO_GLORY?.players || []).slice(0, 10);
  const youngPlayers = (ROAD_TO_GLORY?.youngProspects || []).slice(0, 10);
  const roadTeams = (ROAD_TO_GLORY?.teams || []).slice(0, 10);
  const stanleyCupTeams = useMemo(() => {
    const f = BRACKET?.final?.[0];
    return f?.hi && f?.lo && f.hi !== "TBD" && f.lo !== "TBD" ? [f.hi, f.lo] : null;
  }, [BRACKET]);
  const nhlLegendScores = useMemo(() => {
    const pairs = [
      ...(ROAD_TO_GLORY?.players || []).map(p => [p.id, p.careerScore]),
      ...(ROAD_TO_GLORY?.youngProspects || []).map(p => [p.id, p.projectedScore]),
    ];
    return Object.fromEntries(pairs);
  }, [ROAD_TO_GLORY]);

  // MLB data
  const MLB = window.MLB_DATA;
  const MLB_DIV_ORDER = ["AL East", "AL Central", "AL West", "NL East", "NL Central", "NL West"];
  const MLB_TEAM_DIV = {
    NYY:"AL East", BOS:"AL East", TOR:"AL East", TB:"AL East",  BAL:"AL East",
    CHW:"AL Central", CLE:"AL Central", DET:"AL Central", KC:"AL Central", MIN:"AL Central",
    HOU:"AL West", LAA:"AL West", ATH:"AL West", SEA:"AL West", TEX:"AL West",
    ATL:"NL East", MIA:"NL East", NYM:"NL East", PHI:"NL East", WSH:"NL East",
    CHC:"NL Central", CIN:"NL Central", MIL:"NL Central", PIT:"NL Central", STL:"NL Central",
    LAD:"NL West", ARI:"NL West", COL:"NL West", SF:"NL West",  SD:"NL West",
  };
  const mlbTeamByCode = useMemo(() => Object.fromEntries((MLB?.TEAMS || []).map(t => [t.code, t])), [MLB]);
  const mlbAlive = useMemo(() => MLB ? getAlivePlayoffTeams({ ...MLB.BRACKET, east: MLB.BRACKET?.al, west: MLB.BRACKET?.nl, final: MLB.BRACKET?.ws }) : new Set(), [MLB]);
  const mlbHasPlayoffs = useMemo(() => !!(MLB?.BRACKET?.ws?.[0]?.hi || MLB?.BRACKET?.al?.lcs?.[0]?.hi || MLB?.BRACKET?.nl?.lcs?.[0]?.hi), [MLB]);
  const mlbPitchers = useMemo(() => MLB ? [...MLB.PLAYERS].filter(p => p.stats?.type === "pitching").sort((a, b) => b.score - a.score).slice(0, 10) : [], [MLB]);
  const mlbBatters  = useMemo(() => MLB ? [...MLB.PLAYERS].filter(p => p.stats?.type === "batting").sort((a, b) => b.score - a.score).slice(0, 10) : [], [MLB]);
  const mlbRoadPlayers  = (MLB?.ROAD_TO_GLORY?.players || []).slice(0, 10);
  const mlbYoungPlayers = (MLB?.ROAD_TO_GLORY?.youngProspects || []).slice(0, 10);
  const mlbRoadTeams    = (MLB?.ROAD_TO_GLORY?.teams || []).slice(0, 10);
  const mlbLegends      = (MLB?.HISTORY_PLAYERS || [])
    .map(p => ({ ...p, legendScore: p.legendScore ?? p.score }))
    .sort((a, b) => b.legendScore - a.legendScore)
    .slice(0, 10);
  const mlbLegendThreshold = mlbLegends[9]?.legendScore || MLB?.ROAD_TO_GLORY?.playerThreshold || 0;
  const mlbDivStandings = useMemo(() => {
    if (!MLB) return {};
    const map = {};
    for (const team of MLB.TEAMS) {
      const div = MLB_TEAM_DIV[team.code] || team.div || "Other";
      if (!map[div]) map[div] = [];
      map[div].push(team);
    }
    for (const div of Object.keys(map)) map[div].sort((a, b) => b.w - a.w || a.l - b.l);
    return map;
  }, [MLB]);

  // NFL data
  const NFL = window.NFL_DATA;
  const NFL_DIV_ORDER = ["AFC East", "AFC North", "AFC South", "AFC West", "NFC East", "NFC North", "NFC South", "NFC West"];
  const nflTeamByCode = useMemo(() => Object.fromEntries((NFL?.TEAMS || []).map(t => [t.code, t])), [NFL]);
  const nflAlive = useMemo(() => NFL ? getAlivePlayoffTeams({ ...NFL.BRACKET, east: NFL.BRACKET?.afc, west: NFL.BRACKET?.nfc, final: NFL.BRACKET?.sb }) : new Set(), [NFL]);
  const nflHasPlayoffs = useMemo(() => !!(NFL?.BRACKET?.sb?.[0]?.hi || NFL?.BRACKET?.afc?.conf?.[0]?.hi || NFL?.BRACKET?.nfc?.conf?.[0]?.hi), [NFL]);
  const nflTopQBs = useMemo(() => NFL ? [...NFL.PLAYERS].sort((a, b) => b.score - a.score).slice(0, 10) : [], [NFL]);
  const nflHistoryPlayers = (NFL?.HISTORY_PLAYERS || []).slice(0, 10);
  const nflRoadPlayers = (NFL?.ROAD_TO_GLORY?.players || []).slice(0, 10);
  const nflYoungPlayers = (NFL?.ROAD_TO_GLORY?.youngProspects || []).slice(0, 10);
  const nflPlayerThreshold = NFL?.ROAD_TO_GLORY?.playerThreshold || 0;
  const nflDivStandings = useMemo(() => {
    if (!NFL) return {};
    const map = {};
    for (const team of NFL.TEAMS) {
      const div = team.div || "Other";
      if (!map[div]) map[div] = [];
      map[div].push(team);
    }
    for (const div of Object.keys(map)) map[div].sort((a, b) => b.w - a.w || b.pd - a.pd);
    return map;
  }, [NFL]);
  function nflTeamLogo(teamCode) {
    return nflTeamByCode[teamCode]?.logo || `https://a.espncdn.com/i/teamlogos/nfl/500/${(teamCode || "").toLowerCase()}.png`;
  }
  function nflPlayerMeta(player) {
    const teamName = nflTeamByCode[player.teamCode]?.commonName || player.teamCode;
    const age = player.age ? ` · ${player.age} años` : "";
    return `NFL QB · ${teamName}${age}`;
  }
  function nflPlayerNote(player) {
    const s = player.stats;
    if (!s) return "";
    return `${s.yds} yds · ${s.td} TD · ${s.int} INT · ${s.pct}%`;
  }

  // Tennis data
  const TENNIS = window.TENNIS_DATA;
  const tennisATPFull = useMemo(() => (TENNIS?.ATP || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } })), [TENNIS]);
  const tennisWTAFull = useMemo(() => (TENNIS?.WTA || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } })), [TENNIS]);
  const tennisATP = useMemo(() => tennisATPFull.slice(0, 10), [tennisATPFull]);
  const tennisWTA = useMemo(() => tennisWTAFull.slice(0, 10), [tennisWTAFull]);
  function tennisDisplayList(base, full, aliveSet, minAlive = 2, includeAllAlive = false) {
    const withRank = (player, index) => ({ ...player, displayRank: index + 1 });
    if (aliveSet.size === 0) return base.map(withRank);
    let list = base.map(withRank);
    const aliveCount = () => list.filter(p => aliveSet.has(p.id)).length;
    const seen = new Set(list.map(p => p.id));
    for (const [index, p] of full.entries()) {
      if (!includeAllAlive && aliveCount() >= minAlive) break;
      if (!seen.has(p.id) && aliveSet.has(p.id)) { list.push(withRank(p, index)); seen.add(p.id); }
    }
    return list;
  }
  function tennisPlayerMeta(player, tour) {
    const gs = player.stats?.gs || 0;
    const gsStr = gs > 0 ? ` · ${gs} GS` : "";
    return `${tour} · #${player.rank}${gsStr}`;
  }
  function tennisTournamentNote(player) {
    const st = player.tournamentStatus;
    if (!st?.tournament) return "";
    if (st.state === "alive") return `${st.tournament}: vivo${st.round ? ` · ${st.round}` : ""}`;
    return st.reason || `${st.tournament}: eliminado/no compite`;
  }
  // Nota cuando el Nivel baja por inactividad (semanas sin competir).
  function tennisInactiveNote(player) {
    if (!player.inactiveWeeks || !player.inactivePenalty) return "";
    return `Inactivo ~${player.inactiveWeeks} sem · −${player.inactivePenalty} Nivel`;
  }
  // Variación de Nivel respecto a la semana pasada, redondeada a 1 decimal.
  function tennisScoreDelta(player) {
    if (player.prevActiveScore == null || player.activeScore == null) return undefined;
    return Math.round((player.activeScore - player.prevActiveScore) * 10) / 10;
  }

  // Convierte el delta del ranking oficial ATP/WTA en un prevRank relativo a la posición
  // en la lista para que lo renderice el indicador visual coloreado.
  // Si el ranking oficial no cambió, usa la posición previa en la lista Hermes.
  function tennisPrevRank(player, listIndex) {
    if (player.prevRank != null && player.rank != null) {
      // delta ATP: positivo = subió en ranking, negativo = bajó
      const atpDelta = player.prevRank - player.rank;  // subió si prevRank > rank
      if (atpDelta !== 0) return (listIndex + 1) + atpDelta;
    }
    if (typeof player.prevListRank === "number") return player.prevListRank;
    return undefined;
  }

  // NBA data
  const nbaTeamByCode = useMemo(() => Object.fromEntries((NBA?.TEAMS || []).map(t => [t.code, t])), [NBA]);
  const nbaAlive = useMemo(() => NBA ? getAlivePlayoffTeams(NBA.BRACKET) : new Set(), [NBA]);
  const nbaTopPerformers = useMemo(() => NBA ? [...NBA.PLAYERS].sort((a, b) => b.score - a.score).slice(0, 10) : [], [NBA]);
  const nbaRoadPlayers  = (NBA?.ROAD_TO_GLORY?.players || []).slice(0, 10);
  const nbaYoungPlayers = (NBA?.ROAD_TO_GLORY?.youngProspects || []).slice(0, 10);
  const nbaRoadTeams    = (NBA?.ROAD_TO_GLORY?.teams || []).slice(0, 10);
  const nbaStatsScope = NBA?.STATS_SCOPE || "temporada";
  const nbaStatsLabel = nbaStatsScope === "playoffs" ? "playoffs" : "temporada";
  const nbaFinalsTeams = useMemo(() => {
    const f = NBA?.BRACKET?.final?.[0];
    return f?.hi && f?.lo && f.hi !== "TBD" && f.lo !== "TBD" ? [f.hi, f.lo] : null;
  }, [NBA]);
  const nbaLegendScores = useMemo(() => {
    const rtg = NBA?.ROAD_TO_GLORY || {};
    const pairs = [
      ...(rtg.players || []).map(p => [p.id, p.careerScore]),
      ...(rtg.youngProspects || []).map(p => [p.id, p.projectedScore]),
    ];
    return Object.fromEntries(pairs);
  }, [NBA]);
  const nbaHistoryPlayers = useMemo(() => (NBA?.HISTORY_PLAYERS || [])
    .sort((a, b) => b.score - a.score)
    .slice(0, 10), [NBA]);
  const nbaHistoryThreshold = nbaHistoryPlayers[9]?.score || NBA?.ROAD_TO_GLORY?.playerThreshold || 0;
  const nbaHistoryTeams = useMemo(() => (NBA?.HISTORY_TEAMS || [])
    .sort((a, b) => b.score - a.score)
    .slice(0, 10), [NBA]);
  const nbaHistoryTeamThreshold = nbaHistoryTeams[9]?.score || NBA?.ROAD_TO_GLORY?.teamThreshold || 0;

  function playerMeta(player) {
    const teamName = teamByCode[player.teamCode]?.commonName || player.teamCode;
    const age = player.age ? ` · ${player.age} años` : "";
    return `${player.country || "NHL"} · ${player.pos} · ${teamName}${age}`;
  }

  function mlbTeamLogo(teamCode) {
    return mlbTeamByCode[teamCode]?.logo || `https://a.espncdn.com/i/teamlogos/mlb/500/${(teamCode || "").toLowerCase()}.png`;
  }

  function mlbPlayerMeta(player) {
    const teamName = mlbTeamByCode[player.teamCode]?.commonName || player.teamCode;
    const age = player.age ? ` · ${player.age} años` : "";
    return `MLB · ${player.pos} · ${teamName}${age}`;
  }

  function mlbPlayerNote(player) {
    const s = player.stats;
    if (!s) return "";
    if (s.type === "pitching") return `${s.era} ERA · ${s.so} K · ${s.w} W`;
    return `.${String(Math.round(s.avg * 1000)).padStart(3, "0")} AVG · ${s.hr} HR · ${s.rbi} RBI`;
  }

  function mlbRoadNote(player) {
    const parts = [];
    if (player.battingScore != null) parts.push(`Bat ${Number(player.battingScore).toFixed(0)}`);
    if (player.pitchingScore != null) parts.push(`Pit ${Number(player.pitchingScore).toFixed(0)}`);
    if (player.rings) parts.push(`${player.rings} ring${player.rings !== 1 ? "s" : ""}`);
    const base = parts.length ? `${parts.join(" · ")}. ` : "";
    return `${base}${player.note}`;
  }

  function nbaTeamLogo(teamCode) {
    return nbaTeamByCode[teamCode]?.logo || `https://a.espncdn.com/i/teamlogos/nba/500/${(teamCode || "").toLowerCase()}.png`;
  }

  function nbaPlayerMeta(player) {
    const teamName = nbaTeamByCode[player.teamCode]?.commonName || player.teamCode;
    const age = player.age ? ` · ${player.age} años` : "";
    return `NBA · ${player.pos} · ${teamName}${age}`;
  }

  const [activeSection, setActiveSection] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  function sectionUpdateDate(data) {
    const raw = data?.UPDATED || data?.LAST_UPDATE;
    if (!raw) return null;
    const normalized = String(raw).replace(" UTC", "Z").replace(" ", "T");
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  // "Activo" = hay competición real alrededor de ahora (ventana ±10 días para eventos
  // puntuales; temporada en curso para ligas/series), no solo que el archivo se haya
  // refrescado. La frescura del dato es un guard adicional: si un pipeline deja de
  // actualizar (p. ej. rugby), el deporte se apaga aunque "estuviera en temporada".
  const SECTION_SEASON = {
    nhl: [10, 6], nba: [10, 6], mlb: [3, 11], tennis: [1, 11],
    f1: [3, 12], motogp: [3, 11], indycar: [3, 9], nascar: [2, 11],
    afl: [3, 9], cricket: [1, 12],
  };
  function parseLooseDate(v) {
    if (!v) return null;
    const iso = new Date(String(v).replace(" UTC", "Z").replace(" ", "T"));
    if (!Number.isNaN(iso.getTime())) return iso;
    const months = { ene: 0, jan: 0, feb: 1, mar: 2, abr: 3, apr: 3, may: 4, jun: 5, jul: 6, ago: 7, aug: 7, sep: 8, oct: 9, nov: 10, dic: 11, dec: 11 };
    const m = String(v).trim().match(/^(\d{1,2})\s+([A-Za-z]{3})/);
    if (m && months[m[2].toLowerCase()] !== undefined) {
      return new Date(new Date().getFullYear(), months[m[2].toLowerCase()], parseInt(m[1], 10));
    }
    return null;
  }
  function sectionActivity(id, data) {
    const WINDOW_DAYS = 10;
    const FRESH_MS = WINDOW_DAYS * 24 * 60 * 60 * 1000;
    const now = Date.now();
    const upd = sectionUpdateDate(data);
    const updatedAt = data?.UPDATED || data?.LAST_UPDATE || null;
    const fresh = upd ? (now - upd.getTime() >= 0 && now - upd.getTime() <= FRESH_MS) : false;
    const month = new Date().getMonth() + 1;
    const inSeason = ([s, e]) => (s <= e ? month >= s && month <= e : month >= s || month <= e);
    const within = (d, days = WINDOW_DAYS) => {
      if (!d) return false;
      const diff = (d.getTime() - now) / 86400000;
      return diff >= -days && diff <= days;
    };
    const withinSpan = (startV, endV, pad = WINDOW_DAYS) => {
      const s = parseLooseDate(startV);
      const e = parseLooseDate(endV) || s;
      if (!s) return false;
      return now >= s.getTime() - pad * 86400000 && now <= e.getTime() + pad * 86400000;
    };

    let active, reason;
    switch (id) {
      case "nfl":
        active = fresh && data?.SEASON_STATUS !== "offseason";
        reason = data?.SEASON_STATUS === "offseason" ? "Fuera de temporada" : "Temporada en curso";
        break;
      case "golf": {
        const cm = data?.CURRENT_MAJOR;
        const live = cm && (cm.state === "live" || cm.state === "in_progress");
        active = fresh && !!cm && (live || withinSpan(cm.start, cm.end));
        reason = active ? (cm?.name || "Torneo cercano") : "Sin torneo cercano";
        break;
      }
      case "sumo": {
        const bi = data?.BASHO_INFO;
        active = fresh && !!bi && withinSpan(bi.startDate, bi.endDate);
        reason = active ? "Basho en ventana" : "Entre bashos";
        break;
      }
      case "athletics": {
        const nm = data?.NEXT_MEETING;
        active = within(parseLooseDate(nm?.date));
        reason = active ? (nm?.name || "Mitin cercano") : "Sin mitin cercano";
        break;
      }
      case "cycling": {
        const cr = data?.CURRENT_RACE;
        const ongoing = cr && typeof cr.stage === "number" && typeof cr.total_stages === "number" && cr.stage < cr.total_stages;
        active = fresh && !!cr && (ongoing || within(parseLooseDate(cr.last_stage?.date)));
        reason = active ? (cr?.name || "Carrera en curso") : "Sin carrera cercana";
        break;
      }
      case "football": {
        const wc = data?.WORLD_CUP_2026 && (month === 6 || month === 7);
        active = fresh && (inSeason([8, 5]) || !!wc);
        reason = wc ? "Mundial 2026" : active ? "Temporada en curso" : "Receso";
        break;
      }
      case "rugby": {
        // El rugby de selecciones es esporádico: activo solo si hubo un test reciente.
        // (UPDATED ya es hora de ejecución; la fecha real del test va en LAST_MATCH.)
        const lm = parseLooseDate(data?.LAST_MATCH);
        active = fresh && within(lm, 14);
        reason = active ? "Test reciente" : "Sin test reciente";
        break;
      }
      default:
        if (SECTION_SEASON[id]) {
          active = fresh && inSeason(SECTION_SEASON[id]);
          reason = active ? "Temporada en curso" : "Fuera de temporada";
        } else {
          active = fresh;
          reason = fresh ? "Datos recientes" : "Sin datos recientes";
        }
    }
    return { updatedAt, isFresh: !!active, activityReason: reason, dataFresh: fresh };
  }
  // ── Portada transversal: titular más relevante por deporte ──────────────
  function fmtShortDate(d) {
    if (!d) return "";
    return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" }).replace(".", "");
  }
  const firstOf = arr => (Array.isArray(arr) && arr.length ? arr[0] : null);
  function sectionHeadline(id, data) {
    try {
      switch (id) {
        case "tennis": {
          const top = firstOf(data.ATP);
          // Solo destacamos movimientos de jugadores relevantes (top 20), no de
          // tapados del puesto 180 que tocan el tope de penalización por inactividad.
          const movers = [...(data.ATP || []), ...(data.WTA || [])]
            .filter(p => p.prevActiveScore != null && p.activeScore != null && (p.rank == null || p.rank <= 20))
            .map(p => ({ name: p.name, d: Math.round((p.activeScore - p.prevActiveScore) * 10) / 10 }))
            .filter(p => Math.abs(p.d) >= 0.1)
            .sort((a, b) => Math.abs(b.d) - Math.abs(a.d));
          const mv = movers[0];
          if (top && mv) return `#1 ${top.name} · ${mv.d > 0 ? "▲" : "▼"}${Math.abs(mv.d).toFixed(1)} ${mv.name}`;
          return top ? `#1 ${top.name}` : null;
        }
        case "f1": {
          const l = firstOf(data.DRIVERS);
          return l ? `Líder: ${l.name}${data.LAST_WEEKEND?.name ? ` · últ. ${data.LAST_WEEKEND.name}` : ""}` : null;
        }
        case "motogp": {
          const lr = data.LAST_RACE;
          if (lr?.winner) return `${lr.winner} ganó ${lr.name || "la última"}`;
          const l = firstOf(data.RIDERS); return l ? `Líder: ${l.name}` : null;
        }
        case "nascar": {
          const lr = data.LAST_RACE;
          if (lr?.winner) return `${lr.winner} ganó en ${lr.circuit || lr.name || ""}`;
          const l = firstOf(data.DRIVERS); return l ? `Líder: ${l.name}` : null;
        }
        case "indycar": {
          const l = firstOf(data.DRIVERS) || firstOf(data.CURRENT_CONTENDERS);
          return l ? `Líder: ${l.name}` : null;
        }
        case "afl": {
          const l = firstOf(data.LADDER);
          return l ? `Lidera ${l.name} (${l.wins}-${l.losses})` : null;
        }
        case "golf": {
          const cm = data.CURRENT_MAJOR, top = firstOf(data.CURRENT);
          if (cm?.name) return `${cm.name}${top ? ` · #1 ${top.name}` : ""}`;
          return top ? `#1 ${top.name}` : null;
        }
        case "nba": case "mlb": case "nhl": {
          const t = firstOf(data.TEAMS);
          const nm = t ? (t.commonName || t.shortName || t.city || t.name) : null;
          if (!nm) return null;
          const rec = (t.w != null && t.l != null) ? ` (${t.w}-${t.l})` : "";
          return `Mejor récord: ${nm}${rec}`;
        }
        case "sumo":
          return data.BASHO_INFO?.winner ? `Último basho: ${data.BASHO_INFO.winner}` : null;
        case "football": {
          const wc = data.WORLD_CUP_2026;
          if (wc) return `Mundial 2026 · ${wc.phase === "group_stage" ? "fase de grupos" : (wc.phase || "en juego")}`;
          return null;
        }
        case "cricket": {
          const s = firstOf(data.WTC?.standings);
          return s ? `WTC líder: ${s.country}` : null;
        }
        case "cycling":
          return data.CURRENT_RACE?.name || null;
        default: return null;
      }
    } catch (e) { return null; }
  }
  // ── Feed de Gloria: hechos templados (sin IA) — quién gana, sube o baja ──
  // Devuelve eventos { w (peso), text, detail }. Los pesos colocan los hechos
  // recientes (victorias, entradas al top 10, saltos de Nivel) por encima del
  // estado estático (líder de la tabla).
  function sectionGloryEvents(id, data) {
    const ev = [];
    try {
      switch (id) {
        case "motogp": {
          const lr = data.LAST_RACE;
          if (lr?.winner) ev.push({ w: 100, text: `${lr.winner} ganó el ${lr.name || "último GP"}`, detail: "MotoGP" });
          break;
        }
        case "nascar": {
          const lr = data.LAST_RACE;
          if (lr?.winner) ev.push({ w: 100, text: `${lr.winner} ganó en ${lr.circuit || lr.name || ""}`, detail: "NASCAR" });
          break;
        }
        case "cycling": {
          const ls = data.CURRENT_RACE?.last_stage;
          if (ls?.winner) ev.push({ w: 88, text: `${ls.winner} ganó la última etapa del ${data.CURRENT_RACE.name}`, detail: "Ciclismo" });
          break;
        }
        case "tennis": {
          const allPlayers = [...(data.ATP || []), ...(data.WTA || [])];
          const leyendaOf = name => { const p = allPlayers.find(x => x.name === name); return (typeof p?.leyendaScore === "number" && p.leyendaScore > 0) ? ` · Leyenda ${p.leyendaScore.toFixed(1)}` : ""; };
          [["ATP", data.ATP_CHANGES], ["WTA", data.WTA_CHANGES]].forEach(([tour, changes]) => {
            (changes?.entered || []).forEach(p => ev.push({ w: 90, text: `${p.name} entra en el top 10 ${tour}${leyendaOf(p.name)}`, detail: "Tenis" }));
            (changes?.exited || []).forEach(p => ev.push({ w: 78, text: `${p.name} sale del top 10 ${tour}`, detail: "Tenis" }));
          });
          const movers = allPlayers
            .filter(p => p.prevActiveScore != null && p.activeScore != null && (p.rank == null || p.rank <= 20))
            .map(p => ({ name: p.name, d: Math.round((p.activeScore - p.prevActiveScore) * 10) / 10 }))
            .filter(p => Math.abs(p.d) >= 0.5)
            .sort((a, b) => Math.abs(b.d) - Math.abs(a.d))
            .slice(0, 3);
          movers.forEach(m => ev.push({ w: 70 + Math.min(15, Math.abs(m.d)), text: `${m.name} ${m.d > 0 ? "sube" : "baja"} su Nivel (${m.d > 0 ? "+" : ""}${m.d.toFixed(1)})${leyendaOf(m.name)}`, detail: "Tenis" }));
          break;
        }
        default: break;
      }
    } catch (e) { /* noop */ }
    return ev;
  }
  // ── Informe de cierre: se dispara cuando una competición importante termina ──
  // (campeón en el cuadro / basho cerrado). Función pura de los datos actuales;
  // aparece sola cuando el cron publica el campeón. La persistencia para email
  // llegará con el Glory log en backend.
  function teamNameByCode(data, code) {
    const t = (data.TEAMS || []).find(x => x.code === code || x.teamCode === code);
    return t ? (t.commonName || t.shortName || t.city || t.name || code) : code;
  }
  function recentlyEnded(dv, days) {
    const d = parseLooseDate(dv);
    if (!d) return false;
    const diff = (Date.now() - d.getTime()) / 86400000;
    return diff >= 0 && diff <= days;
  }
  function competitionReport(id, data) {
    try {
      if (id === "nba" || id === "nhl") {
        const fin = (data.BRACKET?.final || [])[0];
        if (!fin?.winner) return null;
        const champ = teamNameByCode(data, fin.winner);
        const other = teamNameByCode(data, fin.winner === fin.hi ? fin.lo : fin.hi);
        const scope = data.STATS_SCOPE === "playoffs" ? "los playoffs" : "la temporada";
        const top5 = (data.PLAYERS || []).slice(0, 5).map(p => ({ name: p.name, score: p.score }));
        return { competition: id === "nba" ? "NBA" : "NHL", champion: `${champ} se proclama campeón${fin.seriesScore ? ` (${fin.seriesScore} a ${other})` : ""}`, scopeLabel: `Top 5 de ${scope}`, top5 };
      }
      if (id === "mlb") {
        const wsRaw = data.BRACKET?.ws;
        const ws = Array.isArray(wsRaw) ? wsRaw[0] : wsRaw;
        if (!ws?.winner) return null;
        const top5 = (data.PLAYERS || []).slice(0, 5).map(p => ({ name: p.name, score: p.score }));
        return { competition: "MLB", champion: `${teamNameByCode(data, ws.winner)} gana las World Series`, scopeLabel: "Top 5 de la temporada", top5 };
      }
      if (id === "sumo") {
        const bi = data.BASHO_INFO;
        if (!bi?.winner || !recentlyEnded(bi.endDate, 16)) return null;
        const top5 = (data.BANZUKE || []).slice(0, 5).map(r => ({ name: r.name, sub: r.rankLabel }));
        return { competition: "Sumo", champion: `${bi.winner} conquista el basho`, scopeLabel: "Cabeza del banzuke", top5 };
      }
    } catch (e) { /* noop */ }
    return null;
  }
  // ── Agenda: próximos eventos con fecha real presente en los datos ───────
  function sectionUpcomingEvents(id, data) {
    const out = [];
    const add = (dv, title, sub) => { const d = parseLooseDate(dv); if (d) out.push({ date: d, title, sub: sub || "" }); };
    try {
      switch (id) {
        case "golf": {
          const cm = data.CURRENT_MAJOR;
          if (cm?.start) add(cm.start, `Golf · ${cm.name}`, [cm.venue, cm.location].filter(Boolean).join(" · "));
          break;
        }
        case "football":
          (data.TEAMS || []).forEach(t => {
            const nm = t?.nextMatch;
            if (nm?.date && nm?.opponent) add(nm.date, `${t.name}–${nm.opponent}`, [nm.city, nm.group ? `Grupo ${nm.group}` : ""].filter(Boolean).join(" · "));
          });
          break;
        case "athletics": {
          const nm = data.NEXT_MEETING;
          if (nm?.date) add(nm.date, `Atletismo · ${nm.name}`, nm.location);
          break;
        }
        default: break;
      }
    } catch (e) { /* noop */ }
    return out;
  }
  const newsletterSections = useMemo(() => {
    const sectionData = [
      { id: "nhl", label: "NHL", icon: "nhl", data: D },
      { id: "nba", label: "NBA", icon: "nba", data: NBA },
      { id: "mlb", label: "MLB", icon: "mlb", data: MLB },
      { id: "nfl", label: "NFL", icon: "nfl", data: NFL },
      { id: "tennis", label: "Tennis", icon: "tennis", data: TENNIS },
      { id: "cycling", label: "Cycling", icon: "cycling", data: window.CYCLING_DATA },
      { id: "sumo", label: "Sumo", icon: "sumo", data: window.SUMO_DATA },
      { id: "f1", label: "F1", icon: "f1", data: window.F1_DATA },
      { id: "indycar", label: "IndyCar", icon: "indycar", data: window.INDYCAR_DATA },
      { id: "nascar", label: "NASCAR", icon: "nascar", data: window.NASCAR_DATA },
      { id: "afl", label: "AFL", icon: "afl", data: window.AFL_DATA },
      { id: "golf", label: "Golf", icon: "golf", data: window.GOLF_DATA },
      { id: "motogp", label: "MotoGP", icon: "motogp", data: window.MOTOGP_DATA },
      { id: "rugby", label: "Rugby", icon: "rugby", data: window.RUGBY_DATA },
      { id: "football", label: "Fútbol", icon: "football", data: window.FOOTBALL_DATA },
      { id: "cricket", label: "Cricket", icon: "cricket", data: window.CRICKET_DATA },
      { id: "athletics", label: "Atletismo", icon: "athletics", data: window.ATHLETICS_DATA },
    ].filter(section => !!section.data).map(section => ({
      ...section,
      ...sectionActivity(section.id, section.data),
    }));
    const hasFreshSection = sectionData.some(section => section.isFresh);
    const navSections = [...sectionData].sort((a, b) =>
      a.label.localeCompare(b.label, "es", { sensitivity: "base" })
    );
    return [
      { id: "all", label: "Todos", icon: "all", available: true, isFresh: hasFreshSection, updatedAt: hasFreshSection ? "Hay novedades esta semana" : "Sin novedades esta semana" },
      ...navSections,
    ];
  }, [D, NBA, MLB, NFL, TENNIS]);
  const visibleSections = newsletterSections.filter(section => section.id !== "all").length;
  const freshSections = newsletterSections.filter(section => section.id !== "all" && section.isFresh).length;
  // Feed de Gloria: hechos recientes (victorias, top-10, saltos de Nivel) por
  // encima del estado estático (líder). Cada deporte activo aporta al menos una
  // línea: si no hay evento, su titular de estado como respaldo.
  const gloryFeed = (() => {
    const out = [];
    newsletterSections.forEach(s => {
      if (s.id === "all" || !s.data) return;
      const imp = (s.data.IMPORTANCE || 0) / 100;
      // Hechos (victorias, top-10, saltos de Nivel): basta con que el pipeline esté
      // vivo, para que el resultado de una competición se vea justo al terminar.
      const events = s.dataFresh ? sectionGloryEvents(s.id, s.data) : [];
      if (events.length) {
        events.forEach(e => out.push({ id: s.id, text: e.text, detail: e.detail, sport: s.label, icon: s.icon, w: e.w + imp }));
      } else if (s.isFresh) {
        // Respaldo de estado (líder): solo si el deporte está realmente en temporada.
        const h = sectionHeadline(s.id, s.data);
        if (h) out.push({ id: s.id, text: h, detail: s.label, sport: s.label, icon: s.icon, w: 30 + imp });
      }
    });
    return out.sort((a, b) => b.w - a.w).slice(0, 14);
  })();
  // Informes de cierre: preferimos el Glory log persistido (backend) — sobrevive
  // aunque los datos del deporte cambien y es la misma fuente que usará el email.
  // Si aún no existe glory_data.js, derivamos en vivo como respaldo.
  const reports = (() => {
    const GLORY = typeof window !== "undefined" ? window.GLORY_DATA : null;
    if (GLORY && Array.isArray(GLORY.REPORTS)) {
      return GLORY.REPORTS.map(r => ({ ...r, id: r.id || r.sport }));
    }
    const out = [];
    newsletterSections.forEach(s => {
      if (s.id === "all" || !s.data || !s.dataFresh) return;
      const r = competitionReport(s.id, s.data);
      if (r) out.push({ ...r, id: s.id, icon: s.icon });
    });
    return out;
  })();
  // Buscador global: índice de nombres (atletas/equipos) de todos los deportes.
  const SEARCH_KEYS = ["PLAYERS", "TEAMS", "ATP", "WTA", "DRIVERS", "RIDERS", "LADDER", "BANZUKE", "CURRENT", "CURRENT_RIDERS", "LEGENDS", "ATP_LEGENDS", "WTA_LEGENDS"];
  const searchIndex = (() => {
    const out = [], seen = new Set();
    newsletterSections.forEach(s => {
      if (s.id === "all" || !s.data) return;
      SEARCH_KEYS.forEach(k => {
        const arr = s.data[k];
        if (!Array.isArray(arr)) return;
        arr.forEach(it => {
          const name = it && (it.name || it.commonName || it.city);
          if (!name) return;
          const key = s.id + ":" + name;
          if (seen.has(key)) return;
          seen.add(key);
          out.push({ name, sport: s.id, sportLabel: s.label });
        });
      });
    });
    return out;
  })();
  const searchResults = (() => {
    const q = searchQuery.trim();
    if (q.length < 2) return [];
    const norm = x => x.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    const nq = norm(q);
    return searchIndex.filter(e => norm(e.name).includes(nq)).slice(0, 8);
  })();
  // Agenda: próximos eventos con fecha (≤45 días), ordenados por fecha.
  const agendaItems = (() => {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const horizon = new Date(today.getTime() + 45 * 86400000);
    const items = [];
    newsletterSections.forEach(s => {
      if (s.id === "all" || !s.data) return;
      sectionUpcomingEvents(s.id, s.data).forEach(ev => {
        if (ev.date >= today && ev.date <= horizon) items.push({ ...ev, icon: s.icon });
      });
    });
    return items.sort((a, b) => a.date - b.date).slice(0, 10);
  })();
  const sectionStyle = (id, importance) => ({
    order: -Math.round(importance * 10),
    display: activeSection === "all" || activeSection === id ? "block" : "none",
  });

  return (
    <div className="app app--newsletter">
      <main className="newsletter" style={{ display: "flex", flexDirection: "column" }}>

        {/* ── HERMES MASTHEAD ───────────────────────────────── */}
        <div style={{ order: -9999, textAlign: "center", padding: "48px 0 36px", borderBottom: "2px solid var(--ink,#1a1714)" }}>
          <div style={{ fontSize: 10, letterSpacing: "0.25em", textTransform: "uppercase", color: "var(--muted,#888)", fontFamily: "monospace", marginBottom: 10 }}>Sports Newsletter</div>
          <h1 style={{ fontSize: "clamp(44px, 13vw, 72px)", fontFamily: "Newsreader, serif", fontWeight: 600, letterSpacing: "-0.03em", color: "var(--ink,#1a1714)", margin: 0, lineHeight: 1 }}>Hermes</h1>
          <div style={{ fontSize: 11, color: "var(--muted,#888)", fontFamily: "monospace", marginTop: 14 }}>
            {new Date().toLocaleDateString("es-ES", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
          </div>
          <details style={{ marginTop: 18, maxWidth: 560, marginLeft: "auto", marginRight: "auto", textAlign: "left" }}>
            <summary style={{ fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--muted,#888)", fontFamily: "monospace", cursor: "pointer", textAlign: "center", listStyle: "none" }}>
              Cómo se calculan los scores
            </summary>
            <div style={{ fontSize: 13, lineHeight: 1.5, color: "var(--ink-2,#444)", marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--rule,#e6e1da)" }}>
              <p style={{ margin: "0 0 8px" }}><strong style={{ color: "var(--ink,#1a1714)" }}>Nivel (0–100)</strong> — lo bueno que es ahora mismo: forma reciente, Elo, ranking y solidez según superficie o contexto. Baja si lleva semanas sin competir y se recupera al volver a jugar.</p>
              <p style={{ margin: "0 0 8px" }}><strong style={{ color: "var(--ink,#1a1714)" }}>Leyenda (0–100)</strong> — su lugar en la historia del deporte: grandes títulos, tiempo en lo más alto y hitos de carrera, medido contra las leyendas de cada deporte (la cima histórica = 100).</p>
              <p style={{ margin: 0, color: "var(--muted,#888)" }}>Cada score solo se compara dentro de su propio deporte: un 100 en tenis no equivale a un 100 en F1. Todo se calcula de forma automática a partir de datos públicos, sin IA.</p>
            </div>
          </details>
          <div style={{ marginTop: 18, position: "relative", maxWidth: 340, marginLeft: "auto", marginRight: "auto" }}>
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Buscar atleta o equipo…"
              aria-label="Buscar atleta o equipo"
              style={{ width: "100%", padding: "8px 12px", fontFamily: "monospace", fontSize: 12, border: "1px solid var(--rule,#ddd)", borderRadius: 4, background: "var(--paper,#fff)", color: "var(--ink,#1a1714)", textAlign: "center" }}
            />
            {searchResults.length > 0 && (
              <div style={{ position: "absolute", top: "calc(100% + 2px)", left: 0, right: 0, zIndex: 50, background: "var(--paper,#fff)", border: "1px solid var(--rule,#ddd)", textAlign: "left", maxHeight: 300, overflowY: "auto", boxShadow: "0 10px 28px rgba(0,0,0,0.10)" }}>
                {searchResults.map((r, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => { setActiveSection(r.sport); setSearchQuery(""); }}
                    style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, width: "100%", padding: "8px 12px", borderBottom: i < searchResults.length - 1 ? "1px solid var(--rule-2,#eee)" : "none", background: "none", border: "none", cursor: "pointer", textAlign: "left" }}
                  >
                    <span style={{ fontSize: 13, color: "var(--ink,#1a1714)" }}>{r.name}</span>
                    <span style={{ fontSize: 10, fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted,#999)", flexShrink: 0 }}>{r.sportLabel}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <nav className="section-nav" style={{ order: -9998 }} aria-label="Secciones de Hermes">
          {newsletterSections.map(section => (
            <button
              key={section.id}
              className={`section-nav__button ${section.isFresh ? "section-nav__button--fresh" : "section-nav__button--stale"} ${activeSection === section.id ? "section-nav__button--on" : ""}`}
              type="button"
              onClick={() => setActiveSection(section.id)}
              aria-pressed={activeSection === section.id}
              title={`${section.id === "all" ? "Ver todas las secciones" : `Ver solo ${section.label}`} · ${section.isFresh ? "Activo" : "Inactivo"}${section.activityReason ? ` (${section.activityReason})` : ""} · ${section.updatedAt || "sin fecha"}`}
            >
              <SectionIcon type={section.icon} />
              <span>{section.label}</span>
              <i aria-hidden="true" />
            </button>
          ))}
          <span className="section-nav__count mono">{freshSections}/{visibleSections} activos</span>
        </nav>

        {activeSection === "all" && reports.length > 0 && (
          <div style={{ order: -9997, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 20, padding: "26px 0 6px" }}>
            {reports.map(r => (
              <div key={r.id} style={{ border: "1px solid var(--ink,#1a1714)", borderTop: "4px solid var(--ink,#1a1714)", padding: "16px 18px" }}>
                <div style={{ fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--muted,#888)", fontFamily: "monospace", marginBottom: 8 }}>Informe de cierre · {r.competition}</div>
                <div style={{ fontSize: 18, fontFamily: "Newsreader, serif", fontWeight: 600, lineHeight: 1.25, color: "var(--ink,#1a1714)", marginBottom: 12 }}>{r.champion}</div>
                {r.top5?.length > 0 && (
                  <>
                    <div style={{ fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--muted,#999)", fontFamily: "monospace", marginBottom: 4 }}>{r.scopeLabel}</div>
                    {r.top5.map((p, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "baseline", gap: 8, padding: "3px 0", fontSize: 13, borderBottom: i < r.top5.length - 1 ? "1px solid var(--rule,#eee)" : "none" }}>
                        <span style={{ width: 16, fontFamily: "monospace", color: "var(--muted,#999)" }}>{i + 1}</span>
                        <span style={{ flex: 1, color: "var(--ink,#1a1714)" }}>{p.name}</span>
                        {p.sub && <span style={{ fontSize: 10, fontFamily: "monospace", color: "var(--muted,#999)" }}>{p.sub}</span>}
                        {p.score != null && <span style={{ fontFamily: "monospace", fontWeight: 700, color: "var(--ink,#1a1714)" }}>{p.score}</span>}
                      </div>
                    ))}
                  </>
                )}
              </div>
            ))}
          </div>
        )}

        {activeSection === "all" && (gloryFeed.length > 0 || agendaItems.length > 0) && (
          <div style={{ order: -9996, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 28, padding: "30px 0 8px", borderBottom: "1px solid var(--rule, #e6e1da)", marginBottom: 8 }}>
            {/* ── GLORIA: lo último ── */}
            {gloryFeed.length > 0 && (
              <div>
                <div style={{ fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--muted,#888)", fontFamily: "monospace", marginBottom: 12 }}>Gloria · lo último</div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  {gloryFeed.map((item, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setActiveSection(item.id)}
                      style={{ display: "flex", alignItems: "baseline", gap: 10, padding: "7px 0", background: "none", border: "none", borderBottom: "1px solid var(--rule,#eee)", textAlign: "left", cursor: "pointer", width: "100%" }}
                      title={`Ver ${item.sport}`}
                    >
                      <span style={{ flexShrink: 0, width: 58, fontSize: 10, fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted,#999)", paddingTop: 2 }}>{item.detail || item.sport}</span>
                      <span style={{ fontSize: 14, lineHeight: 1.35, color: "var(--ink,#1a1714)" }}>{item.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {/* ── AGENDA: próximos eventos ── */}
            {agendaItems.length > 0 && (
              <div>
                <div style={{ fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--muted,#888)", fontFamily: "monospace", marginBottom: 12 }}>En el calendario</div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  {agendaItems.map((ev, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "baseline", gap: 10, padding: "7px 0", borderBottom: "1px solid var(--rule, #eee)" }}>
                      <span style={{ flexShrink: 0, width: 52, fontSize: 11, fontFamily: "monospace", fontWeight: 600, color: "var(--ink-2,#555)", paddingTop: 1 }}>{fmtShortDate(ev.date)}</span>
                      <span style={{ minWidth: 0 }}>
                        <span style={{ fontSize: 14, lineHeight: 1.3, color: "var(--ink,#1a1714)" }}>{ev.title}</span>
                        {ev.sub && <span style={{ display: "block", fontSize: 11, color: "var(--muted,#999)", fontFamily: "monospace", marginTop: 1 }}>{ev.sub}</span>}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div data-section="nhl" style={sectionStyle("nhl", D?.IMPORTANCE || 5)}>
        {/* ── NHL ─────────────────────────────────────────── */}
        <header className="newsletter-hero">
          <div className="newsletter-hero__masthead">
            <span>NHL Tracker</span>
            <span>{D.SEASON}</span>
            <span>Actualizado {D.LAST_UPDATE}</span>
          </div>
          <div className="newsletter-hero__title-row">
            <h1>NHL {nhlSeasonShort || D.SEASON}</h1>
            <p>
              Bracket vivo y rankings top 10 con una lectura rápida:
              las filas sombreadas pertenecen a equipos que ya no siguen vivos en playoff.
            </p>
          </div>
          <div className="newsletter-hero__alive mono">
            Siguen vivos: <strong>{aliveLabel || "TBD"}</strong>
          </div>
        </header>

        <NewsletterSection
          kicker="Playoff bracket"
          title="Camino a la Stanley Cup"
          sub="Series al mejor de siete, con ganadores ya decididos y cruces vivos en conferencia."
        >
          <Bracket bracket={BRACKET} />
        </NewsletterSection>

        <FinalsShowdown
          teams={stanleyCupTeams}
          players={PLAYERS}
          legendScores={nhlLegendScores}
          legendThreshold={ROAD_TO_GLORY?.playerThreshold || 100}
          teamByCode={teamByCode}
          logoForTeam={code => teamByCode[code]?.logo || `https://assets.nhle.com/logos/nhl/svg/${code}_light.svg`}
          playerMeta={playerMeta}
          scoreNote={p => p.pos === "G" ? `${p.stats.svpct.toFixed(3)} SV%` : `${p.stats.p} P · ${p.stats.g} G`}
          kicker="Stanley Cup Showdown"
          title="Top 10 performers por finalista"
          sub="Aparece cuando están definidos los dos equipos de la Stanley Cup. Score actual de temporada y score leyenda/Road To Glory."
        />

        <NewsletterSection
          kicker="Top performers"
          title="Top 10 performers de esta temporada"
          sub="Ranking por score actual ajustado por posición."
        >
          <div className="newsletter-list">
            {topPerformers.map((player, i) => (
              <NewsletterRankRow
                key={player.id}
                rank={i + 1}
                prevRank={player.prevRank}
                item={player}
                alive={alive}
                score={player.score}
                scoreLabel="Score"
                meta={playerMeta(player)}
                note={player.pos === "G"
                  ? `${player.stats.svpct.toFixed(3)} SV%`
                  : `${player.stats.p} P · ${player.stats.g} G`}
              />
            ))}
          </div>
        </NewsletterSection>

        <NewsletterSection
          kicker="Road to glory"
          title="Top 10 jugadores Road To Glory"
          sub={`Umbral top 10 historico: ${ROAD_TO_GLORY?.playerThreshold ?? "N/A"}.`}
        >
          <div className="newsletter-list">
            {roadPlayers.map((player, i) => (
              <NewsletterRankRow
                key={player.id}
                rank={i + 1}
                prevRank={player.prevRank}
                item={player}
                alive={alive}
                score={player.careerScore}
                scoreLabel="Career"
                threshold={ROAD_TO_GLORY?.playerThreshold}
                meta={`${playerMeta(player)} · ${player.seasons} temporadas · ${player.cups} Cups`}
                note={player.note}
              />
            ))}
          </div>
        </NewsletterSection>

        <NewsletterSection
          kicker="Young road to glory"
          title="Top 10 jugadores jovenes Road To Glory"
          sub="Proyeccion de carrera para jugadores de 25 años o menos."
        >
          <div className="newsletter-list">
            {youngPlayers.map((player, i) => (
              <NewsletterRankRow
                key={player.id}
                rank={i + 1}
                prevRank={player.prevRank}
                item={player}
                alive={alive}
                score={player.projectedScore}
                scoreLabel="Proj."
                threshold={ROAD_TO_GLORY?.playerThreshold}
                meta={`${playerMeta(player)} · score actual ${player.currentScore}`}
                note={player.note}
              />
            ))}
          </div>
        </NewsletterSection>

        <NewsletterSection
          kicker="Team road to glory"
          title="Top 10 equipos Road To Glory"
          sub={`Umbral top 10 historico de franquicias: ${ROAD_TO_GLORY?.teamThreshold ?? "N/A"}.`}
        >
          <div className="newsletter-list">
            {roadTeams.map((team, i) => (
              <NewsletterRankRow
                key={`${team.teamCode}-${team.era}`}
                rank={i + 1}
                prevRank={team.prevRank}
                item={{ ...team, name: team.city }}
                alive={alive}
                score={team.dynastyScore}
                scoreLabel="Dynasty"
                threshold={ROAD_TO_GLORY?.teamThreshold}
                meta={`${team.era} · ${team.cups} Cup${team.cups !== 1 ? "s" : ""} · ${team.note}`}
                note={team.needs}
              />
            ))}
          </div>
        </NewsletterSection>
        </div>

        <div data-section="nba" style={sectionStyle("nba", NBA?.IMPORTANCE || 6)}>
        {/* ── NBA ─────────────────────────────────────────── */}
        {NBA && (
          <>
            <header className="newsletter-hero" style={{ marginTop: 48 }}>
              <div className="newsletter-hero__masthead">
                <span>NBA Tracker</span>
                <span>{NBA.SEASON}</span>
                <span>Actualizado {NBA.LAST_UPDATE}</span>
              </div>
              <div className="newsletter-hero__title-row">
                <h1>NBA Playoffs</h1>
                <p>
                  Bracket vivo y rankings top 10 NBA con el mismo formato:
                  las filas sombreadas pertenecen a equipos eliminados.
                </p>
              </div>
              <div className="newsletter-hero__alive mono">
                Siguen vivos: <strong>{[...nbaAlive].sort().join(" · ") || "TBD"}</strong>
              </div>
            </header>

            <NewsletterSection
              kicker="Playoff bracket"
              title="Camino a las NBA Finals"
              sub="Series al mejor de siete, con ganadores ya decididos y cruces vivos en conferencia."
            >
              <NBABracket bracket={NBA.BRACKET} />
            </NewsletterSection>

            <FinalsShowdown
              teams={nbaFinalsTeams}
              players={NBA.PLAYERS || []}
              legendScores={nbaLegendScores}
              legendThreshold={NBA.ROAD_TO_GLORY?.playerThreshold || 100}
              teamByCode={nbaTeamByCode}
              logoForTeam={nbaTeamLogo}
              playerMeta={nbaPlayerMeta}
              scoreNote={p => `${p.stats.pts} PPG · ${p.stats.reb} REB · ${p.stats.ast} AST`}
              kicker="NBA Finals Showdown"
              title="Top 10 performers por finalista"
              sub="Aparece cuando están definidos los dos equipos de las NBA Finals. Score actual de temporada y score leyenda/Road To Glory."
            />

            <NewsletterSection
              kicker="Top performers"
              title={`Top 10 performers NBA ${nbaStatsLabel}`}
              sub={`Ranking por score actual de ${nbaStatsLabel} — pts, reb, ast, stl, blk ponderados por posición.`}
            >
              <div className="newsletter-list">
                {nbaTopPerformers.map((player, i) => (
                  <NewsletterRankRow
                    key={player.id}
                    rank={i + 1}
                    prevRank={player.prevRank}
                    item={player}
                    alive={nbaAlive}
                    score={player.score}
                    scoreLabel="Score"
                    meta={nbaPlayerMeta(player)}
                    note={`${player.stats.pts} PPG · ${player.stats.reb} REB · ${player.stats.ast} AST`}
                    logo={nbaTeamLogo(player.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="Road to glory"
              title="Top 10 jugadores NBA Road To Glory"
              sub={`Umbral top 10 histórico: ${NBA.ROAD_TO_GLORY?.playerThreshold ?? "N/A"} (Tim Duncan).`}
            >
              <div className="newsletter-list">
                {nbaRoadPlayers.map((player, i) => (
                  <NewsletterRankRow
                    key={player.id}
                    rank={i + 1}
                    prevRank={player.prevRank}
                    item={player}
                    alive={nbaAlive}
                    score={player.careerScore}
                    scoreLabel="Career"
                    threshold={NBA.ROAD_TO_GLORY?.playerThreshold}
                    meta={`${nbaPlayerMeta(player)} · ${player.rings} ring${player.rings !== 1 ? "s" : ""}`}
                    note={player.note}
                    logo={nbaTeamLogo(player.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="Young road to glory"
              title="Top 10 jóvenes NBA Road To Glory"
              sub="Proyección de carrera para jugadores de 25 años o menos."
            >
              <div className="newsletter-list">
                {nbaYoungPlayers.map((player, i) => (
                  <NewsletterRankRow
                    key={player.id}
                    rank={i + 1}
                    prevRank={player.prevRank}
                    item={player}
                    alive={nbaAlive}
                    score={player.projectedScore}
                    scoreLabel="Proj."
                    threshold={NBA.ROAD_TO_GLORY?.playerThreshold}
                    meta={`${nbaPlayerMeta(player)} · score actual ${player.currentScore}`}
                    note={player.note}
                    logo={nbaTeamLogo(player.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="Team road to glory"
              title="Top 10 franquicias NBA Road To Glory"
              sub={`Umbral top 10 histórico de franquicias: ${NBA.ROAD_TO_GLORY?.teamThreshold ?? "N/A"}.`}
            >
              <div className="newsletter-list">
                {nbaRoadTeams.map((team, i) => (
                  <NewsletterRankRow
                    key={`${team.teamCode}-${team.era}`}
                    rank={i + 1}
                    prevRank={team.prevRank}
                    item={{ ...team, name: team.city }}
                    alive={nbaAlive}
                    score={team.dynastyScore}
                    scoreLabel="Dynasty"
                    threshold={NBA.ROAD_TO_GLORY?.teamThreshold}
                    meta={`${team.era} · ${team.rings} ring${team.rings !== 1 ? "s" : ""} · ${team.note}`}
                    note={team.needs}
                    logo={nbaTeamLogo(team.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="NBA Legends"
              title="Top 10 jugadores NBA histórico"
              sub={`Ranking all-time cross-era ajustado por posición. Umbral top 10: ${nbaHistoryThreshold.toFixed(1)} (Tim Duncan).`}
            >
              <div className="newsletter-list">
                {nbaHistoryPlayers.map((player, i) => (
                  <NewsletterRankRow
                    key={`${player.name}-${player.era}`}
                    rank={i + 1}
                    item={player}
                    alive={new Set()}
                    score={player.score}
                    scoreLabel="Legend"
                    threshold={nbaHistoryThreshold}
                    meta={`NBA · ${player.pos} · ${player.era} · tier ${player.tier}`}
                    note={player.note}
                    logo={nbaTeamLogo(player.teamCode)}
                    legendActive={player.era?.includes("present")}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="NBA Dynasties"
              title="Top 10 franquicias NBA histórico"
              sub="Las mayores dinastías de la historia de la NBA ordenadas por score all-time."
            >
              <div className="newsletter-list">
                {nbaHistoryTeams.map((team, i) => (
                  <NewsletterRankRow
                    key={`${team.teamCode}-${team.era}`}
                    rank={i + 1}
                    item={{ ...team, name: team.city }}
                    alive={new Set()}
                    score={team.score}
                    scoreLabel="Score"
                    threshold={nbaHistoryTeamThreshold}
                    meta={`${team.conf} · ${team.era} · ${team.titles} título${team.titles !== 1 ? "s" : ""}`}
                    note={team.note}
                    logo={nbaTeamLogo(team.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>
          </>
        )}
        </div>

        <div data-section="mlb" style={sectionStyle("mlb", MLB?.IMPORTANCE || 8)}>
        {/* ── MLB ─────────────────────────────────────────── */}
        {MLB && (
          <>
            <header className="newsletter-hero" style={{ marginTop: 48 }}>
              <div className="newsletter-hero__masthead">
                <span>MLB Tracker</span>
                <span>{MLB.SEASON}</span>
                <span>Actualizado {MLB.LAST_UPDATE}</span>
              </div>
              <div className="newsletter-hero__title-row">
                <h1>MLB {MLB.SEASON}</h1>
                <p>
                  Clasificación por divisiones, top pitchers y batters, y Road to Glory.
                  {mlbHasPlayoffs && " El bracket de playoffs se activa en octubre."}
                </p>
              </div>
            </header>

            {mlbHasPlayoffs ? (
              <NewsletterSection
                kicker="Playoff bracket"
                title="Camino a las World Series"
                sub="Wild Card (3 partidos) → Division Series (5) → LCS (7) → World Series (7)."
              >
                <MLBBracket bracket={MLB.BRACKET} />
              </NewsletterSection>
            ) : (
              <NewsletterSection
                kicker="Clasificación"
                title={`MLB ${MLB.SEASON} · Standings por división`}
                sub="Temporada regular — ordenados por W dentro de cada división."
              >
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" }}>
                  {MLB_DIV_ORDER.map(div => (
                    <div key={div} style={{ marginBottom: 20 }}>
                      <div className="mono mono--muted" style={{ fontSize: 11, letterSpacing: ".08em", textTransform: "uppercase", padding: "6px 0 4px", borderBottom: "1px solid var(--rule)" }}>{div}</div>
                      {(mlbDivStandings[div] || []).map((team, i) => (
                        <div key={team.code} className="newsletter-row" style={{ padding: "5px 0" }}>
                          <span className="newsletter-row__rank" style={{ fontSize: 11 }}>{String(i + 1).padStart(2, "0")}</span>
                          <span className="newsletter-row__identity" style={{ flex: 1 }}>
                            <TeamSwatch colors={team.colors} code={team.code} logo={mlbTeamLogo(team.code)} />
                            <span className="newsletter-row__copy">
                              <span className="newsletter-row__name" style={{ fontSize: 13 }}>{team.shortName}</span>
                              <span className="newsletter-row__meta">{team.w}–{team.l} · {team.rd > 0 ? "+" : ""}{team.rd} RD</span>
                            </span>
                          </span>
                          <span style={{ fontSize: 13, fontVariantNumeric: "tabular-nums", color: "var(--ink-2)" }}>.{String(Math.round(team.winPct * 1000)).padStart(3, "0")}</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </NewsletterSection>
            )}

            <NewsletterSection
              kicker="Top pitchers"
              title="Top 10 pitchers MLB esta temporada"
              sub="Ranking por score — ERA, K, W, WHIP ponderados."
            >
              <div className="newsletter-list">
                {mlbPitchers.map((player, i) => (
                  <NewsletterRankRow
                    key={player.id}
                    rank={i + 1}
                    prevRank={player.prevRank}
                    item={player}
                    alive={mlbAlive}
                    score={player.score}
                    scoreLabel="Score"
                    scoreB={player.legendScore}
                    scoreBDisplay={player.legendScore?.toFixed?.(1)}
                    scoreBLabel="Leyenda"
                    scoreBThreshold={mlbLegendThreshold}
                    meta={mlbPlayerMeta(player)}
                    note={mlbPlayerNote(player)}
                    logo={mlbTeamLogo(player.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="Top batters"
              title="Top 10 batters MLB esta temporada"
              sub="Ranking por score — HR, RBI, AVG, SB, OPS ponderados."
            >
              <div className="newsletter-list">
                {mlbBatters.map((player, i) => (
                  <NewsletterRankRow
                    key={player.id}
                    rank={i + 1}
                    prevRank={player.prevRank}
                    item={player}
                    alive={mlbAlive}
                    score={player.score}
                    scoreLabel="Score"
                    scoreB={player.legendScore}
                    scoreBDisplay={player.legendScore?.toFixed?.(1)}
                    scoreBLabel="Leyenda"
                    scoreBThreshold={mlbLegendThreshold}
                    meta={mlbPlayerMeta(player)}
                    note={mlbPlayerNote(player)}
                    logo={mlbTeamLogo(player.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="Road to glory"
              title="Top 10 jugadores MLB Road To Glory"
              sub={`Legend score proyectado en la misma escala que las leyendas históricas. Umbral top 10: ${MLB.ROAD_TO_GLORY?.playerThreshold ?? "N/A"} (Rogers Hornsby).`}
            >
              <div className="newsletter-list">
                {mlbRoadPlayers.map((player, i) => (
                  <NewsletterRankRow
                    key={player.id}
                    rank={i + 1}
                    prevRank={player.prevRank}
                    item={player}
                    alive={mlbAlive}
                    score={player.legendScore ?? player.careerScore}
                    scoreLabel="Legend"
                    threshold={MLB.ROAD_TO_GLORY?.playerThreshold}
                    meta={`${mlbPlayerMeta(player)} · score actual ${player.currentScore ?? player.score}`}
                    note={mlbRoadNote(player)}
                    logo={mlbTeamLogo(player.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="MLB Legends"
              title="Top 10 jugadores por Legend score histórico"
              sub={`Ranking histórico por Legend score. Corte top 10: ${mlbLegendThreshold.toFixed(1)}.`}
            >
              <div className="newsletter-list">
                {mlbLegends.map((player, i) => (
                  <NewsletterRankRow
                    key={`${player.name}-${player.era}`}
                    rank={i + 1}
                    item={player}
                    alive={new Set()}
                    score={player.legendScore}
                    scoreLabel="Legend"
                    threshold={mlbLegendThreshold}
                    meta={`MLB · ${player.pos} · ${player.era} · tier ${player.tier}`}
                    note={player.note}
                    logo={mlbTeamLogo(player.teamCode)}
                    legendActive={player.era?.includes("present")}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="Young road to glory"
              title="Top 10 jóvenes MLB Road To Glory"
              sub="Proyección de carrera para jugadores de 25 años o menos."
            >
              <div className="newsletter-list">
                {mlbYoungPlayers.map((player, i) => (
                  <NewsletterRankRow
                    key={player.id}
                    rank={i + 1}
                    prevRank={player.prevRank}
                    item={player}
                    alive={mlbAlive}
                    score={player.projectedScore}
                    scoreLabel="Proj."
                    threshold={MLB.ROAD_TO_GLORY?.playerThreshold}
                    meta={`${mlbPlayerMeta(player)} · score actual ${player.currentScore}`}
                    note={player.note}
                    logo={mlbTeamLogo(player.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>

            <NewsletterSection
              kicker="Team road to glory"
              title="Top 10 franquicias MLB Road To Glory"
              sub={`Umbral top 10 histórico de franquicias: ${MLB.ROAD_TO_GLORY?.teamThreshold ?? "N/A"}.`}
            >
              <div className="newsletter-list">
                {mlbRoadTeams.map((team, i) => (
                  <NewsletterRankRow
                    key={`${team.teamCode}-${team.era}`}
                    rank={i + 1}
                    prevRank={team.prevRank}
                    item={{ ...team, name: team.city }}
                    alive={mlbAlive}
                    score={team.dynastyScore}
                    scoreLabel="Dynasty"
                    threshold={MLB.ROAD_TO_GLORY?.teamThreshold}
                    meta={`${team.era} · ${team.rings} ring${team.rings !== 1 ? "s" : ""} · ${team.note}`}
                    note={team.needs}
                    logo={mlbTeamLogo(team.teamCode)}
                  />
                ))}
              </div>
            </NewsletterSection>
          </>
        )}
        </div>

        <div data-section="nfl" style={sectionStyle("nfl", NFL?.IMPORTANCE || 3)}>
        {/* ── NFL ─────────────────────────────────────────── */}
        {NFL && (
          <>
            <header className="newsletter-hero" style={{ marginTop: 48 }}>
              <div className="newsletter-hero__masthead">
                <span>NFL Tracker</span>
                <span>{NFL.SEASON_STATUS === "offseason" ? `${NFL.SEASON} Final` : `${NFL.SEASON} Week`}</span>
                <span>Actualizado {NFL.LAST_UPDATE}</span>
              </div>
              <div className="newsletter-hero__title-row">
                <h1>NFL {NFL.SEASON}</h1>
                <p>
                  {NFL.SEASON_STATUS === "offseason"
                    ? `Clasificación final temporada ${NFL.SEASON}. La temporada ${parseInt(NFL.SEASON) + 1} empieza en septiembre.`
                    : NFL.SEASON_STATUS === "postseason"
                    ? "Playoffs en curso. Bracket activo."
                    : `Temporada regular ${NFL.SEASON} en curso.`}
                </p>
              </div>
            </header>

            {nflHasPlayoffs ? (
              <NewsletterSection
                kicker="Playoff bracket"
                title="Camino al Super Bowl"
                sub="Wild Card → Divisional → Championship → Super Bowl."
              >
                <NFLBracket bracket={NFL.BRACKET} />
              </NewsletterSection>
            ) : (
              <NewsletterSection
                kicker="Clasificación"
                title={`NFL ${NFL.SEASON} · Standings por división`}
                sub={NFL.SEASON_STATUS === "offseason" ? "Clasificación final de temporada regular." : "Temporada regular en curso."}
              >
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" }}>
                  {NFL_DIV_ORDER.map(div => (
                    <div key={div} style={{ marginBottom: 20 }}>
                      <div className="mono mono--muted" style={{ fontSize: 11, letterSpacing: ".08em", textTransform: "uppercase", padding: "6px 0 4px", borderBottom: "1px solid var(--rule)" }}>{div}</div>
                      {(nflDivStandings[div] || []).map((team, i) => (
                        <div key={team.code} className="newsletter-row" style={{ padding: "5px 0" }}>
                          <span className="newsletter-row__rank" style={{ fontSize: 11 }}>{String(i + 1).padStart(2, "0")}</span>
                          <span className="newsletter-row__identity" style={{ flex: 1 }}>
                            <TeamSwatch colors={team.colors} code={team.code} logo={nflTeamLogo(team.code)} />
                            <span className="newsletter-row__copy">
                              <span className="newsletter-row__name" style={{ fontSize: 13 }}>{team.shortName}</span>
                              <span className="newsletter-row__meta">{team.w}–{team.l}{team.t > 0 ? `–${team.t}` : ""} · {team.pd > 0 ? "+" : ""}{team.pd} PD</span>
                            </span>
                          </span>
                          <span style={{ fontSize: 13, fontVariantNumeric: "tabular-nums", color: "var(--ink-2)" }}>.{String(Math.round(team.winPct * 1000)).padStart(3, "0")}</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </NewsletterSection>
            )}

            {nflTopQBs.length > 0 && (
              <NewsletterSection
                kicker="Top QBs"
                title={`Top 10 quarterbacks NFL ${NFL.SEASON}`}
                sub="Ranking por score — yardas, TDs, INTs y completion% ponderados."
              >
                <div className="newsletter-list">
                  {nflTopQBs.map((player, i) => (
                    <NewsletterRankRow
                      key={player.id}
                      rank={i + 1}
                      prevRank={player.prevRank}
                      item={player}
                      alive={nflAlive}
                      score={player.score}
                      scoreLabel="Score"
                      meta={nflPlayerMeta(player)}
                      note={nflPlayerNote(player)}
                      logo={nflTeamLogo(player.teamCode)}
                    />
                  ))}
                </div>
              </NewsletterSection>
            )}

            {nflRoadPlayers.length > 0 && (
              <NewsletterSection
                kicker="Road to glory"
                title="QBs camino del panteón"
                sub={`Score de carrera proyectado. Umbral top 10 histórico: ${nflPlayerThreshold} (Dan Marino).`}
              >
                <div className="newsletter-list">
                  {nflRoadPlayers.map((player, i) => (
                    <NewsletterRankRow
                      key={player.id}
                      rank={i + 1}
                      item={player}
                      alive={nflAlive}
                      score={player.careerScore}
                      scoreLabel="Carrera"
                      threshold={nflPlayerThreshold}
                      meta={`${nflPlayerMeta(player)} · ${player.rings} anillo${player.rings !== 1 ? "s" : ""}`}
                      note={player.note}
                      logo={nflTeamLogo(player.teamCode)}
                    />
                  ))}
                </div>
              </NewsletterSection>
            )}

            {nflYoungPlayers.length > 0 && (
              <NewsletterSection
                kicker="Young road to glory"
                title="Jóvenes promesa NFL"
                sub="Proyección de carrera para QBs de 25 años o menos — quién ha empezado fuerte."
              >
                <div className="newsletter-list">
                  {nflYoungPlayers.map((player, i) => (
                    <NewsletterRankRow
                      key={player.id}
                      rank={i + 1}
                      item={player}
                      alive={nflAlive}
                      score={player.projectedScore}
                      scoreLabel="Proy."
                      threshold={nflPlayerThreshold}
                      meta={`${nflPlayerMeta(player)} · score actual ${player.currentScore}`}
                      note={player.note}
                      logo={nflTeamLogo(player.teamCode)}
                    />
                  ))}
                </div>
              </NewsletterSection>
            )}

            {nflHistoryPlayers.length > 0 && (
              <NewsletterSection
                kicker="NFL Legends"
                title="Top 10 QBs de la historia"
                sub="Panteón all-time de mariscales de campo."
              >
                <div className="newsletter-list">
                  {nflHistoryPlayers.map((player, i) => (
                    <NewsletterRankRow
                      key={`${player.name}-${player.era}`}
                      rank={i + 1}
                      item={{ ...player, colors: player.colors || { primary: "#555", secondary: "#ccc" } }}
                      alive={new Set()}
                      score={player.score}
                      scoreLabel="Histórico"
                      meta={`NFL QB · ${player.teamCode} · ${player.era}`}
                      note={player.note}
                      logo={nflTeamLogo(player.teamCode)}
                    />
                  ))}
                </div>
              </NewsletterSection>
            )}
          </>
        )}
        </div>

        <div data-section="tennis" style={sectionStyle("tennis", TENNIS?.IMPORTANCE || 7)}>
        {/* ── TENNIS ─────────────────────────────────────────── */}
        {TENNIS && (() => {
          const atpChanges  = TENNIS.ATP_CHANGES  || { entered: [], exited: [] };
          const wtaChanges  = TENNIS.WTA_CHANGES  || { entered: [], exited: [] };

          // Legends list = historical legacy only. Active players keep the historical score.
          function buildLegendsMerged(histKey, activeList) {
            const activeByName = Object.fromEntries(activeList.map(p => [p.name, p]));
            return (TENNIS[histKey] || []).map(p => {
              const act = activeByName[p.name];
              return { ...p, colors: { primary: p.primary, secondary: p.secondary },
                        active: act ? true : (p.active || false) };
            }).sort((a, b) => b.legendScore - a.legendScore).slice(0, 10);
          }
          const atpLegends = buildLegendsMerged("ATP_LEGENDS", tennisATPFull);
          const wtaLegends = buildLegendsMerged("WTA_LEGENDS", tennisWTAFull);
          const atpLegendRows = TENNIS.ATP_LEGENDS || [];
          const wtaLegendRows = TENNIS.WTA_LEGENDS || [];
          const tennisLegendRaw = p => (p.stats?.gs || 0) * 12 + (p.stats?.year_end_no1 || 0) * 3 + Math.floor((p.stats?.weeks_no1 || 0) / 10);
          const atpLegendTop = [...atpLegendRows].sort((a, b) => b.legendScore - a.legendScore);
          const wtaLegendTop = [...wtaLegendRows].sort((a, b) => b.legendScore - a.legendScore);
          const atpLegendScoreByName = Object.fromEntries(atpLegendRows.map(p => [p.name, p.legendScore]));
          const wtaLegendScoreByName = Object.fromEntries(wtaLegendRows.map(p => [p.name, p.legendScore]));
          const atpLegendRawByName = Object.fromEntries(atpLegendRows.map(p => [p.name, tennisLegendRaw(p)]));
          const wtaLegendRawByName = Object.fromEntries(wtaLegendRows.map(p => [p.name, tennisLegendRaw(p)]));
          const atpLegendMaxRaw = Math.max(...atpLegendRows.map(tennisLegendRaw), 1);
          const wtaLegendMaxRaw = Math.max(...wtaLegendRows.map(tennisLegendRaw), 1);
          const atpLegendThreshold = atpLegendTop[9]?.legendScore || 0;
          const wtaLegendThreshold = wtaLegendTop[9]?.legendScore || 0;
          const atpLegendThresholdRaw = atpLegendTop[9] ? tennisLegendRaw(atpLegendTop[9]) : 0;
          const wtaLegendThresholdRaw = wtaLegendTop[9] ? tennisLegendRaw(wtaLegendTop[9]) : 0;
          const tennisHistoricalLegendScore = (player, scoreMap, maxRaw) => {
            // Score Leyenda canónico almacenado por el backend (lo que se cita en feed/email).
            if (typeof player.leyendaScore === "number") return player.leyendaScore;
            const score = scoreMap[player.name];
            if (typeof score === "number") return score;
            const raw = (player.stats?.gs || 0) * 12 + Math.floor((player.stats?.weeks_no1 || 0) / 10);
            return Math.round((raw / maxRaw * 100) * 10) / 10;
          };
          const tennisHistoricalRaw = (player, rawMap) => {
            const raw = rawMap[player.name];
            return typeof raw === "number" ? raw : (player.stats?.gs || 0) * 12 + Math.floor((player.stats?.weeks_no1 || 0) / 10);
          };
          const tennisLegendChaseNote = (player, scoreMap, rawMap, maxRaw, threshold, thresholdRaw) => {
            const score = tennisHistoricalLegendScore(player, scoreMap, maxRaw);
            if (score >= threshold) return "Ya está en zona top 10 histórico";
            const gap = Math.max(0, threshold - score);
            const rawGap = Math.max(0, thresholdRaw - tennisHistoricalRaw(player, rawMap));
            const gsNeeded = Math.max(1, Math.ceil(rawGap / 12));
            return rawGap <= 12
              ? `A ${gap.toFixed(1)} del top 10 · 1 GS lo mete`
              : `A ${gap.toFixed(1)} del top 10 · ${gsNeeded} GS aprox.`;
          };

          const atpRecent = TENNIS.ATP_RECENT || [];
          const atpToday = TENNIS.ATP_TODAY || [];
          const wtaRecent = TENNIS.WTA_RECENT || [];
          const wtaToday = TENNIS.WTA_TODAY || [];
          const atpTournament = TENNIS.ATP_TOURNAMENT || {};
          const wtaTournament = TENNIS.WTA_TOURNAMENT || {};
          const atpAliveIds = new Set(tennisATPFull.filter(p => p.tournamentStatus?.state === "alive").map(p => p.id));
          const wtaAliveIds = new Set(tennisWTAFull.filter(p => p.tournamentStatus?.state === "alive").map(p => p.id));
          const atpIncludeAllAlive = atpTournament.aliveCount > 0 && atpTournament.aliveCount <= 8;
          const wtaIncludeAllAlive = wtaTournament.aliveCount > 0 && wtaTournament.aliveCount <= 8;

          const SURFACE_COLOR = { Clay: "#c47a4b", Grass: "#4a8c3f", Hard: "#3a6ea5", Carpet: "#6a4c9c" };
          const playerScoreColors = score => {
            if (score >= 85) return { bg: "#dcefe2", fg: "#1f7a3d" };
            if (score >= 70) return { bg: "#e8efdc", fg: "#5f7d1e" };
            if (score >= 55) return { bg: "#f5ead4", fg: "#a86513" };
            return { bg: "#f8ded9", fg: "#c92d2d" };
          };
          const playerScoreChip = score => score != null ? (
            (() => {
              const colors = playerScoreColors(Number(score));
              return (
                <span style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  minWidth: 34,
                  marginLeft: 5,
                  padding: "1px 5px",
                  borderRadius: 3,
                  background: colors.bg,
                  color: colors.fg,
                  fontFamily: "monospace",
                  fontSize: 10,
                  fontWeight: 700,
                  verticalAlign: "middle",
                }}>{Number(score).toFixed(1)}</span>
              );
            })()
          ) : null;
          function RecentResults({ data, tour, mode = "results" }) {
            if (!data || !data.length) return null;
            const isSchedule = mode === "schedule";
            return (
              <NewsletterSection
                kicker={`${tour} · Partidos importantes`}
                title={`${tour} — ${isSchedule ? "Hoy" : "Ayer"}`}
                sub={isSchedule
                  ? "Top partidos programados hoy, ordenados por el mejor score individual del duelo."
                  : "Top resultados de ayer, ordenados por el mejor score individual del duelo."}
              >
                {data.map((tourney, ti) => (
                  <div key={ti} style={{ marginBottom: 20 }}>
                    {/* Cabecera del torneo */}
                    <div style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "6px 0 5px",
                      borderBottom: "2px solid var(--ink, #1a1714)",
                      marginBottom: 4,
                    }}>
                      <span style={{
                        width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
                        background: SURFACE_COLOR[tourney.surface] || "#888",
                      }} />
                      <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: "-0.01em" }}>
                        {tourney.name}
                      </span>
                      <span style={{
                        fontSize: 10, fontFamily: "monospace", color: "var(--muted, #888)",
                        textTransform: "uppercase", letterSpacing: "0.08em",
                        background: "var(--bar-bg, #e8e4e0)", borderRadius: 3,
                        padding: "1px 5px",
                      }}>
                        {tourney.level}
                      </span>
                      <span style={{
                        fontSize: 10, fontFamily: "monospace", color: "var(--muted, #888)",
                        textTransform: "uppercase", letterSpacing: "0.06em",
                      }}>
                        {tourney.surface}
                      </span>
                    </div>
                    {/* Partidos */}
                    {tourney.matches.map((m, mi) => (
                      <div key={mi} style={{
                        display: "grid",
                        gridTemplateColumns: "80px 1fr auto",
                        gap: "0 10px",
                        alignItems: "center",
                        padding: "5px 0",
                        borderBottom: "1px solid var(--rule, #eee)",
                        fontSize: 13,
                      }}>
                        <span style={{
                          fontSize: 10, fontFamily: "monospace",
                          color: "var(--muted, #888)", textTransform: "uppercase",
                          letterSpacing: "0.05em",
                        }}>
                          {m.day ? `${m.day} · ${m.round}` : m.round}
                        </span>
                        <span style={{ minWidth: 0, overflow: "hidden" }}>
                          {m.w_logo && <img src={m.w_logo} style={{ width: 16, height: 12, verticalAlign: "middle", marginRight: 4, borderRadius: 1 }} />}
                          <span style={{ fontWeight: m.scheduled ? 400 : 600 }}>{m.w}</span>
                          {playerScoreChip(m.w_score)}
                          <span style={{ color: "var(--muted, #888)", margin: "0 6px", fontSize: 11 }}>{m.scheduled ? "vs" : "def."}</span>
                          {m.l_logo && <img src={m.l_logo} style={{ width: 16, height: 12, verticalAlign: "middle", marginRight: 4, borderRadius: 1 }} />}
                          <span style={{ color: "var(--ink-2, #666)" }}>{m.l}</span>
                          {playerScoreChip(m.l_score)}
                        </span>
                        <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--ink-2, #666)", whiteSpace: "nowrap" }}>
                          {m.score}
                        </span>
                      </div>
                    ))}
                  </div>
                ))}
              </NewsletterSection>
            );
          }

          function ChangesRow({ changes, tour }) {
            const { entered = [], exited = [], prev_date = "", curr_date = "" } = changes;
            if (!entered.length && !exited.length) return null;
            const fmt = d => d ? `${d.slice(0,4)}-${d.slice(4,6)}-${d.slice(6,8)}` : "";
            return (
              <div style={{ margin: "8px 0 16px", fontSize: 12, color: "var(--ink-2)" }}>
                <span style={{ marginRight: 8, color: "var(--ink-3)", fontVariantCaps: "all-small-caps", letterSpacing: "0.06em" }}>
                  {tour} TOP 10 · {fmt(prev_date)} → {fmt(curr_date)}
                </span>
                {entered.map(p => (
                  <span key={p.name} style={{ marginRight: 12 }}>
                    <img src={p.logo} style={{ width: 16, height: 12, verticalAlign: "middle", marginRight: 3 }} />
                    <span style={{ color: "#2a7a2a", fontWeight: 600 }}>↑ {p.name}</span>
                    <span style={{ color: "var(--ink-3)" }}> (#{p.rank})</span>
                  </span>
                ))}
                {exited.map(p => (
                  <span key={p.name} style={{ marginRight: 12 }}>
                    <img src={p.logo} style={{ width: 16, height: 12, verticalAlign: "middle", marginRight: 3 }} />
                    <span style={{ color: "#a02020", fontWeight: 600 }}>↓ {p.name}</span>
                    <span style={{ color: "var(--ink-3)" }}> (#{p.rank})</span>
                  </span>
                ))}
              </div>
            );
          }

          function tennisFinalTournaments(recent = []) {
            return recent.filter(tourney =>
              (tourney.matches || []).some(m =>
                m.round === "Final" && !m.scheduled && m.score && m.score !== "por jugar"
              )
            );
          }

          function tennisWithoutFinishedTournaments(tournaments = [], finished = []) {
            const finishedNames = new Set(finished.map(t => t.name).filter(Boolean));
            return tournaments.filter(t => !finishedNames.has(t.name));
          }

          function tennisTournamentScoreDelta(player, tournament) {
            const st = player.tournamentStatus || {};
            if (!tournament?.name || st.tournament !== tournament.name) return null;
            const final = (tournament.matches || []).find(m => m.round === "Final" && !m.scheduled);
            if (final?.w === player.name) return 4.0;
            if (final?.l === player.name) return 3.0;

            const round = String(st.round || st.reason || "").toLowerCase();
            const top32 = (player.prevRank ?? player.rank ?? 999) <= 32;
            if (round.includes("campe")) return 4.0;
            if (round.includes("semifinal")) return 2.0;
            if (round.includes("quarter")) return 1.2;
            if (round.includes("r16")) return 0.4;
            if (round.includes("r32")) return top32 ? -0.5 : 0.2;
            if (round.includes("r64")) return top32 ? -1.2 : -0.4;
            if (round.includes("r128")) return top32 ? -2.0 : -0.8;
            if (String(st.reason || "").toLowerCase().includes("lesi")) return top32 ? -0.8 : -0.2;
            if (String(st.reason || "").toLowerCase().includes("no compite")) return top32 ? -1.0 : -0.2;
            return null;
          }

          function tennisMovementRows(players = [], tournament = null) {
            const enriched = players
              .map(player => {
                const previousScore = player.prevActiveScore ?? player.previousActiveScore ?? player.preTournamentActiveScore;
                if (typeof player.activeScore !== "number") return null;
                const hasPreviousScore = typeof previousScore === "number";
                const rawDelta = hasPreviousScore
                  ? player.activeScore - previousScore
                  : tennisTournamentScoreDelta(player, tournament);
                if (typeof rawDelta !== "number") return null;
                const scoreDelta = Math.round(rawDelta * 10) / 10;
                return {
                  ...player,
                  previousScore,
                  hasPreviousScore,
                  scoreDelta,
                };
              })
              .filter(Boolean)
              .filter(player => player.scoreDelta !== 0);

            return {
              risers: enriched
                .filter(player => player.scoreDelta > 0)
                .sort((a, b) => b.scoreDelta - a.scoreDelta || b.activeScore - a.activeScore)
                .slice(0, 5),
              fallers: enriched
                .filter(player => player.scoreDelta < 0 && (player.prevRank ?? player.rank ?? 999) <= 32)
                .sort((a, b) => a.scoreDelta - b.scoreDelta || b.activeScore - a.activeScore)
                .slice(0, 5),
            };
          }

          function TennisMovementCard({ title, rows, tone, tour }) {
            if (!rows.length) return null;
            const isUp = tone === "up";
            return (
              <div className="newsletter-list" style={{ flex: 1, minWidth: 280 }}>
                <div style={{
                  padding: "6px 0 8px",
                  borderBottom: "2px solid var(--ink,#1a1714)",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: "0.02em",
                  textTransform: "uppercase",
                }}>
                  {title}
                </div>
                {rows.map((player, i) => (
                  <div
                    key={`${tour}-${tone}-${player.id}`}
                    className={`tennis-movement-row ${isUp ? "tennis-movement-row--up" : "tennis-movement-row--down"}`}
                  >
                    <span className="tennis-movement-row__rank">{String(i + 1).padStart(2, "0")}</span>
                    <span className="tennis-movement-row__identity">
                      <TeamSwatch colors={player.colors} code={player.teamCode} logo={player.logo} />
                      <span className="tennis-movement-row__copy">
                        <span className="tennis-movement-row__name">{player.name}</span>
                        <span className="tennis-movement-row__meta">
                          {tour} · #{player.rank} · {player.hasPreviousScore ? `antes ${player.previousScore.toFixed(1)}` : "impacto torneo"}
                        </span>
                      </span>
                    </span>
                    <span className="tennis-movement-row__score">
                      <span className="tennis-movement-row__label">Nivel</span>
                      <span className="tennis-movement-row__value">{player.activeScore.toFixed(1)}</span>
                    </span>
                    <span className="tennis-movement-row__delta">
                      {isUp ? "+" : ""}{player.scoreDelta.toFixed(1)}
                    </span>
                  </div>
                ))}
              </div>
            );
          }

          function TennisTournamentMovement({ tournament, tour, players }) {
            const movement = tennisMovementRows(players, tournament);
            if (!movement.risers.length && !movement.fallers.length) return null;
            const hasPreviousScores = [...movement.risers, ...movement.fallers].some(player => player.hasPreviousScore);
            return (
              <NewsletterSection
                kicker={`${tour} · Movimiento post-final`}
                title={`${tournament.name} — quién sube y quién baja`}
                sub={hasPreviousScores
                  ? "Cambio de score Hermes tras la final. Bajadas filtradas a jugadores que venían del top 32."
                  : "Impacto de score del torneo hasta que exista snapshot previo de Nivel. Bajadas filtradas a jugadores que venían del top 32."}
              >
                <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
                  <TennisMovementCard title="Más suben" rows={movement.risers} tone="up" tour={tour} />
                  <TennisMovementCard title="Más bajan · top 32 previo" rows={movement.fallers} tone="down" tour={tour} />
                </div>
              </NewsletterSection>
            );
          }

          const atpFinalTournaments = tennisFinalTournaments(atpRecent);
          const wtaFinalTournaments = tennisFinalTournaments(wtaRecent);
          const atpTodayOpen = tennisWithoutFinishedTournaments(atpToday, atpFinalTournaments);
          const wtaTodayOpen = tennisWithoutFinishedTournaments(wtaToday, wtaFinalTournaments);

          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Tennis Tracker</span>
                  <span>ATP · WTA</span>
                  <span>Actualizado {TENNIS.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>Tennis Rankings</h1>
                  <p>
                    Top jugadores ATP y WTA singles. Score activo (0–100): forma, Elo, ranking y solidez de superficie.
                    Score Leyenda (0–100): trayectoria histórica — GS, semanas #1, calidad de rivales.
                  </p>
                </div>
              </header>

              <RecentResults data={atpRecent} tour="ATP" />
              <RecentResults data={atpTodayOpen} tour="ATP" mode="schedule" />
              <RecentResults data={wtaRecent} tour="WTA" />
              <RecentResults data={wtaTodayOpen} tour="WTA" mode="schedule" />
              {atpFinalTournaments.map(tournament => (
                <TennisTournamentMovement
                  key={`atp-movement-${tournament.name}`}
                  tournament={tournament}
                  tour="ATP"
                  players={tennisATPFull}
                />
              ))}
              {wtaFinalTournaments.map(tournament => (
                <TennisTournamentMovement
                  key={`wta-movement-${tournament.name}`}
                  tournament={tournament}
                  tour="WTA"
                  players={tennisWTAFull}
                />
              ))}

              <NewsletterSection
                kicker="ATP Singles"
                title="Top 10 ATP Singles — Score activo"
                sub={`${atpTournament.name || "Torneo actual"}: vivos en claro; eliminados, lesionados o no inscritos sombreados. Si el cuadro entra en cuartos, se añaden supervivientes fuera del top 10.`}
              >
                <ChangesRow changes={atpChanges} tour="ATP" />
                <div className="newsletter-list">
                  {tennisDisplayList(tennisATP, tennisATPFull, atpAliveIds, 2, atpIncludeAllAlive).map((player, i) => (
                    <NewsletterRankRow
                      key={player.id}
                      rank={player.displayRank || i + 1}
                      prevRank={tennisPrevRank(player, (player.displayRank || i + 1) - 1)}
                      item={player}
                      alive={atpAliveIds}
                      aliveKey="id"
                      forceOut={player.tournamentStatus?.state && player.tournamentStatus.state !== "alive"}
                      score={player.activeScore}
                      scoreLabel="Nivel"
                      scoreDelta={tennisScoreDelta(player)}
                      scoreB={tennisHistoricalLegendScore(player, atpLegendScoreByName, atpLegendMaxRaw)}
                      scoreBLabel="Leyenda"
                      scoreBThreshold={atpLegendThreshold}
                      meta={tennisPlayerMeta(player, "ATP")}
                      note={[tennisTournamentNote(player), tennisInactiveNote(player), tennisLegendChaseNote(player, atpLegendScoreByName, atpLegendRawByName, atpLegendMaxRaw, atpLegendThreshold, atpLegendThresholdRaw)].filter(Boolean).join(" · ")}
                      logo={player.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="ATP Legends"
                title="Top 10 leyendas ATP"
                sub={`Umbral top 10 histórico: ${atpLegendThreshold.toFixed(1)} (${atpLegendTop[9]?.name || "N/A"}). Score histórico: GS (×12) + Year-end #1 (×3) + semanas en #1 (÷10).`}
              >
                <div className="newsletter-list">
                  {atpLegends.map((p, i) => {
                    const era = p.stats?.era_start ? `${p.stats.era_start}–${p.stats.era_end || "hoy"}` : (p.stats?.birth || "");
                    return (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`ATP · ${p.country} · ${era}${p.active ? " · 🟢 Activo" : ""}`}
                      note={`${p.stats?.gs || 0} GS · ${p.stats?.year_end_no1 || 0}× #1 año · ${p.stats?.weeks_no1 || 0} sem #1`}
                      logo={p.logo}
                      legendActive={p.active}
                    />
                    );
                  })}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="WTA Singles"
                title="Top 10 WTA Singles — Score activo"
                sub={`${wtaTournament.name || "Torneo actual"}: vivas en claro; eliminadas, lesionadas o no inscritas sombreadas. Si el cuadro entra en cuartos, se añaden supervivientes fuera del top 10.`}
              >
                <ChangesRow changes={wtaChanges} tour="WTA" />
                <div className="newsletter-list">
                  {tennisDisplayList(tennisWTA, tennisWTAFull, wtaAliveIds, 2, wtaIncludeAllAlive).map((player, i) => (
                    <NewsletterRankRow
                      key={player.id}
                      rank={player.displayRank || i + 1}
                      prevRank={tennisPrevRank(player, (player.displayRank || i + 1) - 1)}
                      item={player}
                      alive={wtaAliveIds}
                      aliveKey="id"
                      forceOut={player.tournamentStatus?.state && player.tournamentStatus.state !== "alive"}
                      score={player.activeScore}
                      scoreLabel="Nivel"
                      scoreDelta={tennisScoreDelta(player)}
                      scoreB={tennisHistoricalLegendScore(player, wtaLegendScoreByName, wtaLegendMaxRaw)}
                      scoreBLabel="Leyenda"
                      scoreBThreshold={wtaLegendThreshold}
                      meta={tennisPlayerMeta(player, "WTA")}
                      note={[tennisTournamentNote(player), tennisInactiveNote(player), tennisLegendChaseNote(player, wtaLegendScoreByName, wtaLegendRawByName, wtaLegendMaxRaw, wtaLegendThreshold, wtaLegendThresholdRaw)].filter(Boolean).join(" · ")}
                      logo={player.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="WTA Legends"
                title="Top 10 leyendas WTA"
                sub={`Umbral top 10 histórico: ${wtaLegendThreshold.toFixed(1)} (${wtaLegendTop[9]?.name || "N/A"}). Score histórico: GS (×12) + Year-end #1 (×3) + semanas en #1 (÷10).`}
              >
                <div className="newsletter-list">
                  {wtaLegends.map((p, i) => {
                    const era = p.stats?.era_start ? `${p.stats.era_start}–${p.stats.era_end || "hoy"}` : (p.stats?.birth || "");
                    return (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`WTA · ${p.country} · ${era}${p.active ? " · 🟢 Activo" : ""}`}
                      note={`${p.stats?.gs || 0} GS · ${p.stats?.year_end_no1 || 0}× #1 año · ${p.stats?.weeks_no1 || 0} sem #1`}
                      logo={p.logo}
                      legendActive={p.active}
                    />
                    );
                  })}
                </div>
              </NewsletterSection>

              {[["ATP", TENNIS.ATP_PROSPECTS], ["WTA", TENNIS.WTA_PROSPECTS]].map(([tour, prospects]) =>
                (prospects || []).length > 0 && (
                  <NewsletterSection
                    key={`${tour}-prospects`}
                    kicker={`${tour} · Cantera`}
                    title={`Jóvenes promesa ${tour}`}
                    sub="Sub-23 con mejor Nivel actual — quién ha empezado fuerte camino del panteón."
                  >
                    <div className="newsletter-list">
                      {prospects.map((p, i) => (
                        <NewsletterRankRow
                          key={p.id}
                          rank={i + 1}
                          item={{ ...p, colors: { primary: p.primary, secondary: p.secondary } }}
                          alive={new Set()}
                          score={p.activeScore}
                          scoreLabel="Nivel"
                          scoreB={p.leyendaScore}
                          scoreBLabel="Leyenda"
                          meta={`${tour} · #${p.rank} · ${p.age} años`}
                          note={p.note}
                          logo={p.logo}
                        />
                      ))}
                    </div>
                  </NewsletterSection>
                )
              )}
            </>
          );
        })()}
        </div>

        <div data-section="cycling" style={sectionStyle("cycling", window.CYCLING_DATA?.IMPORTANCE || 4)}>
        {/* ── CYCLING ─────────────────────────────────────────── */}
        {window.CYCLING_DATA && (() => {
          const CYC = window.CYCLING_DATA;
          const cr  = CYC.CURRENT_RACE;
          const cycLegends = (CYC.LEGENDS || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } })).slice(0, 10);
          const cycLegendTop = [...(CYC.LEGENDS || [])].sort((a, b) => b.legendScore - a.legendScore);
          const cycLegendThreshold = cycLegendTop[9]?.legendScore || 0;
          const cycCurrentRiders = (CYC.CURRENT_RIDERS || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } })).slice(0, 10);
          const cycProspects = (CYC.CURRENT_PROSPECTS || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } }));
          const cyclingLegendChaseNote = p => {
            if (!cycLegendThreshold) return p.note || "";
            if (p.legendScore >= cycLegendThreshold) return "Ya está en zona top 10 histórico";
            const gap = Math.max(0, cycLegendThreshold - p.legendScore);
            return `${p.insight || "Road to glory abierto"} · a ${gap.toFixed(1)} del top 10 histórico`;
          };

          function cycNote(p) {
            const s = p.stats;
            const parts = [];
            if (s.tour)      parts.push(`TDF×${s.tour}`);
            if (s.giro)      parts.push(`Giro×${s.giro}`);
            if (s.vuelta)    parts.push(`Vuelta×${s.vuelta}`);
            if (s.monuments) parts.push(`Mon×${s.monuments}`);
            if (s.worlds)    parts.push(`Worlds×${s.worlds}`);
            return parts.join(" · ");
          }
          function cycMeta(p) {
            const s = p.stats;
            const status = s.birth >= 1985 ? "Activo" : "Retirado";
            return `Ciclismo · ${p.country} · ${s.birth} · ${status}`;
          }

          const typeES = {
            "Flat stage": "Etapa llana",
            "Mountain stage": "Etapa de montaña",
            "Hilly stage": "Etapa con colinas",
            "Individual time trial": "Contrarreloj individual",
            "Team time trial": "Contrarreloj por equipos",
          };
          const lastStageResult = cr?.last_stage_result || [];
          const rankText = rank => rank ? `${rank}.` : "s/d";
          const raceFinished = !!cr && Number(cr.stage || 0) >= Number(cr.total_stages || 0) && !cr.next_stage;

          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Ciclismo</span>
                  <span>{cr ? cr.name : "Road Cycling"}</span>
                  <span>Actualizado {CYC.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>{cr ? `${cr.name} 2026` : "Grandes Vueltas · Leyendas"}</h1>
                  <p>
                    {cr
                      ? raceFinished
                        ? `Finalizado · ${cr.stage}/${cr.total_stages} etapas · campeón: ${cr.gc?.[0]?.name || cr.jersey_name}.`
                        : `Etapa ${cr.stage} de ${cr.total_stages} · ${cr.jersey_name} · GC en directo.`
                      : "Score 0–100 ponderando Grandes Vueltas (TDF×12, Giro×9, Vuelta×8), Monumentos (×4) y Mundiales (×4)."}
                  </p>
                </div>
              </header>

              {cr && cr.last_stage && (() => {
                const ls = cr.last_stage;
                const ns = cr.next_stage;
                return (
                  <>
                    <NewsletterSection
                      kicker={`Etapa ${ls.stage} / ${cr.total_stages}`}
                      title={`${ls.date} · ${typeES[ls.type] || ls.type}`}
                      sub={`${ls.from} → ${ls.to}`}
                    >
                      {lastStageResult.length > 0 ? (
                        <div className="newsletter-list">
                          {lastStageResult.map((r, i) => {
                            const isGc = !!r.gc_rank;
                            const isGcOutsideTopFive = isGc && r.rank > 5;
                            const note = isGc
                              ? `Top ${r.gc_rank} GC actual${r.team ? ` · ${r.team}` : ""}`
                              : (i < 5 ? "Top 5 de la etapa" : "Clasificación de etapa");
                            return (
                              <NewsletterRankRow
                                key={`${r.rank || "gc"}-${r.name}`}
                                rank={r.rank || i + 1}
                                item={{ ...r, colors: { primary: r.primary || "#4a4745", secondary: "#ffffff" } }}
                                alive={new Set()}
                                score={r.time || ""}
                                scoreDisplay={r.time || "sin dato"}
                                scoreLabel={r.rank === 1 ? "Tiempo" : "Diferencia"}
                                meta={`${rankText(r.rank)} en la etapa${r.country ? ` · ${r.country}` : ""}`}
                                note={note}
                                logo={r.logo}
                                rowClassName={isGcOutsideTopFive ? "newsletter-row--stage-gc-gap" : ""}
                              />
                            );
                          })}
                        </div>
                      ) : (
                        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 0" }}>
                          <img src={ls.winner_logo} alt={ls.winner_cc} style={{ width: 24, height: 18, borderRadius: 2 }} />
                          <span style={{ fontSize: 20, fontWeight: 700 }}>{ls.winner}</span>
                          <span style={{ fontSize: 13, color: "var(--ink2,#555)", fontFamily: "monospace" }}>({ls.winner_cc})</span>
                        </div>
                      )}
                    </NewsletterSection>
                    {ns && (
                      <NewsletterSection
                        kicker={`Próxima · Etapa ${ns.stage} / ${cr.total_stages}`}
                        title={`${ns.date} · ${typeES[ns.type] || ns.type}`}
                        sub={`${ns.from} → ${ns.to}${ns.dist_km ? ` · ${ns.dist_km} km` : ""}`}
                      >
                        <div style={{ padding: "8px 0 4px", fontSize: 13, color: "var(--muted,#888)", fontFamily: "monospace" }}>
                          {ns.type === "Mountain stage" ? "⛰️ Etapa reina — podría haber cambios en GC" :
                           ns.type === "Individual time trial" ? "⏱️ Contrarreloj — favorece a los especialistas" :
                           ns.type === "Flat stage" ? "🏁 Etapa llana — probable sprint masivo" :
                           "Etapa en camino."}
                        </div>
                      </NewsletterSection>
                    )}
                  </>
                );
              })()}

              {cr && cr.gc && cr.gc.length > 0 && (
                <NewsletterSection
                  kicker={`${raceFinished ? "Clasificación General final" : "Clasificación General"} — Etapa ${cr.stage}/${cr.total_stages}`}
                  title={raceFinished ? "Top 10 GC final" : "Top 10 GC"}
                  sub={`${raceFinished ? "Campeón" : "Líder"}: ${cr.gc[0].name} (${cr.jersey_name}). Score leyenda: Tour×12, Giro×9, Vuelta×8, Monumentos×4, Mundiales×4; Merckx=100.`}
                >
                  <div className="newsletter-list">
                    {cr.gc.map((r, i) => (
                      <NewsletterRankRow
                        key={r.name}
                        rank={r.rank || i + 1}
                        item={{ ...r, colors: { primary: r.primary, secondary: "#ffffff" } }}
                        alive={new Set()}
                        score={r.time}
                        scoreDisplay={r.time}
                        scoreLabel={i === 0 ? "Tiempo" : "Diferencia"}
                        scoreB={r.legendScore || 0}
                        scoreBLabel="Leyenda"
                        scoreBThreshold={100}
                        meta={`${r.team} · ${r.country}`}
                        note={r.legendScore > 0 ? "Ya suma palmarés histórico" : "Sin grandes títulos todavía"}
                        logo={r.logo}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}

              {cr && (cr.points_leader || cr.kom_leader || cr.young_leader) && (
                <NewsletterSection
                  kicker={raceFinished ? "Maillots finales" : "Líderes de maillot"}
                  title="Puntos · Montaña · Mejor joven"
                  sub={raceFinished ? "Clasificaciones secundarias finales." : "Clasificaciones secundarias en curso."}
                >
                  <div className="newsletter-list">
                    {[
                      { emoji: "🟣", label: "Maglia Ciclamino — Puntos", leader: cr.points_leader, val: l => l.points != null ? `${l.points} pts` : "" },
                      { emoji: "🔵", label: "Maglia Azzurra — Montaña",  leader: cr.kom_leader,    val: l => l.points != null ? `${l.points} pts` : "" },
                      { emoji: "⬜", label: "Maglia Bianca — Mejor joven", leader: cr.young_leader, val: l => l.time || "" },
                    ].filter(x => x.leader).map(({ emoji, label, leader, val }) => {
                      const lgScore = leader.legendScore || 0;
                      return (
                        <div key={label} style={{
                          display: "flex", alignItems: "flex-start", gap: 10,
                          padding: "10px 0", borderBottom: "1px solid var(--rule,#eee)"
                        }}>
                          <span style={{ fontSize: 20, width: 28, flexShrink: 0 }}>{emoji}</span>
                          <img src={leader.logo} alt={leader.country} style={{ width: 20, height: 15, borderRadius: 2, flexShrink: 0, marginTop: 4 }} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 10, fontFamily: "monospace", color: "var(--muted,#888)", textTransform: "uppercase", letterSpacing: ".06em" }}>{label}</div>
                            <div style={{ fontWeight: 600, fontSize: 14 }}>{leader.name}</div>
                            <div style={{ fontSize: 11, color: "var(--muted,#888)", fontFamily: "monospace", marginTop: 1 }}>{leader.team}</div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                              <div style={{ width: 60, height: 4, background: "var(--bar-bg,#dedad6)", borderRadius: 2, overflow: "hidden" }}>
                                <div style={{ width: `${lgScore}%`, height: "100%", background: lgScore > 0 ? "var(--bar-fill,#4a4745)" : "transparent", borderRadius: 2 }} />
                              </div>
                              <span style={{ fontSize: 10, color: "var(--muted,#888)", fontFamily: "monospace" }}>
                                {lgScore > 0 ? `${lgScore.toFixed(0)}/100` : "0/100"}
                              </span>
                            </div>
                          </div>
                          <span style={{ fontFamily: "monospace", fontSize: 14, fontWeight: 700, color: "var(--accent,#b84832)", paddingTop: 2 }}>{val(leader)}</span>
                        </div>
                      );
                    })}
                  </div>
                </NewsletterSection>
              )}

              {cycCurrentRiders.length > 0 && (
                <NewsletterSection
                  kicker="Road to Glory · Actuales"
                  title="Top 10 ciclistas actuales — Score leyenda"
                  sub={`Ordenado por legado acumulado. Umbral top 10 histórico: ${cycLegendThreshold.toFixed(1)} (${cycLegendTop[9]?.name || "N/A"}). Score: Tour×12, Giro×9, Vuelta×8, Monumentos×4, Mundiales×4.`}
                >
                  <div className="newsletter-list">
                    {cycCurrentRiders.map((p, i) => (
                      <NewsletterRankRow
                        key={p.id}
                        rank={i + 1}
                        prevRank={p.prevRank}
                        item={p}
                        alive={new Set()}
                        score={p.legendScore}
                        scoreLabel="Leyenda"
                        threshold={cycLegendThreshold}
                        meta={cycMeta(p)}
                        note={cyclingLegendChaseNote(p)}
                        logo={p.logo}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}

              {cycProspects.length > 0 && (
                <NewsletterSection
                  kicker="Cantera"
                  title="Jóvenes promesa del ciclismo"
                  sub="Sub-29 con mejor palmarés ya acumulado — quién ha empezado fuerte camino del panteón."
                >
                  <div className="newsletter-list">
                    {cycProspects.map((p, i) => (
                      <NewsletterRankRow
                        key={p.id}
                        rank={i + 1}
                        item={p}
                        alive={new Set()}
                        score={p.legendScore}
                        scoreLabel="Leyenda"
                        threshold={cycLegendThreshold}
                        meta={`${p.country} · ${p.age} años`}
                        note={p.note}
                        logo={p.logo}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}

              <NewsletterSection
                kicker="Road Cycling Legends"
                title="Top 10 leyendas del ciclismo"
                sub="Score histórico — Tour de France, Giro d'Italia, Vuelta, Monumentos y Mundiales ponderados."
              >
                <div className="newsletter-list">
                  {cycLegends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={cycMeta(p)}
                      note={cycNote(p)}
                      logo={p.logo}
                      legendActive={p.active}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="sumo" style={sectionStyle("sumo", window.SUMO_DATA?.IMPORTANCE || 8)}>
        {/* ── SUMO ─────────────────────────────────────────── */}
        {window.SUMO_DATA && (() => {
          const SUMO = window.SUMO_DATA;
          const sumoLegends = (SUMO.LEGENDS || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } })).slice(0, 10);
          const banzuke     = SUMO.BANZUKE || [];
          const bashoInfo   = SUMO.BASHO_INFO;
          function bashoLabel(id) {
            if (!id) return "";
            const month = parseInt(id.slice(4));
            const names = {1:"Hatsu (Enero)",3:"Haru (Marzo)",5:"Natsu (Mayo)",7:"Nagoya (Julio)",9:"Aki (Septiembre)",11:"Kyushu (Noviembre)"};
            return `${id.slice(0,4)} ${names[month] || id}`;
          }

          // Top 5 by wins (exclude pure kyujo with 0 wins AND 0 losses)
          const ranked = [...banzuke]
            .filter(w => w.wins > 0 || w.losses > 0)
            .sort((a, b) => b.wins - a.wins);
          const top5 = ranked.slice(0, 5);
          const top5Names = new Set(top5.map(w => w.name));
          // Always include Yokozunas even if outside top 5
          const yokozunas = banzuke.filter(w => w.rankShort === "Yokozuna" && !top5Names.has(w.name));
          const displayList = [...top5, ...yokozunas];

          function recordStr(w) {
            if (w.wins === 0 && w.losses === 0) return `Kyujo (${w.absences}A)`;
            return `${w.wins}W–${w.losses}L${w.absences > 0 ? `–${w.absences}A` : ""}`;
          }
          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Sumo</span>
                  <span>{bashoLabel(SUMO.BASHO_ID)}</span>
                  <span>Actualizado {SUMO.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>Sumo · {bashoLabel(SUMO.BASHO_ID)}</h1>
                  <p>
                    {bashoInfo?.winner
                      ? `Campeón del torneo: ${bashoInfo.winner}. Score de leyendas: Hakuho=100.`
                      : "Score de leyendas: Hakuho=100."}
                  </p>
                </div>
              </header>

              {banzuke.length > 0 && (
                <NewsletterSection
                  kicker={`Clasificación — ${bashoLabel(SUMO.BASHO_ID)}`}
                  title="Top 5 + Yokozunas"
                  sub="Ordenado por victorias. Score de leyendas (Hakuho=100) al lado de cada luchador."
                >
                  <div className="newsletter-list">
                    {top5.length > 0 && (
                      <div style={{ fontSize: 9, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--muted,#888)", fontFamily: "monospace", padding: "4px 0 6px", borderBottom: "2px solid var(--ink,#1a1714)" }}>
                        Top por victorias
                      </div>
                    )}
                    {top5.map((w, i) => {
                      const lgScore = w.legendScore || 0;
                      const isWinner = bashoInfo?.winner === w.name;
                      return (
                        <div key={w.name} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 0", borderBottom: "1px solid var(--rule,#eee)" }}>
                          <span style={{ width: 20, fontSize: 15, color: "var(--muted,#888)", fontVariantNumeric: "tabular-nums", flexShrink: 0, paddingTop: 2 }}>{i + 1}</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, fontSize: 14, display: "flex", alignItems: "center", gap: 6 }}>
                              {w.name}
                              {w.age != null && <span style={{ fontSize: 11, color: "var(--muted,#888)", fontWeight: 400 }}>{w.age} años</span>}
                              {isWinner && <span style={{ fontSize: 12, background: "var(--accent,#b84832)", color: "#fff", borderRadius: 3, padding: "1px 5px", fontWeight: 700 }}>🏆 Campeón</span>}
                            </div>
                            <div style={{ fontSize: 11, color: "var(--muted,#888)", fontFamily: "monospace", marginTop: 1 }}>{w.rankShort}</div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                              <div style={{ width: 70, height: 4, background: "var(--bar-bg,#dedad6)", borderRadius: 2, overflow: "hidden" }}>
                                <div style={{ width: `${lgScore}%`, height: "100%", background: lgScore > 0 ? "var(--bar-fill,#4a4745)" : "transparent", borderRadius: 2 }} />
                              </div>
                              <span style={{ fontSize: 10, color: "var(--muted,#888)", fontFamily: "monospace" }}>
                                {lgScore > 0 ? `${lgScore.toFixed(0)}/100` : "0/100"}
                              </span>
                            </div>
                          </div>
                          <span style={{ fontFamily: "monospace", fontSize: 13, fontWeight: 600, color: "var(--ink,#1a1714)", whiteSpace: "nowrap", paddingTop: 2 }}>
                            {recordStr(w)}
                          </span>
                        </div>
                      );
                    })}
                    {yokozunas.length > 0 && (
                      <div style={{ fontSize: 9, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--muted,#888)", fontFamily: "monospace", padding: "8px 0 6px", borderBottom: "2px solid var(--ink,#1a1714)", marginTop: 4 }}>
                        Yokozunas
                      </div>
                    )}
                    {yokozunas.map(w => {
                      const lgScore = w.legendScore || 0;
                      return (
                        <div key={w.name} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 0", borderBottom: "1px solid var(--rule,#eee)" }}>
                          <span style={{ width: 20, fontSize: 12, flexShrink: 0, paddingTop: 2 }}>Y</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, fontSize: 14, display: "flex", alignItems: "center", gap: 6 }}>
                              {w.name}
                              {w.age != null && <span style={{ fontSize: 11, color: "var(--muted,#888)", fontWeight: 400 }}>{w.age} años</span>}
                            </div>
                            <div style={{ fontSize: 11, color: "var(--muted,#888)", fontFamily: "monospace", marginTop: 1 }}>{w.rankShort}</div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                              <div style={{ width: 70, height: 4, background: "var(--bar-bg,#dedad6)", borderRadius: 2, overflow: "hidden" }}>
                                <div style={{ width: `${lgScore}%`, height: "100%", background: "var(--bar-fill,#4a4745)", borderRadius: 2 }} />
                              </div>
                              <span style={{ fontSize: 10, color: "var(--muted,#888)", fontFamily: "monospace" }}>{lgScore.toFixed(0)}/100</span>
                            </div>
                          </div>
                          <span style={{ fontFamily: "monospace", fontSize: 13, color: "var(--muted,#888)", whiteSpace: "nowrap", paddingTop: 2 }}>
                            {recordStr(w)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </NewsletterSection>
              )}

              <NewsletterSection
                kicker="Road to Glory · Yokozuna Legends"
                title="Top 10 Yokozuna históricos"
                sub="Score basado en yusho (×5 pts) + basho como Yokozuna (×0.5 pts). Hakuho como referencia: 100."
              >
                <div className="newsletter-list">
                  {sumoLegends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`${p.country} · ${p.stats.yok_start ? `Yokozuna ${p.stats.yok_start}–${p.stats.yok_end || "hoy"}` : ""}`}
                      note={`${p.stats.yusho} yusho · ${p.stats.yokozuna_basho} basho como Yokozuna`}
                      logo={p.logo}
                      legendActive={!p.stats?.yok_end}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="f1" style={sectionStyle("f1", window.F1_DATA?.IMPORTANCE || 7)}>
        {/* ── F1 ───────────────────────────────────────────── */}
        {window.F1_DATA && (() => {
          const F1 = window.F1_DATA;
          const drivers      = (F1.DRIVERS      || []).slice(0, 10);
          const f1Prospects  = (F1.PROSPECTS    || []).map(p => ({ ...p, colors: p.colors || { primary: p.primary, secondary: p.secondary } }));
          const constructors = (F1.CONSTRUCTORS || []).slice(0, 5);
          const lastRace     = F1.LAST_RACE;
          const lastWeekend  = F1.LAST_WEEKEND;
          const legends      = (F1.LEGENDS      || []).slice(0, 10);
          const leaderPts    = drivers.length ? drivers[0].points : 1;
          const f1MaxSeason  = F1.MAX_SEASON_PTS || F1.TOTAL_ROUNDS * 25;
          const f1Remaining  = (F1.TOTAL_ROUNDS - F1.ROUND) * 25;
          const f1Threshold  = Math.round(Math.min((drivers[1]?.points || 0) + f1Remaining + 1, f1MaxSeason) / f1MaxSeason * 1000) / 10;
          const f1LegendByName = Object.fromEntries((F1.LEGENDS || []).map(p => [p.name, p.legendScore]));
          const f1DriverByName = Object.fromEntries((F1.DRIVERS || []).map(d => [d.name, d]));
          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Formula 1</span>
                  <span>Season {F1.SEASON} · Round {F1.ROUND}/{F1.TOTAL_ROUNDS}</span>
                  <span>Actualizado {F1.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>F1 {F1.SEASON}</h1>
                  <p>
                    Importancia del campeonato: <strong>{F1.IMPORTANCE}/10</strong>.
                    {drivers.length > 0 && ` Líder: ${drivers[0].name} (${drivers[0].points} pts).`}
                    {lastRace && ` Última carrera: ${lastRace.name}.`}
                  </p>
                </div>
              </header>

              {/* Driver standings */}
              <NewsletterSection
                kicker="Driver Championship"
                title="Campeonato de Pilotos"
                sub={`Barra sobre ${f1MaxSeason} pts máximos. Últ. finde = puntos ganados en ${lastWeekend?.label || lastRace?.name || "el último GP"}${F1.LAST_SPRINT ? " incluyendo sprint." : "."}`}
              >
                <div className="newsletter-list">
                  {drivers.map((d, i) => {
                    const lgScore = f1LegendByName[d.name];
                    const weekendPts = typeof d.lastWeekendPoints === "number" ? d.lastWeekendPoints : null;
                    return (
                    <NewsletterRankRow
                      key={d.name}
                      rank={i + 1}
                      prevRank={d.prevRank}
                      item={{ ...d, colors: { primary: d.primary, secondary: d.secondary } }}
                      alive={new Set()}
                      score={d.score}
                      scoreDisplay={d.points}
                      scoreLabel="Puntos"
                      threshold={f1Threshold}
                      scoreB={weekendPts ?? 0}
                      scoreBDisplay={weekendPts != null ? `+${weekendPts}` : "—"}
                      scoreBLabel="Últ. finde"
                      meta={`F1 · ${d.country} · ${d.team || d.teamCode}`}
                      note={lgScore != null ? `Legend ${lgScore.toFixed(1)}` : null}
                      logo={d.logo}
                    />
                    );
                  })}
                </div>
              </NewsletterSection>

              {/* Constructor standings */}
              <NewsletterSection
                kicker="Constructor Championship"
                title="Campeonato de Constructores"
                sub="Top 5 equipos por puntos."
              >
                <div className="newsletter-list">
                  {constructors.map((c, i) => {
                    const score = Math.round(c.points / Math.max(constructors[0].points, 1) * 100);
                    return (
                      <div key={c.id} className="newsletter-row">
                        <span className="newsletter-row__rank">{String(i + 1).padStart(2, "0")}</span>
                        <span className="newsletter-row__identity" style={{ flex: 1 }}>
                          <span
                            className="newsletter-row__dot"
                            style={{ background: c.primary, border: `1px solid ${c.secondary}` }}
                          />
                          <span className="newsletter-row__copy">
                            <span className="newsletter-row__name">{c.name}</span>
                          </span>
                        </span>
                        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span className="newsletter-bar" style={{ "--pct": `${score}%`, "--clr": c.primary }} />
                          <span style={{ fontSize: 12, fontVariantNumeric: "tabular-nums", minWidth: 40, textAlign: "right" }}>
                            {c.points} pts
                          </span>
                        </span>
                      </div>
                    );
                  })}
                </div>
              </NewsletterSection>

              {/* Last race podium */}
              {lastRace && lastRace.podium && lastRace.podium.length > 0 && (() => {
                const podiumNames = new Set(lastRace.podium.map(p => p.name));
                const champNotInPodium = drivers.slice(0, 2).filter(d => !podiumNames.has(d.name));
                return (
                <NewsletterSection
                  kicker="Última carrera"
                  title={lastRace.name}
                  sub={`${lastRace.circuit} · ${lastRace.date}`}
                >
                  <div className="newsletter-list">
                    {lastRace.podium.map((p, i) => {
                      const dInfo = f1DriverByName[p.name] || {};
                      return (
                      <div key={i} className="newsletter-row">
                        <span className="newsletter-row__rank" style={{ minWidth: 28 }}>{`P${p.position}`}</span>
                        <span className="newsletter-row__identity" style={{ flex: 1 }}>
                          <span className="newsletter-row__dot" style={{ background: p.primary }} />
                          {dInfo.logo && <img src={dInfo.logo} alt={dInfo.country} style={{ width: 20, height: 15, borderRadius: 2, marginRight: 6, flexShrink: 0 }} />}
                          <span className="newsletter-row__copy">
                            <span className="newsletter-row__name">{p.name}</span>
                            <span className="newsletter-row__meta">{p.team || dInfo.team}</span>
                          </span>
                        </span>
                        {p.time && <span style={{ fontSize: 12, color: "var(--ink-2)" }}>{p.time}</span>}
                      </div>
                      );
                    })}
                  </div>
                  {champNotInPodium.length > 0 && (
                    <div style={{ marginTop: 12, fontSize: 12, color: "var(--ink-2,#666)", fontFamily: "monospace" }}>
                      {champNotInPodium.map(d => (
                        <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                          <span style={{ width: 8, height: 8, borderRadius: 2, background: d.primary, flexShrink: 0, display: "inline-block" }} />
                          <img src={d.logo} alt={d.country} style={{ width: 18, height: 13, borderRadius: 2 }} />
                          <span>{d.name}</span>
                          <span style={{ color: "var(--muted,#999)" }}>— {d.points} pts campeonato · no entró en el podio</span>
                        </div>
                      ))}
                    </div>
                  )}
                </NewsletterSection>
                );
              })()}

              {/* Sprint race */}
              {F1.LAST_SPRINT && F1.LAST_SPRINT.podium && F1.LAST_SPRINT.podium.length > 0 && (
                <NewsletterSection
                  kicker="Sprint Race"
                  title={F1.LAST_SPRINT.name}
                  sub={`${F1.LAST_SPRINT.circuit} · ${F1.LAST_SPRINT.date}`}
                >
                  <div className="newsletter-list">
                    {F1.LAST_SPRINT.podium.map((p, i) => {
                      const dInfo = f1DriverByName[p.name] || {};
                      return (
                      <div key={i} className="newsletter-row">
                        <span className="newsletter-row__rank" style={{ minWidth: 28 }}>{`P${p.position}`}</span>
                        <span className="newsletter-row__identity" style={{ flex: 1 }}>
                          <span className="newsletter-row__dot" style={{ background: p.primary }} />
                          {dInfo.logo && <img src={dInfo.logo} alt={dInfo.country} style={{ width: 20, height: 15, borderRadius: 2, marginRight: 6, flexShrink: 0 }} />}
                          <span className="newsletter-row__copy">
                            <span className="newsletter-row__name">{p.name}</span>
                            <span className="newsletter-row__meta">{p.team || dInfo.team}</span>
                          </span>
                        </span>
                      </div>
                      );
                    })}
                  </div>
                </NewsletterSection>
              )}

              {f1Prospects.length > 0 && (
                <NewsletterSection
                  kicker="Cantera"
                  title="Jóvenes promesa F1"
                  sub="Pilotos sub-26 con mejor marcha en el campeonato — quién ha empezado fuerte."
                >
                  <div className="newsletter-list">
                    {f1Prospects.map((p, i) => (
                      <NewsletterRankRow
                        key={p.name}
                        rank={i + 1}
                        item={{ ...p, teamCode: p.country }}
                        alive={new Set()}
                        score={p.score}
                        scoreLabel="Score"
                        meta={`F1 · ${p.team || p.country} · ${p.age} años`}
                        note={p.note}
                        logo={p.logo}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}

              {/* F1 Legends */}
              <NewsletterSection
                kicker="F1 Legends"
                title="Road to Glory · Leyendas de la F1"
                sub="Score histórico: títulos (×15), victorias (×0.5), poles (×0.3), podios (×0.15). Hamilton como referencia: 100."
              >
                <div className="newsletter-list">
                  {legends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`F1 · ${p.country} · ${p.stats.birth}${p.active ? " · 🟢 Activo" : ""}`}
                      note={`${p.stats.titles} títulos · ${p.stats.wins} victorias · ${p.stats.poles} poles`}
                      logo={p.logo}
                      legendActive={p.active}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="indycar" style={sectionStyle("indycar", window.INDYCAR_DATA?.IMPORTANCE || 6.5)}>
        {/* ── IndyCar ─────────────────────────────────────── */}
        {window.INDYCAR_DATA && (() => {
          const IC = window.INDYCAR_DATA;
          const drivers = (IC.DRIVERS || []).slice(0, 10);
          const legends = (IC.LEGENDS || []).slice(0, 10);
          const currentContenders = (IC.CURRENT_CONTENDERS || []).slice(0, 10);
          const icLegendThreshold = IC.LEGEND_THRESHOLD || legends[9]?.legendScore || 0;
          const last = IC.LAST_RACE;
          const maxSeason = IC.MAX_SEASON_PTS || IC.TOTAL_ROUNDS * 54;
          const remaining = (IC.TOTAL_ROUNDS - IC.ROUND) * 54;
          const threshold = Math.round(Math.min((drivers[1]?.points || 0) + remaining + 1, maxSeason) / Math.max(maxSeason, 1) * 1000) / 10;
          const driverByName = Object.fromEntries((IC.DRIVERS || []).map(d => [d.name, d]));
          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>IndyCar</span>
                  <span>Season {IC.SEASON} · Round {IC.ROUND}/{IC.TOTAL_ROUNDS}</span>
                  <span>Actualizado {IC.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>IndyCar · Series Championship {IC.SEASON}</h1>
                  <p>
                    Importancia: <strong>{IC.IMPORTANCE}/10</strong>.
                    {drivers.length > 0 && ` Líder: ${drivers[0].name} (${drivers[0].points} pts).`}
                    {last && ` Última carrera: ${last.name} → ${last.winner}.`}
                  </p>
                </div>
              </header>

              <NewsletterSection
                kicker="Driver Championship"
                title="Campeonato de Pilotos"
                sub={`Barra sobre ${maxSeason} pts máximos estimados. Línea roja = mínimo matemático aproximado para cerrar el título.`}
              >
                <div className="newsletter-list">
                  {drivers.map((d, i) => (
                    <NewsletterRankRow
                      key={d.id || d.name}
                      rank={i + 1}
                      prevRank={d.prevRank}
                      item={{ ...d, colors: { primary: d.primary, secondary: d.secondary } }}
                      alive={new Set()}
                      score={d.score}
                      scoreDisplay={d.points}
                      scoreLabel="Puntos"
                      threshold={threshold}
                      scoreB={d.legendScore || 0}
                      scoreBDisplay={(d.legendScore || 0).toFixed(1)}
                      scoreBLabel="Leyenda"
                      scoreBThreshold={icLegendThreshold}
                      meta={`IndyCar · ${d.country} · ${d.team}`}
                      note={null}
                      logo={d.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              {last && last.podium && last.podium.length > 0 && (
                <NewsletterSection
                  kicker={`Round ${IC.ROUND} · Última carrera`}
                  title={last.name}
                  sub={`${last.circuit || "Resultado"} · ${last.date}`}
                >
                  <div className="newsletter-list">
                    {last.podium.map((p, i) => {
                      const dInfo = driverByName[p.name] || {};
                      return (
                        <div key={`${p.name}-${i}`} className="newsletter-row">
                          <span className="newsletter-row__rank" style={{ minWidth: 28 }}>{`P${p.position || i + 1}`}</span>
                          <span className="newsletter-row__identity" style={{ flex: 1 }}>
                            <span className="newsletter-row__dot" style={{ background: p.primary || dInfo.primary }} />
                            {(p.logo || dInfo.logo) && <img src={p.logo || dInfo.logo} alt={p.country || dInfo.country} style={{ width: 20, height: 15, borderRadius: 2, marginRight: 6, flexShrink: 0 }} />}
                            <span className="newsletter-row__copy">
                              <span className="newsletter-row__name">{p.name}</span>
                              <span className="newsletter-row__meta">{p.team || dInfo.team}</span>
                            </span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </NewsletterSection>
              )}

              {currentContenders.length > 0 && (
                <NewsletterSection
                  kicker="Road to Glory · Actuales"
                  title="Más cerca del Top 10 histórico"
                  sub={`Umbral top 10 histórico: ${icLegendThreshold}.`}
                >
                  <div className="newsletter-list">
                    {currentContenders.map((p, i) => (
                      <NewsletterRankRow
                        key={p.id}
                        rank={i + 1}
                        prevRank={p.prevRank}
                        item={p}
                        alive={new Set()}
                        score={p.legendScore}
                        scoreLabel="Leyenda"
                        threshold={icLegendThreshold}
                        meta={`IndyCar · ${p.country} · ${p.team}`}
                        note={p.gapToTop10 > 0 ? `A ${p.gapToTop10} del Top 10 histórico` : "Ya está en zona Top 10 histórico"}
                        logo={p.logo}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}

              <NewsletterSection
                kicker="Road to Glory · IndyCar"
                title="Top 10 leyendas IndyCar"
                sub="Score histórico: títulos IndyCar/CART (×12), victorias (×0.45), poles (×0.2). A. J. Foyt como referencia: 100."
              >
                <div className="newsletter-list">
                  {legends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      threshold={legends[9]?.legendScore}
                      meta={`IndyCar · ${p.country} · ${p.stats.birth}${p.active ? " · Activo" : ""}`}
                      note={`${p.stats.titles} títulos · ${p.stats.wins} victorias · ${p.stats.poles} poles`}
                      logo={p.logo}
                      legendActive={p.active}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="nascar" style={sectionStyle("nascar", window.NASCAR_DATA?.IMPORTANCE || 6.5)}>
        {/* ── NASCAR ──────────────────────────────────────── */}
        {window.NASCAR_DATA && (() => {
          const NC = window.NASCAR_DATA;
          const playoffRows = (NC.DRIVERS || []).slice(0, 20);
          const legends = (NC.LEGENDS || []).slice(0, 10);
          const currentContenders = (NC.CURRENT_CONTENDERS || []).slice(0, 10);
          const ncLegendThreshold = NC.LEGEND_THRESHOLD || legends[9]?.legendScore || 0;
          const last = NC.LAST_RACE;
          const cutoff = NC.PLAYOFF_CUTOFF;
          const driverByName = Object.fromEntries((NC.DRIVERS || []).map(d => [d.name, d]));
          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>NASCAR Cup Series</span>
                  <span>Season {NC.SEASON} · Race {NC.ROUND}/{NC.TOTAL_ROUNDS}</span>
                  <span>Actualizado {NC.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>NASCAR · Playoff Picture {NC.SEASON}</h1>
                  <p>
                    Importancia: <strong>{NC.IMPORTANCE}/10</strong>.
                    {playoffRows.length > 0 && ` Líder playoff: ${playoffRows[0].name} (${playoffRows[0].wins} victorias, ${playoffRows[0].points} pts).`}
                    {cutoff && ` Corte actual: P16 ${cutoff.driver}.`}
                  </p>
                </div>
              </header>

              <NewsletterSection
                kicker="Playoff Standings"
                title="Top 16 + burbuja"
                sub="Orden playoff: victorias primero y después puntos. La línea roja marca el primer piloto fuera del corte."
              >
                <div className="newsletter-list">
                  {playoffRows.map(d => (
                    <NewsletterRankRow
                      key={d.id || d.name}
                      rank={d.playoffRank}
                      prevRank={d.prevRank}
                      rowClassName={d.playoffRank === 17 ? "newsletter-row--stage-gc-gap" : ""}
                      item={{ ...d, colors: { primary: d.primary, secondary: d.secondary } }}
                      alive={new Set((NC.DRIVERS || []).filter(x => x.playoffRank <= NC.PLAYOFF_FIELD_SIZE).map(x => x.manufacturer))}
                      aliveKey="manufacturer"
                      forceOut={d.playoffRank > NC.PLAYOFF_FIELD_SIZE}
                      score={d.playoffScore}
                      scoreDisplay={d.points}
                      scoreLabel="Puntos"
                      scoreB={d.legendScore || 0}
                      scoreBDisplay={(d.legendScore || 0).toFixed(1)}
                      scoreBLabel="Leyenda"
                      scoreBThreshold={ncLegendThreshold}
                      meta={`NASCAR · ${d.manufacturer} · ${d.team}`}
                      note={d.playoffRank <= NC.PLAYOFF_FIELD_SIZE ? `${d.wins} W · ${d.playoffPoints} playoff pts` : `${d.wins} W · fuera del corte`}
                      logo={d.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              {last && (
                <NewsletterSection
                  kicker="Última carrera"
                  title={last.name}
                  sub={`${last.circuit || "Resultado"} · ${last.date}`}
                >
                  <div className="newsletter-list">
                    {(last.podium || []).map((p, i) => {
                      const dInfo = driverByName[p.name] || {};
                      return (
                        <div key={`${p.name}-${i}`} className="newsletter-row">
                          <span className="newsletter-row__rank" style={{ minWidth: 28 }}>{`P${p.position || i + 1}`}</span>
                          <span className="newsletter-row__identity" style={{ flex: 1 }}>
                            <span className="newsletter-row__dot" style={{ background: p.primary || dInfo.primary }} />
                            {(p.logo || dInfo.logo) && <img src={p.logo || dInfo.logo} alt={p.country || dInfo.country || "USA"} style={{ width: 20, height: 15, borderRadius: 2, marginRight: 6, flexShrink: 0 }} />}
                            <span className="newsletter-row__copy">
                              <span className="newsletter-row__name">{p.name}</span>
                              <span className="newsletter-row__meta">{p.manufacturer || dInfo.manufacturer} · {p.team || dInfo.team}</span>
                            </span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </NewsletterSection>
              )}

              {currentContenders.length > 0 && (
                <NewsletterSection
                  kicker="Road to Glory · Actuales"
                  title="Más cerca del Top 10 histórico"
                  sub={`Umbral top 10 histórico: ${ncLegendThreshold}.`}
                >
                  <div className="newsletter-list">
                    {currentContenders.map((p, i) => (
                      <NewsletterRankRow
                        key={p.id}
                        rank={i + 1}
                        prevRank={p.prevRank}
                        item={p}
                        alive={new Set()}
                        score={p.legendScore}
                        scoreLabel="Leyenda"
                        threshold={ncLegendThreshold}
                        meta={`NASCAR · ${p.manufacturer} · ${p.team}`}
                        note={p.gapToTop10 > 0 ? `A ${p.gapToTop10} del Top 10 histórico` : "Ya está en zona Top 10 histórico"}
                        logo={p.logo}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}

              <NewsletterSection
                kicker="Road to Glory · NASCAR"
                title="Top 10 leyendas NASCAR"
                sub="Score histórico: Cup Series títulos (×13), victorias (×0.35), poles (×0.15). Richard Petty como referencia: 100."
              >
                <div className="newsletter-list">
                  {legends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      threshold={legends[9]?.legendScore}
                      meta={`NASCAR · ${p.country} · ${p.stats.birth}${p.active ? " · Activo" : ""}`}
                      note={`${p.stats.titles} títulos · ${p.stats.wins} victorias · ${p.stats.poles} poles`}
                      logo={p.logo}
                      legendActive={p.active}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="afl" style={sectionStyle("afl", window.AFL_DATA?.IMPORTANCE || 7)}>
        {/* ── AFL ──────────────────────────────────────────── */}
        {window.AFL_DATA && (() => {
          const AFL     = window.AFL_DATA;
          const ladder  = (AFL.LADDER     || []);
          const performers = (AFL.PERFORMERS || []).slice(0, 10);
          const results = (AFL.LAST_ROUND || []);
          const legends = (AFL.LEGENDS    || []).slice(0, 10);
          const currentContenders = (AFL.CURRENT_CONTENDERS || []).slice(0, 10);
          const aflLegendThreshold = AFL.LEGEND_THRESHOLD || legends[9]?.legendScore || 0;
          const aflLogoCodeByTeam = {
            "Adelaide": "adel",
            "Brisbane Lions": "bl",
            "Carlton": "carl",
            "Collingwood": "coll",
            "Essendon": "ess",
            "Fremantle": "fre",
            "Geelong": "geel",
            "Gold Coast": "gc",
            "Greater Western Sydney": "gws",
            "Hawthorn": "haw",
            "Melbourne": "mel",
            "North Melbourne": "nm",
            "Port Adelaide": "pa",
            "Richmond": "rich",
            "St Kilda": "stk",
            "Sydney": "syd",
            "South Melbourne": "syd",
            "West Coast": "wce",
            "Western Bulldogs": "wb",
          };
          const aflTeamLogo = team => {
            const code = aflLogoCodeByTeam[team] || aflLogoCodeByTeam[String(team || "").trim()];
            return code ? `https://a.espncdn.com/i/teamlogos/afl/500/${code}.png` : null;
          };
          const aflTeamByName = Object.fromEntries(ladder.map(t => [t.name, t]));
          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>AFL</span>
                  <span>Season {AFL.SEASON} · Round {AFL.ROUND}</span>
                  <span>Actualizado {AFL.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>AFL · {AFL.SEASON} Season Ladder</h1>
                  <p>
                    Importancia: <strong>{AFL.IMPORTANCE}/10</strong>.
                    {ladder.length > 0 && ` Líder: ${ladder[0].name} (W${ladder[0].wins}-L${ladder[0].losses}).`}
                    {` Top 8 clasifican para finals.`}
                  </p>
                </div>
              </header>

              {/* Full ladder */}
              <NewsletterSection
                kicker="AFL Ladder"
                title="Clasificación completa"
                sub={`Tras la ronda ${AFL.ROUND}. Los 8 primeros disputan las finals.`}
              >
                <div className="afl-ladder">
                  <div className="afl-ladder__head">
                    <span>#</span>
                    <span>Equipo</span>
                    <span>W</span>
                    <span>L</span>
                    <span>D</span>
                    <span>Pts</span>
                    <span>%</span>
                  </div>
                  {ladder.map((t, i) => {
                    const pr = t.prevRank;
                    const diff2 = typeof pr === "number" ? pr - (i+1) : null;
                    const chipStyle = (bg) => ({ display:"inline-flex", alignItems:"center", justifyContent:"center",
                      fontSize: 10, fontWeight: 700, lineHeight: 1, color: "#fff",
                      background: bg, borderRadius: 3, padding: "2px 4px", minWidth: 22 });
                    const changeEl = diff2 != null && diff2 !== 0
                      ? <span style={chipStyle(diff2 > 0 ? "#2a7a2a" : "#a02020")}>{diff2 > 0 ? `↑${diff2}` : `↓${-diff2}`}</span>
                      : null;
                    const isFinals = i < 8;
                    return (
                      <div key={t.name} className={`afl-ladder__row ${isFinals ? "afl-ladder__row--finals" : ""}`}>
                        <span className="afl-ladder__rank">
                          <span>{i + 1}</span>
                          {changeEl}
                        </span>
                        <span className="afl-ladder__team">
                          <TeamSwatch colors={{ primary: t.primary, secondary: t.secondary }} code={t.name} logo={aflTeamLogo(t.name)} />
                          <span className="afl-ladder__name">
                            {t.name}
                            {isFinals && <span>Finals</span>}
                          </span>
                        </span>
                        <span>{t.wins}</span>
                        <span>{t.losses}</span>
                        <span>{t.draws}</span>
                        <span>{t.pts}</span>
                        <span>{t.percentage.toFixed(1)}</span>
                      </div>
                    );
                  })}
                </div>
              </NewsletterSection>

              {performers.length > 0 && (
                <NewsletterSection
                  kicker="AFL Season Performers"
                  title="Top 10 performers de la temporada"
                  sub="Score mixto de temporada: disposals, contested possessions, clearances, goles, tackles, marks, hit-outs y assists."
                >
                  <div className="newsletter-list">
                    {performers.map((p, i) => (
                      <NewsletterRankRow
                        key={p.id || p.name}
                        rank={i + 1}
                        prevRank={p.prevRank}
                        item={p}
                        alive={new Set()}
                        score={p.score}
                        scoreLabel="Score"
                        scoreB={p.legendScore || 0}
                        scoreBDisplay={(p.legendScore || 0).toFixed(1)}
                        scoreBLabel="Leyenda"
                        scoreBThreshold={aflLegendThreshold}
                        meta={`AFL · ${p.teamCode} · ${p.team}`}
                        note={`${p.stats.games} GM · ${p.stats.disposals} disp · ${p.stats.goals} goles · ${p.stats.clearances} clearances`}
                        logo={aflTeamLogo(p.team)}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}

              {currentContenders.length > 0 && (
                <NewsletterSection
                  kicker="Road to Glory · Actuales"
                  title="Más cerca del Top 10 histórico"
                  sub={`Umbral top 10 histórico: ${aflLegendThreshold}.`}
                >
                  <div className="newsletter-list">
                    {currentContenders.map((p, i) => (
                      <NewsletterRankRow
                        key={p.id}
                        rank={i + 1}
                        prevRank={p.prevRank}
                        item={p}
                        alive={new Set()}
                        score={p.legendScore}
                        scoreLabel="Leyenda"
                        threshold={aflLegendThreshold}
                        meta={`AFL · ${p.teamCode} · ${p.team}`}
                        note={p.gapToTop10 > 0 ? `A ${p.gapToTop10} del Top 10 histórico` : "Ya está en zona Top 10 histórico"}
                        logo={aflTeamLogo(p.team)}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}

              {/* Last round results */}
              {results.length > 0 && (
                <NewsletterSection
                  kicker={`Round ${AFL.ROUND}`}
                  title={`Resultados — Ronda ${AFL.ROUND}`}
                  sub="Resultados completos de la última ronda disputada."
                >
                  <div className="afl-results-grid">
                    {results.map((g, i) => {
                      const home = aflTeamByName[g.hteam] || { primary: g.hprimary, secondary: "#fff" };
                      const away = aflTeamByName[g.ateam] || { primary: g.aprimary, secondary: "#fff" };
                      return (
                      <div key={i} className="afl-match">
                        <span className={`afl-match__team ${g.winner === g.hteam ? "afl-match__team--winner" : ""}`}>
                          <TeamSwatch colors={{ primary: home.primary, secondary: home.secondary }} code={g.hteam} logo={aflTeamLogo(g.hteam)} />
                          <span>{g.hteam}</span>
                        </span>
                        <span className="afl-match__score">
                          <strong>{g.hscore}</strong>
                          <span>–</span>
                          <strong>{g.ascore}</strong>
                        </span>
                        <span className={`afl-match__team afl-match__team--away ${g.winner === g.ateam ? "afl-match__team--winner" : ""}`}>
                          <span>{g.ateam}</span>
                          <TeamSwatch colors={{ primary: away.primary, secondary: away.secondary }} code={g.ateam} logo={aflTeamLogo(g.ateam)} />
                        </span>
                        <span className="afl-match__date">{g.date}</span>
                      </div>
                      );
                    })}
                  </div>
                </NewsletterSection>
              )}

              {/* AFL Legends */}
              <NewsletterSection
                kicker="Road to Glory · VFL/AFL"
                title="Top 10 leyendas del AFL"
                sub="Score histórico: premiaciones (×8), Brownlow Medals (×5), selecciones All-Australian (×1.5). Bartlett como referencia: 100."
              >
                <div className="newsletter-list">
                  {legends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      threshold={legends[9]?.legendScore}
                      meta={`AFL · ${p.teamCode} · ${p.stats.birth}`}
                      note={`${p.stats.flags} premios · ${p.stats.brownlow} Brownlow · ${p.stats.all_aus} All-Aus`}
                      logo={aflTeamLogo(p.teamCode)}
                      legendActive={p.active}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="golf" style={sectionStyle("golf", window.GOLF_DATA?.IMPORTANCE || 5)}>
        {/* ── GOLF ─────────────────────────────────────────── */}
        {window.GOLF_DATA && (() => {
          const GOLF = window.GOLF_DATA;
          const major = GOLF.CURRENT_MAJOR || {};
          const current = (GOLF.CURRENT || []).slice(0, 10);
          const road = (GOLF.ROAD_TO_GLORY || []).slice(0, 10);
          const legends = (GOLF.LEGENDS || []).slice(0, 10);
          const threshold = GOLF.LEGEND_THRESHOLD || legends[9]?.legendScore || 0;
          const stateLabel = major.state === "live"
            ? `Ronda ${major.round || 1} en juego`
            : major.state === "upcoming"
              ? `Empieza en ${major.daysToStart} día${major.daysToStart === 1 ? "" : "s"}`
              : "Último major completado";
          const majorTour = "Men's Major";
          const golfMeta = p => `${p.stats?.tour || p.teamCode} · ${p.country}`;
          const currentNote = p => `${p.stats?.majors || 0} majors · ${p.stats?.eliteWins || 0} victorias élite · ${p.stats?.majorTop10 || 0} top-10 major`;
          const legendNote = p => `${p.stats?.majors || 0} majors · ${p.stats?.wins || 0} victorias · dominio ${p.stats?.dominance || 0}`;
          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Golf Tracker</span>
                  <span>{majorTour}</span>
                  <span>Actualizado {GOLF.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>Golf Majors</h1>
                  <p>
                    Major masculino activo o próximo, top actuales PGA y carrera histórica hacia el top 10.
                    Score leyenda: majors, victorias y dominio/#1.
                  </p>
                </div>
              </header>

              <NewsletterSection
                kicker={`${majorTour} · ${major.state || "major"}`}
                title={major.name || "Major Championship"}
                sub={`${stateLabel}. ${major.startLabel || ""}–${major.endLabel || ""} · ${major.venue || ""}${major.location ? ` · ${major.location}` : ""}. Defiende: ${major.defending || "N/A"}.`}
              >
                {major.leaderboard && major.leaderboard.length > 0 ? (
                  <div className="newsletter-list">
                    {major.leaderboard.slice(0, 10).map((row, i) => (
                      <div key={`${row.rank}-${row.name}`} className="newsletter-row">
                        <span className="newsletter-row__rank">{String(row.rank || i + 1).padStart(2, "0")}</span>
                        <span className="newsletter-row__identity" style={{ flex: 1 }}>
                          <span className="newsletter-row__dot" style={{ background: "#2f6b3f" }} />
                          <span className="newsletter-row__copy">
                            <span className="newsletter-row__name">{row.name}</span>
                            <span className="newsletter-row__meta">{row.today ? `Hoy ${row.today}` : major.surface}</span>
                          </span>
                        </span>
                        <span className="newsletter-row__score">
                          <span className="newsletter-row__score-label">Score</span>
                          <span className="newsletter-row__score-value">{row.score || "-"}</span>
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="newsletter-list">
                    {(major.favorites || []).map((name, i) => (
                      <div key={name} className="newsletter-row">
                        <span className="newsletter-row__rank">{String(i + 1).padStart(2, "0")}</span>
                        <span className="newsletter-row__identity" style={{ flex: 1 }}>
                          <span className="newsletter-row__dot" style={{ background: "#2f6b3f" }} />
                          <span className="newsletter-row__copy">
                            <span className="newsletter-row__name">{name}</span>
                            <span className="newsletter-row__meta">Favorito Hermes · {major.surface}</span>
                          </span>
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </NewsletterSection>

              <NewsletterSection
                kicker="Golf · Actuales"
                title="Top 10 golfistas actuales"
                sub="Score activo PGA: ranking, forma de majors, victorias élite y consistencia reciente."
              >
                <div className="newsletter-list">
                  {current.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.activeScore}
                      scoreLabel="Nivel"
                      scoreB={p.legendScore}
                      scoreBDisplay={p.legendScore.toFixed(1)}
                      scoreBLabel="Leyenda"
                      scoreBThreshold={threshold}
                      meta={golfMeta(p)}
                      note={currentNote(p)}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="Road to Glory"
                title="Top 10 golfistas Road to Glory"
                sub={`Umbral top 10 histórico: ${threshold.toFixed(1)}. Ordenado por cercanía al territorio de leyenda.`}
              >
                <div className="newsletter-list">
                  {road.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Leyenda"
                      threshold={threshold}
                      meta={golfMeta(p)}
                      note={p.note || (p.gapToTop10 > 0 ? `A ${p.gapToTop10} del top 10 histórico` : "Ya está en zona top 10 histórico")}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="Golf Legends"
                title="Top 10 golfistas leyendas"
                sub="Score histórico: majors (×12), victorias (×0.45) y dominio mundial/#1 (×0.10)."
              >
                <div className="newsletter-list">
                  {legends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      threshold={threshold}
                      meta={`${p.stats?.tour || p.teamCode} · ${p.country}${p.active ? " · Activo" : ""}`}
                      note={legendNote(p)}
                      logo={p.logo}
                      legendActive={p.active}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="motogp" style={sectionStyle("motogp", window.MOTOGP_DATA?.IMPORTANCE || 7)}>
        {/* ── MotoGP ───────────────────────────────────────── */}
        {window.MOTOGP_DATA && (() => {
          const MG         = window.MOTOGP_DATA;
          const riders     = (MG.RIDERS  || []).slice(0, 10);
          const mgProspects = (MG.PROSPECTS || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } }));
          const legends    = (MG.LEGENDS || []).slice(0, 10);
          const last       = MG.LAST_RACE;
          const mgMaxSeason = MG.MAX_SEASON_PTS || MG.TOTAL_ROUNDS * 25;
          const mgRemaining = (MG.TOTAL_ROUNDS - MG.ROUND) * 25;
          const mgThreshold = Math.round(Math.min((riders[1]?.points || 0) + mgRemaining + 1, mgMaxSeason) / mgMaxSeason * 1000) / 10;
          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>MotoGP</span>
                  <span>Season {MG.SEASON} · Round {MG.ROUND}/{MG.TOTAL_ROUNDS}</span>
                  <span>Actualizado {MG.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>MotoGP · World Championship {MG.SEASON}</h1>
                  <p>
                    Importancia: <strong>{MG.IMPORTANCE}/10</strong>.
                    {riders.length > 0 && ` Líder: ${riders[0].name} (${riders[0].points} pts).`}
                    {last && ` Última carrera: ${last.name} → ${last.winner}.`}
                  </p>
                </div>
              </header>

              <NewsletterSection
                kicker="Rider Championship"
                title="Campeonato de Pilotos"
                sub={`Barra sobre ${mgMaxSeason} pts máximos. Línea roja = mínimo para ser campeón matemático (2º + puntos restantes + 1).`}
              >
                <div className="newsletter-list">
                  {riders.map((r, i) => (
                    <NewsletterRankRow
                      key={r.name}
                      rank={i + 1}
                      prevRank={r.prevRank}
                      item={{ ...r, colors: { primary: r.primary, secondary: r.secondary } }}
                      alive={new Set()}
                      score={r.score}
                      scoreDisplay={r.points}
                      scoreLabel="Puntos"
                      threshold={mgThreshold}
                      meta={`MotoGP · ${r.country} · ${r.bike}`}
                      note={null}
                      logo={r.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              {last && (
                <NewsletterSection
                  kicker={`Round ${last.round} · Última carrera`}
                  title={last.name}
                  sub={last.bike ? `${last.bike}` : "Resultado GP"}
                >
                  <div className="newsletter-list">
                    {(last.podium || [{ pos: 1, name: last.winner, country: last.country, logo: null, bike: last.bike, primary: last.primary }]).map((p, i) => (
                      <div key={i} className="newsletter-row">
                        <span className="newsletter-row__rank" style={{ minWidth: 28 }}>{`P${p.pos || p.position || i + 1}`}</span>
                        <span className="newsletter-row__identity" style={{ flex: 1 }}>
                          <span className="newsletter-row__dot" style={{ background: p.primary || last.primary }} />
                          {p.logo && <img src={p.logo} alt={p.country} style={{ width: 20, height: 15, borderRadius: 2, marginRight: 6, flexShrink: 0 }} />}
                          <span className="newsletter-row__copy">
                            <span className="newsletter-row__name">{p.name}</span>
                            <span className="newsletter-row__meta">{p.bike || last.bike}</span>
                          </span>
                        </span>
                      </div>
                    ))}
                  </div>
                </NewsletterSection>
              )}

              {mgProspects.length > 0 && (
                <NewsletterSection
                  kicker="Cantera"
                  title="Jóvenes promesa MotoGP"
                  sub="Pilotos sub-26 con mejor marcha en el Mundial — quién ha empezado fuerte."
                >
                  <div className="newsletter-list">
                    {mgProspects.map((p, i) => (
                      <NewsletterRankRow
                        key={p.name}
                        rank={i + 1}
                        item={{ ...p, teamCode: p.country }}
                        alive={new Set()}
                        score={p.score}
                        scoreLabel="Score"
                        meta={`MotoGP · ${p.bike || p.country} · ${p.age} años`}
                        note={p.note}
                        logo={p.logo}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}

              <NewsletterSection
                kicker="MotoGP Legends"
                title="Road to Glory · Leyendas de MotoGP"
                sub="Score histórico (clase premier): títulos 500cc/MotoGP (×10), victorias (×0.2), poles (×0.1). Agostini como referencia: 100."
              >
                <div className="newsletter-list">
                  {legends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      prevRank={p.prevRank}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`MotoGP · ${p.country} · ${p.stats.birth}${p.active ? " · 🟢 Activo" : ""}`}
                      note={`${p.stats.titles} títulos · ${p.stats.wins} victorias · ${p.stats.poles} poles`}
                      logo={p.logo}
                      legendActive={p.active}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="rugby" style={sectionStyle("rugby", window.RUGBY_DATA?.IMPORTANCE || 3)}>
        {/* ── RUGBY ─────────────────────────────────────────── */}
        {window.RUGBY_DATA && (() => {
          const RUG = window.RUGBY_DATA;
          const teams = [...(RUG.TEAMS || [])].sort((a, b) => b.elo - a.elo).slice(0, 10);
          const dynasties = (RUG.ROAD_TO_GLORY?.dynasties || []).slice(0, 10);
          const dynastyThreshold = RUG.ROAD_TO_GLORY?.dynastyThreshold || 73;

          function wcLabel(count) {
            return `${count} Mundial${count === 1 ? "" : "es"}`;
          }

          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Rugby Tracker</span>
                  <span>Hermes Elo · desde 1871</span>
                  <span>Actualizado {RUG.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>Rugby Union</h1>
                  <p>
                    Top 10 por Hermes Elo y legado de selecciones: rachas largas en la cima
                    y Mundiales conquistados dentro de cada época.
                  </p>
                </div>
              </header>

              <NewsletterSection
                kicker="Rugby Elo"
                title="Top 10 selecciones — Elo actual"
                sub={`Modelo propio desde 1871: ${RUG.SOURCE?.matches || 0} partidos y ${RUG.SOURCE?.teams || 0} selecciones hasta ${RUG.SOURCE?.through || RUG.UPDATED}. El ranking actual aplica decay por inactividad; las dinastías usan Elo histórico raw.`}
              >
                <div className="newsletter-list">
                  {teams.map((team, i) => (
                    <NewsletterRankRow
                      key={team.teamCode}
                      rank={i + 1}
                      item={team}
                      alive={new Set()}
                      score={team.elo}
                      scoreDisplay={team.elo.toFixed(2)}
                      scoreLabel="Elo"
                      scoreB={team.worldCups}
                      scoreBDisplay={team.worldCups}
                      scoreBLabel="Mundiales"
                      meta={`Rugby Union · ${team.country}`}
                      note={`${wcLabel(team.worldCups)} · ${team.note}`}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="Road to Glory"
                title="Dinastías de Elo"
                sub={`Umbral top 10: ${dynastyThreshold.toFixed(1)}. Score: años como #1 ajustados por densidad de tests + Mundiales ganados en la época.`}
              >
                <div className="newsletter-list">
                  {dynasties.map((team, i) => (
                    <NewsletterRankRow
                      key={`${team.teamCode}-${team.era}`}
                      rank={i + 1}
                      item={team}
                      alive={new Set()}
                      score={team.dynastyScore}
                      scoreLabel="Dynasty"
                      threshold={dynastyThreshold}
                      meta={`${team.era} · ${team.weeksNo1} semanas #1/Elo · ${team.matchCount || 0} tests`}
                      note={`${wcLabel(team.worldCups)} en la época: ${team.worldCupYears}. ${team.note}`}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="football" style={sectionStyle("football", window.FOOTBALL_DATA?.IMPORTANCE || 6)}>
        {/* ── FÚTBOL SELECCIONES ───────────────────────────── */}
        {window.FOOTBALL_DATA && (() => {
          const FTB = window.FOOTBALL_DATA;
          const teams = [...(FTB.TEAMS || [])].sort((a, b) => b.elo - a.elo).slice(0, 10);
          const contenders = (FTB.ROAD_TO_GLORY?.currentContenders || []).slice(0, 10);
          const dynasties = (FTB.ROAD_TO_GLORY?.dynasties || []).slice(0, 10);
          const dynastyThreshold = FTB.ROAD_TO_GLORY?.dynastyThreshold || dynasties[9]?.dynastyScore || 70;
          const rawDynastyThreshold = FTB.ROAD_TO_GLORY?.rawDynastyThreshold || 0;
          const wc = FTB.WORLD_CUP_2026;
          const wcGroupByCode = {};
          if (wc?.groups) Object.entries(wc.groups).forEach(([code, info]) => { wcGroupByCode[code] = info; });
          const topCodes = new Set(teams.map(t => t.teamCode));

          function trophyLabel(wc, continental) {
            const parts = [];
            if (wc) parts.push(`${wc} Mundial${wc === 1 ? "" : "es"}`);
            if (continental) parts.push(`${continental} continental${continental === 1 ? "" : "es"}`);
            return parts.length ? parts.join(" · ") : "Sin grandes títulos en la era";
          }

          function nextMatchNote(team) {
            const nm = team.nextMatch;
            if (!nm || !nm.opponent) return null;
            const d = nm.date?.substring(5).replace("-", "/");
            const place = nm.city ? ` · ${nm.city}` : "";
            return `Próximo: vs ${nm.opponent} · ${d}${place}`;
          }

          function wcMatchDate(dateStr) {
            const months = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
            const [, m, d] = dateStr.split("-");
            return `${parseInt(d)} ${months[parseInt(m) - 1]}`;
          }

          function eloChipStyle(elo) {
            if (!elo) return { bg: "#f0ede8", fg: "#999" };
            if (elo >= 2000) return { bg: "#dcefe2", fg: "#1f7a3d" };
            if (elo >= 1900) return { bg: "#e8efdc", fg: "#5f7d1e" };
            if (elo >= 1800) return { bg: "#f5ead4", fg: "#a86513" };
            if (elo >= 1700) return { bg: "#fde8d8", fg: "#c05a20" };
            return { bg: "#f8ded9", fg: "#c92d2d" };
          }

          function deltaChipStyle(delta) {
            if (delta >= 6)  return { bg: "#dcefe2", fg: "#1f7a3d" };
            if (delta > 0)   return { bg: "#e8efdc", fg: "#5f7d1e" };
            if (delta === 0) return { bg: "#f0ede8", fg: "#888" };
            if (delta > -6)  return { bg: "#f5ead4", fg: "#a86513" };
            return { bg: "#f8ded9", fg: "#c92d2d" };
          }

          const chipBase = {
            display: "inline-flex", alignItems: "center",
            fontSize: 10, fontFamily: "monospace", fontWeight: 700,
            padding: "1px 5px", borderRadius: 3, verticalAlign: "middle",
          };

          const matchRowStyle = {
            display: "flex", alignItems: "center", gap: 8,
            padding: "7px 0", borderTop: "1px solid var(--border,#e0dcd5)",
            fontSize: 13,
          };

          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Fútbol Selecciones</span>
                  <span>Hermes Elo · masculino</span>
                  <span>Actualizado {FTB.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>Fútbol de Selecciones</h1>
                  <p>
                    Top 10 masculino por rating Elo y dinastías históricas.
                    {wc && <> <strong>Mundial 2026</strong> — {wc.hosts} · del {wc.startDate} al {wc.finalDate}.</>}
                  </p>
                </div>
              </header>

              {wc && wc.upcomingMatches && wc.upcomingMatches.length > 0 && (
                <NewsletterSection
                  kicker={`Mundial 2026 · ${wc.phase === "pre_tournament" ? "Arranca mañana" : "En curso"}`}
                  title="Próximos partidos — Top 10 Elo"
                  sub={`${wc.hosts} · 48 selecciones · Fase de grupos`}
                >
                  {[1, 2].map(round => {
                    const roundMatches = wc.upcomingMatches.filter(
                      m => m.round === round && (topCodes.has(m.home) || topCodes.has(m.away))
                    );
                    if (!roundMatches.length) return null;
                    return (
                      <React.Fragment key={round}>
                        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase",
                          color: "var(--muted,#888)", padding: "10px 0 4px", marginTop: round === 2 ? 12 : 0 }}>
                          Jornada {round}
                        </div>
                        {roundMatches.map((m, i) => {
                          const hc = eloChipStyle(m.homeElo);
                          const ac = eloChipStyle(m.awayElo);
                          return (
                            <div key={i} style={matchRowStyle}>
                              <span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--muted,#888)", minWidth: 70, flexShrink: 0 }}>
                                {wcMatchDate(m.date)} · {m.timeET}
                              </span>
                              <span style={{ flex: 1, display: "flex", alignItems: "center", gap: 5, flexWrap: "wrap" }}>
                                <span style={{ fontWeight: 700 }}>{m.homeName}</span>
                                {m.homeElo && <span style={{ ...chipBase, background: hc.bg, color: hc.fg }}>{m.homeElo}</span>}
                                <span style={{ color: "var(--muted,#888)", fontSize: 11 }}>vs</span>
                                <span style={{ fontWeight: 700 }}>{m.awayName}</span>
                                {m.awayElo && <span style={{ ...chipBase, background: ac.bg, color: ac.fg }}>{m.awayElo}</span>}
                              </span>
                              <span style={{ fontSize: 10, fontFamily: "monospace", fontWeight: 700,
                                background: "var(--ink,#1a1714)", color: "var(--paper,#faf9f7)",
                                padding: "2px 6px", borderRadius: 3, letterSpacing: "0.05em", flexShrink: 0 }}>
                                Gr.{m.group}
                              </span>
                              <span style={{ fontSize: 11, color: "var(--muted,#888)", minWidth: 110, textAlign: "right", flexShrink: 0 }}>
                                {m.city}
                              </span>
                            </div>
                          );
                        })}
                      </React.Fragment>
                    );
                  })}
                </NewsletterSection>
              )}

              <NewsletterSection
                kicker="Football Elo"
                title="Top 10 selecciones — Ranking Elo"
                sub={`Snapshot Hermes basado en ratings tipo World Football Elo / MoreElo. Fuente: ${FTB.SOURCE?.name || "Elo snapshot"}.`}
              >
                <div className="newsletter-list">
                  {teams.map((team, i) => (
                    <NewsletterRankRow
                      key={team.teamCode}
                      rank={i + 1}
                      item={team}
                      alive={new Set()}
                      score={team.eloScore}
                      scoreDisplay={team.elo}
                      scoreLabel="Elo"
                      scoreB={team.worldCups}
                      scoreBDisplay={team.worldCups}
                      scoreBLabel="Mundiales"
                      meta={wcGroupByCode[team.teamCode]
                        ? `Grupo ${wcGroupByCode[team.teamCode].group} · ${wcGroupByCode[team.teamCode].groupTeams.join(", ")}`
                        : `Selecciones · ${team.country}`}
                      note={[nextMatchNote(team), trophyLabel(team.worldCups, team.continentalTitles)].filter(Boolean).join(" · ")}
                      logo={team.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="Road to Glory · Actual"
                title="Top 10 selecciones con potencial dinástico"
                sub={`Quién puede meterse en el top 10 de dinastías. Umbral bruto estimado: ${rawDynastyThreshold.toFixed(1)}; score combina Elo actual, años de ciclo, títulos recientes, finales y curva generacional.`}
              >
                <div className="newsletter-list">
                  {contenders.map((team, i) => (
                    <NewsletterRankRow
                      key={team.id}
                      rank={i + 1}
                      item={team}
                      alive={new Set()}
                      score={team.dynastyPotential}
                      scoreLabel="Potencial"
                      threshold={100}
                      scoreB={team.eloScore}
                      scoreBDisplay={team.elo}
                      scoreBLabel="Elo"
                      meta={`Ciclo ${team.cycleYears} años · ${team.country}`}
                      note={`${trophyLabel(team.currentWorldCups, team.currentContinentalTitles)} · ${team.recentFinals} finales recientes. ${team.note}`}
                      logo={team.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="Road to Glory"
                title="Top 10 dinastías de selecciones"
                sub={`Umbral top 10: ${dynastyThreshold.toFixed(1)}. Score: años #1/Elo + Mundiales + títulos continentales + pico Elo.`}
              >
                <div className="newsletter-list">
                  {dynasties.map((team, i) => (
                    <NewsletterRankRow
                      key={team.id}
                      rank={i + 1}
                      item={team}
                      alive={new Set()}
                      score={team.dynastyScore}
                      scoreLabel="Dynasty"
                      threshold={dynastyThreshold}
                      meta={`${team.era} · ${team.weeksNo1} semanas #1/Elo · pico ${team.peakElo}`}
                      note={`${trophyLabel(team.worldCups, team.continentalTitles)}. ${team.note}`}
                      logo={team.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="cricket" style={sectionStyle("cricket", window.CRICKET_DATA?.IMPORTANCE || 4)}>
        {/* ── CRICKET ───────────────────────────────────────── */}
        {window.CRICKET_DATA && (() => {
          const CRI = window.CRICKET_DATA;
          const players = CRI.PLAYERS || [];
          const formatGroups = [
            ["Test", CRI.FORMAT_KINGS?.test || []],
            ["ODI", CRI.FORMAT_KINGS?.odi || []],
            ["T20", CRI.FORMAT_KINGS?.t20 || []],
          ];
          const wtc = CRI.WTC?.standings || [];
          const wtcRecent = CRI.WTC?.recentMatches || [];
          const wtcUpcoming = CRI.WTC?.upcomingMatches || [];
          const wtcPlayers = CRI.WTC?.players || [];
          const trophies = CRI.TROPHIES || [];
          const road = CRI.ROAD_TO_GLORY?.players || [];
          const legendThreshold = CRI.ROAD_TO_GLORY?.playerThreshold || 79;
          const wtcThreshold = wtc[1]?.pct || 60;

          function cricketMeta(p) {
            const age = p.birth ? ` · ${new Date().getFullYear() - p.birth} años` : "";
            return `Cricket · ${p.country || p.teamCode}${p.role ? ` · ${p.role}` : ""}${age}`;
          }

          function cricketNote(p) {
            const s = p.stats || {};
            return `Test ${s.test ?? "-"} · ODI ${s.odi ?? "-"} · T20 ${s.t20 ?? "-"} · Franq. ${s.franchise ?? "-"}`;
          }

          const wtcMatchRow = {
            display: "grid",
            gridTemplateColumns: "78px minmax(0,1fr)",
            columnGap: 10,
            rowGap: 2,
            alignItems: "center",
            padding: "8px 0",
            borderTop: "1px solid var(--border,#e0dcd5)",
            fontSize: 12,
          };

          function wtcMatchLine(m) {
            return `${m.match} · ${m.home} v ${m.away}`;
          }

          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Cricket Tracker</span>
                  <span>All formats · Test / ODI / T20</span>
                  <span>Actualizado {CRI.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>Cricket World Tracker</h1>
                  <p>
                    Ranking multi-formato de jugadores actuales, reyes por formato,
                    carrera WTC y legado ICC de selecciones.
                  </p>
                </div>
              </header>

              <NewsletterSection
                kicker="All-Format Crown"
                title="Top 10 jugadores multi-formato"
                sub="Score Hermes: Test 34%, ODI 24%, T20I 18%, franquicias 14%, bonus ICC 10%. La segunda métrica mide legado histórico."
              >
                <div className="newsletter-list">
                  {players.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      item={p}
                      alive={new Set()}
                      score={p.score}
                      scoreDisplay={p.score.toFixed(1)}
                      scoreLabel="All-format"
                      scoreB={p.legendScore}
                      scoreBLabel="Leyenda"
                      scoreBThreshold={legendThreshold}
                      meta={cricketMeta(p)}
                      note={cricketNote(p)}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="Format Kings"
                title="Top 5 por formato"
                sub="Tres lecturas separadas para no mezclar un monstruo Test con un especialista T20."
              >
                <div className="cricket-format-grid">
                  {formatGroups.map(([label, rows]) => (
                    <div className="cricket-format" key={label}>
                      <div className="cricket-format__head">{label}</div>
                      <div className="newsletter-list">
                        {rows.slice(0, 5).map((p, i) => (
                          <NewsletterRankRow
                            key={`${label}-${p.id}`}
                            rank={i + 1}
                            item={p}
                            alive={new Set()}
                            score={p.score}
                            scoreDisplay={p.score.toFixed(1)}
                            scoreLabel={label}
                            meta={`${p.country} · ${p.role}`}
                            note={label === "T20" ? `T20I ${p.stats.t20} · Franq. ${p.stats.franchise}` : `${label} score ${p.stats[label.toLowerCase()]}`}
                            logo={p.logo}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="World Test Championship"
                title={`WTC Race ${CRI.WTC?.cycle || ""}`}
                sub={`${CRI.WTC?.sourceNote || "Tabla WTC actual."} PCT como score y línea roja aproximada del corte actual de final.`}
              >
                <div className="newsletter-list">
                  {wtc.map((team, i) => (
                    <NewsletterRankRow
                      key={team.teamCode}
                      rank={i + 1}
                      item={team}
                      alive={new Set()}
                      score={team.pct}
                      scoreDisplay={`${team.pct.toFixed(1)}%`}
                      scoreLabel="PCT"
                      threshold={wtcThreshold}
                      meta={`WTC · ${team.played} Tests · ${team.points} pts`}
                      note={`${team.won}V-${team.lost}D-${team.drawn}E. ${team.note}`}
                      logo={team.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="WTC Fixture Board"
                title="Últimos 5 y próximos 5 Tests WTC"
                sub="Resultados recientes y calendario inmediato del ciclo 2025-27."
              >
                <div className="cricket-format-grid">
                  <div className="cricket-format">
                    <div className="cricket-format__head">Últimos 5</div>
                    {wtcRecent.map((m, i) => (
                      <div key={`recent-${i}`} style={wtcMatchRow}>
                        <span style={{ fontFamily: "monospace", color: "var(--muted,#888)" }}>{m.date}</span>
                        <span>
                          <strong>{wtcMatchLine(m)}</strong>
                          <br />
                          <span style={{ color: "var(--muted,#888)" }}>{m.venue}</span>
                        </span>
                        <span style={{ gridColumn: "2", fontWeight: 700 }}>{m.result}</span>
                      </div>
                    ))}
                  </div>
                  <div className="cricket-format">
                    <div className="cricket-format__head">Próximos 5</div>
                    {wtcUpcoming.map((m, i) => (
                      <div key={`upcoming-${i}`} style={wtcMatchRow}>
                        <span style={{ fontFamily: "monospace", color: "var(--muted,#888)" }}>{m.date}</span>
                        <span>
                          <strong>{wtcMatchLine(m)}</strong>
                          <br />
                          <span style={{ color: "var(--muted,#888)" }}>{m.venue}</span>
                        </span>
                        <span style={{ gridColumn: "2", color: "var(--muted,#888)" }}>{m.series}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="WTC Player Index"
                title="Top 10 jugadores del ciclo WTC 2025-27"
                sub="Nivel 0-100 del ciclo Test actual, acompañado de score de leyenda de carrera."
              >
                <div className="newsletter-list">
                  {wtcPlayers.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      item={p}
                      alive={new Set()}
                      score={p.level}
                      scoreDisplay={p.level.toFixed(1)}
                      scoreLabel="WTC"
                      scoreB={p.legendScore}
                      scoreBDisplay={p.legendScore.toFixed(1)}
                      scoreBLabel="Leyenda"
                      scoreBThreshold={legendThreshold}
                      meta={`WTC 2025-27 · ${p.country} · ${p.role}`}
                      note={`${p.stats.runs} runs · ${p.stats.wickets} wickets. ${p.note}`}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="ICC Trophy Cabinet"
                title="Legado de selecciones"
                sub="Score: ODI World Cup x14, T20 World Cup x9, Champions Trophy x6, WTC x10."
              >
                <div className="newsletter-list">
                  {trophies.map((team, i) => (
                    <NewsletterRankRow
                      key={team.teamCode}
                      rank={i + 1}
                      item={team}
                      alive={new Set()}
                      score={team.score}
                      scoreDisplay={team.score.toFixed(1)}
                      scoreLabel="Trophy"
                      meta={`ICC · ${team.country}`}
                      note={`ODI WC ${team.stats.odi_wc} · T20 WC ${team.stats.t20_wc} · CT ${team.stats.ct} · WTC ${team.stats.wtc}. ${team.note}`}
                      logo={team.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="Road to Glory"
                title="Top 10 carrera hacia leyenda"
                sub={`Umbral top 10 histórico estimado: ${legendThreshold.toFixed(1)}. Sirve para ver quién está entrando en territorio de leyenda real.`}
              >
                <div className="newsletter-list">
                  {road.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Leyenda"
                      threshold={legendThreshold}
                      meta={cricketMeta(p)}
                      note={p.legendScore >= legendThreshold ? "Ya está en zona top 10 histórico" : `A ${(legendThreshold - p.legendScore).toFixed(1)} del umbral histórico`}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}
        </div>

        <div data-section="athletics" style={sectionStyle("athletics", window.ATHLETICS_DATA?.IMPORTANCE || 7)}>
        {/* ── ATLETISMO ─────────────────────────────────────── */}
        {window.ATHLETICS_DATA && (() => {
          const ATH = window.ATHLETICS_DATA;
          const meeting = ATH.NEXT_MEETING;
          const eventHeaderStyle = {
            fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase",
            color: "var(--ink,#1a1714)", padding: "12px 0 5px", marginTop: 4,
            borderTop: "1px solid var(--border,#e0dcd5)",
            display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap",
          };
          const wrStyle = {
            fontWeight: 400, fontSize: 10, color: "var(--muted,#888)",
            textTransform: "none", letterSpacing: 0,
          };

          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Athletics Tracker</span>
                  <span>Diamond League {ATH.SEASON}</span>
                  <span>Actualizado {ATH.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>Atletismo</h1>
                  <p>
                    Los 32 eventos de la Diamond League {ATH.SEASON}: líderes de temporada,
                    records del mundo y leyendas de la pista.
                    {meeting && meeting.state === "upcoming" && (
                      <> Próxima cita: <strong>{meeting.name}</strong> · {meeting.location} · {meeting.date}.</>
                    )}
                  </p>
                </div>
              </header>

              {(ATH.GROUPS || []).map(group => (
                <NewsletterSection
                  key={group.id}
                  kicker="Diamond League"
                  title={group.label}
                  sub={`${group.sub} · Top 3 por evento · DL ${ATH.SEASON}`}
                >
                  {(group.events || []).map(event => (
                    <React.Fragment key={event.id}>
                      <div style={eventHeaderStyle}>
                        <span>{event.name}</span>
                        <span style={wrStyle}>
                          WR {event.wr.mark} · {event.wr.athlete} ({event.wr.country}, {event.wr.year})
                        </span>
                      </div>
                      <div className="newsletter-list">
                        {(event.athletes || []).map((athlete, i) => (
                          <NewsletterRankRow
                            key={athlete.id}
                            rank={i + 1}
                            item={athlete}
                            alive={new Set()}
                            score={athlete.activeScore}
                            scoreDisplay={athlete.sb}
                            scoreLabel="SB"
                            meta={`${event.name.split("—")[0].trim()} · ${athlete.country}`}
                            note={`PB: ${athlete.pb}`}
                            logo={athlete.logo}
                            prevRank={athlete.prevRank}
                          />
                        ))}
                      </div>
                    </React.Fragment>
                  ))}
                </NewsletterSection>
              ))}

              {ATH.LEGENDS && ATH.LEGENDS.length > 0 && (
                <NewsletterSection
                  kicker="Historia"
                  title="Leyendas del atletismo"
                  sub="Los más grandes de la historia: dominio olímpico, records del mundo y legado universal."
                >
                  <div className="newsletter-list">
                    {ATH.LEGENDS.map((legend, i) => (
                      <NewsletterRankRow
                        key={legend.id}
                        rank={i + 1}
                        item={legend}
                        alive={new Set()}
                        score={legend.legendScore}
                        scoreLabel="Legacy"
                        meta={`${legend.events} · ${legend.country}`}
                        note={legend.note}
                        logo={legend.logo}
                        legendActive={legend.active}
                      />
                    ))}
                  </div>
                </NewsletterSection>
              )}
            </>
          );
        })()}
        </div>

        {/* ── PLACEHOLDERS ─────────────────────────────────── */}
        {["Boxeo", "Snooker", "Ciclismo — UCI WorldTour live", "Euroliga"].map(sport => (
          <section key={sport} className="newsletter-section" style={{ opacity: 0.45, marginTop: 24, display: activeSection === "all" ? "block" : "none" }}>
            <div className="newsletter-section__head">
              <WFLabel>PRÓXIMAMENTE</WFLabel>
              <h2 style={{ fontSize: 18 }}>{sport}</h2>
            </div>
          </section>
        ))}

      </main>

      <Footer />
    </div>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner mono mono--muted">
        <span>Hermes</span>
        <span className="footer__dot">·</span>
        <span>Datos actualizados diariamente a las 06:00</span>
        <span className="footer__dot">·</span>
        <span>Refresh: python3 scripts/update_all_data.py</span>
      </div>
    </footer>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<NewsletterApp />);
