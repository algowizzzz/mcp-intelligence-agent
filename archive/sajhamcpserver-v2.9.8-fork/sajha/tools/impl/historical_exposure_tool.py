"""
Historical Exposure Tool
Loads historical counterparty exposure data from local disk or S3 via DataLoader.
"""
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.data_loader import DataLoader


class HistoricalExposureTool(BaseMCPTool):
    """
    Tool to retrieve historical counterparty exposure data for a given quarter-end date.
    Available dates: 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'get_historical_exposure',
            'description': 'Retrieve historical counterparty exposure data for a specific quarter-end date',
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
                "date": {
                    "type": "string",
                    "description": "Quarter-end date in YYYY-MM-DD format (e.g. 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31)"
                },
                "counterparty": {
                    "type": "string",
                    "description": "Filter by counterparty name (optional). Returns all counterparties if omitted."
                }
            },
            "required": ["date"]
        }

    def get_output_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "counterparties": {"type": "array"},
                "_source": {"type": "string"}
            },
            "required": ["counterparties", "_source"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        date = arguments['date']
        relative_path = f'counterparties/historical/{date}.json'
        data = self._loader.load(relative_path)
        counterparty_filter = arguments.get('counterparty')
        if counterparty_filter:
            data = [r for r in data if r.get('counterparty', '').lower() == counterparty_filter.lower()]
        return {
            'counterparties': data,
            '_source': self._loader.resolve_path(relative_path)
        }
