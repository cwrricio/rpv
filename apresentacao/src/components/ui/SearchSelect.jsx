import { useState, useRef, useEffect } from "react";

// props: items [{id,name}], multiple (bool), placeholder, onChange(selected)
export default function SearchSelect({
  items = [],
  multiple = false,
  placeholder = "Pesquisar...",
  onChange,
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(multiple ? [] : null);
  const ref = useRef(null);

  const filtered = items.filter((it) =>
    (it.name || "").toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    function onDoc(e) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, []);

  function toggleItem(item) {
    if (multiple) {
      const s = selected || [];
      const exists = s.find((x) => x.id === item.id);
      const next = exists ? s.filter((x) => x.id !== item.id) : [...s, item];
      setSelected(next);
      onChange && onChange(next);
    } else {
      setSelected(item);
      onChange && onChange(item);
      setOpen(false);
    }
  }

  function remove(item) {
    const s = selected || [];
    const next = s.filter((x) => x.id !== item.id);
    setSelected(next);
    onChange && onChange(next);
  }

  return (
    <div className="search-select" ref={ref} style={{ position: "relative" }}>
      <div className="search-input" onClick={() => setOpen((o) => !o)}>
        {multiple ? (
          <div className="chips">
            {(selected || []).map((s) => (
              <span key={s.id} className="chip">
                {s.name}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    remove(s);
                  }}
                >
                  ×
                </button>
              </span>
            ))}
            <input
              placeholder={placeholder}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setOpen(true)}
            />
          </div>
        ) : (
          <input
            placeholder={placeholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setOpen(true)}
          />
        )}
      </div>

      {open && (
        <div
          className="search-dropdown"
          style={{
            position: "absolute",
            zIndex: 20,
            background: "white",
            border: "1px solid #eee",
            width: "100%",
            maxHeight: 200,
            overflow: "auto",
          }}
        >
          {filtered.map((it) => (
            <div
              key={it.id}
              className="search-item"
              onClick={() => toggleItem(it)}
              style={{ padding: "0.5rem", cursor: "pointer" }}
            >
              {it.name}
            </div>
          ))}
          {filtered.length === 0 && (
            <div style={{ padding: "0.5rem" }}>Nenhum resultado</div>
          )}
        </div>
      )}
    </div>
  );
}
