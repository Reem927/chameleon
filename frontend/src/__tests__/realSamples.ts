// Shared loader for tests: reads the official samples from input/ on disk.
// No fixture data is authored here.
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const INPUT_DIR = join(__dirname, '../../../input')

export const sampleFiles = readdirSync(INPUT_DIR).filter((f) => f.endsWith('.json'))

export function readSample(file: string): string {
  return readFileSync(join(INPUT_DIR, file), 'utf-8')
}
