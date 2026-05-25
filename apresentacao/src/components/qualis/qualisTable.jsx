// src/components/qualis/QualisTable.jsx
export default function QualisTable({ data = [] }) {
  if (!data.length) {
    return (
      <p style={{ color: "#6b7280", marginTop: 16 }}>
        Nenhum registro Qualis encontrado.
      </p>
    );
  }

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 16 }}>
      <thead>
        <tr style={{ background: "#f9fafb" }}>
          <th style={{ border: "1px solid #e5e7eb", padding: 8 }}>#</th>
          <th style={{ border: "1px solid #e5e7eb", padding: 8 }}>Título</th>
          <th style={{ border: "1px solid #e5e7eb", padding: 8 }}>Qualis</th>
          <th style={{ border: "1px solid #e5e7eb", padding: 8 }}>Tipo</th>
          <th style={{ border: "1px solid #e5e7eb", padding: 8 }}>Ano</th>
        </tr>
      </thead>
      <tbody>
        {data.map((q, i) => (
          <tr key={q.workId || i}>
            <td style={{ border: "1px solid #e5e7eb", padding: 8 }}>{i + 1}</td>
            <td style={{ border: "1px solid #e5e7eb", padding: 8 }}>
              {q.url ? (
                <a href={q.url} target="_blank" rel="noreferrer" style={{ color: "#2563eb" }}>
                  {q.title}
                </a>
              ) : (
                q.title
              )}
            </td>
            <td style={{ border: "1px solid #e5e7eb", padding: 8 }}>{q.qualis}</td>
            <td style={{ border: "1px solid #e5e7eb", padding: 8 }}>{q.tipo}</td>
            <td style={{ border: "1px solid #e5e7eb", padding: 8 }}>{q.year}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
