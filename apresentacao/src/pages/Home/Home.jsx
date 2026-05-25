import React, { useEffect, useMemo, useState } from "react";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const RTDB_FALLBACK = (import.meta.env.VITE_RTDB_URL || "https://poshbard-default-rtdb.firebaseio.com").replace(/\/$/, "");

function normalizeMap(obj) {
  if (!obj) return [];
  if (Array.isArray(obj)) return obj;
  if (typeof obj === "object") {
    return Object.keys(obj)
      .filter((k) => k !== "_")
      .map((k) => ({ id: k, ...obj[k] }));
  }
  return [];
}

function SmallCard({ title, value }) {
  return (
    <div style={{ padding: 10, borderRadius: 8, background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.06)", marginBottom: 8 }}>
      <div style={{ fontSize: 12, color: "#2f3f46", marginBottom: 6 }}>{title}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: "#123"> }}>{value ?? "—"}</div>
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [authors, setAuthors] = useState([]);
  const [loadingAuthors, setLoadingAuthors] = useState(false);
  const [selectedAuthor, setSelectedAuthor] = useState(null);

  const [metrics, setMetrics] = useState(null);
  const [loadingMetrics, setLoadingMetrics] = useState(false);
  const [metricsError, setMetricsError] = useState(null);

  useEffect(() => {
    let mounted = true;
    setLoadingAuthors(true);
    async function load() {
      const candidates = [`${API}/autores_flat`, `${RTDB_FALLBACK}/autores_flat.json`];
      let data = null;
      for (const url of candidates) {
        try {
          const r = await fetch(url);
          if (!r.ok) continue;
          data = await r.json();
          break;
        } catch (e) { /* try next */ }
      }
      if (!mounted) return;
      if (!data) {
        setAuthors([]);
        setLoadingAuthors(false);
        return;
      }
      const arr = normalizeMap(data).map(a => ({
        id: a.id,
        name: a.nome || a.name || a.display_name || a.nome_completo || "",
      })).filter(a => a.name);
      setAuthors(arr);
      setLoadingAuthors(false);
    }
    load();
    return () => (mounted = false);
  }, []);

  const suggestions = useMemo(() => {
    const q = (query || "").trim().toLowerCase();
    if (!q) return [];
    return authors.filter(a => (a.name || "").toLowerCase().includes(q) || (a.id || "").toLowerCase().includes(q));
  }, [authors, query]);

  async function fetchMetricsForAuthor(author) {
    setMetrics(null);
    setMetricsError(null);
    setLoadingMetrics(true);
    try {
      const id = encodeURIComponent(author.id || author.name || "");
      const url = `${API}/autores/${id}/metrics`;
      const r = await fetch(url);
      if (r.ok) {
        const data = await r.json();
        setMetrics(data);
        setLoadingMetrics(false);
        return;
      }
      // fallback: tentar RTDB node do autor (autores_flat/<id>/works) e montar resumo mínimo
      const fr = await fetch(`${RTDB_FALLBACK}/autores_flat/${author.id}.json`);
      if (fr.ok) {
        const node = await fr.json();
        const works = node?.works || node?.work || {};
        const arr = normalizeMap(works);
        const sample = arr.slice(0, 6).map(w => ({ id: w.id, title: w.title || w.titulo || w.name, year: w.year || w.ano }));
        setMetrics({
          author_id: author.id,
          name: author.name,
          publications_count: arr.length,
          total_citations: null,
          h_index: null,
          first_year: arr.length ? Math.min(...arr.map(x => Number(x.year || x.ano || 0)).filter(y => y)) : null,
          last_year: arr.length ? Math.max(...arr.map(x => Number(x.year || x.ano || 0)).filter(y => y)) : null,
          top_concepts: [],
          top_coauthors: [],
          sample_publications: sample,
        });
        setLoadingMetrics(false);
        return;
      }
      throw new Error("Nenhuma métrica disponível");
    } catch (e) {
      setMetricsError("Métricas não disponíveis");
      setLoadingMetrics(false);
    }
  }

  function onSelectAuthor(a) {
    setSelectedAuthor(a);
    setQuery(a.name);
    fetchMetricsForAuthor(a);
  }

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      <h2 style={{ marginBottom: 12 }}>Buscar autores</h2>

      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <input
          placeholder="Pesquisar autor..."
          value={query}
          onChange={(e) => { setQuery(e.target.value); setSelectedAuthor(null); setMetrics(null); }}
          style={{ flex: 1, padding: "10px 12px", borderRadius: 8, border: "1px solid #dfe7ee" }}
        />
        <button onClick={() => { if (suggestions.length === 1) onSelectAuthor(suggestions[0]); }} style={{ padding: "10px 14px", borderRadius: 8, background: "#d97706", color: "#fff", border: "none" }}>
          Selecionar
        </button>
      </div>

      {loadingAuthors && <div>Carregando autores...</div>}
      {!loadingAuthors && query && suggestions.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, marginBottom: 12 }}>
          {suggestions.map(s => (
            <li key={s.id} style={{ marginBottom: 6 }}>
              <button onClick={() => onSelectAuthor(s)} style={{ cursor: "pointer", background: "transparent", border: "1px solid #e6eef6", padding: "8px 10px", borderRadius: 6 }}>
                {s.name} <span style={{ color: "#6b7280", marginLeft: 8, fontSize: 12 }}>{s.id}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selectedAuthor && (
        <div style={{ display: "flex", gap: 18, alignItems: "flex-start" }}>
          <aside style={{ width: 320 }}>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 14, color: "#2f3f46", fontWeight: 700 }}>{selectedAuthor.name}</div>
              <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{selectedAuthor.id}</div>
            </div>

            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 13, marginBottom: 8, color: "#2f3f46", fontWeight: 700 }}>Métricas</div>
              {loadingMetrics ? (
                <div>Carregando métricas...</div>
              ) : metricsError ? (
                <div style={{ color: "crimson" }}>{metricsError}</div>
              ) : metrics ? (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    <SmallCard title="Produções" value={metrics.publications_count} />
                    <SmallCard title="Citações totais" value={metrics.total_citations ?? "—"} />
                    <SmallCard title="h‑index" value={metrics.h_index ?? "—"} />
                    <SmallCard title="Período" value={metrics.first_year ? `${metrics.first_year} — ${metrics.last_year ?? ""}` : "—"} />
                  </div>

                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Top conceitos</div>
                    {metrics.top_concepts && metrics.top_concepts.length ? (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {metrics.top_concepts.map(([c, cnt]) => (
                          <span key={c} style={{ background: "#eef2ff", padding: "6px 8px", borderRadius: 16, fontSize: 12 }}>{c} ({cnt})</span>
                        ))}
                      </div>
                    ) : <div style={{ color: "#6b7280" }}>—</div>}
                  </div>

                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Top coautores</div>
                    {metrics.top_coauthors && metrics.top_coauthors.length ? (
                      <ol style={{ paddingLeft: 18, margin: 0 }}>
                        {metrics.top_coauthors.map(([name, cnt]) => (
                          <li key={name} style={{ marginBottom: 6 }}>{name} <span style={{ color: "#6b7280", fontSize: 12 }}>({cnt})</span></li>
                        ))}
                      </ol>
                    ) : <div style={{ color: "#6b7280" }}>—</div>}
                  </div>
                </>
              ) : (
                <div style={{ color: "#6b7280" }}>Métricas não disponíveis</div>
              )}
            </div>
          </aside>

          <div style={{ flex: 1 }}>
            {/* Campo "Amostra de publicações" removido por ser redundante */}
            {/* Se quiser mostrar outras informações detalhadas do autor, adicione aqui */}
          </div>
        </div>
      )}
    </div>
  );
}