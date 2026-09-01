from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from app.protocol_contracts import (
    HypothesisInput,
    ResearchProgramSpec,
    StudyProtocolIndex,
    StudyProtocolSpec,
)
from app.services.repository_io import (
    _read_json_safe,
    _utc_now,
    _write_json_atomic,
    resolve_owned_path,
    safe_identifier,
)
from app.settings import Settings


class ProtocolRepositoryMixin:
    settings: Settings

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_program(self, program: ResearchProgramSpec) -> None:
        program_id = safe_identifier(program.id, label="program id")
        created_at = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_programs (id, title, theoretical_question, target_journal, owner, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    theoretical_question = excluded.theoretical_question,
                    target_journal = excluded.target_journal,
                    owner = excluded.owner,
                    updated_at = excluded.updated_at
                """,
                (
                    program_id,
                    program.title,
                    program.theoretical_question,
                    program.target_journal,
                    program.owner,
                    created_at,
                    created_at,
                ),
            )
        path = (
            self.settings.state_root
            / "projects"
            / "default"
            / "programs"
            / program_id
            / "program.json"
        )
        _write_json_atomic(path, program.model_dump(by_alias=True))

    def get_program(self, program_id: str) -> ResearchProgramSpec:
        program_id = safe_identifier(program_id, label="program id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM research_programs WHERE id = ?", (program_id,)
            ).fetchone()
        if row is None:
            raise LookupError(f"ResearchProgram 不存在: {program_id}")
        path = resolve_owned_path(
            self.settings.state_root,
            f"projects/default/programs/{program_id}/program.json",
            label="program path",
            expected_parent=self.settings.state_root
            / "projects"
            / "default"
            / "programs"
            / program_id,
            expected_name="program.json",
        )
        data = _read_json_safe(path)
        return ResearchProgramSpec.model_validate(data)

    def record_protocol_draft(
        self, program_id: str, study_id: str, protocol: StudyProtocolSpec
    ) -> Path:
        program_id = safe_identifier(program_id, label="program id")
        study_id = safe_identifier(study_id, label="study id")

        self.get_program(program_id)

        created_at = _utc_now()
        path = (
            self.settings.state_root
            / "projects"
            / "default"
            / "programs"
            / program_id
            / "protocols"
            / study_id
            / "draft.json"
        )

        _write_json_atomic(path, protocol.model_dump(by_alias=True))
        relative_path = path.relative_to(self.settings.state_root).as_posix()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO study_protocols (study_id, version_id, program_id, title, design_type, is_frozen, path, created_at, updated_at)
                VALUES (?, 'draft', ?, ?, ?, 0, ?, ?, ?)
                ON CONFLICT(program_id, study_id, version_id) DO UPDATE SET
                    title = excluded.title,
                    design_type = excluded.design_type,
                    path = excluded.path,
                    updated_at = excluded.updated_at
                """,
                (
                    study_id,
                    program_id,
                    protocol.title,
                    protocol.design_type,
                    relative_path,
                    created_at,
                    created_at,
                ),
            )
        return path

    def get_protocol_draft(self, program_id: str, study_id: str) -> StudyProtocolSpec:
        program_id = safe_identifier(program_id, label="program id")
        study_id = safe_identifier(study_id, label="study id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT path FROM study_protocols WHERE program_id = ? AND study_id = ? AND version_id = 'draft'",
                (program_id, study_id),
            ).fetchone()
        if row is None:
            raise LookupError(f"StudyProtocol 草稿不存在: {study_id}")
        path = resolve_owned_path(
            self.settings.state_root,
            row["path"],
            label="study protocol draft path",
            expected_parent=self.settings.state_root
            / "projects"
            / "default"
            / "programs"
            / program_id
            / "protocols"
            / study_id,
            expected_name="draft.json",
        )
        data = _read_json_safe(path)
        return StudyProtocolSpec.model_validate(data)

    def freeze_protocol(
        self,
        program_id: str,
        study_id: str,
        version_id: str,
        preregistration_url: str | None = None,
        preregistration_sha256: str | None = None,
    ) -> str:
        program_id = safe_identifier(program_id, label="program id")
        study_id = safe_identifier(study_id, label="study id")
        version_id = safe_identifier(version_id, label="version id")
        if version_id == "draft":
            raise ValueError("冻结版本号不能为 'draft'")

        draft = self.get_protocol_draft(program_id, study_id)
        if preregistration_url or preregistration_sha256:
            draft_dict = draft.model_dump(by_alias=True)
            if preregistration_url:
                draft_dict["preregistrationUrl"] = preregistration_url
            if preregistration_sha256:
                draft_dict["preregistrationSha256"] = preregistration_sha256
            draft_dict["protocolVersionId"] = version_id
            draft = StudyProtocolSpec.model_validate(draft_dict)
        elif draft.protocol_version_id != version_id:
            draft_dict = draft.model_dump(by_alias=True)
            draft_dict["protocolVersionId"] = version_id
            draft = StudyProtocolSpec.model_validate(draft_dict)

        version_file = (
            self.settings.state_root
            / "projects"
            / "default"
            / "programs"
            / program_id
            / "protocols"
            / study_id
            / f"{version_id}.json"
        )
        if version_file.exists():
            raise ValueError(f"协议版本 {version_id} 已经存在，不可覆盖")

        _write_json_atomic(version_file, draft.model_dump(by_alias=True))

        file_bytes = version_file.read_bytes()
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        created_at = _utc_now()
        relative_path = version_file.relative_to(self.settings.state_root).as_posix()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO study_protocols (study_id, version_id, program_id, title, design_type, is_frozen, frozen_hash, path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    study_id,
                    version_id,
                    program_id,
                    draft.title,
                    draft.design_type,
                    sha256_hash,
                    relative_path,
                    created_at,
                    created_at,
                ),
            )
        return sha256_hash

    def get_protocol_version(
        self, program_id: str, study_id: str, version_id: str
    ) -> StudyProtocolSpec:
        program_id = safe_identifier(program_id, label="program id")
        study_id = safe_identifier(study_id, label="study id")
        version_id = safe_identifier(version_id, label="version id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT path, frozen_hash FROM study_protocols WHERE program_id = ? AND study_id = ? AND version_id = ?",
                (program_id, study_id, version_id),
            ).fetchone()
        if row is None:
            raise LookupError(f"StudyProtocol 版本 {version_id} 不存在: {study_id}")
        path = resolve_owned_path(
            self.settings.state_root,
            row["path"],
            label="study protocol version path",
            expected_parent=self.settings.state_root
            / "projects"
            / "default"
            / "programs"
            / program_id
            / "protocols"
            / study_id,
            expected_name=f"{version_id}.json",
        )
        file_bytes = path.read_bytes()
        current_hash = hashlib.sha256(file_bytes).hexdigest()
        if current_hash != row["frozen_hash"]:
            raise ValueError(f"StudyProtocol 版本 {version_id} 完整性校验失败，文件已被篡改")

        data = _read_json_safe(path)
        return StudyProtocolSpec.model_validate(data)

    def record_hypothesis(self, program_id: str, study_id: str, hyp: HypothesisInput) -> None:
        program_id = safe_identifier(program_id, label="program id")
        study_id = safe_identifier(study_id, label="study id")
        hyp_id = safe_identifier(hyp.id, label="hypothesis id")

        self.get_program(program_id)

        created_at = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO hypotheses (
                    id, program_id, study_id, text, directionality, analysis_role,
                    is_preregistered, status, construct_keys, estimand_ids,
                    evidence_ids, counterevidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    text = excluded.text,
                    directionality = excluded.directionality,
                    analysis_role = excluded.analysis_role,
                    is_preregistered = excluded.is_preregistered,
                    status = excluded.status,
                    construct_keys = excluded.construct_keys,
                    estimand_ids = excluded.estimand_ids,
                    evidence_ids = excluded.evidence_ids,
                    counterevidence = excluded.counterevidence
                """,
                (
                    hyp_id,
                    program_id,
                    study_id,
                    hyp.text,
                    hyp.directionality,
                    hyp.analysis_role,
                    1 if hyp.is_preregistered else 0,
                    hyp.status,
                    json.dumps(hyp.construct_keys, ensure_ascii=False),
                    json.dumps(hyp.estimand_ids, ensure_ascii=False),
                    json.dumps(hyp.evidence_ids, ensure_ascii=False),
                    hyp.counterevidence,
                    created_at,
                ),
            )

    def list_hypotheses_for_study(self, program_id: str, study_id: str) -> list[HypothesisInput]:
        program_id = safe_identifier(program_id, label="program id")
        study_id = safe_identifier(study_id, label="study id")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, text, directionality, analysis_role, is_preregistered, status, construct_keys, estimand_ids, evidence_ids, counterevidence FROM hypotheses WHERE program_id = ? AND study_id = ?",
                (program_id, study_id),
            ).fetchall()
        return [
            HypothesisInput(
                id=row["id"],
                text=row["text"],
                directionality=row["directionality"],
                analysis_role=row["analysis_role"],
                is_preregistered=bool(row["is_preregistered"]),
                status=row["status"],
                construct_keys=json.loads(row["construct_keys"] or "[]"),
                estimand_ids=json.loads(row["estimand_ids"] or "[]"),
                evidence_ids=json.loads(row["evidence_ids"] or "[]"),
                counterevidence=row["counterevidence"],
            )
            for row in rows
        ]

    def list_protocol_studies(self, program_id: str) -> list[StudyProtocolIndex]:
        program_id = safe_identifier(program_id, label="program id")
        self.get_program(program_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT study_id, title, design_type, version_id, is_frozen
                FROM study_protocols
                WHERE program_id = ?
                ORDER BY study_id, version_id
                """,
                (program_id,),
            ).fetchall()
        grouped: dict[str, StudyProtocolIndex] = {}
        for row in rows:
            item = grouped.get(row["study_id"])
            if item is None:
                item = StudyProtocolIndex(
                    study_id=row["study_id"],
                    title=row["title"],
                    design_type=row["design_type"],
                )
                grouped[row["study_id"]] = item
            item.version_ids.append(row["version_id"])
            if row["is_frozen"]:
                item.frozen_version_ids.append(row["version_id"])
        return list(grouped.values())
