# Defines the main error types used during deterministic replay.


class ReplayError(Exception):
    pass


class BusinessOutcomeError(ReplayError):
    pass


class RecoverableReplayError(ReplayError):
    pass


class HardReplayError(ReplayError):
    pass