import { useMemo, useState, useCallback } from "react";
import TeacherProvider, {
  useTeachers,
} from "../components/teacher/TeacherContext";
import PieChart from "../components/ui/PieChart";
import "./Report.css";
import { useEffect } from "react";

function computeHIndex(citations = []) {
  const sorted = citations
    .slice()
    .map((n) => Number(n) || 0)
    .sort((a, b) => b - a);
  let h = 0;
  for (let i = 0; i < sorted.length; i++) {
    if (sorted[i] >= i + 1) h = i + 1;
    else break;
  }
  return h;
}

function ReportContent() {
  const { teachers } = useTeachers();
  const [activeTeacherId, setActiveTeacherId] = useState(null); // filter by click
  const [filter, setFilter] = useState({ kind: "none", value: "" });
  const [autoresFlat, setAutoresFlat] = useState([]);
  // removed hRange and topN per request; only year filter remains

  // paleta consistente para fatias do pie e swatches do ranking
  const palette = [
    "#60a5fa",
    "#34d399",
    "#f472b6",
    "#f59e0b",
    "#a78bfa",
    "#fb7185",
    "#f97316",
    "#06b6d4",
    "#ef4444",
    "#10b981",
  ];

  // construir produções reais a partir dos teachers -> works (quando presente)
  // preferir autores_flat do backend (fonte primária para relatórios)
  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const API = (
          import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
        ).replace(/\/$/, "");
        const res = await fetch(`${API}/autores_flat`);
        if (!res.ok) return;
        const json = await res.json();
        const arr = Array.isArray(json)
          ? json
          : Object.keys(json || {})
              .filter((k) => k !== "_")
              .map((k) => ({ id: k, ...json[k] }));
        if (mounted) setAutoresFlat(arr);
      } catch (e) {
        // ignore
      }
    }
    load();
    return () => (mounted = false);
  }, []);

  const mockProductions = useMemo(() => {
    const prods = [];
    const source =
      autoresFlat && autoresFlat.length > 0 ? autoresFlat : teachers;
    source.forEach((t) => {
      const works = t.works || (t.raw && t.raw.works) || null;
      if (!works) return;
      if (Array.isArray(works)) {
        works.forEach((w) => {
          prods.push({
            titulo: w.title || w.titulo || w.name || "--",
            autores: (w.authorships || []).map(
              (a) => a.author?.display_name || a.name || a || ""
            ),
            ano: (() => {
              const y =
                w.year ??
                w.ano ??
                w.published_year ??
                w.year_published ??
                w.date ??
                null;
              if (!y && y !== 0) return null;
              const s = String(y).trim();
              // tentativa direta de número (ano)
              const n = parseInt(s.slice(0, 4), 10);
              if (!Number.isNaN(n) && n > 0) return n;
              // tentativa parse de data completa
              const d = Date.parse(s);
              if (!Number.isNaN(d)) return new Date(d).getFullYear();
              return null;
            })(),
            veiculo: w.host_venue?.display_name || w.veiculo || w.venue || "",
            qualis: w.qualis || null,
            teacherId: t.id,
            cited_by_count: w.cited_by_count || w.citations || 0,
            id: w.id || w.doi || String(Math.random()).slice(2),
            raw: w,
          });
        });
      } else if (typeof works === "object") {
        Object.keys(works).forEach((k) => {
          const w = works[k] || {};
          prods.push({
            titulo: w.title || w.titulo || w.name || "--",
            autores: (w.authorships || []).map(
              (a) => a.author?.display_name || a.name || a || ""
            ),
            ano: (() => {
              const y =
                w.year ??
                w.ano ??
                w.published_year ??
                w.year_published ??
                w.date ??
                null;
              if (!y && y !== 0) return null;
              const s = String(y).trim();
              const n = parseInt(s.slice(0, 4), 10);
              if (!Number.isNaN(n) && n > 0) return n;
              const d = Date.parse(s);
              if (!Number.isNaN(d)) return new Date(d).getFullYear();
              return null;
            })(),
            veiculo: w.host_venue?.display_name || w.veiculo || w.venue || "",
            qualis: w.qualis || null,
            teacherId: t.id,
            cited_by_count: w.cited_by_count || w.citations || 0,
            id: w.id || k,
            raw: w,
          });
        });
      }
    });
    return prods;
  }, [teachers, autoresFlat]);

  // aplica seleção de teacher e filtro
  const filtered = useMemo(() => {
    let arr = mockProductions.slice();
    if (activeTeacherId)
      arr = arr.filter((p) => p.teacherId === activeTeacherId);
    if (filter.kind === "ano" && filter.value)
      arr = arr.filter(
        (p) => p.ano != null && Number(p.ano) === Number(filter.value)
      );
    if (filter.kind === "veiculo" && filter.value)
      arr = arr.filter((p) => p.veiculo === filter.value);
    if (filter.kind === "qualis" && filter.value)
      arr = arr.filter((p) => p.qualis === filter.value);
    return arr;
  }, [mockProductions, activeTeacherId, filter, teachers]);
  // removed hRange from deps; ensure memo updates when teachers change

  const totalPublications = filtered.length;

  // agrupa por autor a partir das produções filtradas (garante reatividade ao filtro)
  const countsByAuthor = useMemo(() => {
    const map = new Map();

    filtered.forEach((p) => {
      const authorId = p.teacherId || null;
      // nome preferencial: buscar em autoresFlat/teachers por id, senão usar autores[0] do produto
      let name = "Desconhecido";
      if (authorId) {
        const foundA = (autoresFlat || []).find(
          (a) => String(a.id) === String(authorId)
        );
        if (foundA)
          name = foundA.nome || foundA.name || foundA.display_name || name;
        else {
          const foundT = (teachers || []).find(
            (t) => String(t.id) === String(authorId)
          );
          if (foundT) name = foundT.name || foundT.nome || name;
        }
      }
      if (
        (!authorId || name === "Desconhecido") &&
        Array.isArray(p.autores) &&
        p.autores.length > 0
      ) {
        // tenta extrair nome do primeiro autor listado na publicação
        const first = p.autores[0];
        if (typeof first === "string") name = first;
        else if (first && (first.name || first.display_name))
          name = first.name || first.display_name;
      }

      const key = authorId || name || "desconhecido";
      const cur = map.get(key) || {
        id: key,
        name: name || "Desconhecido",
        count: 0,
      };
      cur.count = (cur.count || 0) + 1;
      map.set(key, cur);
    });

    return Array.from(map.values()).sort((a, b) => b.count - a.count);
  }, [filtered, autoresFlat, teachers]);

  // ranking data (all authors with publications)
  const rankingData = countsByAuthor.map((c, i) => ({
    id: c.id,
    name: c.name,
    count: c.count,
    color: palette[i % palette.length],
  }));

  // publications per year series (global)
  const pubsByYear = useMemo(() => {
    const map = new Map();
    mockProductions.forEach((p) => {
      const y = p.ano || (p.raw && p.raw.year) || null;
      if (!y) return;
      map.set(y, (map.get(y) || 0) + 1);
    });
    const arr = Array.from(map.entries())
      .map(([k, v]) => ({ x: Number(k), y: v }))
      .sort((a, b) => a.x - b.x);
    return arr;
  }, [mockProductions]);

  // compute h-index per teacher for histogram and display
  const hIndexByTeacher = useMemo(() => {
    const out = [];
    teachers.forEach((t) => {
      const works = t.works || (t.raw && t.raw.works) || {};
      const arrWorks = Array.isArray(works)
        ? works
        : Object.values(works || {});
      const citations = arrWorks.map(
        (w) => Number(w.cited_by_count || w.citations || 0) || 0
      );
      out.push({ id: t.id, name: t.name, h: computeHIndex(citations) });
    });
    return out;
  }, [teachers]);

  // distribution by qualis
  const qualisDistribution = useMemo(() => {
    const map = new Map();
    mockProductions.forEach((p) => {
      const q = p.qualis || "Nenhum";
      map.set(q, (map.get(q) || 0) + 1);
    });
    return Array.from(map.entries()).map(([k, v]) => ({ name: k, value: v }));
  }, [mockProductions]);

  // palette and pie data for distribution by author (derived from countsByAuthor)
  const pieData = countsByAuthor
    .filter((c) => c.count > 0)
    .map((c, i) => ({
      id: c.id,
      name: c.name,
      count: c.count,
      color: palette[i % palette.length],
    }));

  // fallback: quando pieData estiver vazio, buscar diretamente /produtos e agregar por autor
  const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    ""
  );
  const [produtosPieData, setProdutosPieData] = useState([]);

  useEffect(() => {
    let mounted = true;
    async function loadRanking() {
      // tenta endpoint dedicado primeiro
      try {
        const res = await fetch(`${API}/produtos/ranking`);
        if (res.ok) {
          const json = await res.json();
          const arr = (Array.isArray(json) ? json : []).map((x, i) => ({
            id: x.name || x.id || String(i),
            name: x.name,
            count: x.count,
            color: palette[i % palette.length],
          }));
          if (mounted) setProdutosPieData(arr);
          return;
        }
      } catch (e) {
        // fallback para buscar /produtos
      }

      // fallback: varrer /produtos se /produtos/ranking indisponível
      try {
        const res2 = await fetch(`${API}/produtos`);
        if (!res2.ok) return;
        const produtos = await res2.json();
        const list = Array.isArray(produtos)
          ? produtos
          : Object.keys(produtos || {}).map((k) => ({ id: k, ...produtos[k] }));
        const map = new Map();
        list.forEach((p) => {
          const autoresField =
            p.autores || p.authorships || p.autores_list || p.authors || null;
          if (!autoresField) return;
          if (Array.isArray(autoresField)) {
            autoresField.forEach((a) => {
              let name = "";
              if (typeof a === "string") name = a;
              else if (a && (a.name || a.author_name))
                name = a.name || a.author_name;
              else if (
                a &&
                a.author &&
                (a.author.display_name || a.author.name)
              )
                name = a.author.display_name || a.author.name;
              name = (name || "").trim();
              if (!name) return;
              const key = name.toLowerCase();
              map.set(key, map.get(key) || { name, count: 0 });
              map.get(key).count += 1;
            });
          } else if (typeof autoresField === "string") {
            const parts = autoresField
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean);
            parts.forEach((name) => {
              const key = name.toLowerCase();
              map.set(key, map.get(key) || { name, count: 0 });
              map.get(key).count += 1;
            });
          }
        });
        const arr = Array.from(map.values()).map((v, i) => ({
          id: v.name,
          name: v.name,
          count: v.count,
          color: palette[i % palette.length],
        }));
        if (mounted) setProdutosPieData(arr.sort((a, b) => b.count - a.count));
      } catch (e) {
        // ignore
      }
    }
    loadRanking();
    return () => (mounted = false);
  }, [API, palette]);

  // opções para filtros
  const anos = Array.from(
    new Set(mockProductions.map((p) => p.ano).filter((y) => y != null))
  ).sort((a, b) => b - a);
  const veiculos = Array.from(new Set(mockProductions.map((p) => p.veiculo)));
  const qualis = Array.from(new Set(mockProductions.map((p) => p.qualis)));

  // simplified controls: only show year filter
  return (
    <div className="reports-page">
      <div className="reports-header">
        <h1>Relatórios</h1>
      </div>

      <div className="reports-controls">
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
          <div style={{ minWidth: 180 }}>
            <label style={{ display: "block", marginBottom: 6 }}>
              Filtrar por ano
            </label>
            <select
              value={filter.kind === "ano" ? filter.value : ""}
              onChange={(e) =>
                setFilter({ kind: "ano", value: e.target.value || "" })
              }
            >
              <option value="">Todos os anos</option>
              {anos.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              onClick={() => setFilter({ kind: "none", value: "" })}
              style={{
                padding: "8px 12px",
                borderRadius: 8,
                border: "1px solid var(--input-border)",
                background: "#fff",
                cursor: "pointer",
              }}
            >
              Limpar filtro
            </button>
          </div>
        </div>
      </div>

      <div className="reports-grid">
        {/* coluna principal: cartão com título e gráfico */}
        <div className="reports-card main-card">
          <h3 className="reports-chart-title">Distribuição de publicações</h3>
          <div className="chart-center">
            <div className="pie-wrapper" style={{ minWidth: 0 }}>
              {(() => {
                // prioridade: rankingData (autores_flat) -> pieData (counts by teacher) -> produtosPieData (fallback)
                const dataToShow =
                  rankingData && rankingData.length > 0
                    ? rankingData
                    : pieData && pieData.length > 0
                    ? pieData
                    : produtosPieData;
                if (!dataToShow || dataToShow.length === 0) {
                  return (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        height: "100%",
                        color: "var(--muted)",
                      }}
                    >
                      Sem dados para exibir
                    </div>
                  );
                }
                if (process.env.NODE_ENV !== "production" && console.debug)
                  console.debug("Report dataToShow:", dataToShow);
                return (
                  <PieChart
                    data={dataToShow}
                    // height controla proporção; largura será 100% do contêiner
                    height={420}
                    colors={palette}
                    onSliceClick={(id) => setActiveTeacherId(id)}
                  />
                );
              })()}
            </div>
          </div>
        </div>

        {/* coluna lateral: ranking/legenda (ocupa 2ª coluna do grid) */}
        <aside className="reports-card side-card">
          <div className="chart-total" style={{ marginBottom: 12 }}>
            Publicações totais: <strong>{totalPublications}</strong>
          </div>
          <h4 style={{ margin: "12px 0" }}>Ranking de autores</h4>
          <div className="ranking-list" style={{ paddingRight: 6 }}>
            {rankingData.map((p, idx) => (
              <div
                key={p.id}
                style={{
                  display: "flex",
                  gap: 10,
                  alignItems: "center",
                  marginBottom: 12,
                }}
              >
                <button
                  onClick={() => setActiveTeacherId(p.id)}
                  style={{
                    width: 18,
                    height: 18,
                    background: p.color,
                    borderRadius: 4,
                    border: "none",
                    cursor: "pointer",
                  }}
                  aria-label={`Selecionar ${p.name}`}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontWeight: 700,
                      whiteSpace: "normal",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {idx + 1}. {p.name}
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>
                    {p.count} publicações
                  </div>
                </div>
                <div style={{ fontWeight: 700 }}>{p.count}</div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

export default function Report() {
  return (
    <TeacherProvider>
      <ReportContent />
    </TeacherProvider>
  );
}
