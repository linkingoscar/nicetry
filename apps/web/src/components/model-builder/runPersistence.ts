export function activeRunStorageKey(datasetId: string, modelId: string) {
  return `researchpath_active_run:${datasetId}:${modelId}`
}

export function restoreActiveRunId(datasetId: string, modelId: string) {
  return localStorage.getItem(activeRunStorageKey(datasetId, modelId))
}
