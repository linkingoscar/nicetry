export function parseIntegerGrid(value: string, minimum: number): number[] {
  return [...new Set(value.split(/[,，\s]+/)
    .map((entry) => Number(entry))
    .filter((entry) => Number.isInteger(entry) && entry >= minimum))]
    .sort((left, right) => left - right)
}
