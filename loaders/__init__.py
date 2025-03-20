import six

if six.PY2:
    from pge_budget_loader import PGEBudgetLoader
else:
    from .pge_budget_loader import PGEBudgetLoader
