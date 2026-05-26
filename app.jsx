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

function NewsletterRankRow({ rank, item, alive, score, scoreDisplay, scoreLabel, meta, note, threshold, logo }) {
  const isAlive = alive.size === 0 || alive.has(item.teamCode);
  const displayed = scoreDisplay !== undefined ? scoreDisplay : score;

  return (
    <div className={`newsletter-row ${!isAlive ? "newsletter-row--out" : ""}`}>
      <span className="newsletter-row__rank">{String(rank).padStart(2, "0")}</span>
      <span className="newsletter-row__identity">
        <TeamSwatch colors={item.colors} code={item.teamCode} logo={logo} />
        <span className="newsletter-row__copy">
          <span className="newsletter-row__name">{item.name || item.city}</span>
          <span className="newsletter-row__meta">{meta}</span>
        </span>
      </span>
      <span className="newsletter-row__score">
        <span className="newsletter-row__score-label">{scoreLabel}</span>
        {threshold ? (
          <span className="newsletter-row__threshold">
            <ThresholdBar value={score} threshold={threshold} width={124} />
            <span className="newsletter-row__score-value">{displayed}</span>
          </span>
        ) : (
          <span className="newsletter-row__score-value">{displayed}</span>
        )}
      </span>
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

function NewsletterApp() {
  const D = window.NHL_DATA;
  const NBA = window.NBA_DATA;
  const { TEAMS, PLAYERS, BRACKET, ROAD_TO_GLORY } = D;
  const teamByCode = useMemo(() => Object.fromEntries(TEAMS.map(t => [t.code, t])), [TEAMS]);
  const alive = useMemo(() => getAlivePlayoffTeams(BRACKET), [BRACKET]);
  const aliveLabel = [...alive].sort().join(" · ");

  const topPerformers = useMemo(() => [...PLAYERS].sort((a, b) => b.score - a.score).slice(0, 10), [PLAYERS]);
  const roadPlayers = (ROAD_TO_GLORY?.players || []).slice(0, 10);
  const youngPlayers = (ROAD_TO_GLORY?.youngProspects || []).slice(0, 10);
  const roadTeams = (ROAD_TO_GLORY?.teams || []).slice(0, 10);

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
  const tennisATP = useMemo(() => (TENNIS?.ATP || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } })).slice(0, 10), [TENNIS]);
  const tennisWTA = useMemo(() => (TENNIS?.WTA || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } })).slice(0, 10), [TENNIS]);
  function tennisPlayerMeta(player, tour) {
    const gs = player.stats?.gs || 0;
    const wk = player.stats?.weeks_no1 || 0;
    const gsStr = gs > 0 ? ` · ${gs} GS` : "";
    const wkStr = wk > 0 ? ` · ${wk} sem. #1` : "";
    return `${tour} · #${player.rank} ranking${gsStr}${wkStr}`;
  }
  function tennisPlayerNote(player) {
    const surfParts = [];
    if (player.surface?.hard != null) surfParts.push(`H:${Math.round(player.surface.hard * 100)}%`);
    if (player.surface?.clay != null) surfParts.push(`C:${Math.round(player.surface.clay * 100)}%`);
    if (player.surface?.grass != null) surfParts.push(`G:${Math.round(player.surface.grass * 100)}%`);
    return `Legend ${player.legendScore}${surfParts.length ? " · " + surfParts.join(" · ") : ""}`;
  }

  // NBA data
  const nbaTeamByCode = useMemo(() => Object.fromEntries((NBA?.TEAMS || []).map(t => [t.code, t])), [NBA]);
  const nbaAlive = useMemo(() => NBA ? getAlivePlayoffTeams(NBA.BRACKET) : new Set(), [NBA]);
  const nbaTopPerformers = useMemo(() => NBA ? [...NBA.PLAYERS].sort((a, b) => b.score - a.score).slice(0, 10) : [], [NBA]);
  const nbaRoadPlayers  = (NBA?.ROAD_TO_GLORY?.players || []).slice(0, 10);
  const nbaYoungPlayers = (NBA?.ROAD_TO_GLORY?.youngProspects || []).slice(0, 10);
  const nbaRoadTeams    = (NBA?.ROAD_TO_GLORY?.teams || []).slice(0, 10);

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

  function nbaTeamLogo(teamCode) {
    return nbaTeamByCode[teamCode]?.logo || `https://a.espncdn.com/i/teamlogos/nba/500/${(teamCode || "").toLowerCase()}.png`;
  }

  function nbaPlayerMeta(player) {
    const teamName = nbaTeamByCode[player.teamCode]?.commonName || player.teamCode;
    const age = player.age ? ` · ${player.age} años` : "";
    return `NBA · ${player.pos} · ${teamName}${age}`;
  }

  return (
    <div className="app app--newsletter">
      <main className="newsletter">

        {/* ── NHL ─────────────────────────────────────────── */}
        <header className="newsletter-hero">
          <div className="newsletter-hero__masthead">
            <span>NHL Tracker</span>
            <span>{D.SEASON}</span>
            <span>Actualizado {D.LAST_UPDATE}</span>
          </div>
          <div className="newsletter-hero__title-row">
            <h1>Playoff newsletter</h1>
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

            <NewsletterSection
              kicker="Top performers"
              title="Top 10 performers NBA esta temporada"
              sub="Ranking por score actual — pts, reb, ast, stl, blk ponderados por posición."
            >
              <div className="newsletter-list">
                {nbaTopPerformers.map((player, i) => (
                  <NewsletterRankRow
                    key={player.id}
                    rank={i + 1}
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
          </>
        )}

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
                    item={player}
                    alive={mlbAlive}
                    score={player.score}
                    scoreLabel="Score"
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
                    item={player}
                    alive={mlbAlive}
                    score={player.score}
                    scoreLabel="Score"
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
              sub={`Umbral top 10 histórico: ${MLB.ROAD_TO_GLORY?.playerThreshold ?? "N/A"} (Rogers Hornsby).`}
            >
              <div className="newsletter-list">
                {mlbRoadPlayers.map((player, i) => (
                  <NewsletterRankRow
                    key={player.id}
                    rank={i + 1}
                    item={player}
                    alive={mlbAlive}
                    score={player.careerScore}
                    scoreLabel="Career"
                    threshold={MLB.ROAD_TO_GLORY?.playerThreshold}
                    meta={`${mlbPlayerMeta(player)} · ${player.rings} ring${player.rings !== 1 ? "s" : ""}`}
                    note={player.note}
                    logo={mlbTeamLogo(player.teamCode)}
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
          </>
        )}

        {/* ── TENNIS ─────────────────────────────────────────── */}
        {TENNIS && (() => {
          const atpChanges  = TENNIS.ATP_CHANGES  || { entered: [], exited: [] };
          const wtaChanges  = TENNIS.WTA_CHANGES  || { entered: [], exited: [] };
          const atpLegends  = (TENNIS.ATP_LEGENDS || []).slice(0, 10).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } }));
          const wtaLegends  = (TENNIS.WTA_LEGENDS || []).slice(0, 10).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } }));

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

              <NewsletterSection
                kicker="ATP Singles"
                title="Top 10 ATP Singles — Score activo"
                sub="Score 0–100 basado en forma reciente, Elo, ranking y win-rate por superficie."
              >
                <ChangesRow changes={atpChanges} tour="ATP" />
                <div className="newsletter-list">
                  {tennisATP.map((player, i) => (
                    <NewsletterRankRow
                      key={player.id}
                      rank={i + 1}
                      item={player}
                      alive={new Set()}
                      score={player.activeScore}
                      scoreLabel="Active"
                      meta={tennisPlayerMeta(player, "ATP")}
                      note={tennisPlayerNote(player)}
                      logo={player.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="WTA Singles"
                title="Top 10 WTA Singles — Score activo"
                sub="Score 0–100 basado en forma reciente, Elo, ranking y win-rate por superficie."
              >
                <ChangesRow changes={wtaChanges} tour="WTA" />
                <div className="newsletter-list">
                  {tennisWTA.map((player, i) => (
                    <NewsletterRankRow
                      key={player.id}
                      rank={i + 1}
                      item={player}
                      alive={new Set()}
                      score={player.activeScore}
                      scoreLabel="Active"
                      meta={tennisPlayerMeta(player, "WTA")}
                      note={tennisPlayerNote(player)}
                      logo={player.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              {/* Road to Glory */}
              <NewsletterSection
                kicker="ATP Legends"
                title="Road to Glory · Leyendas del ATP"
                sub="Score histórico: GS (×12) + Year-end #1 (×3) + semanas en #1 (÷10). Djokovic como referencia: 100."
              >
                <div className="newsletter-list">
                  {atpLegends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      item={p}
                      alive={new Set(atpLegends.filter(l => l.active).map(l => l.id))}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`ATP · ${p.country} · ${p.stats.birth}`}
                      note={`${p.stats.gs} GS · ${p.stats.year_end_no1}× #1 año · ${p.stats.weeks_no1} sem #1`}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>

              <NewsletterSection
                kicker="WTA Legends"
                title="Road to Glory · Leyendas del WTA"
                sub="Score histórico: GS (×12) + Year-end #1 (×3) + semanas en #1 (÷10). Graf como referencia: 100."
              >
                <div className="newsletter-list">
                  {wtaLegends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      item={p}
                      alive={new Set(wtaLegends.filter(l => l.active).map(l => l.id))}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`WTA · ${p.country} · ${p.stats.birth}`}
                      note={`${p.stats.gs} GS · ${p.stats.year_end_no1}× #1 año · ${p.stats.weeks_no1} sem #1`}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}

        {/* ── CYCLING ─────────────────────────────────────────── */}
        {window.CYCLING_DATA && (() => {
          const CYC = window.CYCLING_DATA;
          const cr  = CYC.CURRENT_RACE;
          const cycLegends = (CYC.LEGENDS || []).map(p => ({ ...p, colors: { primary: p.primary, secondary: p.secondary } })).slice(0, 10);

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
                      ? `Etapa ${cr.stage} de ${cr.total_stages} · ${cr.jersey_name} · GC en directo.`
                      : "Score 0–100 ponderando Grandes Vueltas (TDF×12, Giro×9, Vuelta×8), Monumentos (×4) y Mundiales (×5)."}
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
                      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 0" }}>
                        <img src={ls.winner_logo} alt={ls.winner_cc} style={{ width: 24, height: 18, borderRadius: 2 }} />
                        <span style={{ fontSize: 20, fontWeight: 700 }}>{ls.winner}</span>
                        <span style={{ fontSize: 13, color: "var(--ink2,#555)", fontFamily: "monospace" }}>({ls.winner_cc})</span>
                      </div>
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
                  kicker={`Clasificación General — Etapa ${cr.stage}/${cr.total_stages}`}
                  title="Top 10 GC"
                  sub={`Líder: ${cr.gc[0].name} (${cr.jersey_name}) · Barra = score leyendas (Merckx=100)`}
                >
                  <div className="newsletter-list">
                    {cr.gc.map((r, i) => {
                      const lgScore = r.legendScore || 0;
                      return (
                        <div key={r.name} style={{
                          display: "flex", alignItems: "flex-start", gap: 8,
                          padding: "9px 0", borderBottom: "1px solid var(--rule,#eee)"
                        }}>
                          <span style={{ width: 24, fontSize: 15, color: "var(--muted,#888)", fontVariantNumeric: "tabular-nums", flexShrink: 0, paddingTop: 2 }}>{r.rank}</span>
                          <div style={{ width: 10, height: 10, borderRadius: 2, background: r.primary, flexShrink: 0, marginTop: 4 }} />
                          <img src={r.logo} alt={r.country} style={{ width: 20, height: 15, borderRadius: 2, flexShrink: 0, marginTop: 3 }} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, fontSize: 14 }}>{r.name}</div>
                            <div style={{ fontSize: 11, color: "var(--muted,#888)", fontFamily: "monospace" }}>{r.team}</div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                              <div style={{ width: 70, height: 4, background: "var(--bar-bg,#dedad6)", borderRadius: 2, overflow: "hidden" }}>
                                <div style={{ width: `${lgScore}%`, height: "100%", background: lgScore > 0 ? "var(--bar-fill,#4a4745)" : "transparent", borderRadius: 2 }} />
                              </div>
                              <span style={{ fontSize: 10, color: "var(--muted,#888)", fontFamily: "monospace" }}>
                                {lgScore > 0 ? `${lgScore.toFixed(0)}/100 leyenda` : "sin títulos aún"}
                              </span>
                            </div>
                          </div>
                          <span style={{
                            fontFamily: "monospace", fontSize: 13,
                            fontWeight: i === 0 ? 700 : 400,
                            color: i === 0 ? "var(--accent,#b84832)" : "var(--ink2,#555)",
                            whiteSpace: "nowrap", paddingTop: 2
                          }}>{r.time}</span>
                        </div>
                      );
                    })}
                  </div>
                </NewsletterSection>
              )}

              {cr && (cr.points_leader || cr.kom_leader || cr.young_leader) && (
                <NewsletterSection
                  kicker="Líderes de maillot"
                  title="Puntos · Montaña · Mejor joven"
                  sub="Clasificaciones secundarias en curso."
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
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={cycMeta(p)}
                      note={cycNote(p)}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}

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
          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Sumo</span>
                  <span>{bashoLabel(SUMO.BASHO_ID)}</span>
                  <span>Actualizado {SUMO.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>Sumo · Yokozuna Leyendas</h1>
                  <p>
                    Ranking histórico de Yokozuna por yusho (Copa del Emperador) y basho compitiendo como Yokozuna.
                    {bashoInfo?.winner && ` Ganador del Natsu 2026: ${bashoInfo.winner}.`}
                  </p>
                </div>
              </header>
              <NewsletterSection
                kicker="Yokozuna Legends"
                title="Top 10 Yokozuna históricos"
                sub="Score basado en yusho (×5 pts) + basho como Yokozuna (×0.5 pts). Hakuho como referencia: 100."
              >
                <div className="newsletter-list">
                  {sumoLegends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      item={p}
                      alive={new Set()}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`Sumo · ${p.country} · ${p.stats.birth}`}
                      note={`${p.stats.yusho} yusho · ${p.stats.yokozuna_basho} basho como Yokozuna`}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>
              {banzuke.length > 0 && (
                <NewsletterSection
                  kicker="Banzuke"
                  title={`Makuuchi banzuke — ${bashoLabel(SUMO.BASHO_ID)}`}
                  sub="Los 20 mejores luchadores de la división principal, ordenados por rango."
                >
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" }}>
                    {banzuke.map((w, i) => (
                      <div key={`${w.side}-${i}`} className="newsletter-row" style={{ padding: "5px 0" }}>
                        <span className="newsletter-row__rank" style={{ fontSize: 11 }}>{String(i + 1).padStart(2, "0")}</span>
                        <span className="newsletter-row__identity" style={{ flex: 1 }}>
                          <span className="newsletter-row__copy">
                            <span className="newsletter-row__name" style={{ fontSize: 13 }}>{w.name}</span>
                            <span className="newsletter-row__meta">{w.rankLabel}</span>
                          </span>
                        </span>
                        <span style={{ fontSize: 12, fontVariantNumeric: "tabular-nums", color: "var(--ink-2)" }}>
                          {w.wins}-{w.losses}{w.absences > 0 ? `-${w.absences}` : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                </NewsletterSection>
              )}
            </>
          );
        })()}

        {/* ── F1 ───────────────────────────────────────────── */}
        {window.F1_DATA && (() => {
          const F1 = window.F1_DATA;
          const drivers      = (F1.DRIVERS      || []).slice(0, 10);
          const constructors = (F1.CONSTRUCTORS || []).slice(0, 5);
          const lastRace     = F1.LAST_RACE;
          const legends      = (F1.LEGENDS      || []).slice(0, 10);
          const leaderPts    = drivers.length ? drivers[0].points : 1;
          const f1MaxSeason  = F1.MAX_SEASON_PTS || F1.TOTAL_ROUNDS * 25;
          const f1Remaining  = (F1.TOTAL_ROUNDS - F1.ROUND) * 25;
          const f1Threshold  = Math.round(Math.min((drivers[1]?.points || 0) + f1Remaining + 1, f1MaxSeason) / f1MaxSeason * 1000) / 10;
          return (
            <>
              <header className="newsletter-hero" style={{ marginTop: 48 }}>
                <div className="newsletter-hero__masthead">
                  <span>Formula 1</span>
                  <span>Season {F1.SEASON} · Round {F1.ROUND}/{F1.TOTAL_ROUNDS}</span>
                  <span>Actualizado {F1.UPDATED}</span>
                </div>
                <div className="newsletter-hero__title-row">
                  <h1>F1 · World Championship {F1.SEASON}</h1>
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
                sub={`Barra sobre ${f1MaxSeason} pts máximos. Línea roja = mínimo para ser campeón matemático (2º + puntos restantes + 1).`}
              >
                <div className="newsletter-list">
                  {drivers.map((d, i) => (
                    <NewsletterRankRow
                      key={d.name}
                      rank={i + 1}
                      item={{ ...d, colors: { primary: d.primary, secondary: d.secondary } }}
                      alive={new Set()}
                      score={d.score}
                      scoreDisplay={d.points}
                      scoreLabel="Puntos"
                      threshold={f1Threshold}
                      meta={`F1 · ${d.country} · ${d.team || d.teamCode}`}
                      note={null}
                      logo={d.logo}
                    />
                  ))}
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
              {lastRace && lastRace.podium && lastRace.podium.length > 0 && (
                <NewsletterSection
                  kicker="Last Race"
                  title={lastRace.name}
                  sub={`${lastRace.circuit} · ${lastRace.date}`}
                >
                  <div className="newsletter-list">
                    {lastRace.podium.map((p, i) => (
                      <div key={i} className="newsletter-row">
                        <span className="newsletter-row__rank">{`P${p.position}`}</span>
                        <span className="newsletter-row__identity" style={{ flex: 1 }}>
                          <span
                            className="newsletter-row__dot"
                            style={{ background: p.primary }}
                          />
                          <span className="newsletter-row__copy">
                            <span className="newsletter-row__name">{p.name}</span>
                            <span className="newsletter-row__meta">{p.team}</span>
                          </span>
                        </span>
                        {p.time && (
                          <span style={{ fontSize: 12, color: "var(--ink-2)" }}>{p.time}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </NewsletterSection>
              )}

              {/* F1 Legends */}
              <NewsletterSection
                kicker="F1 Legends"
                title="Road to Glory · Leyendas de la F1"
                sub="Score histórico ponderando títulos (×15), victorias (×0.5), poles (×0.3) y podios (×0.15). Hamilton como referencia: 100."
              >
                <div className="newsletter-list">
                  {legends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      item={p}
                      alive={new Set(legends.filter(l => l.active).map(l => l.id))}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`F1 · ${p.country} · ${p.stats.birth}`}
                      note={`${p.stats.titles} títulos · ${p.stats.wins} victorias · ${p.stats.poles} poles`}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}

        {/* ── AFL ──────────────────────────────────────────── */}
        {window.AFL_DATA && (() => {
          const AFL     = window.AFL_DATA;
          const ladder  = (AFL.LADDER     || []).slice(0, 8);   // top 8 = finals
          const results = (AFL.LAST_ROUND || []);
          const legends = (AFL.LEGENDS    || []).slice(0, 10);
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

              {/* Ladder top 8 */}
              <NewsletterSection
                kicker="AFL Ladder"
                title="Top 8 — Clasificación"
                sub={`Tras la ronda ${AFL.ROUND}. Los 8 primeros disputan las finals.`}
              >
                <div className="newsletter-list">
                  {ladder.map((t, i) => {
                    const maxPts = ladder[0].pts || 1;
                    const score  = Math.round(t.pts / maxPts * 100);
                    return (
                      <div key={t.name} className="newsletter-row">
                        <span className="newsletter-row__rank">{String(i + 1).padStart(2, "0")}</span>
                        <span className="newsletter-row__identity" style={{ flex: 1 }}>
                          <span
                            className="newsletter-row__dot"
                            style={{ background: t.primary, border: `1px solid ${t.secondary}` }}
                          />
                          <span className="newsletter-row__copy">
                            <span className="newsletter-row__name">{t.name}</span>
                            <span className="newsletter-row__meta">
                              {`W${t.wins} L${t.losses}${t.draws > 0 ? ` D${t.draws}` : ""} · ${t.percentage}%`}
                            </span>
                          </span>
                        </span>
                        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span className="newsletter-bar" style={{ "--pct": `${score}%`, "--clr": t.primary }} />
                          <span style={{ fontSize: 12, fontVariantNumeric: "tabular-nums", minWidth: 28, textAlign: "right" }}>
                            {t.pts} pts
                          </span>
                        </span>
                      </div>
                    );
                  })}
                </div>
              </NewsletterSection>

              {/* Last round results */}
              {results.length > 0 && (
                <NewsletterSection
                  kicker={`Round ${AFL.ROUND}`}
                  title={`Resultados — Ronda ${AFL.ROUND}`}
                  sub="Resultados completos de la última ronda disputada."
                >
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 32px" }}>
                    {results.map((g, i) => (
                      <div key={i} className="newsletter-row" style={{ padding: "5px 0", alignItems: "center" }}>
                        <span style={{ flex: 1, fontSize: 12 }}>
                          <span style={{
                            fontWeight: g.winner === g.hteam ? 700 : 400,
                            color: g.winner === g.hteam ? g.hprimary : "var(--ink-2)"
                          }}>{g.hteam}</span>
                          <span style={{ margin: "0 4px", color: "var(--ink-3)" }}>
                            {g.hscore}–{g.ascore}
                          </span>
                          <span style={{
                            fontWeight: g.winner === g.ateam ? 700 : 400,
                            color: g.winner === g.ateam ? g.aprimary : "var(--ink-2)"
                          }}>{g.ateam}</span>
                        </span>
                      </div>
                    ))}
                  </div>
                </NewsletterSection>
              )}

              {/* AFL Legends */}
              <NewsletterSection
                kicker="VFL/AFL Legends"
                title="Road to Glory · Leyendas del AFL"
                sub="Score histórico: premiaciones (×8), Brownlow Medals (×5), selecciones All-Australian (×1.5). Bartlett como referencia: 100."
              >
                <div className="newsletter-list">
                  {legends.map((p, i) => (
                    <NewsletterRankRow
                      key={p.id}
                      rank={i + 1}
                      item={p}
                      alive={new Set(legends.filter(l => l.active).map(l => l.id))}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`AFL · ${p.teamCode} · ${p.stats.birth}`}
                      note={`${p.stats.flags} premios · ${p.stats.brownlow} Brownlow · ${p.stats.all_aus} All-Aus`}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}

        {/* ── MotoGP ───────────────────────────────────────── */}
        {window.MOTOGP_DATA && (() => {
          const MG         = window.MOTOGP_DATA;
          const riders     = (MG.RIDERS  || []).slice(0, 10);
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
                  kicker={`Round ${last.round}`}
                  title={last.name}
                  sub={`Ganador del GP · ${last.bike}`}
                >
                  <div className="newsletter-row" style={{ padding: "8px 0" }}>
                    <span className="newsletter-row__rank">P1</span>
                    <span className="newsletter-row__identity">
                      <span className="newsletter-row__dot" style={{ background: last.primary }} />
                      <span className="newsletter-row__copy">
                        <span className="newsletter-row__name">{last.winner}</span>
                        <span className="newsletter-row__meta">{last.bike}</span>
                      </span>
                    </span>
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
                      item={p}
                      alive={new Set(legends.filter(l => l.active).map(l => l.id))}
                      score={p.legendScore}
                      scoreLabel="Legend"
                      meta={`MotoGP · ${p.country} · ${p.stats.birth}`}
                      note={`${p.stats.titles} títulos · ${p.stats.wins} victorias · ${p.stats.poles} poles`}
                      logo={p.logo}
                    />
                  ))}
                </div>
              </NewsletterSection>
            </>
          );
        })()}

        {/* ── PLACEHOLDERS ─────────────────────────────────── */}
        {["Cricket", "Rugby", "Golf", "Boxeo", "Snooker", "Ciclismo — UCI WorldTour live", "Euroliga", "NASCAR · IndyCar"].map(sport => (
          <section key={sport} className="newsletter-section" style={{ opacity: 0.45, marginTop: 24 }}>
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
        <span>Hermes · Sports Newsletter</span>
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
