export const APA_MANUSCRIPT_STYLES = `
    @page {
      size: A4;
      margin: 1in;
      @bottom-right {
        content: counter(page);
      }
    }
    body {
      font-family: 'Times New Roman', SimSun, serif;
      font-size: 12pt;
      line-height: 2.0;
      color: #000000;
      margin: 0;
      padding: 40px;
      background: #ffffff;
    }
    .running-head {
      font-size: 10pt;
      text-transform: uppercase;
      margin-bottom: 24pt;
      border-bottom: 1px solid #000000;
      padding-bottom: 4pt;
      display: flex;
      justify-content: space-between;
    }
    h1.title {
      font-size: 16pt;
      font-weight: bold;
      text-align: center;
      margin-top: 36pt;
      margin-bottom: 18pt;
    }
    .author-note {
      text-align: center;
      font-style: italic;
      margin-bottom: 36pt;
    }
    h2 {
      font-size: 13pt;
      font-weight: bold;
      margin-top: 24pt;
      margin-bottom: 12pt;
      border-bottom: 1px solid #000000;
    }
    .apa-table {
      width: 100%;
      border-collapse: collapse;
      margin: 18pt 0;
      font-size: 10.5pt;
      line-height: 1.5;
    }
    .apa-table caption {
      font-weight: bold;
      text-align: left;
      margin-bottom: 6pt;
      font-style: italic;
    }
    .apa-table th, .apa-table td {
      padding: 6pt 8pt;
      text-align: right;
    }
    .apa-table th:first-child, .apa-table td:first-child {
      text-align: left;
    }
    .apa-table thead tr:first-child {
      border-top: 2.0pt solid #000000;
      border-bottom: 1.0pt solid #000000;
    }
    .apa-table tbody tr:last-child {
      border-bottom: 2.0pt solid #000000;
    }
    .table-note {
      font-size: 9.5pt;
      margin-top: 4pt;
      line-height: 1.4;
    }
    .page-break {
      page-break-after: always;
      break-after: page;
    }
    .action-bar {
      position: fixed;
      top: 16px;
      right: 20px;
      background: #0f172a;
      padding: 8px 16px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
      z-index: 1000;
    }
    .action-bar button {
      background: #1037b9;
      color: #ffffff;
      border: 0;
      padding: 6px 14px;
      font-size: 12px;
      font-weight: bold;
      border-radius: 4px;
      cursor: pointer;
    }
    @media print {
      .action-bar { display: none; }
    }
`
