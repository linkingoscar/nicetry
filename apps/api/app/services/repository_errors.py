class DatasetNotFoundError(LookupError):
    pass


class DictionaryUpdateError(ValueError):
    pass


class MeasurementNotFoundError(LookupError):
    pass


class ModelVersionNotFoundError(LookupError):
    pass


class ModelDraftNotFoundError(LookupError):
    pass
