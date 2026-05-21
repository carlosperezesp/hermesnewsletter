// screens-players.jsx — age-season comparison for current stars and legends

function PlayersCompare({ onOpenMethodology }) {
  const { PLAYER_COMPARISONS } = window.NHL_DATA;
  const [age, setAge] = useState(22);
  const [status, setStatus] = useState("ALL");

  const gretzky = PLAYER_COMPARISONS.find(p => p.name === "Wayne Gretzky");
  const gretzkySeason = gretzky?.seasons.find(s => s.age === age) || gretzky?.age22Season || gretzky?.bestSeason;

  const rows = useMemo(() => {
    return PLAYER_COMPARISONS
      .filter(p => status === "ALL" || (status === "ACTIVE" ? p.active : !p.active))
      .map(p => {
        const season = p.seasons.find(s => s.age === age);
        return { ...p, selectedSeason: season, compareScore: season?.score ?? -1 };
      })
      .filter(p => p.selectedSeason)
      .sort((a, b) => b.compareScore - a.compareScore);
  }, [PLAYER_COMPARISONS, age, status]);

  const cols = [
    {
      key: "rank", label: "#", w: 36, numeric: true, sortable: false,
      render: (_r, i) => <span className="rank-num">{String(i + 1).padStart(2, "0")}</span>,
    },
    {
      key: "name", label: "Player",
      render: r => (
        <span className="hist-cell">
          <span className="player-line">
            <TeamSwatch colors={r.colors} code={r.teamCode} />
            <span className="hist-cell__name">{r.name}</span>
          </span>
          <span className="hist-cell__meta">{r.country} · {r.teamCode}</span>
        </span>
      ),
    },
    { key: "status", label: "Status", w: 88, sortable: false, render: r => <StatusBadge active={r.active} /> },
    { key: "pos", label: "Pos", w: 56, sortable: false, render: r => <PosBadge pos={r.pos} /> },
    { key: "season", label: "Season", w: 92, render: r => <span className="mono">{r.selectedSeason.season}</span>, value: r => r.selectedSeason.seasonId },
    {
      key: "line", label: "Line", w: 150, sortable: false,
      render: r => <span className="mono mono--muted">{r.selectedSeason.g} G · {r.selectedSeason.a} A · {r.selectedSeason.p} P</span>,
    },
    { key: "gp", label: "GP", w: 54, numeric: true, render: r => <span className="mono">{r.selectedSeason.gp}</span>, value: r => r.selectedSeason.gp },
    { key: "score", label: `Score at ${age}`, numeric: true, w: 142, render: r => <ScoreBar value={r.selectedSeason.score} width={68} />, value: r => r.selectedSeason.score },
  ];

  return (
    <div className="screen screen--players">
      <SectionHead
        kicker="Screen 03 / Jugadores"
        title="Comparador por edad y temporada"
        sub="Compara temporadas NHL de estrellas actuales y leyendas a la misma edad. La edad se calcula al 1 de octubre de cada temporada."
        right={<button className="link-button" onClick={onOpenMethodology}>Scoring notes →</button>}
      />

      <div className="compare-controls">
        <label className="compare-age">
          <span className="wf-label">AGE</span>
          <span className="compare-age__value">{age}</span>
          <input type="range" min="18" max="40" value={age} onChange={e => setAge(Number(e.target.value))} />
        </label>
        <div className="seg">
          <button className={`seg__btn ${status === "ALL" ? "seg__btn--on" : ""}`} onClick={() => setStatus("ALL")}>All</button>
          <button className={`seg__btn ${status === "ACTIVE" ? "seg__btn--on" : ""}`} onClick={() => setStatus("ACTIVE")}>Active</button>
          <button className={`seg__btn ${status === "LEGEND" ? "seg__btn--on" : ""}`} onClick={() => setStatus("LEGEND")}>Legends</button>
        </div>
        <div className="compare-note">
          Scores are normalized across the comparison set's NHL regular seasons, so this view answers age-relative questions like Gretzky at 22 versus today's stars at 22.
        </div>
      </div>

      {gretzkySeason && (
        <div className="reference-strip">
          <div>
            <div className="reference-strip__name">Wayne Gretzky at {gretzkySeason.age}</div>
            <div className="mono mono--muted">{gretzkySeason.teamName} · {gretzkySeason.season}</div>
          </div>
          <div className="reference-strip__metric"><strong>{gretzkySeason.score}</strong>Score</div>
          <div className="reference-strip__metric"><strong>{gretzkySeason.p}</strong>Points</div>
          <div className="reference-strip__metric"><strong>{gretzkySeason.g}</strong>Goals</div>
          <div className="reference-strip__metric"><strong>{gretzkySeason.a}</strong>Assists</div>
        </div>
      )}

      <section className="block">
        <div className="block__head">
          <WFLabel>PLAYER SEASONS AT AGE {age}</WFLabel>
          <span className="block__head-meta">{rows.length} comparable NHL seasons</span>
        </div>
        <SortableTable
          columns={cols}
          rows={rows}
          defaultSort={{ key: "score", dir: "desc" }}
          rowKey={r => `${r.id}-${r.selectedSeason.seasonId}`}
        />
      </section>
    </div>
  );
}

Object.assign(window, { PlayersCompare });
