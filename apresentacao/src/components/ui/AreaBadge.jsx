import React from "react";
import "./AreaBadge.css";

/**
 * Componente que exibe uma área de pesquisa como uma badge colorida
 */
export default function AreaBadge({ area, limit = null, showAll = false }) {
  // Se não houver área, retorna um placeholder
  if (!area)
    return <span className="area-badge area-none">Não especificada</span>;

  // Se for um array, mostramos múltiplas badges ou limitamos com contador
  if (Array.isArray(area)) {
    // Se showAll é true, mostra todas as áreas
    if (showAll || !limit || area.length <= limit) {
      return (
        <div className="area-badges-container">
          {area.map((a, index) => (
            <span key={index} className="area-badge">
              {a}
            </span>
          ))}
        </div>
      );
    }
    // Caso contrário, mostra apenas o número limitado com contador
    else {
      return (
        <div className="area-badges-container">
          {area.slice(0, limit).map((a, index) => (
            <span key={index} className="area-badge">
              {a}
            </span>
          ))}
          <span className="area-badge area-more">+{area.length - limit}</span>
        </div>
      );
    }
  }

  // Se for string, mostra uma única badge
  return <span className="area-badge">{area}</span>;
}
