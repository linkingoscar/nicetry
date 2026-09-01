from __future__ import annotations


def binding_value(binding: dict[str, object], name: str) -> object:
    camel = "".join([name.split("_")[0], *[part.title() for part in name.split("_")[1:]]])
    return binding.get(name) if name in binding else binding.get(camel)


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def execution_value(
    execution_spec: dict[str, object], name: str
) -> tuple[bool, object]:
    candidates = [name]
    if "_" in name:
        candidates.append("".join([name.split("_")[0], *[part.title() for part in name.split("_")[1:]]]))
    else:
        candidates.append("".join(
            part if index == 0 else part[:1].upper() + part[1:]
            for index, part in enumerate(name.split("_"))
        ))
    for candidate in candidates:
        if candidate in execution_spec:
            return True, execution_spec[candidate]
    return False, None


def declaration_deviation(
    declaration: dict[str, object],
    execution_spec: dict[str, object] | None,
) -> str | None:
    if execution_spec is None:
        return None
    declared_slice = str(declaration.get("capabilitySliceId", "")).strip()
    actual_slices = string_list(execution_spec.get("applicableCapabilitySlices"))
    if declared_slice and actual_slices and declared_slice not in actual_slices:
        return (
            "ANALYSIS_DECLARATION_CAPABILITY_SLICE_MISMATCH: "
            f"声明 {declared_slice}，实际执行 {', '.join(actual_slices)}"
        )

    declared_method = str(declaration.get("requestedMethod", "")).strip()
    direct_methods: list[str] = []
    for key in ("requestedMethod", "method", "capabilitySliceId"):
        present, value = execution_value(execution_spec, key)
        if present and value is not None and str(value).strip():
            direct_methods.append(str(value).strip())
    if declared_method and direct_methods and declared_method not in direct_methods:
        return (
            "ANALYSIS_DECLARATION_METHOD_MISMATCH: "
            f"声明 {declared_method}，实际执行 {', '.join(direct_methods)}"
        )
    if declared_method.startswith("empirical.") and actual_slices and declared_method not in actual_slices:
        return (
            "ANALYSIS_DECLARATION_METHOD_MISMATCH: "
            f"声明 {declared_method} 未出现在实际执行切片中"
        )

    parameters = declaration.get("parameters")
    if isinstance(parameters, dict):
        for key, expected in parameters.items():
            present, actual = execution_value(execution_spec, str(key))
            if present and actual != expected:
                return (
                    "ANALYSIS_DECLARATION_PARAMETER_MISMATCH: "
                    f"参数 {key} 声明为 {expected!r}，实际为 {actual!r}"
                )
    return None


def identity_value(identity: dict[str, object], name: str) -> object:
    if name in identity:
        return identity[name]
    nested_name = (
        name[:-6]
        if name.endswith("Sha256")
        else name[:-4]
        if name.endswith("Hash")
        else name[:-9]
        if name.endswith("VersionId")
        else name
    )
    nested = identity.get(nested_name)
    if isinstance(nested, dict):
        if name.endswith("Sha256"):
            return nested.get("sha256")
        if name.endswith("Hash"):
            return nested.get("hash")
        return nested.get("id")
    return None
