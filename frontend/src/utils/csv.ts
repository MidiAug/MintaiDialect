export async function fetchCsv<T = Record<string, string>>(url: string): Promise<T[]> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to load CSV: ${url}`)
  const text = await res.text()
  return parseCsv<T>(text)
}

export function parseCsv<T = Record<string, string>>(csv: string): T[] {
  const lines = csv.split(/\r?\n/).filter(l => l.trim().length > 0)
  if (lines.length === 0) return []
  const headers = splitCsvLine(lines[0])
  const rows: T[] = []
  for (let i = 1; i < lines.length; i++) {
    const values = splitCsvLine(lines[i])
    const row: Record<string, string> = {}
    headers.forEach((h, idx) => {
      row[h] = values[idx] ?? ''
    })
    rows.push(row as T)
  }
  return rows
}

function splitCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"'
        i++
      } else {
        inQuotes = !inQuotes
      }
    } else if (ch === ',' && !inQuotes) {
      result.push(current)
      current = ''
    } else {
      current += ch
    }
  }
  result.push(current)
  return result.map(s => s.trim())
}

