from __future__ import annotations

import pandas as pd


def profile_structure(
    frame: pd.DataFrame,
    roles: dict[str, str | None],
    *,
    data_layout: str = "long",
    wave_count: int | None = None,
) -> tuple[dict[str, object], str, list[dict[str, str]]]:
    missing_role_counts: dict[str, int] = {}
    for role, variable_id in roles.items():
        if variable_id is not None:
            if variable_id not in frame.columns:
                raise ValueError("STRUCTURE_ROLE_INVALID: 角色变量不存在: " + variable_id)
            missing_role_counts[role] = int(frame[variable_id].isna().sum())

    subject_id = roles.get("subjectId")
    cluster_id = roles.get("clusterId")
    time_id = roles.get("timeId")
    duplicate_subject_time_count: int | None = None
    if subject_id and time_id:
        duplicate_subject_time_count = int(
            frame.duplicated(subset=[subject_id, time_id], keep=False).sum()
        )
    subject_count = int(frame[subject_id].nunique(dropna=True)) if subject_id else None
    cluster_count = int(frame[cluster_id].nunique(dropna=True)) if cluster_id else None
    singleton_cluster_count: int | None = None
    cluster_size: dict[str, int | float] | None = None
    if cluster_id:
        counts = frame[cluster_id].dropna().value_counts()
        singleton_cluster_count = int((counts == 1).sum())
        if not counts.empty:
            cluster_size = {
                "minimum": int(counts.min()),
                "median": float(counts.median()),
                "maximum": int(counts.max()),
            }
    observations_per_subject: dict[str, int | float] | None = None
    if subject_id:
        counts = frame[subject_id].dropna().value_counts()
        if not counts.empty:
            observations_per_subject = {
                "minimum": int(counts.min()),
                "median": float(counts.median()),
                "maximum": int(counts.max()),
            }
    time_point_count = (
        wave_count
        if data_layout == "wide"
        else int(frame[time_id].nunique(dropna=True)) if time_id else None
    )

    nesting_classification = "none"
    if cluster_id:
        if subject_id:
            per_subject = frame.dropna(subset=[subject_id, cluster_id]).groupby(subject_id)[
                cluster_id
            ]
            cross_classified = bool((per_subject.nunique() > 1).any())
            if cross_classified:
                nesting_classification = "cross_classified"
            elif time_id:
                nesting_classification = "three_level"
            else:
                nesting_classification = "two_level"
        else:
            nesting_classification = "two_level"

    profile = {
        "rowCount": int(len(frame)),
        "missingRoleCounts": missing_role_counts,
        "duplicateSubjectTimeCount": duplicate_subject_time_count,
        "subjectCount": subject_count,
        "clusterCount": cluster_count,
        "singletonClusterCount": singleton_cluster_count,
        "clusterSize": cluster_size,
        "observationsPerSubject": observations_per_subject,
        "timePointCount": time_point_count,
        "nestingClassification": nesting_classification,
    }
    warnings: list[dict[str, str]] = []
    status = "valid"
    if duplicate_subject_time_count:
        status = "invalid"
        warnings.append(
            {
                "code": "DUPLICATE_SUBJECT_TIME",
                "severity": "error",
                "message": "subject 与 time 的联合键存在重复",
            }
        )
    if cluster_count is not None and cluster_count < 2:
        status = "invalid"
        warnings.append(
            {
                "code": "INSUFFICIENT_CLUSTERS",
                "severity": "error",
                "message": "嵌套数据至少需要两个 cluster",
            }
        )
    if cluster_count is not None and cluster_count < 20:
        status = "warning" if status == "valid" else status
        warnings.append(
            {
                "code": "FEW_CLUSTERS",
                "severity": "warning",
                "message": "cluster 数少于 20，推断应谨慎",
            }
        )
    if singleton_cluster_count:
        status = "warning" if status == "valid" else status
        warnings.append(
            {
                "code": "SINGLETON_CLUSTERS",
                "severity": "warning",
                "message": "存在只有一条观测的 cluster",
            }
        )
    return profile, status, warnings
