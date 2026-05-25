import { useState, useMemo, useEffect } from "react";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  ""
);
const RTDB_FALLBACK = (
  import.meta.env.VITE_RTDB_URL ||
  "https://poshbard-default-rtdb.firebaseio.com"
).replace(/\/$/, "");

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

function worksMapToArray(worksMap) {
  if (!worksMap) return [];
  if (Array.isArray(worksMap)) return worksMap;
  if (typeof worksMap === "object")
    return Object.keys(worksMap)
      .filter((k) => k !== "_")
      .map((k) => ({ id: k, ...worksMap[k] }));
  return [];
}

function DetailsModal({ work, onClose }) {
  if (!work) return null;
  const w = work.original || work;
  const doi = w.doi || w.DOI || (w.open_access && w.open_access.oa_url) || null;
  const cited = w.cited_by_count ?? w.citations ?? null;
  const concepts = Array.isArray(w.concepts) ? w.concepts : w.topics || [];
  const authorships = w.authorships || w.autores || w.authors || [];

  return (
    <div
      style={{
        position: "fixed",
        left: 0,
        top: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "white",
          padding: 22,
          borderRadius: 10,
          width: "min(900px, 95%)",
          maxHeight: "90%",
          overflow: "auto",
          boxShadow: "0 12px 40px rgba(10,20,30,0.12)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
          }}
        >
          <h3 style={{ margin: 0, textAlign: "left", flex: 1, fontSize: 20 }}>
            {w.title || w.titulo || "Detalhes"}
          </h3>
          <button
            onClick={onClose}
            aria-label="Fechar"
            style={{
              background: "var(--accent)",
              color: "var(--accent-contrast)",
              border: "none",
              padding: "0.45rem 0.7rem",
              borderRadius: 8,
              cursor: "pointer",
            }}
          >
            Fechar
          </button>
        </div>

        <div style={{ marginTop: 12, textAlign: "left" }}>
          <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
            <div>
              <strong>Ano:</strong> {w.year || w.ano || "-"}
            </div>
            <div>
              <strong>Citações:</strong> {cited ?? "-"}
            </div>
          </div>

          <div style={{ marginTop: 10 }}>
            <strong>DOI / Link:</strong>{" "}
            {doi ? (
              <a
                href={doi.startsWith("http") ? doi : `https://doi.org/${doi}`}
                target="_blank"
                rel="noreferrer"
              >
                {doi}
              </a>
            ) : (
              "-"
            )}
          </div>

          <div style={{ marginTop: 12 }}>
            <strong>Conceitos:</strong>
            <div
              style={{
                marginTop: 8,
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
              }}
            >
              {Array.isArray(concepts) && concepts.length > 0
                ? concepts.map((c, i) => (
                    <span
                      key={i}
                      style={{
                        background: "#f3f6f9",
                        padding: "6px 10px",
                        borderRadius: 16,
                        fontSize: 13,
                        color: "#24333a",
                      }}
                    >
                      {typeof c === "string"
                        ? c
                        : c.display_name ||
                          c.normalized_name ||
                          JSON.stringify(c)}
                    </span>
                  ))
                : " -"}
            </div>
          </div>

          <div style={{ marginTop: 14 }}>
            <strong>Autores:</strong>
            <div style={{ marginTop: 8 }}>
              {Array.isArray(authorships) && authorships.length > 0 ? (
                <ol style={{ paddingLeft: 20, marginTop: 6 }}>
                  {authorships.map((au, i) => (
                    <li key={i} style={{ marginBottom: 6 }}>
                      {au.author_name || au.name || au}
                    </li>
                  ))}
                </ol>
              ) : (
                " -"
              )}
            </div>
          </div>

          <div style={{ marginTop: 14 }}>
            <strong>Área(s) de Pesquisa:</strong>
            <div
              style={{
                marginTop: 8,
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
              }}
            >
              {Array.isArray(w.research_areas || w.area) &&
              (w.research_areas || w.area).length > 0 ? (
                (w.research_areas || w.area).map((area, i) => (
                  <span
                    key={i}
                    style={{
                      background: "#e6f7ff",
                      padding: "6px 10px",
                      borderRadius: 16,
                      fontSize: 13,
                      color: "#1890ff",
                      border: "1px solid #91d5ff",
                    }}
                  >
                    {area}
                  </span>
                ))
              ) : (
                <span style={{ color: "var(--muted)" }}>Não especificado</span>
              )}
            </div>
          </div>

          {w.qualis && (
            <div style={{ marginTop: 14 }}>
              <strong>Qualis:</strong>
              <div style={{ marginTop: 8 }}>
                <span
                  style={{
                    background: "#f6f0ff",
                    padding: "6px 10px",
                    borderRadius: 16,
                    fontSize: 13,
                    color: "#722ed1",
                    border: "1px solid #d3adf7",
                    fontWeight: "bold",
                  }}
                >
                  {w.qualis}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [authors, setAuthors] = useState([]);
  const [loadingAuthors, setLoadingAuthors] = useState(false);
  const [error, setError] = useState(null);
  const [selectedAreaFilter, setSelectedAreaFilter] = useState(""); // Filtro de área de pesquisa

  const [selectedAuthor, setSelectedAuthor] = useState(null);
  const [authorWorks, setAuthorWorks] = useState([]);
  const [loadingWorks, setLoadingWorks] = useState(false);
  const [selectedWork, setSelectedWork] = useState(null);
  const [selectedSort, setSelectedSort] = useState("recent");

  const [authorMetrics, setAuthorMetrics] = useState(null);
  const [loadingMetrics, setLoadingMetrics] = useState(false);

  useEffect(() => {
    let mounted = true;
    setLoadingAuthors(true);
    setError(null);

    async function fetchAutoresFlat() {
      const candidates = [
        `${API}/autores_flat`,
        `${API}/autores-flat`,
        `${RTDB_FALLBACK}/autores_flat.json`,
      ];
      let data = null;
      for (const url of candidates) {
        try {
          const res = await fetch(url);
          if (!res.ok) continue;
          data = await res.json();
          break;
        } catch (e) {
          // ignore and try next
        }
      }
      if (!mounted) return;
      if (!data) {
        setAuthors([]);
        setError("Não foi possível carregar autores (autores_flat)");
        setLoadingAuthors(false);
        return;
      }
      const raw = normalizeMap(data);
      const list = raw
        .map((a) => ({
          id: a.id,
          name: a.nome || a.nome_completo || a.name || a.display_name || "",
          orcid: a.orcid || (a.ids && a.ids.orcid) || null,
          works: a.works || a.works_map || {},
          research_areas:
            a.research_areas ||
            (Array.isArray(a.research)
              ? a.research
              : a.research
              ? [a.research]
              : null) ||
            (Array.isArray(a.linha_pesquisa)
              ? a.linha_pesquisa
              : a.linha_pesquisa
              ? [a.linha_pesquisa]
              : []),
        }))
        .filter((a) => a.name && a.name.trim());
      setAuthors(list);
      setLoadingAuthors(false);
    }

    fetchAutoresFlat();
    return () => (mounted = false);
  }, []);

  // Extrair áreas de pesquisa únicas para o filtro
  const availableAreas = useMemo(() => {
    const areas = new Set();
    authors.forEach((author) => {
      if (Array.isArray(author.research_areas)) {
        author.research_areas.forEach((area) => {
          if (area) areas.add(area);
        });
      }
    });
    return [...areas].sort();
  }, [authors]);

  const suggestions = useMemo(() => {
    let filtered = authors;

    // Aplicar filtro de área de pesquisa se selecionado
    if (selectedAreaFilter) {
      filtered = filtered.filter(
        (author) =>
          Array.isArray(author.research_areas) &&
          author.research_areas.includes(selectedAreaFilter)
      );
    }

    // Aplicar filtro de busca por nome/orcid
    const q = (query || "").trim().toLowerCase();
    if (q) {
      filtered = filtered.filter(
        (a) =>
          (a.name || "").toLowerCase().includes(q) ||
          (a.orcid || "").toLowerCase().includes(q)
      );
    }

    return filtered;
  }, [authors, query, selectedAreaFilter]);

  const sortedWorks = useMemo(() => {
    if (!authorWorks) return [];
    const copy = [...authorWorks];
    const yearOf = (p) => {
      const v =
        (p.original && (p.original.year || p.original.ano)) || p.year || p.ano;
      const n = parseInt(v, 10);
      return Number.isFinite(n) ? n : 0;
    };
    const citedOf = (p) => {
      const v =
        (p.original && (p.original.cited_by_count || p.original.citations)) ||
        p.cited_by_count ||
        0;
      const n = parseInt(v, 10);
      return Number.isFinite(n) ? n : 0;
    };
    if (selectedSort === "recent") copy.sort((a, b) => yearOf(b) - yearOf(a));
    else if (selectedSort === "oldest")
      copy.sort((a, b) => yearOf(a) - yearOf(b));
    else if (selectedSort === "cited")
      copy.sort((a, b) => citedOf(b) - citedOf(a));
    return copy;
  }, [authorWorks, selectedSort]);

  async function fetchAuthorMetrics(key) {
    if (!key) return null;
    try {
      const res = await fetch(
        `${API}/autores/${encodeURIComponent(key)}/metrics`
      );
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  async function onSelectAuthor(a) {
    setSelectedAuthor(a);
    setAuthorWorks([]);
    setAuthorMetrics(null);
    setLoadingWorks(true);
    setLoadingMetrics(true);
    setError(null);

    const authorKey = a.id || a.orcid || "";

    // fetch metrics in background
    fetchAuthorMetrics(authorKey)
      .then((m) => {
        setAuthorMetrics(m);
        setLoadingMetrics(false);
      })
      .catch(() => setLoadingMetrics(false));

    // try works from author node
    if (a.works && Object.keys(a.works || {}).length > 0) {
      const arr = worksMapToArray(a.works);
      setAuthorWorks(
        arr.map((w) => {
          // Garantir que as publicações tenham a área de pesquisa do autor
          const work = { ...w };

          // Adicionar áreas de pesquisa do autor à publicação
          if (Array.isArray(a.research_areas) && a.research_areas.length > 0) {
            work.research_areas = a.research_areas;
          }

          return {
            id: w.id || w.W || w.key,
            title: w.title || w.titulo || w.name || "Sem título",
            year: w.year || w.ano || "",
            url:
              w.url || (w.open_access && w.open_access.oa_url) || w.doi || "",
            area: a.research_areas || [],
            original: work,
          };
        })
      );
      setLoadingWorks(false);
      setQuery(a.name || "");
      return;
    }

    // try backend endpoint /autores/{id}/produtos
    try {
      if (authorKey) {
        const res = await fetch(
          `${API}/autores/${encodeURIComponent(authorKey)}/produtos`
        );
        if (res.ok) {
          const data = await res.json();
          const normalized = normalizeMap(data);
          setAuthorWorks(
            normalized.map((p) => {
              // Garantir que as publicações tenham a área de pesquisa do autor
              const work = { ...p };

              // Adicionar áreas de pesquisa do autor à publicação
              if (
                Array.isArray(a.research_areas) &&
                a.research_areas.length > 0
              ) {
                work.research_areas = a.research_areas;
              }

              return {
                id: p.id || p._id,
                title: p.titulo || p.title || p.nome || "Sem título",
                year: p.ano || p.year || "",
                url: p.url || "",
                area: a.research_areas || [],
                original: work,
              };
            })
          );
          setLoadingWorks(false);
          setQuery(a.name || "");
          return;
        }
      }
    } catch (e) {
      // continue to fallback
    }

    // last fallback: RTDB /produtos
    try {
      const r = await fetch(`${RTDB_FALLBACK}/produtos.json`);
      if (r.ok) {
        const all = await r.json();
        const normalized = normalizeMap(all);
        const produtoIds =
          (a.produto_ids && Array.isArray(a.produto_ids)
            ? a.produto_ids
            : a.produto_id
            ? [a.produto_id]
            : []) || [];
        let matched = [];
        if (produtoIds.length > 0) {
          const idSet = new Set(produtoIds);
          matched = normalized.filter(
            (p) => idSet.has(p.id) || idSet.has(p._id)
          );
        } else {
          const nameLower = (a.name || "").trim().toLowerCase();
          matched = normalized.filter((p) => {
            if (!p) return false;
            if (Array.isArray(p.autores))
              return p.autores.some(
                (x) => (x || "").trim().toLowerCase() === nameLower
              );
            if (typeof p.autores === "string")
              return p.autores
                .split(",")
                .map((s) => s.trim().toLowerCase())
                .includes(nameLower);
            return false;
          });
        }
        setAuthorWorks(
          matched.map((p) => {
            // Garantir que as publicações tenham a área de pesquisa do autor
            const work = { ...p };

            // Adicionar áreas de pesquisa do autor à publicação
            if (
              Array.isArray(a.research_areas) &&
              a.research_areas.length > 0
            ) {
              work.research_areas = a.research_areas;
            }

            return {
              id: p.id || p._id,
              title: p.titulo || p.title || p.nome || "Sem título",
              year: p.ano || p.year || "",
              url: p.url || "",
              area: a.research_areas || [],
              original: work,
            };
          })
        );
        setLoadingWorks(false);
        setQuery(a.name || "");
        return;
      }
    } catch (e) {
      // final fail
    }

    setError("Não foi possível obter produções deste autor");
    setLoadingWorks(false);
    setQuery(a.name || "");
  }

  return (
    <>
      <div style={{ maxWidth: 980, margin: "0 auto", textAlign: "left" }}>
        <h2>Busca rápida (autores do sistema)</h2>

        <div
          style={{
            background: "#f9fafb",
            padding: "1rem",
            borderRadius: "8px",
            marginBottom: "1.5rem",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <div>
              <label
                style={{
                  display: "block",
                  marginBottom: "6px",
                  fontWeight: "500",
                  fontSize: "14px",
                }}
              >
                Filtrar por área de pesquisa:
              </label>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                }}
              >
                <select
                  value={selectedAreaFilter}
                  onChange={(e) => {
                    setSelectedAreaFilter(e.target.value);
                    setSelectedAuthor(null);
                    setAuthorWorks([]);
                  }}
                  style={{
                    flex: 1,
                    padding: "0.6rem 0.8rem",
                    borderRadius: 8,
                    border: "1px solid var(--input-border)",
                  }}
                >
                  <option value="">Todas as áreas</option>
                  {availableAreas.map((area) => (
                    <option key={area} value={area}>
                      {area}
                    </option>
                  ))}
                </select>
                {selectedAreaFilter && (
                  <button
                    onClick={() => setSelectedAreaFilter("")}
                    style={{
                      padding: "0.5rem",
                      background: "#f0f0f0",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                    }}
                  >
                    Limpar
                  </button>
                )}
              </div>
            </div>

            <div>
              <label
                style={{
                  display: "block",
                  marginBottom: "6px",
                  fontWeight: "500",
                  fontSize: "14px",
                }}
              >
                Buscar por nome ou ORCID:
              </label>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                }}
              >
                <input
                  aria-label="Pesquisar autor"
                  placeholder="Pesquisar autor..."
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setSelectedAuthor(null);
                    setAuthorWorks([]);
                  }}
                  style={{
                    flex: 1,
                    padding: "0.6rem 0.8rem",
                    borderRadius: 8,
                    border: "1px solid var(--input-border)",
                    boxSizing: "border-box",
                  }}
                />
                <button
                  onClick={() => {
                    if (suggestions.length === 1)
                      onSelectAuthor(suggestions[0]);
                  }}
                  style={{
                    padding: "0.55rem 1rem",
                    borderRadius: 8,
                    background: "var(--accent)",
                    color: "var(--accent-contrast)",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Buscar
                </button>
              </div>
            </div>
          </div>

          {(query || selectedAreaFilter) && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                marginTop: "0.5rem",
                padding: "0.5rem",
                background: "#f0f7ff",
                borderRadius: "6px",
              }}
            >
              <div style={{ flex: 1, fontSize: "14px" }}>
                <strong>Filtros aplicados:</strong>
                {selectedAreaFilter && (
                  <span
                    style={{
                      display: "inline-block",
                      margin: "0 8px",
                      padding: "3px 8px",
                      background: "#e6f7ff",
                      borderRadius: "4px",
                      border: "1px solid #91d5ff",
                    }}
                  >
                    Área: {selectedAreaFilter}
                  </span>
                )}
                {query && (
                  <span
                    style={{
                      display: "inline-block",
                      margin: "0 8px",
                      padding: "3px 8px",
                      background: "#e6f7ff",
                      borderRadius: "4px",
                      border: "1px solid #91d5ff",
                    }}
                  >
                    Busca: "{query}"
                  </span>
                )}
              </div>
              <button
                onClick={() => {
                  setQuery("");
                  setSelectedAreaFilter("");
                  setSelectedAuthor(null);
                  setAuthorWorks([]);
                }}
                style={{
                  padding: "4px 8px",
                  background: "#ff4d4f",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                Limpar filtros
              </button>
            </div>
          )}
        </div>

        {loadingAuthors && <div>Carregando autores...</div>}
        {error && <div style={{ color: "crimson" }}>{error}</div>}

        {(query || selectedAreaFilter) && suggestions.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div
              style={{
                fontSize: 16,
                fontWeight: 500,
                color: "var(--text)",
                marginBottom: 12,
              }}
            >
              Resultados da pesquisa ({suggestions.length})
            </div>
            <ul
              style={{
                paddingLeft: 16,
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
                gap: "10px",
              }}
            >
              {suggestions.map((s) => (
                <li key={s.id || s.orcid}>
                  <button
                    onClick={() => onSelectAuthor(s)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      background: "white",
                      border: "1px solid var(--card-border)",
                      padding: "0.75rem 1rem",
                      borderRadius: 8,
                      boxShadow: "0 2px 6px rgba(0,0,0,0.05)",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{s.name}</span>
                    {s.orcid && (
                      <span style={{ fontSize: "0.8rem", color: "#555" }}>
                        ORCID: {s.orcid}
                      </span>
                    )}
                    {Array.isArray(s.research_areas) &&
                      s.research_areas.length > 0 && (
                        <div
                          style={{
                            marginTop: "4px",
                            display: "flex",
                            gap: "4px",
                            flexWrap: "wrap",
                          }}
                        >
                          {s.research_areas.map((area, index) => (
                            <span
                              key={index}
                              style={{
                                fontSize: "0.75rem",
                                padding: "2px 6px",
                                background: "#e6f7ff",
                                color: "#1890ff",
                                borderRadius: "4px",
                                border: "1px solid #91d5ff",
                              }}
                            >
                              {area}
                            </span>
                          ))}
                        </div>
                      )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {selectedAuthor ? (
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <h3 style={{ margin: 0 }}>
                Produções de {selectedAuthor.name}
                {selectedAuthor.orcid ? ` — ${selectedAuthor.orcid}` : ""}
              </h3>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <label
                  style={{ fontSize: 13, color: "var(--muted)" }}
                  htmlFor="sort-select"
                >
                  Ordenar:
                </label>
                <select
                  id="sort-select"
                  value={selectedSort}
                  onChange={(e) => setSelectedSort(e.target.value)}
                  style={{
                    padding: "0.35rem 0.6rem",
                    borderRadius: 6,
                    border: "1px solid var(--input-border)",
                    background: "white",
                  }}
                >
                  <option value="recent">Mais recentes</option>
                  <option value="oldest">Mais antigas</option>
                  <option value="cited">Mais citadas</option>
                </select>
              </div>
            </div>

            {loadingWorks ? (
              <div>Carregando publicações...</div>
            ) : authorWorks.length === 0 ? (
              <div style={{ color: "var(--muted)", marginTop: 8 }}>
                Nenhuma produção encontrada para este autor.
              </div>
            ) : (
              <div
                style={{ display: "flex", gap: 18, alignItems: "flex-start" }}
              >
                <div style={{ flex: 1 }}>
                  <ul style={{ paddingLeft: 16 }}>
                    {sortedWorks.map((p) => (
                      <li
                        key={p.id || p.title}
                        style={{
                          marginBottom: 12,
                          borderBottom: "1px solid #f4f6fb",
                          paddingBottom: 8,
                        }}
                      >
                        <div style={{ fontWeight: 700 }}>{p.title}</div>
                        <div style={{ color: "#4b616e", fontSize: 14 }}>
                          Ano: {p.year}
                        </div>
                        <div style={{ marginTop: 6 }}>
                          {p.url && (
                            <a href={p.url} target="_blank" rel="noreferrer">
                              Abrir publicação
                            </a>
                          )}
                          <button
                            onClick={() => setSelectedWork(p)}
                            style={{
                              marginLeft: 10,
                              background: "transparent",
                              border: "none",
                              padding: 0,
                              color: "var(--accent)",
                              textDecoration: "underline",
                              cursor: "pointer",
                              fontSize: "0.95rem",
                            }}
                            aria-label="Ver detalhes da publicação"
                          >
                            Detalhes
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>

                <aside style={{ width: 300, flexShrink: 0 }}>
                  <div
                    style={{
                      background: "white",
                      padding: 12,
                      borderRadius: 8,
                      boxShadow: "0 6px 16px rgba(20,30,40,0.05)",
                      marginBottom: 12,
                      marginTop: 6,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        color: "var(--muted)",
                        marginBottom: 8,
                      }}
                    >
                      Métricas do autor
                    </div>
                    {loadingMetrics ? (
                      <div>Carregando métricas...</div>
                    ) : authorMetrics ? (
                      <div>
                        <div
                          style={{ display: "flex", gap: 8, marginBottom: 8 }}
                        >
                          <div style={{ flex: 1 }}>
                            <div
                              style={{ fontSize: 12, color: "var(--muted)" }}
                            >
                              Produções
                            </div>
                            <div style={{ fontWeight: 700, fontSize: 18 }}>
                              {authorMetrics.publications_count}
                            </div>
                          </div>
                          <div style={{ flex: 1 }}>
                            <div
                              style={{ fontSize: 12, color: "var(--muted)" }}
                            >
                              Citações
                            </div>
                            <div style={{ fontWeight: 700, fontSize: 18 }}>
                              {authorMetrics.total_citations}
                            </div>
                          </div>
                        </div>

                        <div
                          style={{ display: "flex", gap: 8, marginBottom: 8 }}
                        >
                          <div style={{ flex: 1 }}>
                            <div
                              style={{ fontSize: 12, color: "var(--muted)" }}
                            >
                              h-index
                            </div>
                            <div style={{ fontWeight: 700, fontSize: 18 }}>
                              {authorMetrics.h_index}
                            </div>
                          </div>
                          <div style={{ flex: 1 }}>
                            <div
                              style={{ fontSize: 12, color: "var(--muted)" }}
                            >
                              Período
                            </div>
                            <div style={{ fontWeight: 700, fontSize: 14 }}>
                              {authorMetrics.first_year || "-"} —{" "}
                              {authorMetrics.last_year || "-"}
                            </div>
                          </div>
                        </div>

                        <div style={{ marginTop: 6 }}>
                          <div
                            style={{
                              fontSize: 12,
                              color: "var(--muted)",
                              marginBottom: 6,
                            }}
                          >
                            Top conceitos
                          </div>
                          <div
                            style={{
                              display: "flex",
                              flexWrap: "wrap",
                              gap: 6,
                            }}
                          >
                            {authorMetrics.top_concepts &&
                            authorMetrics.top_concepts.length > 0 ? (
                              authorMetrics.top_concepts
                                .slice(0, 6)
                                .map(([c, n], i) => (
                                  <span
                                    key={i}
                                    style={{
                                      background: "#f6fbff",
                                      padding: "4px 8px",
                                      borderRadius: 12,
                                      fontSize: 12,
                                    }}
                                  >
                                    {c} ({n})
                                  </span>
                                ))
                            ) : (
                              <div style={{ color: "var(--muted)" }}>—</div>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div style={{ color: "var(--muted)" }}>
                        Métricas não disponíveis
                      </div>
                    )}
                  </div>
                </aside>
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: "var(--muted)", marginTop: 12 }}>
            Digite o nome de um autor e selecione para ver as produções.
          </div>
        )}
      </div>

      {selectedWork && (
        <DetailsModal
          work={selectedWork}
          onClose={() => setSelectedWork(null)}
        />
      )}
    </>
  );
}
