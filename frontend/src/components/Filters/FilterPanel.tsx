import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState, useRef, useEffect } from "react";
import { fetchFilterOptions } from "../../api/media";
import { filterDefinitions } from "./filterDefinitions";

interface SavedQuery {
  name: string;
  filters: Record<string, string>;
  libraryId: number | null;
}

interface Props {
  filters: Record<string, string>;
  onChange: (filters: Record<string, string>) => void;
  onChangeMulti?: (updates: Record<string, string>) => void;
  libraryId?: number | null;
  onLoadQuery?: (filters: Record<string, string>, libraryId: number | null) => void;
}

const STORAGE_KEY = "mediainfo-saved-queries";

function loadQueries(): SavedQuery[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function persistQueries(queries: SavedQuery[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queries));
}

const GROUPS = [
  { key: "general", label: "General" },
  { key: "video", label: "Video" },
  { key: "audio", label: "Audio" },
  { key: "subtitle", label: "Subtitles" },
] as const;

export default function FilterPanel({ filters, onChange, libraryId, onLoadQuery }: Props) {
  const [queries, setQueries] = useState<SavedQuery[]>(loadQueries);
  const [saving, setSaving] = useState(false);
  const [queryName, setQueryName] = useState("");

  const { data: options, isFetching: optionsFetching } = useQuery({
    queryKey: ["filterOptions", libraryId],
    queryFn: () => fetchFilterOptions(libraryId),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });

  function setFilter(key: string, value: string) {
    const next = { ...filters };
    if (value) {
      next[key] = value;
    } else {
      delete next[key];
    }
    onChange(next);
  }

  function setFilters(updates: Record<string, string>) {
    const next = { ...filters };
    for (const [key, value] of Object.entries(updates)) {
      if (value) {
        next[key] = value;
      } else {
        delete next[key];
      }
    }
    onChange(next);
  }

  function clearAll() {
    onChange({});
  }

  function handleSaveQuery() {
    if (!queryName.trim()) return;
    const next = [...queries, { name: queryName.trim(), filters, libraryId: libraryId ?? null }];
    persistQueries(next);
    setQueries(next);
    setQueryName("");
    setSaving(false);
  }

  function handleDeleteQuery(index: number) {
    const next = queries.filter((_, i) => i !== index);
    persistQueries(next);
    setQueries(next);
  }

  function handleLoadQuery(index: number) {
    const query = queries[index];
    if (!query) return;
    if (onLoadQuery) {
      onLoadQuery(query.filters, query.libraryId);
    } else {
      onChange(query.filters);
    }
  }

  const hasFilters = Object.keys(filters).length > 0;

  return (
    <div className="filter-panel">
      <div className="filter-header">
        <h3>Filters</h3>
        {hasFilters && (
          <button className="btn btn-sm" onClick={clearAll}>
            Clear
          </button>
        )}
      </div>

      <SavedQueriesDropdown
        queries={queries}
        hasFilters={hasFilters}
        saving={saving}
        queryName={queryName}
        onStartSave={() => setSaving(true)}
        onCancelSave={() => setSaving(false)}
        onNameChange={setQueryName}
        onSave={handleSaveQuery}
        onLoad={handleLoadQuery}
        onDelete={handleDeleteQuery}
      />

      {GROUPS.map((group) => {
        const defs = filterDefinitions.filter((d) => d.group === group.key);
        if (defs.length === 0) return null;

        return (
          <details key={group.key} className="filter-group" open>
            <summary>{group.label}</summary>
            <div className="filter-group-items">
              {defs.map((def) => (
                <FilterInput
                  key={def.key}
                  def={def}
                  value={filters[def.apiParam] || ""}
                  valueMax={def.apiParamMax ? filters[def.apiParamMax] || "" : ""}
                  options={options?.[def.apiParam]}
                  loading={optionsFetching}
                  onChange={(v) => setFilter(def.apiParam, v)}
                  onChangeRange={(min, max) => {
                    if (def.apiParamMax) {
                      setFilters({ [def.apiParam]: min, [def.apiParamMax]: max });
                    }
                  }}
                />
              ))}
            </div>
          </details>
        );
      })}
    </div>
  );
}

function SavedQueriesDropdown({
  queries,
  hasFilters,
  saving,
  queryName,
  onStartSave,
  onCancelSave,
  onNameChange,
  onSave,
  onLoad,
  onDelete,
}: {
  queries: SavedQuery[];
  hasFilters: boolean;
  saving: boolean;
  queryName: string;
  onStartSave: () => void;
  onCancelSave: () => void;
  onNameChange: (name: string) => void;
  onSave: () => void;
  onLoad: (index: number) => void;
  onDelete: (index: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="saved-queries-section">
      <div className="saved-queries-row">
        <div className="saved-queries-dropdown-wrap" ref={containerRef}>
          <button
            className="saved-queries-trigger"
            onClick={() => setOpen(!open)}
          >
            <span>Saved queries</span>
            <span className="saved-queries-arrow">{open ? "▴" : "▾"}</span>
          </button>
          {open && (
            <div className="saved-queries-menu">
              {queries.length === 0 ? (
                <div className="saved-queries-empty">No saved queries</div>
              ) : (
                queries.map((q, i) => (
                  <div key={i} className="saved-queries-menu-item">
                    <button
                      className="saved-queries-menu-load"
                      onClick={() => { onLoad(i); setOpen(false); }}
                    >
                      {q.name}
                    </button>
                    <button
                      className="saved-queries-menu-delete"
                      onClick={(e) => { e.stopPropagation(); onDelete(i); }}
                      title="Delete"
                    >
                      ×
                    </button>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
        {hasFilters && !saving && (
          <button className="btn btn-sm" onClick={onStartSave} title="Save current filters">
            Save
          </button>
        )}
      </div>
      {saving && (
        <div className="saved-queries-form">
          <input
            type="text"
            placeholder="Query name..."
            value={queryName}
            onChange={(e) => onNameChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSave();
              if (e.key === "Escape") onCancelSave();
            }}
            autoFocus
          />
          <button className="btn btn-sm btn-primary" onClick={onSave} disabled={!queryName.trim()}>
            Save
          </button>
          <button className="btn btn-sm" onClick={onCancelSave}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

interface FilterInputProps {
  def: (typeof filterDefinitions)[number];
  value: string;
  valueMax?: string;
  options?: string[];
  loading?: boolean;
  onChange: (value: string) => void;
  onChangeRange?: (min: string, max: string) => void;
}

function SearchableSelect({
  value,
  options,
  onChange,
  label,
  multiSelect,
}: {
  value: string;
  options?: string[];
  onChange: (value: string) => void;
  label: string;
  multiSelect?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const selected = multiSelect && value ? value.split(",").map((v) => v.trim()) : [];

  const filtered = (options || []).filter((opt) =>
    opt.toLowerCase().includes(search.toLowerCase())
  );

  function toggleOption(opt: string) {
    if (!multiSelect) {
      onChange(opt);
      setOpen(false);
      setSearch("");
      return;
    }
    const next = selected.includes(opt)
      ? selected.filter((v) => v !== opt)
      : [...selected, opt];
    onChange(next.join(","));
  }

  function selectAllFiltered() {
    const unselected = filtered.filter((opt) => !selected.includes(opt));
    if (unselected.length > 0) {
      onChange([...selected, ...unselected].join(","));
    }
  }

  const displayValue = multiSelect && selected.length > 0
    ? `${selected.length} selected`
    : value || "";

  return (
    <div className="searchable-select" ref={containerRef}>
      <div
        className="searchable-select-trigger"
        onClick={() => {
          setOpen(true);
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
      >
        <span className={displayValue ? "selected-value" : "placeholder"}>
          {displayValue || "All"}
        </span>
        {(value) && (
          <button
            className="clear-btn"
            onClick={(e) => {
              e.stopPropagation();
              onChange("");
            }}
          >
            ×
          </button>
        )}
      </div>
      {open && (
        <div className="searchable-select-dropdown">
          {multiSelect && selected.length > 0 && (
            <div className="searchable-select-tags">
              {selected.map((v) => (
                <span key={v} className="select-tag">
                  {v}
                  <button onClick={() => toggleOption(v)}>×</button>
                </span>
              ))}
            </div>
          )}
          <input
            ref={inputRef}
            type="text"
            className="searchable-select-input"
            placeholder={`Search ${label.toLowerCase()}...`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {multiSelect && search && filtered.some((opt) => !selected.includes(opt)) && (
            <button
              className="select-all-btn"
              onClick={selectAllFiltered}
            >
              Select all matching "{search}"
            </button>
          )}
          <ul className="searchable-select-list">
            <li
              className={!value ? "active" : ""}
              onClick={() => { onChange(""); setOpen(false); setSearch(""); }}
            >
              All
            </li>
            {filtered.map((opt) => (
              <li
                key={opt}
                className={`${multiSelect && selected.includes(opt) ? "active" : ""} ${!multiSelect && opt === value ? "active" : ""}`}
                onClick={() => toggleOption(opt)}
              >
                {multiSelect && (
                  <span className="select-checkbox">{selected.includes(opt) ? "☑" : "☐"}</span>
                )}
                {opt}
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="no-results">No matches</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

function FolderLevelSelect({
  items,
  selected,
  placeholder,
  onSelect,
}: {
  items: string[];
  selected: string;
  placeholder: string;
  onSelect: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = items.filter((item) =>
    item.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="folder-level-select" ref={containerRef}>
      <div
        className="folder-level-trigger"
        onClick={() => {
          setOpen(true);
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
      >
        <span className={selected ? "selected-value" : "placeholder"}>
          {selected || placeholder}
        </span>
      </div>
      {open && (
        <div className="folder-level-dropdown">
          <input
            ref={inputRef}
            type="text"
            className="searchable-select-input"
            placeholder="Type to filter..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <ul className="searchable-select-list">
            <li
              className={!selected ? "active" : ""}
              onClick={() => { onSelect(""); setOpen(false); setSearch(""); }}
            >
              {placeholder}
            </li>
            {filtered.map((item) => (
              <li
                key={item}
                className={item === selected ? "active" : ""}
                onClick={() => { onSelect(item); setOpen(false); setSearch(""); }}
              >
                {item}
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="no-results">No matches</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

function FolderPathPicker({
  value,
  options,
  loading,
  onChange,
}: {
  value: string;
  options?: string[];
  loading?: boolean;
  onChange: (value: string) => void;
}) {
  const allDirs = options || [];

  const currentParts = value ? value.split("/") : [];

  const levels: string[][] = [];
  if (!loading) {
    for (let depth = 0; depth <= currentParts.length; depth++) {
      const prefix = currentParts.slice(0, depth).join("/");
      const children = new Set<string>();
      for (const dir of allDirs) {
        const parts = dir.split("/");
        if (parts.length > depth) {
          const parentPath = parts.slice(0, depth).join("/");
          if (parentPath === prefix) {
            children.add(parts[depth]);
          }
        }
      }
      if (children.size > 0) {
        levels.push(Array.from(children).sort());
      } else {
        break;
      }
    }
  }

  return (
    <div className="folder-path-picker">
      {loading ? (
        <span className="folder-path-loading">Loading…</span>
      ) : levels.length === 0 ? (
        <span className="folder-path-empty">No folders</span>
      ) : (
        <>
          {value && (
            <div className="folder-path-breadcrumb">
              <button className="breadcrumb-root" onClick={() => onChange("")}>All</button>
              {currentParts.map((part, i) => (
                <span key={i}>
                  <span className="breadcrumb-sep">/</span>
                  <button
                    className="breadcrumb-part"
                    onClick={() => onChange(currentParts.slice(0, i + 1).join("/"))}
                  >
                    {part}
                  </button>
                </span>
              ))}
            </div>
          )}
          {levels.map((children, depth) => (
            <FolderLevelSelect
              key={depth}
              items={children}
              selected={currentParts[depth] || ""}
              placeholder={depth === 0 ? "All folders" : "— select —"}
              onSelect={(val) => {
                if (val) {
                  onChange([...currentParts.slice(0, depth), val].join("/"));
                } else {
                  onChange(currentParts.slice(0, depth).join("/"));
                }
              }}
            />
          ))}
        </>
      )}
    </div>
  );
}

function FilterInput({ def, value, valueMax, options, loading, onChange, onChangeRange }: FilterInputProps) {
  if (def.type === "enum") {
    if (def.apiParam === "folder_path") {
      return (
        <div className="filter-item filter-item-folder">
          <span>{def.label}</span>
          <FolderPathPicker value={value} options={options} loading={loading} onChange={onChange} />
        </div>
      );
    }
    const inverted = value.startsWith("!");
    const rawValue = inverted ? value.slice(1) : value;
    return (
      <div className="filter-item">
        <div className="filter-label-row">
          <span>{def.label}</span>
          {rawValue && (
            <label className="invert-toggle" title="Exclude selected values">
              <input
                type="checkbox"
                checked={inverted}
                onChange={(e) => {
                  onChange(e.target.checked ? `!${rawValue}` : rawValue);
                }}
              />
              <span className="invert-toggle-label">NOT</span>
            </label>
          )}
        </div>
        <SearchableSelect
          value={rawValue}
          options={options}
          onChange={(v) => onChange(inverted && v ? `!${v}` : v)}
          label={def.label}
          multiSelect
        />
      </div>
    );
  }

  if (def.type === "boolean") {
    return (
      <div className="filter-item filter-boolean">
        <span>{def.label}</span>
        <select
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">Any</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      </div>
    );
  }

  if (def.type === "text") {
    return (
      <label className="filter-item">
        <span>{def.label}</span>
        <input
          type="text"
          value={value}
          placeholder={`Search ${def.label.toLowerCase()}...`}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
    );
  }

  if (def.type === "range") {
    return (
      <div className="filter-item filter-range">
        <span>{def.label}</span>
        <div className="range-inputs">
          <input
            type="number"
            value={value}
            placeholder="Min"
            onChange={(e) => onChangeRange?.(e.target.value, valueMax || "")}
          />
          <span className="range-separator">–</span>
          <input
            type="number"
            value={valueMax || ""}
            placeholder="Max"
            onChange={(e) => onChangeRange?.(value, e.target.value)}
          />
        </div>
      </div>
    );
  }

  if (def.type === "date_range") {
    return (
      <div className="filter-item filter-range">
        <span>{def.label}</span>
        <div className="range-inputs">
          <input
            type="date"
            value={value}
            onChange={(e) => onChangeRange?.(e.target.value, valueMax || "")}
          />
          <span className="range-separator">–</span>
          <input
            type="date"
            value={valueMax || ""}
            onChange={(e) => onChangeRange?.(value, e.target.value)}
          />
        </div>
      </div>
    );
  }

  if (def.type === "number_min" || def.type === "number_max") {
    return (
      <label className="filter-item">
        <span>{def.label}</span>
        <input
          type="number"
          value={value}
          placeholder="0"
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
    );
  }

  return null;
}
