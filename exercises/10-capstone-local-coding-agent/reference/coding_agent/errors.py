class AgentError(RuntimeError):
    """Base class for expected coding-agent failures."""


class ContractError(AgentError):
    """A model or tool value violated a published contract."""


class PolicyDenied(AgentError):
    """The task-scoped policy denied an effect."""


class ApprovalRequired(PolicyDenied):
    """A mutating action lacks an exact approval."""


class OperationConflict(AgentError):
    """An operation ID or workspace precondition conflicts."""


class BudgetExceeded(AgentError):
    """The run cannot reserve another bounded operation."""


class ReconciliationRequired(AgentError):
    """Durable state cannot safely infer an external effect."""
