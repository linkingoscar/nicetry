import { readFileSync, readdirSync } from 'node:fs'
import { basename, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { gzipSync } from 'node:zlib'

const root = new URL('../', import.meta.url)
const dist = process.argv[2]
  ? pathToFileURL(`${resolve(process.argv[2])}/`)
  : new URL('apps/web/dist/', root)
const assets = new URL('assets/', dist)
const assetsPath = fileURLToPath(assets)
const html = readFileSync(new URL('index.html', dist), 'utf8')
const initialNames = new Set(
  [...html.matchAll(/<script[^>]+src="[^"]*\/([^/"]+\.js)"/g)].map((match) => basename(match[1])),
)
const javascript = readdirSync(assetsPath)
  .filter((name) => name.endsWith('.js'))
  .map((name) => ({
    name,
    gzipBytes: gzipSync(readFileSync(join(assetsPath, name))).byteLength,
  }))

const initialBytes = javascript
  .filter((entry) => initialNames.has(entry.name))
  .reduce((total, entry) => total + entry.gzipBytes, 0)
const initialBudget = 100 * 1024
const asyncBudget = 150 * 1024
const failures = []
if (initialBytes === 0) failures.push('No initial JavaScript entry was discovered in index.html')
if (initialBytes > initialBudget) {
  failures.push(`Initial JavaScript is ${(initialBytes / 1024).toFixed(1)} KiB gzip; budget is 100 KiB`)
}
for (const entry of javascript.filter((item) => !initialNames.has(item.name))) {
  if (entry.gzipBytes > asyncBudget) {
    failures.push(`${entry.name} is ${(entry.gzipBytes / 1024).toFixed(1)} KiB gzip; budget is 150 KiB`)
  }
}
const cssBudget = 50 * 1024
const stylesheets = readdirSync(assetsPath)
  .filter((name) => name.endsWith('.css'))
  .map((name) => ({
    name,
    gzipBytes: gzipSync(readFileSync(join(assetsPath, name))).byteLength,
  }))
const totalCssBytes = stylesheets.reduce((total, entry) => total + entry.gzipBytes, 0)
if (totalCssBytes > cssBudget) {
  failures.push(`Total CSS is ${(totalCssBytes / 1024).toFixed(1)} KiB gzip; budget is 50 KiB`)
}

if (failures.length > 0) {
  console.error(failures.join('\n'))
  process.exit(1)
}
const largestAsync = javascript
  .filter((entry) => !initialNames.has(entry.name))
  .sort((left, right) => right.gzipBytes - left.gzipBytes)[0]
console.log(
  `Bundle budgets passed: initial ${(initialBytes / 1024).toFixed(1)} KiB gzip; ` +
    `largest async ${largestAsync ? (largestAsync.gzipBytes / 1024).toFixed(1) : '0.0'} KiB gzip.`,
)
