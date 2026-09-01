import React, { type Key, type ReactNode } from 'react';
import { formatMetric, formatPValue, formatCI } from '../../utils/statFormatters';

export type ColumnType = 'metric' | 'probability' | 'ci' | 'text' | 'custom';

export interface ColumnDef<T> {
  header: ReactNode;
  accessor?: keyof T | ((row: T) => unknown);
  type?: ColumnType;
  align?: 'left' | 'right' | 'center';
  digits?: number;
  render?: (val: unknown, row: T) => ReactNode;
}

export type StatColumn<T> = ColumnDef<T>;

export interface StatTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  rowKey: (row: T) => Key;
  groupBy?: (row: T) => string;
  methodNote?: ReactNode;
}

function StatTableInner<T>({
  data,
  columns,
  rowKey,
  groupBy,
  methodNote,
}: StatTableProps<T>) {
  
  const renderCell = (col: ColumnDef<T>, row: T) => {
    let val: unknown;
    if (col.accessor) {
      if (typeof col.accessor === 'function') {
        val = col.accessor(row);
      } else {
        val = row[col.accessor];
      }
    }

    if (col.render) {
      return col.render(val, row);
    }

    const type = col.type || 'text';

    switch (type) {
      case 'metric':
        return formatMetric(val as number | null | undefined, col.digits);
      case 'probability':
        return formatPValue(val as number | null | undefined);
      case 'ci':
        if (Array.isArray(val) && val.length === 2) {
          return formatCI(val[0], val[1], col.digits);
        }
        return '—';
      default:
        return val as ReactNode;
    }
  };

  const renderRows = () => {
    if (!groupBy) {
      return data.map((row) => (
        <tr key={rowKey(row)}>
          {columns.map((col, colIdx) => (
            <td key={typeof col.header === 'string' ? col.header : colIdx} className={col.align ? `text-${col.align}` : undefined}>
              {renderCell(col, row)}
            </td>
          ))}
        </tr>
      ));
    }

    const groups: Record<string, T[]> = {};
    for (const row of data) {
      const g = groupBy(row);
      if (!groups[g]) groups[g] = [];
      groups[g].push(row);
    }

    return Object.entries(groups).map(([groupName, rows]) => (
      <React.Fragment key={groupName}>
        <tr className="group-header">
          <th colSpan={columns.length} className="text-left font-bold">
            {groupName}
          </th>
        </tr>
        {rows.map((row) => (
          <tr key={`${groupName}-${String(rowKey(row))}`}>
            {columns.map((col, colIdx) => (
              <td key={typeof col.header === 'string' ? col.header : colIdx} className={col.align ? `text-${col.align}` : undefined}>
                {renderCell(col, row)}
              </td>
            ))}
          </tr>
        ))}
      </React.Fragment>
    ));
  };

  if (!data || data.length === 0) return null;

  return (
    <>
      {methodNote && (
        <p className="method-note">{methodNote}</p>
      )}
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead>
            <tr>
              {columns.map((col, colIdx) => (
                <th key={typeof col.header === 'string' ? col.header : colIdx}>{col.header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {renderRows()}
          </tbody>
        </table>
      </div>
    </>
  );
}

// Ensure type safety when memoizing generic components
export const StatTable = React.memo(StatTableInner) as typeof StatTableInner;
