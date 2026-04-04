"""
Copyright All rights Reserved 2025-2030, Ashutosh Sinha, Email: ajsinha@gmail.com
IRIS CCR Tools — Counterparty Credit Risk limit and exposure analytics.
9 pandas-based MCP tools over iris_combined.csv.
"""

import io
import math
import pandas as pd
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator
from sajha.storage import storage
from sajha.path_resolver import resolve as path_resolve


def _get_worker_ctx():
    try:
        from flask import g as _g
        return getattr(_g, 'worker_ctx', {}) or {}
    except RuntimeError:
        return {}


def _clean(val):
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def _clean_row(row: dict) -> dict:
    return {k: _clean(v) for k, v in row.items()}


class IrisBaseTool(BaseMCPTool):
    """Shared base for all IRIS tools. Loads CSV once at class level."""
    _df = None
    _df_path = None  # track which path the class-level df was loaded from

    @classmethod
    def _get_config(cls, key, default=None):
        """Read a value from application.properties via PropertiesConfigurator."""
        try:
            val = PropertiesConfigurator().get(key)
            return val if val is not None else default
        except Exception:
            return default

    @classmethod
    def _iris_csv_path(cls) -> str:
        """Return iris CSV path, preferring per-request worker root (G-04)."""
        try:
            from flask import g as _g
            worker_root = getattr(_g, 'worker_data_root', None)
            if worker_root:
                return worker_root.rstrip('/') + '/iris/iris_combined.csv'
        except RuntimeError:
            pass
        return cls._get_config('data.iris_combined_csv', './data/domain_data/iris/iris_combined.csv')

    @classmethod
    def _get_df(cls):
        path = cls._iris_csv_path()
        # Reload if path changed (different worker) or not yet loaded
        if cls._df is None or cls._df_path != path:
            data = storage.read_bytes(path)
            cls._df = pd.read_csv(io.BytesIO(data), encoding='latin1', low_memory=False)
            cls._df['Date'] = cls._df['Date'].astype(str)
            cls._df_path = path
        return cls._df

    @classmethod
    def _latest_date(cls):
        return cls._get_df()['Date'].max()

    @classmethod
    def _valid_dates(cls):
        return sorted(cls._get_df()['Date'].unique().tolist())

    def _make_limit_key(self, row):
        code = row.get('Customer Code', '')
        fid = row.get('Facility ID', '')
        le = row.get('Legal Entity', '')
        prod = row.get('Product', '')
        return f'{code} / {fid} / {le} / {prod}'

    LEGAL_ENTITY_ENUM = ['BCMC', 'HARRIS BANK', 'BMO', 'BNBI', 'BOMI', 'BHIC', 'BMN', 'BCML', 'BLAC', 'BMMC']

    def _validate_legal_entity(self, le):
        if le and le not in self.LEGAL_ENTITY_ENUM:
            return {'error': True, 'error_code': 'INVALID_ENUM',
                    'message': f'Invalid legal_entity: {le}',
                    'valid_options': self.LEGAL_ENTITY_ENUM}
        return None

    def _validate_date(self, date):
        valid = self._valid_dates()
        if date not in valid:
            return {'error': True, 'error_code': 'INVALID_DATE',
                    'message': f'Date {date} not found in dataset.',
                    'valid_options': valid}
        return None

    # BaseMCPTool requires these abstract methods
    def get_input_schema(self):
        return self._input_schema or {}

    def get_output_schema(self):
        return self._output_schema or {}


# ---------------------------------------------------------------------------
# Tool 1: List available dates
# ---------------------------------------------------------------------------
class IrisListDatesTool(IrisBaseTool):
    def execute(self, params):
        dates = self._valid_dates()
        return {'dates': dates, 'count': len(dates), 'latest': dates[-1] if dates else None}


# ---------------------------------------------------------------------------
# Tool 2: Search counterparties
# ---------------------------------------------------------------------------
class IrisSearchCounterpartiesTool(IrisBaseTool):
    def execute(self, params):
        search_term = params.get('search_term', '')
        counterparty_code = params.get('counterparty_code', '')
        uen = params.get('uen', '')
        date = params.get('date', self._latest_date())
        limit = int(params.get('limit', 50))

        err = self._validate_date(date)
        if err:
            return err

        df = self._get_df()
        df = df[df['Date'] == date]

        if counterparty_code:
            df = df[df['Customer Code'] == counterparty_code]
        elif uen:
            df = df[df['Facility ID'].astype(str) == str(uen)]
        elif search_term:
            mask = (df['Customer Code'].str.contains(search_term, case=False, na=False) |
                    df['Customer Name'].str.contains(search_term, case=False, na=False))
            df = df[mask]
        else:
            return {'error': True, 'error_code': 'MISSING_PARAM',
                    'message': 'Provide at least one of: search_term, counterparty_code, uen'}

        cols = ['Customer Code', 'Customer Name', 'Customer Internal Rating',
                'Legal Entity', 'Facility ID', 'Country', 'Country Rating', 'Connection Code']
        df = df[cols].drop_duplicates().head(limit)
        results = [_clean_row(r) for r in df.to_dict('records')]
        return {'counterparties': results, 'count': len(results), 'date_used': date}


# ---------------------------------------------------------------------------
# Tool 3: Counterparty dashboard
# ---------------------------------------------------------------------------
class IrisCounterpartyDashboardTool(IrisBaseTool):
    def execute(self, params):
        date = params.get('date', self._latest_date())
        counterparty_code = params.get('counterparty_code', '')
        uen = params.get('uen', '')
        legal_entity = params.get('legal_entity', '')
        product = params.get('product', '')
        max_rows = int(params.get('max_rows', 500))

        if not counterparty_code:
            return {'error': True, 'error_code': 'MISSING_PARAM', 'message': 'counterparty_code is required'}
        err = self._validate_date(date)
        if err:
            return err
        err = self._validate_legal_entity(legal_entity)
        if err:
            return err

        df = self._get_df()
        df = df[df['Date'] == date]
        df = df[df['Customer Code'] == counterparty_code]
        if uen:
            df = df[df['Facility ID'].astype(str) == str(uen)]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if product:
            df = df[df['Product'].str.contains(product, case=False, na=False)]

        total = len(df)
        df = df.head(max_rows)
        rows = [_clean_row(r) for r in df.to_dict('records')]
        filters = {k: v for k, v in {'uen': uen, 'legal_entity': legal_entity, 'product': product}.items() if v}
        return {'rows': rows, 'row_count': len(rows), 'total_matched': total,
                'filters_applied': filters, 'date_used': date}


# ---------------------------------------------------------------------------
# Tool 4: Limit lookup
# ---------------------------------------------------------------------------
class IrisLimitLookupTool(IrisBaseTool):
    def execute(self, params):
        date = params.get('date', self._latest_date())
        counterparty_code = params.get('counterparty_code', '')
        facility_id = params.get('facility_id', '')
        legal_entity = params.get('legal_entity', '')
        product = params.get('product', '')

        if not counterparty_code:
            return {'error': True, 'error_code': 'MISSING_PARAM', 'message': 'counterparty_code is required'}
        err = self._validate_date(date)
        if err:
            return err
        err = self._validate_legal_entity(legal_entity)
        if err:
            return err

        df = self._get_df()
        df = df[(df['Date'] == date) & (df['Customer Code'] == counterparty_code)]
        if facility_id:
            df = df[df['Facility ID'].astype(str) == str(facility_id)]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if product:
            df = df[df['Product'].str.contains(product, case=False, na=False)]

        if df.empty:
            return {'error': True, 'error_code': 'NO_DATA', 'message': 'No matching limit record found'}

        results = []
        for _, row in df.iterrows():
            results.append({
                'limit_key': self._make_limit_key(row),
                'limit': _clean(row.get('Product Limit')),
                'exposure': _clean(row.get('Product Exposure')),
                'headroom': _clean(row.get('Product Avail')),
                'currency': _clean(row.get('Product Limit Currency')),
                'agreement': _clean(row.get('Agreement')),
                'cust_limit': _clean(row.get('Cust Limit')),
                'conn_limit': _clean(row.get('Conn Limit')),
                'internal_rating': _clean(row.get('Customer Internal Rating')),
                'date_used': date,
            })
        return {'records': results, 'count': len(results), 'date_used': date}


# ---------------------------------------------------------------------------
# Tool 5: Limit breach check (single counterparty)
# ---------------------------------------------------------------------------
class IrisLimitBreachCheckTool(IrisBaseTool):
    def execute(self, params):
        date = params.get('date', self._latest_date())
        counterparty_code = params.get('counterparty_code', '')
        legal_entity = params.get('legal_entity', '')
        product = params.get('product', '')
        level = params.get('level', '')

        if not counterparty_code:
            return {'error': True, 'error_code': 'MISSING_PARAM', 'message': 'counterparty_code is required'}
        err = self._validate_date(date)
        if err:
            return err
        err = self._validate_legal_entity(legal_entity)
        if err:
            return err

        df = self._get_df()
        df = df[(df['Date'] == date) & (df['Customer Code'] == counterparty_code)]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if product:
            df = df[df['Product'].str.contains(product, case=False, na=False)]

        breaches = []
        check_levels = [level] if level else ['product', 'customer', 'connection']

        for _, row in df.iterrows():
            lk = self._make_limit_key(row)
            if 'product' in check_levels:
                lim = row.get('Product Limit')
                exp = row.get('Product Exposure')
                if lim is not None and exp is not None and not math.isnan(float(lim)) and not math.isnan(float(exp)):
                    if float(exp) > float(lim):
                        overage = float(exp) - float(lim)
                        breaches.append({'limit_key': lk, 'counterparty': counterparty_code,
                                         'product': _clean(row.get('Product')), 'level': 'product',
                                         'limit': float(lim), 'exposure': float(exp),
                                         'overage': overage, 'overage_pct': round(overage / float(lim) * 100, 2),
                                         'date_used': date})
            if 'customer' in check_levels:
                lim = row.get('Cust Limit')
                exp = row.get('Cust Exposure')
                if lim is not None and exp is not None and not math.isnan(float(lim)) and not math.isnan(float(exp)):
                    if float(exp) > float(lim):
                        overage = float(exp) - float(lim)
                        breaches.append({'limit_key': lk, 'counterparty': counterparty_code,
                                         'product': _clean(row.get('Product')), 'level': 'customer',
                                         'limit': float(lim), 'exposure': float(exp),
                                         'overage': overage, 'overage_pct': round(overage / float(lim) * 100, 2),
                                         'date_used': date})
            if 'connection' in check_levels:
                lim = row.get('Conn Limit')
                exp = row.get('Conn Exposure')
                if lim is not None and exp is not None and not math.isnan(float(lim)) and not math.isnan(float(exp)):
                    if float(exp) > float(lim):
                        overage = float(exp) - float(lim)
                        breaches.append({'limit_key': lk, 'counterparty': counterparty_code,
                                         'product': _clean(row.get('Product')), 'level': 'connection',
                                         'limit': float(lim), 'exposure': float(exp),
                                         'overage': overage, 'overage_pct': round(overage / float(lim) * 100, 2),
                                         'date_used': date})

        return {'breaches': breaches, 'breach_count': len(breaches), 'date_used': date}


# ---------------------------------------------------------------------------
# Tool 6: Exposure trend (single counterparty over time)
# ---------------------------------------------------------------------------
class IrisExposureTrendTool(IrisBaseTool):
    def execute(self, params):
        date_from = params.get('date_from', '')
        date_to = params.get('date_to', self._latest_date())
        counterparty_code = params.get('counterparty_code', '')
        legal_entity = params.get('legal_entity', '')
        product = params.get('product', '')
        level = params.get('level', 'product')

        if not counterparty_code:
            return {'error': True, 'error_code': 'MISSING_PARAM', 'message': 'counterparty_code is required'}
        if not date_from:
            return {'error': True, 'error_code': 'MISSING_PARAM', 'message': 'date_from is required'}

        df = self._get_df()
        dates_in_range = sorted([d for d in df['Date'].unique() if date_from <= d <= date_to])

        if not dates_in_range:
            return {'error': True, 'error_code': 'NO_DATA', 'message': 'No dates found in specified range'}

        exp_col = {'product': 'Product Exposure', 'customer': 'Cust Exposure', 'connection': 'Conn Exposure'}.get(level, 'Product Exposure')
        lim_col = {'product': 'Product Limit', 'customer': 'Cust Limit', 'connection': 'Conn Limit'}.get(level, 'Product Limit')

        trend = []
        for d in dates_in_range:
            sub = df[(df['Date'] == d) & (df['Customer Code'] == counterparty_code)]
            if legal_entity:
                sub = sub[sub['Legal Entity'] == legal_entity]
            if product:
                sub = sub[sub['Product'].str.contains(product, case=False, na=False)]
            for _, row in sub.iterrows():
                exp = _clean(row.get(exp_col))
                lim = _clean(row.get(lim_col))
                headroom = (float(lim) - float(exp)) if (lim is not None and exp is not None) else None
                trend.append({'date': d, 'limit_key': self._make_limit_key(row),
                               'exposure': exp, 'limit': lim, 'headroom': headroom})

        delta = None
        if len(trend) >= 2 and trend[0]['exposure'] is not None and trend[-1]['exposure'] is not None:
            delta = float(trend[-1]['exposure']) - float(trend[0]['exposure'])

        return {'trend': trend, 'delta_first_to_last': delta, 'date_count': len(dates_in_range)}


# ---------------------------------------------------------------------------
# Tool 7: Multi-counterparty comparison
# ---------------------------------------------------------------------------
class IrisMultiCounterpartyComparisonTool(IrisBaseTool):
    def execute(self, params):
        date = params.get('date', self._latest_date())
        counterparty_codes = params.get('counterparty_codes', [])
        legal_entity = params.get('legal_entity', '')
        product = params.get('product', '')
        group_by = params.get('group_by', '')

        if not counterparty_codes or len(counterparty_codes) < 2:
            return {'error': True, 'error_code': 'MISSING_PARAM',
                    'message': 'counterparty_codes must be a list with 2+ entries'}
        err = self._validate_date(date)
        if err:
            return err
        err = self._validate_legal_entity(legal_entity)
        if err:
            return err

        df = self._get_df()
        df = df[(df['Date'] == date) & (df['Customer Code'].isin(counterparty_codes))]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if product:
            df = df[df['Product'].str.contains(product, case=False, na=False)]

        comparison = []
        for _, row in df.iterrows():
            lim = _clean(row.get('Product Limit'))
            exp = _clean(row.get('Product Exposure'))
            util = (round(float(exp) / float(lim) * 100, 2) if (lim and exp and float(lim) > 0) else None)
            comparison.append({
                'limit_key': self._make_limit_key(row),
                'counterparty': _clean(row.get('Customer Code')),
                'counterparty_name': _clean(row.get('Customer Name')),
                'rating': _clean(row.get('Customer Internal Rating')),
                'country': _clean(row.get('Country')),
                'product': _clean(row.get('Product')),
                'legal_entity': _clean(row.get('Legal Entity')),
                'limit': lim,
                'exposure': exp,
                'headroom': _clean(row.get('Product Avail')),
                'utilization_pct': util,
            })

        return {'comparison': comparison, 'count': len(comparison), 'date_used': date, 'group_by': group_by}


# ---------------------------------------------------------------------------
# Tool 8: Portfolio breach scan (all counterparties)
# ---------------------------------------------------------------------------
class IrisPortfolioBreachScanTool(IrisBaseTool):
    def execute(self, params):
        date = params.get('date', '')
        min_overage = params.get('min_overage', None)
        legal_entity = params.get('legal_entity', '')
        country = params.get('country', '')
        internal_rating = params.get('internal_rating', None)
        level = params.get('level', '')

        if not date:
            return {'error': True, 'error_code': 'MISSING_PARAM', 'message': 'date is required'}
        if min_overage is None:
            return {'error': True, 'error_code': 'MISSING_PARAM',
                    'message': 'min_overage is required. Specify a threshold (e.g. 1000000) to prevent full-book dumps.'}
        err = self._validate_date(date)
        if err:
            return err
        err = self._validate_legal_entity(legal_entity)
        if err:
            return err

        df = self._get_df()
        df = df[df['Date'] == date]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if country:
            df = df[df['Country'].str.contains(country, case=False, na=False)]
        if internal_rating is not None:
            df = df[df['Customer Internal Rating'] <= int(internal_rating)]

        min_overage = float(min_overage)
        check_levels = [level] if level else ['product', 'customer', 'connection']
        limit_map = {'product': ('Product Limit', 'Product Exposure'),
                     'customer': ('Cust Limit', 'Cust Exposure'),
                     'connection': ('Conn Limit', 'Conn Exposure')}

        breaches = []
        for _, row in df.iterrows():
            lk = self._make_limit_key(row)
            for lvl in check_levels:
                lim_col, exp_col = limit_map[lvl]
                lim = row.get(lim_col)
                exp = row.get(exp_col)
                if lim is None or exp is None:
                    continue
                try:
                    lim, exp = float(lim), float(exp)
                except (ValueError, TypeError):
                    continue
                if math.isnan(lim) or math.isnan(exp):
                    continue
                if exp > lim:
                    overage = exp - lim
                    if overage >= min_overage:
                        breaches.append({
                            'limit_key': lk,
                            'counterparty': _clean(row.get('Customer Code')),
                            'counterparty_name': _clean(row.get('Customer Name')),
                            'rating': _clean(row.get('Customer Internal Rating')),
                            'country': _clean(row.get('Country')),
                            'legal_entity': _clean(row.get('Legal Entity')),
                            'product': _clean(row.get('Product')),
                            'level': lvl,
                            'limit': lim,
                            'exposure': exp,
                            'overage': overage,
                            'overage_pct': round(overage / lim * 100, 2),
                            'date_used': date,
                        })

        total_overage = sum(b['overage'] for b in breaches)
        return {'breaches': breaches, 'total_breaches': len(breaches),
                'total_overage': total_overage, 'date_used': date}


# ---------------------------------------------------------------------------
# Tool 9: Rating screen (portfolio-wide)
# ---------------------------------------------------------------------------
class IrisRatingScreenTool(IrisBaseTool):
    def execute(self, params):
        date = params.get('date', self._latest_date())
        min_rating = params.get('min_rating', None)
        max_rating = params.get('max_rating', None)
        country_rating = params.get('country_rating', '')
        legal_entity = params.get('legal_entity', '')
        country = params.get('country', '')
        min_exposure = params.get('min_exposure', None)

        err = self._validate_date(date)
        if err:
            return err
        err = self._validate_legal_entity(legal_entity)
        if err:
            return err

        df = self._get_df()
        df = df[df['Date'] == date]
        if min_rating is not None:
            df = df[df['Customer Internal Rating'] >= int(min_rating)]
        if max_rating is not None:
            df = df[df['Customer Internal Rating'] <= int(max_rating)]
        if country_rating:
            df = df[df['Country Rating'] == country_rating]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if country:
            df = df[df['Country'].str.contains(country, case=False, na=False)]
        if min_exposure is not None:
            df = df[df['Product Exposure'] >= float(min_exposure)]

        cols = ['Customer Code', 'Customer Name', 'Customer Internal Rating', 'Country',
                'Country Rating', 'Legal Entity', 'Product', 'Facility ID',
                'Product Exposure', 'Product Avail']
        df = df[cols].drop_duplicates()

        results = []
        for _, row in df.iterrows():
            results.append({
                'limit_key': self._make_limit_key(row),
                'name': _clean(row.get('Customer Name')),
                'code': _clean(row.get('Customer Code')),
                'rating': _clean(row.get('Customer Internal Rating')),
                'country': _clean(row.get('Country')),
                'country_rating': _clean(row.get('Country Rating')),
                'legal_entity': _clean(row.get('Legal Entity')),
                'product': _clean(row.get('Product')),
                'exposure': _clean(row.get('Product Exposure')),
                'headroom': _clean(row.get('Product Avail')),
            })

        return {'counterparties': results, 'count': len(results), 'date_used': date}

