import assert from 'node:assert/strict'
import { randomBytes } from 'node:crypto'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import test from 'node:test'

const budgetScript = fileURLToPath(new URL('./check-bundle-budget.mjs', import.meta.url))

test('rejects a production fixture whose compressed CSS exceeds the budget', () => {
  const fixtureRoot = mkdtempSync(join(tmpdir(), 'researchpath-bundle-budget-'))
  const assetsRoot = join(fixtureRoot, 'assets')

  try {
    mkdirSync(assetsRoot)
    writeFileSync(
      join(fixtureRoot, 'index.html'),
      '<script type="module" src="/assets/index.js"></script>',
      'utf8',
    )
    writeFileSync(join(assetsRoot, 'index.js'), 'console.log("fixture")', 'utf8')
    writeFileSync(join(assetsRoot, 'oversized.css'), randomBytes(60 * 1024))

    const result = spawnSync(process.execPath, [budgetScript, fixtureRoot], {
      encoding: 'utf8',
    })

    assert.notEqual(result.status, 0)
    assert.match(result.stderr, /Total CSS is .* budget is 50 KiB/)
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
})
