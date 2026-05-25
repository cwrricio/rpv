import { createContext, useContext, useEffect, useState } from "react";

// Se NÃO usa Firebase aqui, pode remover firebase e trocar por fetch/axios.
// Mantive só o shape do Provider; você pode plugar sua API depois.
const QualisContext = createContext(null);

export function useQualis() {
  const ctx = useContext(QualisContext);
  if (!ctx) throw new Error("useQualis deve ser usado dentro de <QualisProvider>");
  return ctx;
}

export function QualisProvider({ children }) {
  const [qualisList, setQualisList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // TODO: troque por sua fonte real (API/Firebase).
    // De propósito: carregar algo para vermos conteúdo na tela.
    async function load() {
      try {
        setLoading(true);
        // MOCK: um item só pra confirmar render
        setQualisList([
          { id: "demo1", title: "Exemplo de Periódico", qualis: "A1", tipo: "Periódico", year: 2024, url: "" },
          { id: "demo2", title: "Exemplo de Conferência", qualis: "B1", tipo: "Conferência", year: 2023, url: "" },
        ]);
        setError("");
      } catch (e) {
        setError(e.message || String(e));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <QualisContext.Provider value={{ qualisList, loading, error }}>
      {children}
    </QualisContext.Provider>
  );
}

// Também exporta default (para não quebrar caso importe default em algum lugar)
export default QualisProvider;
