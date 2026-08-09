class AgentError(RuntimeError):
    """Base class for expected runtime failures."""


class ContractError(AgentError):
    pass


class PolicyDenied(AgentError):
    pass


class ApprovalRequired(PolicyDenied):
    pass


class OperationConflict(AgentError):
    pass


class BudgetExceeded(AgentError):
    pass


class ReconciliationRequired(AgentError):
    pass
