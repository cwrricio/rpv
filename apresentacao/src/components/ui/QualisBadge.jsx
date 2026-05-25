import React from "react";

/**
 * Componente que exibe uma classificação Qualis como uma badge colorida
 */
export default function QualisBadge({ qualis }) {
  // Determina a cor do background baseado no valor do Qualis
  function getBadgeClass(qualisValue) {
    if (!qualisValue || qualisValue === "Não classificado") {
      return "qualis-badge qualis-none";
    }

    const upperQualis = qualisValue.toUpperCase();

    if (upperQualis === "A1") return "qualis-badge qualis-a1";
    if (upperQualis === "A2") return "qualis-badge qualis-a2";
    if (upperQualis === "A3") return "qualis-badge qualis-a3";
    if (upperQualis === "A4") return "qualis-badge qualis-a4";
    if (upperQualis === "B1") return "qualis-badge qualis-b1";
    if (upperQualis === "B2") return "qualis-badge qualis-b2";
    if (upperQualis === "B3") return "qualis-badge qualis-b3";
    if (upperQualis === "B4") return "qualis-badge qualis-b4";
    if (upperQualis === "C") return "qualis-badge qualis-c";

    // Caso não seja um valor padrão conhecido
    return "qualis-badge qualis-other";
  }

  return <span className={getBadgeClass(qualis)}>{qualis || "—"}</span>;
}
