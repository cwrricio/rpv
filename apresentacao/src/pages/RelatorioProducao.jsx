import React, { useMemo, useState, useEffect } from "react";
import { Bar } from "react-chartjs-2";
import "./RelatorioProducao.css";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import TeacherProvider, {
  useTeachers,
} from "../components/teacher/TeacherContext";
import QualisBadge from "../components/ui/QualisBadge";
import "../components/ui/QualisBadge.css";
import AreaBadge from "../components/ui/AreaBadge";
import "../components/ui/AreaBadge.css";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

// Modal de detalhes da publicação reutilizado da Home
function PublicationDetailsModal({ work, onClose }) {
  if (!work) return null;
  const w = work.raw || work;
  const doi = w.doi || w.DOI || (w.open_access && w.open_access.oa_url) || null;
  const cited = w.citacoes ?? w.cited_by_count ?? w.citations ?? null;
  const concepts = Array.isArray(w.concepts) ? w.concepts : w.topics || [];
  const authorships = w.autores || w.authorships || w.authors || [];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{work.titulo || w.title || "Detalhes da Publicação"}</h3>
          <button
            onClick={onClose}
            aria-label="Fechar"
            className="modal-close-btn"
          >
            Fechar
          </button>
        </div>

        <div className="modal-body">
          <div className="detail-flex-row">
            <div>
              <strong>Ano:</strong> {work.ano || w.year || "-"}
            </div>
            <div>
              <strong>Citações:</strong> {cited ?? "-"}
            </div>
            <div>
              <strong>Tipo:</strong> {work.tipo || w.type || "-"}
            </div>
          </div>

          <div className="detail-item">
            <strong>Veículo:</strong>{" "}
            {work.veiculo || w.host_venue?.display_name || "-"}
          </div>

          <div className="detail-item">
            <strong>Qualis:</strong> {work.qualis || "-"}
          </div>

          <div className="detail-item">
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

          <div className="detail-item">
            <strong>Conceitos:</strong>
            <div className="tags-container">
              {Array.isArray(concepts) && concepts.length > 0
                ? concepts.map((c, i) => (
                    <span key={i} className="concept-tag">
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

          <div className="detail-item">
            <strong>Autores:</strong>
            <div>
              {Array.isArray(authorships) && authorships.length > 0 ? (
                <ol className="authors-list">
                  {authorships.map((au, i) => (
                    <li key={i}>
                      {typeof au === "string"
                        ? au
                        : au.author_name || au.name || JSON.stringify(au)}
                    </li>
                  ))}
                </ol>
              ) : (
                " -"
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Modal para filtros
function FilterModal({ title, options, selected, onChange, onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-content filter-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3>{title}</h3>
          <button onClick={onClose} className="modal-close-btn">
            Fechar
          </button>
        </div>
        <div className="modal-body filter-options-container">
          {options.length === 0 ? (
            <p className="no-options">Nenhuma opção disponível</p>
          ) : (
            options.map((option) => {
              const value = typeof option === "object" ? option.id : option;
              const label =
                typeof option === "object"
                  ? option.nome || option.name
                  : option;

              return (
                <label key={value} className="filter-checkbox">
                  <input
                    type="checkbox"
                    checked={selected.includes(value)}
                    onChange={() => onChange(value)}
                  />
                  <span>{label}</span>
                </label>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

// Componente principal (observer)
function RelatorioContent() {
  // Estado central do componente (Subject no padrão Observer)
  const [filtros, setFiltros] = useState({
    areas: [],
    qualis: [],
    anos: [],
    quads: [],
    professores: [],
  });

  const [autoresFlat, setAutoresFlat] = useState([]);
  const [producoes, setProducoes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedProduction, setSelectedProduction] = useState(null);
  const [activeFilter, setActiveFilter] = useState(null);
  const [ordenacao, setOrdenacao] = useState({
    campo: "ano",
    direcao: "desc", // 'asc' ou 'desc'
  });

  const { teachers } = useTeachers(); // Acessa os professores via TeacherContext

  const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    ""
  );
  const RTDB_FALLBACK = (
    import.meta.env.VITE_RTDB_URL ||
    "https://poshboard-default-rtdb.firebaseio.com"
  ).replace(/\/$/, "");

  // Carrega autores e produções (assinatura para os eventos/observable data sources)
  useEffect(() => {
    let mounted = true;
    setIsLoading(true);

    async function fetchData() {
      try {
        // Busca autores_flat (contém informações de autores com obras)
        const autoresRes = await fetch(`${API}/autores_flat`);
        let autoresData = [];

        if (autoresRes.ok) {
          const json = await autoresRes.json();
          autoresData = Array.isArray(json)
            ? json
            : Object.keys(json || {})
                .filter((k) => k !== "_")
                .map((k) => ({ id: k, ...json[k] }));
        } else {
          // Fallback para RTDB
          const fallbackRes = await fetch(`${RTDB_FALLBACK}/autores_flat.json`);
          if (fallbackRes.ok) {
            const json = await fallbackRes.json();
            autoresData = Object.keys(json || {})
              .filter((k) => k !== "_")
              .map((k) => ({ id: k, ...json[k] }));
          }
        }

        // Extrair produções dos autores
        const todasProducoes = [];
        // Usar um Set para controlar IDs já processados e evitar duplicação
        const processedWorkIds = new Set();

        autoresData.forEach((autor) => {
          const works = autor.works || {};

          // Normaliza works de objeto para array
          const worksArray = Array.isArray(works)
            ? works
            : Object.keys(works)
                .filter((k) => k !== "_")
                .map((k) => ({ id: k, ...works[k] }));

          worksArray.forEach((work) => {
            // Verificar se já processamos este trabalho para evitar duplicações
            const workId = work.id || work.DOI || work.doi;
            if (processedWorkIds.has(workId)) {
              return; // Pular este trabalho, já foi adicionado
            }
            processedWorkIds.add(workId);

            todasProducoes.push({
              id: workId,
              titulo: work.title || work.titulo || work.name || "Sem título",
              professor:
                autor.nome ||
                autor.name ||
                autor.display_name ||
                "Desconhecido",
              professorId: autor.id,
              ano: work.year || work.ano || work.publication_year || null,
              tipo: work.type || work.tipo || "Não especificado",
              veiculo:
                work.host_venue?.display_name ||
                work.veiculo ||
                work.venue ||
                "Não especificado",
              qualis: work.qualis || "Não classificado",
              citacoes: work.cited_by_count || work.citations || 0,
              doi: work.doi || null,
              url: work.url || null,
              autores: Array.isArray(work.authorships)
                ? work.authorships
                    .map((a) =>
                      typeof a === "string"
                        ? a
                        : a.author?.display_name || a.name || ""
                    )
                    .filter(Boolean)
                : typeof work.autores === "string"
                ? work.autores
                    .split(",")
                    .map((a) => a.trim())
                    .filter(Boolean)
                : [],
              area: autor.research_areas
                ? Array.isArray(autor.research_areas)
                  ? autor.research_areas
                  : [autor.research_areas]
                : autor.research
                ? Array.isArray(autor.research)
                  ? autor.research
                  : [autor.research]
                : autor.linha_pesquisa
                ? Array.isArray(autor.linha_pesquisa)
                  ? autor.linha_pesquisa
                  : [autor.linha_pesquisa]
                : ["Não especificada"],
              raw: work,
            });
          });
        });

        if (mounted) {
          setAutoresFlat(autoresData);
          setProducoes(todasProducoes);
          setIsLoading(false);
        }
      } catch (error) {
        console.error("Erro ao buscar dados:", error);
        if (mounted) setIsLoading(false);
      }
    }

    fetchData();
    return () => {
      mounted = false;
    };
  }, [API, RTDB_FALLBACK]);

  // Listas para os filtros (derivadas do estado central - observable)
  const areas = useMemo(() => {
    // Combina áreas de teachers e de autoresFlat para não perder informações
    const areasSet = new Set();

    // De teachers
    teachers.forEach((t) => {
      // Verifica research_areas primeiro
      if (Array.isArray(t.research_areas)) {
        t.research_areas.forEach((r) => areasSet.add(r));
      } else if (t.research_areas) {
        areasSet.add(t.research_areas);
      }
      // Verifica research (compatibilidade)
      else if (Array.isArray(t.research)) {
        t.research.forEach((r) => areasSet.add(r));
      } else if (t.research) {
        areasSet.add(t.research);
      }
    });

    // De autores_flat
    autoresFlat.forEach((a) => {
      // Verifica research_areas primeiro
      if (Array.isArray(a.research_areas)) {
        a.research_areas.forEach((r) => areasSet.add(r));
      } else if (a.research_areas) {
        areasSet.add(a.research_areas);
      }
      // Verifica research (compatibilidade)
      else if (Array.isArray(a.research)) {
        a.research.forEach((r) => areasSet.add(r));
      } else if (a.research) {
        areasSet.add(a.research);
      }

      if (a.linha_pesquisa) {
        if (Array.isArray(a.linha_pesquisa)) {
          a.linha_pesquisa.forEach((l) => areasSet.add(l));
        } else {
          areasSet.add(a.linha_pesquisa);
        }
      }
    });

    // Também buscar de produções
    producoes.forEach((p) => {
      if (Array.isArray(p.area)) {
        p.area.forEach((a) => areasSet.add(a));
      } else if (p.area) {
        areasSet.add(p.area);
      }
    });

    // Se não houver áreas, adicionar valores padrão
    if (areasSet.size === 0) {
      [
        "Inteligência Artificial",
        "Sistemas Embarcados",
        "Engenharia de Software",
        "Ciência de Dados",
      ].forEach((a) => areasSet.add(a));
    }

    return [...areasSet].sort();
  }, [teachers, autoresFlat, producoes]);

  const anosDisponiveis = useMemo(() => {
    const anosSet = new Set();
    producoes.forEach((p) => {
      if (p.ano) anosSet.add(parseInt(p.ano));
    });
    return [...anosSet].sort((a, b) => b - a); // Ordenação decrescente
  }, [producoes]);

  const qualis = useMemo(() => {
    const qualisSet = new Set();
    producoes.forEach((p) => {
      if (p.qualis && p.qualis !== "Não classificado") qualisSet.add(p.qualis);
    });

    // Se não houver qualis, adicionar valores padrão
    if (qualisSet.size === 0) {
      ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "C"].forEach((q) =>
        qualisSet.add(q)
      );
    }

    return [...qualisSet].sort();
  }, [producoes]);

  const quadsDisponiveis = useMemo(() => {
    const quadsSet = new Set();
    anosDisponiveis.forEach((ano) => {
      const inicio = Math.floor((ano - 1) / 4) * 4 + 1;
      const fim = inicio + 3;
      quadsSet.add(`${inicio}-${fim}`);
    });
    return [...quadsSet].sort((a, b) => {
      const anoA = parseInt(a.split("-")[0]);
      const anoB = parseInt(b.split("-")[0]);
      return anoB - anoA; // Ordenação decrescente
    });
  }, [anosDisponiveis]);

  const professoresDisponiveis = useMemo(() => {
    const professoresSet = new Set();
    const idSet = new Set();

    // Combina teachers e autores das produções
    [...teachers, ...autoresFlat].forEach((t) => {
      const id = t.id;
      const nome = t.nome || t.name || t.display_name || "";

      if (id && nome && !idSet.has(id)) {
        idSet.add(id);
        professoresSet.add({ id, nome });
      }
    });

    return [...professoresSet].sort((a, b) => a.nome.localeCompare(b.nome));
  }, [teachers, autoresFlat]);

  // Filtragem de produções (Observer: reage às mudanças no estado dos filtros)
  const producoesFiltradas = useMemo(() => {
    let result = [...producoes];

    // Filtro de professores
    if (filtros.professores.length > 0) {
      result = result.filter((p) => {
        const prof = professoresDisponiveis.find((prof) =>
          filtros.professores.includes(prof.id)
        );
        return prof && (p.professor === prof.nome || p.professorId === prof.id);
      });
    }

    // Filtro de áreas - agora suporta múltiplas áreas por publicação
    if (filtros.areas.length > 0) {
      result = result.filter((p) => {
        // Se a área estiver em formato de array, verificamos se alguma das áreas da publicação está nos filtros
        if (Array.isArray(p.area)) {
          return p.area.some((area) => filtros.areas.includes(area));
        }
        // Para compatibilidade com o formato antigo (string simples)
        return filtros.areas.includes(p.area);
      });
    }

    // Filtro de qualis
    if (filtros.qualis.length > 0) {
      result = result.filter((p) => filtros.qualis.includes(p.qualis));
    }

    // Filtro de anos
    if (filtros.anos.length > 0) {
      result = result.filter(
        (p) => p.ano && filtros.anos.includes(parseInt(p.ano))
      );
    }

    // Filtro de quadriênios
    if (filtros.quads.length > 0) {
      result = result.filter((p) => {
        if (!p.ano) return false;
        const ano = parseInt(p.ano);
        const quad = `${Math.floor((ano - 1) / 4) * 4 + 1}-${
          Math.floor((ano - 1) / 4) * 4 + 4
        }`;
        return filtros.quads.includes(quad);
      });
    }

    // Ordenação
    result.sort((a, b) => {
      let valA, valB;
      switch (ordenacao.campo) {
        case "titulo":
          valA = a.titulo || "";
          valB = b.titulo || "";
          return ordenacao.direcao === "asc"
            ? valA.localeCompare(valB)
            : valB.localeCompare(valA);
        case "professor":
          valA = a.professor || "";
          valB = b.professor || "";
          return ordenacao.direcao === "asc"
            ? valA.localeCompare(valB)
            : valB.localeCompare(valA);
        case "ano":
          valA = a.ano ? parseInt(a.ano) : 0;
          valB = b.ano ? parseInt(b.ano) : 0;
          return ordenacao.direcao === "asc" ? valA - valB : valB - valA;
        case "citacoes":
          valA = a.citacoes ? parseInt(a.citacoes) : 0;
          valB = b.citacoes ? parseInt(b.citacoes) : 0;
          return ordenacao.direcao === "asc" ? valA - valB : valB - valA;
        case "qualis":
          return ordenarPorQualis(a, b, ordenacao.direcao);
        default:
          return 0;
      }
    });

    return result;
  }, [producoes, filtros, ordenacao, professoresDisponiveis]);

  // Dados para o gráfico (observer que reage às mudanças nas produções filtradas)
  const dadosGrafico = useMemo(() => {
    const porAno = {};
    const porProfessor = {};

    // Agrupar por ano
    producoesFiltradas.forEach((p) => {
      if (p.ano) {
        porAno[p.ano] = porAno[p.ano] || 0;
        porAno[p.ano]++;
      }

      if (p.professor) {
        porProfessor[p.professor] = porProfessor[p.professor] || 0;
        porProfessor[p.professor]++;
      }
    });

    // Ordenar anos para melhor visualização
    const anosOrdenados = Object.keys(porAno).sort();

    return {
      labels: anosOrdenados,
      datasets: [
        {
          label: "Publicações",
          data: anosOrdenados.map((ano) => porAno[ano]),
          backgroundColor: "var(--accent)",
          borderColor: "var(--accent-dark)",
          borderWidth: 1,
        },
      ],
    };
  }, [producoesFiltradas]);

  // Handlers (atualizam o estado central - subject)
  function handleCheckbox(tipo, valor) {
    setFiltros((prev) => {
      const atual = prev[tipo];
      return {
        ...prev,
        [tipo]: atual.includes(valor)
          ? atual.filter((v) => v !== valor)
          : [...atual, valor],
      };
    });
  }

  function handleOpenFilter(filtroTipo) {
    setActiveFilter(filtroTipo);
  }

  // Função para obter o título do filtro ativo
  function getFilterTitle(filtroTipo) {
    const titulos = {
      areas: "Áreas",
      qualis: "Qualis",
      anos: "Anos",
      quads: "Quadriênios",
      professores: "Professores",
    };
    return titulos[filtroTipo] || filtroTipo;
  }

  // Função para obter as opções do filtro ativo
  function getFilterOptions() {
    switch (activeFilter) {
      case "areas":
        return areas
          .map((area) => ({ value: area, label: area }))
          .sort((a, b) => a.label.localeCompare(b.label));
      case "qualis":
        // Ordenação específica para Qualis: A1, A2, A3, A4, B1, B2, B3, B4, C
        const qualisOrdem = {
          A1: 1,
          A2: 2,
          A3: 3,
          A4: 4,
          B1: 5,
          B2: 6,
          B3: 7,
          B4: 8,
          C: 9,
        };
        return qualis
          .map((q) => ({ value: q, label: q }))
          .sort((a, b) => {
            // Se ambos forem qualis padrão, usamos a ordem específica
            if (qualisOrdem[a.value] && qualisOrdem[b.value]) {
              return qualisOrdem[a.value] - qualisOrdem[b.value];
            }
            // Caso contrário, ordem alfabética
            return a.label.localeCompare(b.label);
          });
      case "anos":
        return anosDisponiveis
          .map((ano) => ({
            value: ano,
            label: ano.toString(),
          }))
          .sort((a, b) => b.value - a.value); // Anos em ordem decrescente
      case "quads":
        return quadsDisponiveis
          .map((quad) => ({ value: quad, label: quad }))
          .sort((a, b) => {
            const anoA = parseInt(a.value.split("-")[0]);
            const anoB = parseInt(b.value.split("-")[0]);
            return anoB - anoA; // Quadriênios em ordem decrescente
          });
      case "professores":
        return professoresDisponiveis
          .map((prof) => ({
            value: prof.id,
            label: prof.nome,
          }))
          .sort((a, b) => a.label.localeCompare(b.label)); // Professores em ordem alfabética
      default:
        return [];
    }
  }

  function handleCloseFilter() {
    setActiveFilter(null);
  }

  function getFilterLabel(filtroTipo) {
    const count = filtros[filtroTipo].length;
    return count > 0 ? `${count} selecionado${count > 1 ? "s" : ""}` : "Todos";
  }

  function handleLimparFiltros() {
    setFiltros({
      areas: [],
      qualis: [],
      anos: [],
      quads: [],
      professores: [],
    });
  }

  // Função para lidar com a ordenação
  function handleOrdenar(campo) {
    setOrdenacao((prev) => ({
      campo,
      direcao: prev.campo === campo && prev.direcao === "asc" ? "desc" : "asc",
    }));
  }

  // Função para ordenar por qualis
  function ordenarPorQualis(a, b, direcao) {
    // Ordem específica para qualis
    const qualisOrdem = {
      A1: 1,
      A2: 2,
      A3: 3,
      A4: 4,
      B1: 5,
      B2: 6,
      B3: 7,
      B4: 8,
      C: 9,
      "Não classificado": 10,
    };

    const valorA = qualisOrdem[a.qualis] || 999;
    const valorB = qualisOrdem[b.qualis] || 999;

    return direcao === "asc" ? valorA - valorB : valorB - valorA;
  }

  // Função para obter a classe de ordenação
  function getSortClass(campo) {
    if (ordenacao.campo !== campo) return "";
    return ordenacao.direcao === "asc" ? "sort-asc" : "sort-desc";
  }

  return (
    <div className="relatorio-producao">
      <h2>Relatório de Produções Acadêmicas</h2>

      {isLoading ? (
        <div className="loading-indicator">Carregando dados...</div>
      ) : (
        <>
          <div className="filter-container">
            <h3>Filtros Aplicados</h3>
            <div className="filter-buttons">
              <div className="filter-row">
                <div className="filter-btn-group">
                  <button
                    className={`btn filter-btn ${
                      filtros.areas.length > 0 ? "active-filter" : ""
                    }`}
                    onClick={() => handleOpenFilter("areas")}
                  >
                    <span className="filter-btn-label">Áreas</span>
                    <span className="filter-btn-count">
                      {getFilterLabel("areas")}
                    </span>
                  </button>

                  <button
                    className={`btn filter-btn ${
                      filtros.professores.length > 0 ? "active-filter" : ""
                    }`}
                    onClick={() => handleOpenFilter("professores")}
                  >
                    <span className="filter-btn-label">Professores</span>
                    <span className="filter-btn-count">
                      {getFilterLabel("professores")}
                    </span>
                  </button>

                  <button
                    className={`btn filter-btn ${
                      filtros.anos.length > 0 ? "active-filter" : ""
                    }`}
                    onClick={() => handleOpenFilter("anos")}
                  >
                    <span className="filter-btn-label">Anos</span>
                    <span className="filter-btn-count">
                      {getFilterLabel("anos")}
                    </span>
                  </button>

                  <button
                    className={`btn filter-btn ${
                      filtros.quads.length > 0 ? "active-filter" : ""
                    }`}
                    onClick={() => handleOpenFilter("quads")}
                  >
                    <span className="filter-btn-label">Quadriênios</span>
                    <span className="filter-btn-count">
                      {getFilterLabel("quads")}
                    </span>
                  </button>

                  <button
                    className={`btn filter-btn ${
                      filtros.qualis.length > 0 ? "active-filter" : ""
                    }`}
                    onClick={() => handleOpenFilter("qualis")}
                  >
                    <span className="filter-btn-label">Qualis</span>
                    <span className="filter-btn-count">
                      {getFilterLabel("qualis")}
                    </span>
                  </button>
                </div>
              </div>

              {(filtros.areas.length > 0 ||
                filtros.professores.length > 0 ||
                filtros.anos.length > 0 ||
                filtros.quads.length > 0 ||
                filtros.qualis.length > 0) && (
                <div className="filters-summary">
                  <div className="active-filters">
                    <h4>Filtros ativos:</h4>
                    <div className="active-filters-list">
                      {filtros.areas.length > 0 && (
                        <div className="active-filter-item">
                          <span>Áreas:</span>
                          {filtros.areas.map((area, idx) => (
                            <AreaBadge key={idx} area={area} />
                          ))}
                        </div>
                      )}
                      {filtros.qualis.length > 0 && (
                        <div className="active-filter-item">
                          <span>Qualis:</span>
                          {filtros.qualis.map((q, idx) => (
                            <QualisBadge key={idx} qualis={q} />
                          ))}
                        </div>
                      )}
                      {filtros.professores.length > 0 && (
                        <div className="active-filter-item">
                          <span>Professores:</span>
                          {filtros.professores
                            .map((id) => {
                              const prof = professoresDisponiveis.find(
                                (p) => p.id === id
                              );
                              return prof ? prof.nome : id;
                            })
                            .join(", ")}
                        </div>
                      )}
                      {filtros.anos.length > 0 && (
                        <div className="active-filter-item">
                          <span>Anos:</span> {filtros.anos.join(", ")}
                        </div>
                      )}
                      {filtros.quads.length > 0 && (
                        <div className="active-filter-item">
                          <span>Quadriênios:</span> {filtros.quads.join(", ")}
                        </div>
                      )}
                    </div>
                  </div>

                  <button className="btn danger" onClick={handleLimparFiltros}>
                    Limpar todos os filtros
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Seção do gráfico foi removida conforme solicitado */}

          <section className="publications-section">
            <h3>Publicações ({producoesFiltradas.length})</h3>

            <div className="order-controls">
              <span className="order-label">Ordenar por:</span>
              <div className="order-buttons">
                <button
                  className={`btn order-btn ${getSortClass("titulo")}`}
                  onClick={() => handleOrdenar("titulo")}
                >
                  Título
                </button>
                <button
                  className={`btn order-btn ${getSortClass("professor")}`}
                  onClick={() => handleOrdenar("professor")}
                >
                  Professor
                </button>
                <button
                  className={`btn order-btn ${getSortClass("ano")}`}
                  onClick={() => handleOrdenar("ano")}
                >
                  Ano
                </button>
                <button
                  className={`btn order-btn ${getSortClass("citacoes")}`}
                  onClick={() => handleOrdenar("citacoes")}
                >
                  Citações
                </button>
                <button
                  className={`btn order-btn ${getSortClass("qualis")}`}
                  onClick={() => handleOrdenar("qualis")}
                >
                  Qualis
                </button>
              </div>
            </div>

            {producoesFiltradas.length === 0 ? (
              <div className="no-data-message">
                Nenhuma publicação encontrada com os filtros atuais
              </div>
            ) : (
              <div className="publications-table-container">
                <table className="publications-table">
                  <thead>
                    <tr>
                      <th
                        className={`sortable ${getSortClass("titulo")}`}
                        onClick={() => handleOrdenar("titulo")}
                      >
                        Título
                        <span className="sort-icon"></span>
                      </th>
                      <th
                        className={`sortable ${getSortClass("professor")}`}
                        onClick={() => handleOrdenar("professor")}
                      >
                        Professor
                        <span className="sort-icon"></span>
                      </th>
                      <th
                        className={`sortable ${getSortClass("ano")}`}
                        onClick={() => handleOrdenar("ano")}
                      >
                        Ano
                        <span className="sort-icon"></span>
                      </th>
                      <th>Quadriênio</th>
                      <th>Área</th>
                      <th
                        className={`sortable ${getSortClass("qualis")}`}
                        onClick={() => handleOrdenar("qualis")}
                      >
                        Qualis
                        <span className="sort-icon"></span>
                      </th>
                      <th
                        className={`sortable ${getSortClass("citacoes")}`}
                        onClick={() => handleOrdenar("citacoes")}
                      >
                        Citações
                        <span className="sort-icon"></span>
                      </th>
                      <th>Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {producoesFiltradas.map((p) => {
                      const quad = p.ano
                        ? `${Math.floor((p.ano - 1) / 4) * 4 + 1}-${
                            Math.floor((p.ano - 1) / 4) * 4 + 4
                          }`
                        : "N/A";

                      // Mostrar apenas o primeiro autor na tabela principal
                      const primeiroAutor =
                        p.autores && p.autores.length > 0
                          ? p.autores[0]
                          : p.professor;

                      // Vamos usar o componente AreaBadge para exibição

                      return (
                        <tr
                          key={p.id}
                          className={
                            selectedProduction?.id === p.id
                              ? "selected-row"
                              : ""
                          }
                        >
                          <td>{p.titulo}</td>
                          <td>{primeiroAutor}</td>
                          <td>{p.ano || "—"}</td>
                          <td>{quad}</td>
                          <td>
                            <AreaBadge area={p.area} limit={1} />
                          </td>
                          <td>
                            <QualisBadge qualis={p.qualis} />
                          </td>
                          <td>{p.citacoes}</td>
                          <td>
                            <button
                              className="btn action-btn"
                              onClick={() => setSelectedProduction(p)}
                            >
                              Detalhes
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Modal de detalhes da publicação */}
          {selectedProduction && (
            <div
              className="modal-backdrop"
              onClick={() => setSelectedProduction(null)}
            >
              <div
                className="modal-content"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="modal-header">
                  <h3>{selectedProduction.titulo}</h3>
                  <button
                    className="modal-close-btn"
                    onClick={() => setSelectedProduction(null)}
                  >
                    Fechar
                  </button>
                </div>

                <div className="modal-body">
                  <div className="details-grid">
                    <div className="detail-item">
                      <span className="detail-label">Autores:</span>
                      <div className="detail-value autores-lista">
                        {selectedProduction.autores?.length > 0 ? (
                          <ol className="authors-list">
                            {selectedProduction.autores.map((autor, index) => (
                              <li key={index}>{autor}</li>
                            ))}
                          </ol>
                        ) : (
                          selectedProduction.professor
                        )}
                      </div>
                    </div>

                    <div className="detail-item">
                      <span className="detail-label">Tipo:</span>
                      <span className="detail-value">
                        {selectedProduction.tipo}
                      </span>
                    </div>

                    <div className="detail-item">
                      <span className="detail-label">Veículo:</span>
                      <span className="detail-value">
                        {selectedProduction.veiculo}
                      </span>
                    </div>

                    <div className="detail-item">
                      <span className="detail-label">Qualis:</span>
                      <span className="detail-value">
                        <QualisBadge qualis={selectedProduction.qualis} />
                      </span>
                    </div>

                    <div className="detail-item">
                      <span className="detail-label">Área(s) de Pesquisa:</span>
                      <div className="detail-value">
                        <AreaBadge
                          area={selectedProduction.area}
                          showAll={true}
                        />
                      </div>
                    </div>

                    <div className="detail-item">
                      <span className="detail-label">Citações:</span>
                      <span className="detail-value">
                        {selectedProduction.citacoes}
                      </span>
                    </div>

                    {selectedProduction.doi && (
                      <div className="detail-item">
                        <span className="detail-label">DOI:</span>
                        <a
                          href={`https://doi.org/${selectedProduction.doi}`}
                          target="_blank"
                          rel="noreferrer"
                          className="detail-link"
                        >
                          {selectedProduction.doi}
                        </a>
                      </div>
                    )}

                    {selectedProduction.url && (
                      <div className="detail-item">
                        <span className="detail-label">URL:</span>
                        <a
                          href={selectedProduction.url}
                          target="_blank"
                          rel="noreferrer"
                          className="detail-link"
                        >
                          Acessar publicação
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Modais de filtro */}
          {activeFilter && (
            <div className="modal-backdrop">
              <div
                className="modal-content filter-modal"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="modal-header">
                  <h3>Filtrar por {getFilterTitle(activeFilter)}</h3>
                  <button
                    className="modal-close-btn"
                    onClick={handleCloseFilter}
                  >
                    Fechar
                  </button>
                </div>
                <div className="modal-body">
                  <div className="filter-options scrollable">
                    {getFilterOptions().map((option) => (
                      <label key={option.value} className="filter-checkbox">
                        <input
                          type="checkbox"
                          checked={filtros[activeFilter].includes(option.value)}
                          onChange={() =>
                            handleCheckbox(activeFilter, option.value)
                          }
                        />
                        <span>{option.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="modal-footer">
                  <button className="btn primary" onClick={handleCloseFilter}>
                    Aplicar
                  </button>
                  <button
                    className="btn secondary"
                    onClick={() => {
                      setFiltros({
                        ...filtros,
                        [activeFilter]: [],
                      });
                    }}
                  >
                    Limpar filtro
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Wrapper para providenciar o contexto do TeacherProvider
export default function RelatorioProducao() {
  return (
    <TeacherProvider>
      <RelatorioContent />
    </TeacherProvider>
  );
}
