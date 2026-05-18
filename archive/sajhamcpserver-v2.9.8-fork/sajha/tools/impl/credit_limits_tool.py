"""
Credit Limits Tool
Loads credit limit data from local disk or S3 via DataLoader.
"""
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.data_loader import DataLoader


class CreditLimitsTool(BaseMCPTool):
    """
    Tool to retrieve credit limits and utilization data.
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'get_credit_limits',
            'description': 'Retrieve credit limit utilization data including Settlement, Pre-Settlement, PFE and Wrong-Way-Risk limits',
            'version': '1.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)
        self._loader = DataLoader()

    def get_input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "counterparty": {
                    "type": "string",
                    "description": "Filter by counterparty name (optional). Returns all limit records if omitted."
                }
            }
        }

    def get_output_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "limits": {"type": "array"},
                "_source": {"type": "string"}
            },
            "required": ["limits", "_source"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        relative_path = 'counterparties/credit_limits.json'
        data = self._loader.load(relative_path)
        counterparty_filter = arguments.get('counterparty')
        if counterparty_filter:
            data = [r for r in data if r.get('counterparty', '').lower() == counterparty_filter.lower()]
        return {
            'limits': data,
            '_source': self._loader.resolve_path(relative_path)
        }
