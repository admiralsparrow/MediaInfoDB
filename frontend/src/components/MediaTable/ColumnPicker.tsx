import { COLUMN_GROUPS, type ColumnDef } from "./columns";

interface Props {
  allColumns: ColumnDef[];
  visibleKeys: string[];
  onChange: (keys: string[]) => void;
  onClose: () => void;
}

export default function ColumnPicker({ allColumns, visibleKeys, onChange, onClose }: Props) {
  function toggle(key: string) {
    if (visibleKeys.includes(key)) {
      if (visibleKeys.length <= 1) return;
      onChange(visibleKeys.filter((k) => k !== key));
    } else {
      onChange([...visibleKeys, key]);
    }
  }

  return (
    <div className="column-picker">
      <div className="column-picker-header">
        <span>Select Columns</span>
        <button className="btn btn-xs" onClick={onClose}>&times;</button>
      </div>
      <div className="column-picker-body">
        {COLUMN_GROUPS.map((group) => {
          const cols = allColumns.filter((c) => c.group === group.key);
          if (!cols.length) return null;
          return (
            <div key={group.key} className="column-picker-group">
              <span className="column-picker-group-label">{group.label}</span>
              {cols.map((col) => (
                <label key={col.key} className="column-picker-item">
                  <input
                    type="checkbox"
                    checked={visibleKeys.includes(col.key)}
                    onChange={() => toggle(col.key)}
                  />
                  {col.label}
                </label>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
