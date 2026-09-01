from __future__ import annotations

import pandas as pd

from app.services.dataset_import import DatasetImportError


def merge_datasets(
    primary_df: pd.DataFrame,
    target_df: pd.DataFrame,
    subject_key: str,
    wave_key: str | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Merge two datasets (primary and target) using an outer join.

    Verifies subject/wave key overlap and generates diagnostic reports.
    """
    if subject_key not in primary_df.columns:
        raise DatasetImportError(f"主数据集中找不到主键变量: {subject_key}")
    if subject_key not in target_df.columns:
        raise DatasetImportError(f"目标数据集中找不到主键变量: {subject_key}")

    join_keys = [subject_key]
    if wave_key:
        if wave_key not in primary_df.columns:
            raise DatasetImportError(f"主数据集中找不到波次变量: {wave_key}")
        if wave_key not in target_df.columns:
            raise DatasetImportError(f"目标数据集中找不到波次变量: {wave_key}")
        join_keys.append(wave_key)

    # Calculate key diagnostics
    primary_keys = primary_df[join_keys].dropna()
    target_keys = target_df[join_keys].dropna()

    # Find duplicates
    primary_dup_mask = primary_keys.duplicated(keep=False)
    target_dup_mask = target_keys.duplicated(keep=False)
    primary_dup_count = int(primary_dup_mask.sum())
    target_dup_count = int(target_dup_mask.sum())

    # Build unique tuples sets for overlap checking
    if len(join_keys) == 1:
        primary_set = set(primary_keys[subject_key].tolist())
        target_set = set(target_keys[subject_key].tolist())
    else:
        primary_set = set(zip(primary_keys[subject_key], primary_keys[wave_key], strict=False))
        target_set = set(zip(target_keys[subject_key], target_keys[wave_key], strict=False))

    matched_keys = primary_set.intersection(target_set)
    primary_only = primary_set - target_set
    target_only = target_set - primary_set

    # Perform outer merge
    merged_df = pd.merge(
        primary_df,
        target_df,
        on=join_keys,
        how="outer",
        suffixes=("", "__target"),
    )

    primary_counts = primary_keys.value_counts(dropna=False)
    target_counts = target_keys.value_counts(dropna=False)
    duplicate_key_details: list[dict[str, object]] = []
    one_to_many = 0
    many_to_many = 0
    for key in sorted(matched_keys, key=str):
        primary_value = primary_counts.loc[key]
        target_value = target_counts.loc[key]
        primary_count = int(
            primary_value.iloc[0] if isinstance(primary_value, pd.Series) else primary_value
        )
        target_count = int(
            target_value.iloc[0] if isinstance(target_value, pd.Series) else target_value
        )
        if primary_count > 1 or target_count > 1:
            if primary_count > 1 and target_count > 1:
                many_to_many += 1
                cardinality = "many_to_many"
            else:
                one_to_many += 1
                cardinality = "one_to_many"
            if len(duplicate_key_details) < 100:
                rendered_key = key if isinstance(key, tuple) else (key,)
                duplicate_key_details.append(
                    {
                        "key": [str(value) for value in rendered_key],
                        "primaryCount": primary_count,
                        "targetCount": target_count,
                        "cardinality": cardinality,
                    }
                )

    warnings: list[str] = []
    if primary_dup_count > 0:
        warnings.append(
            f"主数据集中存在 {primary_dup_count} 行主键重复记录，合并可能会导致多对多/一对多膨胀"
        )
    if target_dup_count > 0:
        warnings.append(
            f"目标数据集中存在 {target_dup_count} 行主键重复记录，合并可能会导致多对多/一对多膨胀"
        )

    summary: dict[str, object] = {
        "matchedCount": len(matched_keys),
        "primaryOnlyCount": len(primary_only),
        "targetOnlyCount": len(target_only),
        "primaryDuplicates": primary_dup_count,
        "targetDuplicates": target_dup_count,
        "mergedRowCount": int(len(merged_df)),
        "oneToManyConflictCount": one_to_many,
        "manyToManyConflictCount": many_to_many,
        "duplicateKeyDetails": duplicate_key_details,
        "joinKeys": join_keys,
        "joinType": "outer",
        "warnings": warnings,
    }

    return merged_df, summary
