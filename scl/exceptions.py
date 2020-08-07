

class TimingViolationException(Exception):
    def __init__(self, *args):
        Exception.__init__(self, 'Timing violation violation', *args)


class FreshnessConstraintViolationException(TimingViolationException):
    def __init__(self, *args):
        Exception.__init__(self, 'Freshness constriant violation', *args)


class DataAbsenceException(Exception):
    def __init__(self, *args):
        Exception.__init__(self, 'Data absence', *args)


class DataCorruptionException(Exception):
    def __init__(self, *args):
        Exception.__init__(self, 'Data corruption', *args)


class InvalidStreamDataException(DataCorruptionException):
    def __init__(self, *args):
        Exception.__init__(self, 'Invalid stream data', *args)


class InvalidEvent(DataCorruptionException):
    def __init__(self, *args):
        Exception.__init__(self, 'Invalid event', *args)


class InvalidModeChange(DataCorruptionException):
    def __init__(self, *args):
        Exception.__init__(self, 'Invalid mode change', *args)
