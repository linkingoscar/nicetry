import type {
  ResearchProgramSpec,
  StudyProtocolSpec,
  HypothesisInput,
  ProtocolDeviation,
  StudyProtocolIndex,
} from '../types/protocol'
import { requestJson } from './client'

export function saveProgram(program: ResearchProgramSpec): Promise<ResearchProgramSpec> {
  return requestJson('/api/v1/programs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(program),
  })
}

export function getProgram(programId: string): Promise<ResearchProgramSpec> {
  return requestJson(`/api/v1/programs/${encodeURIComponent(programId)}`)
}

export function saveProtocolDraft(
  programId: string,
  studyId: string,
  protocol: StudyProtocolSpec,
): Promise<StudyProtocolSpec> {
  return requestJson(
    `/api/v1/programs/${encodeURIComponent(programId)}/protocols/${encodeURIComponent(studyId)}/draft`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(protocol),
    },
  )
}

export function getProtocolDraft(programId: string, studyId: string): Promise<StudyProtocolSpec> {
  return requestJson(
    `/api/v1/programs/${encodeURIComponent(programId)}/protocols/${encodeURIComponent(studyId)}/draft`,
  )
}

export function freezeProtocol(
  programId: string,
  studyId: string,
  versionId: string,
  preregistrationUrl?: string | null,
  preregistrationSha256?: string | null,
): Promise<{ status: string; versionId: string; frozenHash: string }> {
  const preregParam = preregistrationUrl
    ? `&preregistration_url=${encodeURIComponent(preregistrationUrl)}`
    : ''
  const preregHashParam = preregistrationSha256
    ? `&preregistration_sha256=${encodeURIComponent(preregistrationSha256)}`
    : ''
  return requestJson(
    `/api/v1/programs/${encodeURIComponent(programId)}/protocols/${encodeURIComponent(studyId)}/freeze?version_id=${encodeURIComponent(versionId)}${preregParam}${preregHashParam}`,
    {
      method: 'POST',
    },
  )
}

export function getProtocolVersion(
  programId: string,
  studyId: string,
  versionId: string,
): Promise<StudyProtocolSpec> {
  return requestJson(
    `/api/v1/programs/${encodeURIComponent(programId)}/protocols/${encodeURIComponent(studyId)}/versions/${encodeURIComponent(versionId)}`,
  )
}

export function addOrUpdateHypothesis(
  programId: string,
  studyId: string,
  hypothesis: HypothesisInput,
): Promise<HypothesisInput> {
  return requestJson(
    `/api/v1/programs/${encodeURIComponent(programId)}/protocols/${encodeURIComponent(studyId)}/hypotheses`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(hypothesis),
    },
  )
}

export function listHypotheses(programId: string, studyId: string): Promise<HypothesisInput[]> {
  return requestJson(
    `/api/v1/programs/${encodeURIComponent(programId)}/protocols/${encodeURIComponent(studyId)}/hypotheses`,
  )
}

export function listProgramStudies(programId: string): Promise<StudyProtocolIndex[]> {
  return requestJson<StudyProtocolIndex[]>(`/api/v1/programs/${encodeURIComponent(programId)}/studies`)
}

export function verifyProtocolDeviation(
  programId: string,
  studyId: string,
  versionId: string,
  analysisSpec: Record<string, unknown>,
): Promise<ProtocolDeviation[]> {
  return requestJson<ProtocolDeviation[]>(
    `/api/v1/programs/${encodeURIComponent(programId)}/protocols/${encodeURIComponent(studyId)}/verify-deviation?version_id=${encodeURIComponent(versionId)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(analysisSpec),
    },
  )
}

export function listProtocolDeviations(
  programId: string,
  studyId: string,
  versionId: string,
): Promise<ProtocolDeviation[]> {
  return requestJson(
    `/api/v1/programs/${encodeURIComponent(programId)}/protocols/${encodeURIComponent(studyId)}/versions/${encodeURIComponent(versionId)}/deviations`,
  )
}
