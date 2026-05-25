import React, { useState, useEffect, useMemo } from "react";
import {
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from "recharts";
import "./Qualis.css";

const QUALIS_ORDEM = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "C"];

const QUALIS_CORES = {
  A1: "#4CAF50", // Verde
  A2: "#8BC34A", // Verde claro
  A3: "#CDDC39", // Lima
  A4: "#FFEB3B", // Amarelo
  B1: "#FFC107", // Âmbar
  B2: "#FF9800", // Laranja
  B3: "#FF5722", // Laranja escuro
  B4: "#F44336", // Vermelho
  C: "#9E9E9E", // Cinza
};

export default function Qualis() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [docentes, setDocentes] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [veiculos, setVeiculos] = useState({});
  const [selectedProfessors, setSelectedProfessors] = useState([]);
  const [areaFilter, setAreaFilter] = useState("todas");

  // Função para inspecionar e transformar propriedades de veículos
  const inspecionarVeiculos = (veiculosData) => {
    console.log("Inspeção detalhada de veículos");

    // Verificar quais campos de Qualis existem
    const camposQualis = new Set();
    Object.values(veiculosData).forEach((veiculo) => {
      if (veiculo && typeof veiculo === "object") {
        Object.keys(veiculo).forEach((key) => {
          if (key.toLowerCase().includes("qualis")) {
            camposQualis.add(key);
          }
        });
      }
    });

    console.log("Campos relacionados a Qualis encontrados:", [...camposQualis]);

    // Contar valores de Qualis
    const contadorQualis = {};
    Object.values(veiculosData).forEach((veiculo) => {
      if (veiculo && typeof veiculo === "object" && veiculo.qualis) {
        const qualis = veiculo.qualis;
        contadorQualis[qualis] = (contadorQualis[qualis] || 0) + 1;
      }
    });

    console.log("Contagem de valores de Qualis:", contadorQualis);
    return camposQualis;
  };

  // Buscar dados do Firebase
  useEffect(() => {
    const RTDB_URL =
      import.meta.env.VITE_RTDB_URL ||
      "https://poshbard-default-rtdb.firebaseio.com";
    const API = "http://127.0.0.1:8000";

    const fetchData = async () => {
      try {
        setLoading(true);

        // Buscar autores_flat (dados completos de professores)
        let autoresData = null;

        // Tentar diferentes endpoints para autores
        const autoresCandidates = [
          `${RTDB_URL}/autores_flat.json`,
          `${RTDB_URL}/autores.json`,
          `${API}/autores_flat`,
        ];

        for (const url of autoresCandidates) {
          try {
            console.log("Tentando buscar autores de:", url);
            const res = await fetch(url);
            if (res.ok) {
              autoresData = await res.json();
              console.log("Sucesso ao buscar autores de:", url);
              break;
            }
          } catch (e) {
            console.log("Erro ao buscar autores de:", url, e);
            // continuar para o próximo candidato
          }
        }

        if (!autoresData) throw new Error("Erro ao buscar autores");

        // Buscar produtos (publicações)
        let produtosData = null;
        const produtosCandidates = [
          `${RTDB_URL}/produtos.json`,
          `${API}/produtos`,
        ];

        for (const url of produtosCandidates) {
          try {
            console.log("Tentando buscar produtos de:", url);
            const res = await fetch(url);
            if (res.ok) {
              produtosData = await res.json();
              console.log("Sucesso ao buscar produtos de:", url);
              break;
            }
          } catch (e) {
            console.log("Erro ao buscar produtos de:", url, e);
          }
        }

        if (!produtosData) throw new Error("Erro ao buscar produtos");

        // Buscar veículos (para obter Qualis)
        let veiculosData = null;
        const veiculosCandidates = [
          `${RTDB_URL}/veiculos.json`,
          `${API}/veiculos`,
        ];

        for (const url of veiculosCandidates) {
          try {
            console.log("Tentando buscar veículos de:", url);
            const res = await fetch(url);
            if (res.ok) {
              veiculosData = await res.json();
              console.log("Sucesso ao buscar veículos de:", url);
              break;
            }
          } catch (e) {
            console.log("Erro ao buscar veículos de:", url, e);
          }
        }

        if (!veiculosData) throw new Error("Erro ao buscar veículos");

        // Processar docentes a partir de autores_flat
        const docentesArray = Object.entries(autoresData)
          .filter(([key, data]) => key !== "_" && data?.nome)
          .map(([id, data]) => ({
            id,
            ...data,
            nome: data.nome || id.replace(/_/g, " "),
            areas: Array.isArray(data.research_areas)
              ? data.research_areas
              : data.research_areas
              ? [data.research_areas]
              : Array.isArray(data.research)
              ? data.research
              : data.research
              ? [data.research]
              : Array.isArray(data.linha_pesquisa)
              ? data.linha_pesquisa
              : data.linha_pesquisa
              ? [data.linha_pesquisa]
              : [],
          }));

        // Processar produtos
        const produtosArray = Object.entries(produtosData)
          .filter(([key]) => key !== "_")
          .map(([id, data]) => {
            // Buscar o veiculo_id em várias propriedades possíveis
            let veiculoId = null;

            if (data.veiculo_id) {
              veiculoId = data.veiculo_id;
            } else if (data.veiculo) {
              veiculoId = data.veiculo;
            } else if (data.journal_id) {
              veiculoId = data.journal_id;
            } else if (data.venue_id) {
              veiculoId = data.venue_id;
            }

            return {
              id,
              ...data,
              titulo: data.titulo || data.title || "Título não especificado",
              ano: data.ano || data.year || "Ano não especificado",
              veiculo_id: veiculoId,
            };
          });

        // Verificar produtos com veículos
        const totalProdutosComVeiculos = produtosArray.filter(
          (p) => p.veiculo_id
        ).length;
        console.log(
          `Produtos processados: ${produtosArray.length}, com veiculo_id: ${totalProdutosComVeiculos}`
        );
        if (totalProdutosComVeiculos > 0) {
          const exemplos = produtosArray
            .filter((p) => p.veiculo_id)
            .slice(0, 3);
          console.log("Exemplos de produtos com veículo_id:", exemplos);
        }

        // Processar veículos para lookup
        const veiculosObj = {};
        console.log("Dados de veículos recebidos:", veiculosData);

        // Inspecionar estrutura dos veículos
        const camposQualis = inspecionarVeiculos(veiculosData);

        Object.entries(veiculosData)
          .filter(([key]) => key !== "_")
          .forEach(([id, data]) => {
            // Verificar formato dos dados
            if (data && typeof data === "object") {
              // Procurar o campo Qualis em vários formatos possíveis
              let qualisValue = data.qualis;

              // Se não encontrou diretamente, tentar outros campos
              if (!qualisValue) {
                for (const campo of camposQualis) {
                  if (data[campo]) {
                    qualisValue = data[campo];
                    console.log(
                      `Encontrou Qualis no campo alternativo '${campo}': ${qualisValue}`
                    );
                    break;
                  }
                }
              }

              // Normalizar o valor do Qualis para o formato esperado (A1, A2, etc)
              if (qualisValue) {
                // Garantir que está no formato correto
                qualisValue = qualisValue.toUpperCase().trim();

                // Se for um número ou letra+número sem espaço, formatar
                if (/^[A-Z]\d+$/.test(qualisValue)) {
                  const letra = qualisValue.charAt(0);
                  const numero = qualisValue.substring(1);
                  qualisValue = `${letra}${numero}`;
                }
              }

              console.log(
                `Processando veículo ${id}:`,
                data,
                "Qualis normalizado:",
                qualisValue
              );

              veiculosObj[id] = {
                ...data,
                qualis: qualisValue || "Não classificado",
              };
            } else {
              console.log(`Veículo ${id} com formato inválido:`, data);
              veiculosObj[id] = {
                qualis: "Não classificado",
              };
            }
          });

        console.log("Veículos processados:", veiculosObj);
        console.log("Exemplo de alguns produtos:", produtosArray.slice(0, 5));

        // Verificar relação entre produtos e veículos
        const produtosComVeiculosList = produtosArray.filter(
          (p) => p.veiculo_id
        );
        console.log(
          `Total de produtos: ${produtosArray.length}, com veículo_id: ${produtosComVeiculosList.length}`
        );

        // Verificar matching entre produtos e veículos
        const veiculosIds = Object.keys(veiculosObj);
        const produtosComVeiculosValidos = produtosComVeiculosList.filter((p) =>
          veiculosIds.includes(p.veiculo_id)
        );
        console.log(
          `Produtos com veículo_id válido: ${produtosComVeiculosValidos.length}`
        );

        // Analisar estrutura dos works dos docentes
        console.log("Verificando estrutura dos works dos docentes:");
        let contagemDocentesComWorks = 0;
        
        // Analisar mais profundamente os works
        for (const docente of docentesArray) {
          if (docente.works) {
            contagemDocentesComWorks++;
            const tipoWorks = typeof docente.works;
            
            // Inspeção profunda dos works para procurar informações de Qualis
            if (tipoWorks === 'object' && !Array.isArray(docente.works)) {
              // Obter até 2 exemplos para análise
              const workIds = Object.keys(docente.works).slice(0, 2);
              console.log(`Docente ${docente.nome || docente.id} - works: ${tipoWorks}, exemplo:`, workIds);
              
              // Analisar detalhes dos works
              for (const workId of workIds) {
                const work = docente.works[workId];
                console.log(`Exemplo detalhado work ${workId}:`, work);
                
                // Verificar se o work contém informação de qualis ou veiculo
                if (work && typeof work === 'object') {
                  const temQualis = work.qualis || work.QUALIS || work.qualisValue;
                  const temVeiculo = work.veiculo_id || work.veiculo || work.journal_id || work.journal;
                  console.log(`Work ${workId} tem qualis direto: ${!!temQualis}, tem veiculo: ${!!temVeiculo}`);
                  
                  if (temQualis) {
                    console.log(`QUALIS ENCONTRADO DIRETAMENTE: ${temQualis}`);
                  }
                  
                  // Exibir todas as propriedades para diagnóstico
                  if (work) console.log("Todas as propriedades:", Object.keys(work));
                }
              }
            } else if (Array.isArray(docente.works)) {
              const exemplo = docente.works.slice(0, 2);
              console.log(`Docente ${docente.nome || docente.id} - works: array, exemplo:`, exemplo);
            } else {
              console.log(`Docente ${docente.nome || docente.id} - works: ${tipoWorks}`);
            }
          }
        }
        console.log(
          `Total de docentes com works: ${contagemDocentesComWorks} de ${docentesArray.length}`
        );

        setDocentes(docentesArray);
        setProdutos(produtosArray);
        setVeiculos(veiculosObj);

        // Selecionar todos os professores por padrão
        const initialSelected = docentesArray.map((d) => d.id);
        setSelectedProfessors(initialSelected);
      } catch (err) {
        console.error("Erro ao buscar dados:", err);
        setError(`Falha ao carregar dados: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Obter lista de áreas de pesquisa únicas (temporariamente comentado)
  const areas = useMemo(() => {
    const uniqueAreas = [...new Set(docentes.flatMap((d) => d.areas || []))];
    return ["todas", ...uniqueAreas];
  }, [docentes]);

  // Não estamos mais filtrando por área, exibindo todos os docentes
  const filteredDocentes = useMemo(() => {
    // Removemos temporariamente o filtro de área
    return docentes;
  }, [docentes]);

  // Calcular dados para os gráficos
  const chartData = useMemo(() => {
    console.log("Recalculando gráficos - docentes:", docentes.length);
    console.log("Recalculando gráficos - produtos:", produtos.length);
    console.log(
      "Recalculando gráficos - veiculos:",
      Object.keys(veiculos).length
    );

    const result = {};

    filteredDocentes
      .filter((d) => selectedProfessors.includes(d.id))
      .forEach((docente) => {
        const qualisCounts = {};
        QUALIS_ORDEM.forEach((q) => (qualisCounts[q] = 0));

        // Vamos usar os dados de work diretamente do docente, sem buscar produtos
        if (docente.works && typeof docente.works === 'object') {
          console.log(
            `Professor ${docente.nome} - works:`,
            typeof docente.works,
            Array.isArray(docente.works)
              ? docente.works.length
              : Object.keys(docente.works).length
          );

          // Usar um contador para facilitar o diagnóstico
          let totalWorksProcessados = 0;
          let worksComQualis = 0;

          // Se works for objeto (mais comum)
          if (!Array.isArray(docente.works)) {
            // Percorrer cada work do docente
            Object.entries(docente.works).forEach(([workId, work]) => {
              totalWorksProcessados++;
              
              // Extrair informações de Qualis - tentando várias abordagens
              let qualisValue = null;
              
              // 1. Tentar obter o Qualis diretamente do work
              if (work && typeof work === 'object') {
                qualisValue = work.qualis || work.QUALIS || work.qualisValue;
              }
              
              // 2. Se não encontrou e temos o veículo_id, tentar da tabela de veículos
              if (!qualisValue && work && work.veiculo_id && veiculos[work.veiculo_id]) {
                qualisValue = veiculos[work.veiculo_id].qualis;
              }
              
              // 3. Tentar encontrar em outras propriedades do work
              if (!qualisValue && work && typeof work === 'object') {
                // Buscar em qualquer campo que tenha "qualis" no nome
                const qualisKey = Object.keys(work).find(key => 
                  key.toLowerCase().includes('qualis')
                );
                
                if (qualisKey) {
                  qualisValue = work[qualisKey];
                }
              }
              
              // Se encontrou o Qualis, processar e normalizar
              if (qualisValue) {
                worksComQualis++;
                
                // Normalizar o Qualis
                qualisValue = String(qualisValue).toUpperCase().trim();
                
                // Ajustar formatos como "A1", "A2", etc.
                if (/^[A-Z]\d$/.test(qualisValue)) {
                  const letra = qualisValue.charAt(0);
                  const numero = qualisValue.charAt(1);
                  qualisValue = `${letra}${numero}`;
                }
                
                // Se é um Qualis válido na nossa ordem, contar
                if (QUALIS_ORDEM.includes(qualisValue)) {
                  qualisCounts[qualisValue] += 1;
                  console.log(`Contabilizado Qualis ${qualisValue} para work ${workId}`);
                } else {
                  console.log(`Qualis não reconhecido: "${qualisValue}" para work ${workId}`);
                }
              } else {
                console.log(`Sem Qualis para work ${workId}`);
              }
            });
          } else {
            // Se works for array, tentar encontrar pelo ID
            docente.works.forEach(workId => {
              totalWorksProcessados++;
              console.log(`Processando work ID ${workId} - não implementado para arrays`);
            });
          }
          
          console.log(`Professor ${docente.nome}: ${worksComQualis} de ${totalWorksProcessados} works com Qualis`);
        } // Fim do processamento de works
        
        // Após o processamento, montar resultado
        result[docente.id] = {
          nome: docente.nome,
          area: docente.area_pesquisa || "Não especificada",
          areas: docente.areas || [],
          data: QUALIS_ORDEM.map((qualis) => ({
            qualis,
            artigos: qualisCounts[qualis],
          })),
        };
        
        // Mostrar o resumo dos dados do docente
        const totalArtigos = QUALIS_ORDEM.reduce((sum, q) => sum + qualisCounts[q], 0);
        console.log(`Professor ${docente.nome}: Total de ${totalArtigos} artigos contabilizados por Qualis`);
        
        // Exibir contagem por Qualis
        QUALIS_ORDEM.forEach(q => {
          if (qualisCounts[q] > 0) {
            console.log(`  - ${q}: ${qualisCounts[q]} artigos`);
          }
        });
      });

    return result;
  }, [filteredDocentes, selectedProfessors, produtos, veiculos]);

  const handleProfessorToggle = (id) => {
    setSelectedProfessors((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const handleAreaChange = (e) => {
    setAreaFilter(e.target.value);
  };

  if (loading) {
    return <div className="qualis-loading">Carregando dados...</div>;
  }

  if (error) {
    return <div className="qualis-error">{error}</div>;
  }

  return (
    <div className="qualis-page">
      <div className="qualis-header">
        <h1>Análise de Produção por Qualis</h1>
        <p>
          Visualize a distribuição das publicações por classificação Qualis para
          cada professor
        </p>
      </div>

      <div className="qualis-filters">
        {/* Filtro de área temporariamente removido */}

        <div className="filter-section">
          <h3>
            Exibindo todos os professores ({filteredDocentes.length} no total)
          </h3>
          <p>
            Filtro de áreas temporariamente removido. Exibindo todos os dados.
          </p>

          {/* 
          <div className="professor-checkboxes">
            {filteredDocentes.length === 0 ? (
              <p>Nenhum professor encontrado para os filtros selecionados.</p>
            ) : (
              filteredDocentes.map((docente) => (
                <label key={docente.id} className="professor-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedProfessors.includes(docente.id)}
                    onChange={() => handleProfessorToggle(docente.id)}
                  />
                  {docente.nome || `Professor ${docente.id}`}
                  {docente.area_pesquisa && (
                    <span className="area-tag">{docente.area_pesquisa}</span>
                  )}
                </label>
              ))
            )}
          </div>
          */}
        </div>
      </div>

      <div className="qualis-grid">
        {selectedProfessors.length === 0 ? (
          <div className="no-selection">
            Selecione pelo menos um professor para visualizar os dados.
          </div>
        ) : (
          filteredDocentes
            .filter((d) => selectedProfessors.includes(d.id))
            .map((docente) => {
              const professorData = chartData[docente.id];

              // Total de artigos do professor
              const totalArtigos =
                professorData?.data?.reduce(
                  (sum, item) => sum + item.artigos,
                  0
                ) || 0;

              return (
                <div key={docente.id} className="professor-card">
                  <h3>{docente.nome || `Professor ${docente.id}`}</h3>
                  <p className="area-label">
                    {docente.areas && docente.areas.length > 0
                      ? docente.areas.join(", ")
                      : "Sem área definida"}
                  </p>

                  <div className="chart-container">
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={professorData?.data || []}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="qualis" />
                        <YAxis allowDecimals={false} />
                        <Tooltip
                          formatter={(value) => [
                            `${value} artigos`,
                            "Publicações",
                          ]}
                          labelFormatter={(label) => `Qualis ${label}`}
                          contentStyle={{
                            backgroundColor: "rgba(255, 255, 255, 0.95)",
                          }}
                        />
                        <Legend />
                        <Bar
                          dataKey="artigos"
                          name="Artigos"
                          isAnimationActive={true}
                          barSize={30}
                          fill="#8884d8"
                          fillOpacity={0.85}
                          stroke="#666"
                          strokeWidth={1}
                          // Definir cores diferentes para cada barra baseado no Qualis
                          {...{
                            fill: "#8884d8", // Cor padrão, caso nada funcione
                          }}
                          // Definir cor para cada barra individualmente
                          children={professorData?.data?.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={QUALIS_CORES[entry.qualis] || "#8884d8"}
                            />
                          ))}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="qualis-summary">
                    <p>Total: {totalArtigos} publicações</p>
                    <div className="qualis-details">
                      {professorData?.data?.map(
                        (item) =>
                          item.artigos > 0 && (
                            <span key={item.qualis} className="qualis-detail">
                              {item.qualis}: {item.artigos}
                            </span>
                          )
                      )}
                    </div>
                  </div>
                </div>
              );
            })
        )}
      </div>
    </div>
  );
}