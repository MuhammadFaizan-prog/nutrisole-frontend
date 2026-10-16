// Minimal XLSX reader (first worksheet → string rows) on top of fflate's unzip. Works on
// web, Hermes and Node; no SheetJS. Date-formatted cells become "YYYY-MM-DD HH:MM".
import { unzipSync, strFromU8 } from 'fflate';
import { excelSerialToParts } from './dates';

const decodeXml = (s: string) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n))).replace(/&amp;/g, '&');
const builtinDateFormats = new Set([14, 15, 16, 17, 18, 19, 20, 21, 22, 27, 30, 36, 45, 46, 47, 50, 57]);

function colIndex(ref: string) { let n = 0; for (const ch of ref.replace(/\d+$/, '')) n = n * 26 + ch.charCodeAt(0) - 64; return n - 1; }

export function isXlsx(bytes: Uint8Array) { return bytes.length > 4 && bytes[0] === 0x50 && bytes[1] === 0x4b && bytes[2] === 0x03 && bytes[3] === 0x04; }

export function readXlsx(bytes: Uint8Array): { sheetName: string; rows: string[][] } {
  let files: Record<string, Uint8Array>;
  try { files = unzipSync(bytes); } catch { throw new Error('This file is not a readable .xlsx workbook.'); }
  const text = (path: string) => (files[path] ? strFromU8(files[path]) : '');
  const workbook = text('xl/workbook.xml');
  if (!workbook) throw new Error('This file is not a readable .xlsx workbook.');
  const firstSheet = /<sheet\b[^>]*name="([^"]*)"[^>]*r:id="([^"]+)"/.exec(workbook) || /<sheet\b[^>]*r:id="([^"]+)"[^>]*name="([^"]*)"/.exec(workbook);
  const sheetName = firstSheet ? decodeXml(firstSheet[1].startsWith('rId') ? firstSheet[2] : firstSheet[1]) : 'Sheet1';
  const rid = firstSheet ? (firstSheet[2].startsWith('rId') ? firstSheet[2] : firstSheet[1]) : 'rId1';
  const rels = text('xl/_rels/workbook.xml.rels');
  const target = new RegExp(`<Relationship\\b[^>]*Id="${rid}"[^>]*Target="([^"]+)"`).exec(rels)?.[1] || new RegExp(`<Relationship\\b[^>]*Target="([^"]+)"[^>]*Id="${rid}"`).exec(rels)?.[1] || 'worksheets/sheet1.xml';
  const sheetPath = target.startsWith('/') ? target.slice(1) : `xl/${target.replace(/^\.\//, '')}`;
  const shared = [...text('xl/sharedStrings.xml').matchAll(/<si>([\s\S]*?)<\/si>/g)].map(m => decodeXml([...m[1].matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map(t => t[1]).join('')));
  // Styles: which cellXfs indexes are date/time formats.
  const styles = text('xl/styles.xml');
  const customDate = new Set([...styles.matchAll(/<numFmt\b[^>]*numFmtId="(\d+)"[^>]*formatCode="([^"]*)"/g)].filter(m => /[dmyhs]/i.test(m[2].replace(/"[^"]*"|\[[^\]]*\]/g, ''))).map(m => Number(m[1])));
  const xfs = /<cellXfs[^>]*>([\s\S]*?)<\/cellXfs>/.exec(styles)?.[1] || '';
  const dateStyle = [...xfs.matchAll(/<xf\b[^>]*?numFmtId="(\d+)"/g)].map(m => builtinDateFormats.has(Number(m[1])) || customDate.has(Number(m[1])));
  const sheet = text(sheetPath);
  if (!sheet) throw new Error('The first worksheet could not be read.');
  const rows: string[][] = [];
  for (const rowMatch of sheet.matchAll(/<row\b[^>]*>([\s\S]*?)<\/row>/g)) {
    const row: string[] = [];
    for (const c of rowMatch[1].matchAll(/<c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
      const attrs = c[1]; const body = c[2] || '';
      const ref = /r="([A-Z]+\d+)"/.exec(attrs)?.[1]; const type = /t="([^"]+)"/.exec(attrs)?.[1]; const style = Number(/s="(\d+)"/.exec(attrs)?.[1] ?? -1);
      const v = /<v>([\s\S]*?)<\/v>/.exec(body)?.[1];
      let value = '';
      if (type === 's' && v !== undefined) value = shared[Number(v)] ?? '';
      else if (type === 'inlineStr') value = decodeXml([...body.matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map(t => t[1]).join(''));
      else if (type === 'str' || type === 'e') value = decodeXml(v || '');
      else if (type === 'b') value = v === '1' ? 'TRUE' : 'FALSE';
      else if (v !== undefined) {
        const n = Number(v);
        if (style >= 0 && dateStyle[style] && Number.isFinite(n)) {
          const p = excelSerialToParts(n); const pad = (x: number) => String(x).padStart(2, '0');
          value = n < 1 ? `${pad(p.hour)}:${pad(p.minute)}` : `${p.year}-${pad(p.month + 1)}-${pad(p.day)}${n % 1 ? ` ${pad(p.hour)}:${pad(p.minute)}` : ''}`;
        } else value = Number.isFinite(n) ? String(Math.round(n * 1e6) / 1e6) : v;
      }
      const idx = ref ? colIndex(ref) : row.length;
      while (row.length < idx) row.push('');
      row[idx] = value.trim();
    }
    rows.push(row);
  }
  return { sheetName, rows: rows.filter(r => r.some(c => c !== '')) };
}
