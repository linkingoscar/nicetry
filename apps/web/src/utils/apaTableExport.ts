export {
  parseMarkdownTable,
  convertTableDataToWordHtml,
  convertTableDataToLaTeX,
  convertTableDataToTSV,
  convertTableDataToMarkdown,
  extractTableDataFromDOM,
  copyAPATableToClipboard,
  escapeHtml,
  escapeSpreadsheetFormula,
} from './apaTableFormat'
export type { APATableData } from './apaTableFormat'
export { generateMultiGroupInvarianceAPATable } from './apaInvarianceTable'
