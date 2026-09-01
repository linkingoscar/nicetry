from __future__ import annotations

from app.services.canonical_identity import canonical_sha256
from app.services.dataset_repository import DatasetRepository


def resolve_current_artifact_identity(
    repository: DatasetRepository,
    dataset_id: str,
    binding: dict[str, object],
) -> dict[str, str]:
    """Resolve current server-owned dataset, sample and measurement identities."""
    dataset = repository.get_dataset(dataset_id)
    original_file = dataset.get("originalFile")
    dataset_sha256 = (
        str(original_file.get("sha256", ""))
        if isinstance(original_file, dict)
        else ""
    )

    bound_sample_id = str(binding.get("sampleVersionId", "")).strip()
    if not bound_sample_id or bound_sample_id.startswith("sample_all_"):
        current_sample_id = f"sample_all_{dataset_sha256[:16]}" if dataset_sha256 else ""
        current_sample_hash = (
            canonical_sha256({"datasetSha256": dataset_sha256, "rule": "all_rows"})
            if dataset_sha256
            else ""
        )
    else:
        samples = repository.list_analysis_samples(dataset_id)
        current_sample = samples[0] if samples else None
        current_sample_id = str(current_sample.get("id", "")) if isinstance(current_sample, dict) else ""
        current_sample_hash = (
            str(current_sample.get("sampleHash", ""))
            if isinstance(current_sample, dict)
            else ""
        )

    try:
        current_measurement = repository.get_measurement(dataset_id)
    except LookupError:
        current_measurement = None
    current_measurement_id = (
        str(current_measurement.get("id", ""))
        if isinstance(current_measurement, dict)
        else ""
    )
    current_measurement_hash = (
        canonical_sha256(current_measurement)
        if isinstance(current_measurement, dict)
        else ""
    )
    return {
        "datasetSha256": dataset_sha256,
        "sampleVersionId": current_sample_id,
        "sampleHash": current_sample_hash,
        "measurementVersionId": current_measurement_id,
        "measurementHash": current_measurement_hash,
    }
