"""
VaR Contribution Tool
Loads Value-at-Risk data from local disk or S3 via DataLoader.
"""
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.data_loader import DataLoader


class VaRContributionTool(BaseMCPTool):
    """
    Tool to retrieve VaR contribution data per counterparty.
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'get_var_contribution',
            'description': 'Retrieve Value-at-Risk (VaR) contribution data including 95%, 99% and stress VaR per counterparty',
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
                    "description": "Filter by counterparty name (optional). Returns all VaR records if omitted."
                }
            }
        }

    def get_output_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "var_data": {"type": "array"},
                "_source": {"type": "string"}
            },
            "required": ["var_data", "_source"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        relative_path = 'counterparties/var.json'
        data = self._loader.load(relative_path)
        counterparty_filter = arguments.get('counterparty')
        if counterparty_filter:
            data = [r for r in data if r.get('counterparty', '').lower() == counterparty_filter.lower()]
        return {
            'var_data': data,
            '_source': self._loader.resolve_path(relative_path)
        }
