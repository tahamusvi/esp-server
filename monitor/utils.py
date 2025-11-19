# app/utils.py
import re

from .models import ForwardRule, IncomingMessage


def rule_matches_message(rule: ForwardRule, msg: IncomingMessage) -> bool:
    """
    Evaluate rule.filters against an IncomingMessage.
    filters structure example:
    {
      "all": [
        {"field": "from_number", "op": "eq", "value": "+98912..."},
        {"field": "body", "op": "contains", "value": "بانک پارسیان"}
      ]
    }
    or:
    {
      "any": [
        {"field": "body", "op": "regex", "value": "پارسیان|ملت"},
      ]
    }
    """
    filters = rule.filters or {}

    # If no filters defined, treat as match-all
    if not filters:
        return True

    def get_target(field: str) -> str:
        if field == "from_number":
            return msg.from_number or ""
        if field == "to_number":
            return msg.to_number or ""
        if field == "body":
            return msg.body or ""
        return ""

    def eval_condition(cond: dict) -> bool:
        field = cond.get("field")
        op = cond.get("op")
        value = cond.get("value", "")

        target = get_target(field)

        if op == "eq":
            return target == value
        if op == "neq":
            return target != value
        if op == "contains":
            return value in target
        if op == "icontains":
            return value.lower() in target.lower()
        if op == "regex":
            try:
                return re.search(value, target) is not None
            except re.error:
                return False

        # Unknown operator
        return False

    if "all" in filters:
        return all(eval_condition(c) for c in filters.get("all", []))

    if "any" in filters:
        conds = filters.get("any", [])
        return any(eval_condition(c) for c in conds) if conds else False

    # Fallback: no recognized structure
    return False
