export function suggestSubjectKey(commonCols: string[]) {
  return commonCols.find((col) =>
    /id|uid|subject|user|respondent|编号|序号/i.test(col),
  ) || commonCols[0] || ''
}

export function suggestWaveKey(commonCols: string[]) {
  return commonCols.find((col) =>
    /wave|time|wave_id|波次/i.test(col),
  ) || ''
}
