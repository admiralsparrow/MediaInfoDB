import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchMedia, fetchMediaCount, rescanFiles } from "../../api/media";
import type { MediaFileDetail } from "../../types/media";
import TrackDetails from "./TrackDetails";
import { ALL_COLUMNS, DEFAULT_COLUMN_KEYS, COLUMN_GROUPS, orderByGroup, type ColumnDef } from "./columns";
import ColumnPicker from "./ColumnPicker";

interface Props {
  filters: Record<string, string>;
}

const STORAGE_KEY = "mediainfodb_columns";

function loadColumns(): string[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch {}
  return DEFAULT_COLUMN_KEYS;
}

export default function MediaTable({ filters }: Props) {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("file_name");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [visibleKeys, setVisibleKeys] = useState<string[]>(loadColumns);
  const [showColumnPicker, setShowColumnPicker] = useState(false);
  const [colWidths, setColWidths] = useState<Record<string, number>>(() => {
    try {
      const saved = localStorage.getItem("mediainfo-col-widths");
      if (saved) return JSON.parse(saved);
    } catch {}
    return {};
  });
  const colWidthsRef = useRef(colWidths);
  colWidthsRef.current = colWidths;
  const [dragKey, setDragKey] = useState<string | null>(null);
  const [dragOverKey, setDragOverKey] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [pageSize, setPageSize] = useState<number>(() => {
    const saved = localStorage.getItem("mediainfo-page-size");
    return saved ? Number(saved) : 100;
  });

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const activeFilters = debouncedSearch
    ? { ...filters, search: debouncedSearch }
    : filters;

  const visibleColumns = visibleKeys
    .map((k) => ALL_COLUMNS.find((c) => c.key === k))
    .filter(Boolean) as ColumnDef[];

  const { data: media, isLoading } = useQuery({
    queryKey: ["media", activeFilters, page, pageSize, sort, order],
    queryFn: () => fetchMedia(activeFilters, page, pageSize, sort, order),
  });

  const { data: countData } = useQuery({
    queryKey: ["mediaCount", activeFilters],
    queryFn: () => fetchMediaCount(activeFilters),
  });

  const totalPages = Math.ceil((countData?.count || 0) / pageSize);

  const queryClient = useQueryClient();
  const rescanMutation = useMutation({
    mutationFn: (ids: number[]) => rescanFiles(ids),
    onSuccess: () => {
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["media"] }), 3000);
    },
  });

  function handleRescan() {
    if (!media?.length) return;
    rescanMutation.mutate(media.map((f) => f.id));
  }

  function handleSort(field: string | undefined) {
    if (!field) return;
    if (sort === field) {
      setOrder(order === "asc" ? "desc" : "asc");
    } else {
      setSort(field);
      setOrder("asc");
    }
    setPage(1);
  }

  function toggleExpand(id: number) {
    setExpandedId(expandedId === id ? null : id);
  }

  function updateColumns(keys: string[]) {
    const kept = visibleKeys.filter((k) => keys.includes(k));
    const added = orderByGroup(keys.filter((k) => !visibleKeys.includes(k)));
    const merged = [...kept, ...added];
    setVisibleKeys(merged);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  }

  // Drag & drop reorder
  function handleDragStart(key: string) {
    setDragKey(key);
  }

  function handleDragOver(e: React.DragEvent, targetKey: string) {
    e.preventDefault();
    if (!dragKey || dragKey === targetKey) return;
    setDragOverKey(targetKey);

    const fromIdx = visibleKeys.indexOf(dragKey);
    const toIdx = visibleKeys.indexOf(targetKey);
    if (fromIdx === -1 || toIdx === -1) return;

    const newKeys = [...visibleKeys];
    newKeys.splice(fromIdx, 1);
    newKeys.splice(toIdx, 0, dragKey);
    setVisibleKeys(newKeys);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newKeys));
  }

  function handleDragEnd() {
    setDragKey(null);
    setDragOverKey(null);
  }

  const groupSpans = buildGroupSpans(visibleColumns);

  return (
    <div className="media-table-container">
      <div className="table-toolbar">
        <span className="media-count">{countData?.count ?? 0} files found</span>
        <input
          type="text"
          className="search-input"
          placeholder="Search filename..."
          autoComplete="off"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <button className="btn btn-sm" onClick={() => setShowColumnPicker(!showColumnPicker)}>
          Columns
        </button>
      </div>

      {showColumnPicker && (
        <ColumnPicker
          allColumns={ALL_COLUMNS}
          visibleKeys={visibleKeys}
          onChange={updateColumns}
          onClose={() => setShowColumnPicker(false)}
        />
      )}

      {isLoading && <p>Loading media...</p>}
      {!isLoading && !media?.length && <p className="empty">No media files found.</p>}

      {!isLoading && media && media.length > 0 && <div className="table-scroll">
        <table className="media-table">
          <thead>
            <tr className="group-header-row">
              <th className="group-header" />
              {groupSpans.map((span, i) => (
                <th
                  key={i}
                  colSpan={span.count}
                  className={`group-header group-${span.group}`}
                >
                  {span.group !== "file" ? span.label : ""}
                </th>
              ))}
            </tr>
            <tr>
              <th className="col-rescan" />
              {visibleColumns.map((col) => (
                <ResizableHeader
                  key={col.key}
                  col={col}
                  sort={sort}
                  order={order}
                  width={colWidths[col.key]}
                  onSort={handleSort}
                  onResize={(w) => setColWidths((prev) => {
                    if (w === 0) {
                      const { [col.key]: _, ...rest } = prev;
                      return rest;
                    }
                    return { ...prev, [col.key]: w };
                  })}
                  onResizeEnd={() => localStorage.setItem("mediainfo-col-widths", JSON.stringify(colWidthsRef.current))}
                  onDragStart={() => handleDragStart(col.key)}
                  onDragOver={(e) => handleDragOver(e, col.key)}
                  onDragEnd={handleDragEnd}
                  isDragging={dragKey === col.key}
                  isDragOver={dragOverKey === col.key}
                />
              ))}
            </tr>
          </thead>
          <tbody>
            {media.map((file) => (
              <>
                <tr
                  key={file.id}
                  className={expandedId === file.id ? "expanded" : ""}
                  onClick={() => toggleExpand(file.id)}
                >
                  <td className="col-rescan">
                    <button
                      className="btn-rescan"
                      title="Rescan file"
                      onClick={(e) => { e.stopPropagation(); rescanMutation.mutate([file.id]); }}
                    >
                      &#x21bb;
                    </button>
                  </td>
                  {visibleColumns.map((col) => (
                    <td
                      key={col.key}
                      className={["filename", "audio_name", "sub_names", "title"].includes(col.key) && !colWidths[col.key] ? "col-title" : ""}
                      style={colWidths[col.key] ? { width: colWidths[col.key], minWidth: colWidths[col.key], maxWidth: colWidths[col.key] } : undefined}
                    >
                      {renderCell(col, file)}
                    </td>
                  ))}
                </tr>
                {expandedId === file.id && (
                  <tr key={`${file.id}-detail`} className="detail-row">
                    <td colSpan={visibleColumns.length + 1}>
                      <TrackDetails detail={file} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>}

      <div className="pagination">
        <button
          className="btn btn-sm"
          onClick={handleRescan}
          disabled={rescanMutation.isPending || !media?.length}
        >
          {rescanMutation.isPending ? "Rescanning..." : "Re-analyse files in above table"}
        </button>
        <button className="btn btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
          Previous
        </button>
        <span>Page {page} of {totalPages || 1}</span>
        <button className="btn btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
          Next
        </button>
        <select
          className="page-size-select"
          value={pageSize}
          onChange={(e) => {
            const newSize = Number(e.target.value);
            setPageSize(newSize);
            localStorage.setItem("mediainfo-page-size", String(newSize));
            setPage(1);
          }}
        >
          <option value={25}>25 / page</option>
          <option value={50}>50 / page</option>
          <option value={100}>100 / page</option>
          <option value={200}>200 / page</option>
          <option value={500}>500 / page</option>
          <option value={1000}>1000 / page</option>
          <option value={10000}>10000 / page</option>
        </select>
      </div>
    </div>
  );
}

interface ResizableHeaderProps {
  col: ColumnDef;
  sort: string;
  order: "asc" | "desc";
  width: number | undefined;
  onSort: (field: string | undefined) => void;
  onResize: (width: number) => void;
  onResizeEnd: () => void;
  onDragStart: () => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragEnd: () => void;
  isDragging: boolean;
  isDragOver: boolean;
}

function ResizableHeader({
  col, sort, order, width, onSort, onResize, onResizeEnd,
  onDragStart, onDragOver, onDragEnd, isDragging, isDragOver,
}: ResizableHeaderProps) {
  const thRef = useRef<HTMLTableCellElement>(null);
  const startX = useRef(0);
  const startWidth = useRef(0);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    startX.current = e.clientX;
    startWidth.current = thRef.current?.offsetWidth || 100;

    const handleMouseMove = (ev: MouseEvent) => {
      const diff = ev.clientX - startX.current;
      const newWidth = Math.max(50, startWidth.current + diff);
      onResize(newWidth);
    };

    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      onResizeEnd();
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  }, [onResize, onResizeEnd]);

  const active = sort === col.sortField;

  return (
    <th
      ref={thRef}
      className={`${col.sortField ? "sortable" : ""} ${active ? "sorted" : ""} ${isDragging ? "dragging" : ""} ${isDragOver ? "drag-over" : ""}`}
      style={width ? { width, minWidth: width } : undefined}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        onDragStart();
      }}
      onDragOver={onDragOver}
      onDragEnd={onDragEnd}
      onClick={() => onSort(col.sortField)}
    >
      <span className="th-content">
        {col.label}
        {active && <span className="sort-arrow">{order === "asc" ? " ▲" : " ▼"}</span>}
      </span>
      <span
        className="resize-handle"
        onMouseDown={handleMouseDown}
        onDoubleClick={(e) => { e.stopPropagation(); onResize(0); onResizeEnd(); }}
      />
    </th>
  );
}

function buildGroupSpans(columns: ColumnDef[]) {
  const spans: { group: string; label: string; count: number }[] = [];
  for (const col of columns) {
    const groupDef = COLUMN_GROUPS.find((g) => g.key === col.group);
    const label = groupDef?.label || col.group;
    if (spans.length > 0 && spans[spans.length - 1].group === col.group) {
      spans[spans.length - 1].count++;
    } else {
      spans.push({ group: col.group, label, count: 1 });
    }
  }
  return spans;
}

function renderCell(col: ColumnDef, file: MediaFileDetail): React.ReactNode {
  if (col.key === "hdr") return renderHdr(file);
  if (col.key === "audio") return renderAudio(file);
  if (col.key === "subs") return renderSubs(file);
  if (col.key === "audio_language") return renderAudioLanguages(file);
  const val = col.getValue(file);
  if (typeof val === "string" && val.includes("\n")) {
    const parts = val.split("\n");
    return <>{parts.map((p, i) => <div key={i} className={p.startsWith("+") ? "audio-more" : ""}>{p}</div>)}</>;
  }
  return val;
}

function renderHdr(file: MediaFileDetail): React.ReactNode {
  const v = file.video_tracks?.[0];
  if (!v) return "-";

  const badges: string[] = [];
  if (v.dolby_vision) badges.push(`DV P${v.dv_profile ?? "?"}.L${v.dv_layer ? parseInt(v.dv_layer, 10) : "?"}`);
  if (v.hdr10) badges.push("HDR10");
  if (v.hdr10_plus) badges.push("HDR10+");

  if (!badges.length) return "SDR";

  return (
    <span className="hdr-badges">
      {badges.map((b) => (
        <span key={b} className={`badge ${b.startsWith("DV") ? "badge-dv" : ""}`}>{b}</span>
      ))}
    </span>
  );
}

function renderAudio(file: MediaFileDetail): React.ReactNode {
  const tracks = file.audio_tracks;
  if (!tracks?.length) return "-";

  const MAX_SHOWN = 2;
  const shown = tracks.slice(0, MAX_SHOWN);
  const remaining = tracks.length - MAX_SHOWN;

  return (
    <div className="audio-lines">
      {shown.map((t) => (
        <div key={t.id} className="audio-line">
          {t.language && <span className="lang-tag">{t.language}</span>}
          <span className="track-codec">{t.codec}</span>
          <span className="audio-layout">{t.channel_layout}</span>
          {t.is_atmos && <span className="badge badge-atmos">Atmos</span>}
          {t.is_commentary && <span className="badge badge-commentary">Comm</span>}
          {renderTrackName(t.track_name, t.language)}
        </div>
      ))}
      {remaining > 0 && <div className="audio-line audio-more">+{remaining} more</div>}
    </div>
  );
}

function renderTrackName(name: string | null | undefined, language: string | null | undefined): React.ReactNode {
  if (!name) return null;
  const langNames = ["english", "french", "spanish", "german", "italian", "japanese", "korean", "chinese", "portuguese", "russian", "dutch", "arabic", "hindi"];
  if (langNames.includes(name.toLowerCase())) return null;
  if (language && name.toLowerCase() === language.toLowerCase()) return null;
  return <span className="track-name-inline">{name}</span>;
}

function renderAudioLanguages(file: MediaFileDetail): React.ReactNode {
  const langs = [...new Set(file.audio_tracks?.map((a) => a.language).filter(Boolean))] as string[];
  if (!langs.length) return "-";
  return (
    <span className="sub-langs">
      {langs.map((lang) => (
        <span key={lang} className="lang-tag">{lang}</span>
      ))}
    </span>
  );
}

function renderSubs(file: MediaFileDetail): React.ReactNode {
  const subs = file.subtitle_tracks;
  if (!subs?.length) return "-";

  const langs = [...new Set(subs.map((s) => s.language).filter(Boolean))] as string[];
  if (!langs.length) return `${subs.length} tracks`;

  const sorted = langs.sort((a, b) => {
    if (a.match(/^en/i)) return -1;
    if (b.match(/^en/i)) return 1;
    return a.localeCompare(b);
  });

  const MAX_SHOWN = 4;
  const shown = sorted.slice(0, MAX_SHOWN);
  const remaining = sorted.length - MAX_SHOWN;

  return (
    <span className="sub-langs">
      {shown.map((lang) => (
        <span key={lang} className="lang-tag">{lang}</span>
      ))}
      {remaining > 0 && <span className="lang-tag lang-more">+{remaining}</span>}
    </span>
  );
}
