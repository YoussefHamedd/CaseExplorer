import re
from sqlalchemy import cast, Date, column
from sqlalchemy.sql import select, func, and_, or_, text
# from sqlalchemy.sql.expression import table
from flask import current_app
import json
from . import models
from .models import *
from .utils import get_orm_class_by_name, get_eager_query, db_session, get_root_model_list, decimal_to_float
from .officer import Officer, CopCache


class DataService:
    '''Service for fetching data from backend case database'''

    def __init__(self, app=None):
        if app:
            return self.init_app(app)

    def init_app(self, app):
        pass

    @classmethod
    def fetch_cases_by_cop(cls, seq_number, req):
        result = fetch_rows_by_cop(seq_number, req)
        return {
            'rows': result['rows'],
            'lastRow': result['last_row']
        }

    @classmethod
    def fetch_seq_number_by_id(cls, id):
        with db_session(current_app.config.bpdwatch_db_engine) as bpdwatch_db:
            officer = bpdwatch_db.query(Officer).get(id)
            return officer.unique_internal_identifier

    @classmethod
    def fetch_label_by_cop(cls, seq_number):
        with db_session(current_app.config.bpdwatch_db_engine) as bpdwatch_db:
            officer = bpdwatch_db.query(Officer).filter(Officer.unique_internal_identifier == seq_number).one()
            return f'{officer.job_title()} {officer.full_name()} ({seq_number})'

    @classmethod
    def fetch_rows_orm(cls, table_name, req):
        orm_cls = get_orm_class_by_name(table_name)
        result = fetch_rows_from_model(orm_cls, req)
        return {
            'rows': result['rows'],
            'lastRow': result['last_row']
        }
    
    @classmethod
    def fetch_bail_rows(cls, req):
        result = fetch_bail_stats(req)
        return {
            'rows': result['rows'],
            'lastRow': result['last_row']
        }

    @classmethod
    def fetch_foreclosure_rows(cls, req):
        result = fetch_mjcs2_stats(req, case_types=[
            'Foreclosure', 'Foreclosure - Residential',
            'Foreclosure - Commercial', 'Foreclosure - In Rem.'
        ])
        return {'rows': result['rows'], 'lastRow': result['last_row']}

    @classmethod
    def fetch_redemption_rows(cls, req):
        result = fetch_mjcs2_stats(req, case_types=['Right of Redemption'])
        return {'rows': result['rows'], 'lastRow': result['last_row']}

    @classmethod
    def fetch_case_stats(cls):
        return fetch_case_stats_summary()

    @classmethod
    def fetch_rows_orm_eager(cls, table_name, req):
        orm_cls = get_orm_class_by_name(table_name)
        result = fetch_rows_from_model(orm_cls, req, eager=True)
        return {
            'rows': result['rows'],
            'lastRow': result['last_row']
        }
    
    @classmethod
    def fetch_metadata(cls):
        query_results = ColumnMetadata.query.all()
        column_metadata = {}
        for result in query_results:
            if result.redacted == True:
                continue
            if result.table not in column_metadata:
                column_metadata[result.table] = {}
            column_metadata[result.table][result.column_name] = {
                'label': result.label,
                'description': result.description,
                'allowed_values': result.allowed_values,
                'order': result.order
            }

        table_metadata = {}
        for root_model in get_root_model_list(models):
            # model_list.append(root_model)
            subtables = []
            for rel_name, relationship in root_model.__mapper__.relationships.items():
                if relationship.target.name == 'cases':
                    continue
                model = get_orm_class_by_name(relationship.target.name)
                if model.__table__.name not in subtables:
                    subtables.append(model.__table__.name)
            table_metadata[root_model.__table__.name] = {
                'subtables': subtables,
                'description': root_model.__doc__
            }
        return {
            'columns': column_metadata,
            'tables': table_metadata
        }

    @classmethod
    def fetch_total(cls, table_name):
        with db_session() as db:
            results = db.execute(f"SELECT reltuples FROM pg_class WHERE oid = '{table_name}'::regclass").scalar()
        return int(results)
    
    @classmethod
    def fetch_filtered_total(cls, table_name, req):
        orm_cls = get_orm_class_by_name(table_name)
        result = fetch_rows_from_model(orm_cls, req, total_only=True)
        return result
    
    @classmethod
    def fetch_filtered_total_by_cop(cls, seq_number, req=None):
        result = fetch_rows_by_cop(seq_number, req, total_only=True)
        return result


def fetch_rows_by_cop(seq_number, req, total_only=False):
    query = Case.query\
        .join(CopCache, Case.case_number == CopCache.case_number)\
        .filter(CopCache.officer_seq_no == seq_number)

    # If no results in cache table, just do active search by sequence number
    if query.count() == 0:
        q1 = Case.query\
            .join(DSCRRelatedPerson, Case.case_number == DSCRRelatedPerson.case_number)\
            .filter(
                and_(
                    DSCRRelatedPerson.connection.like('%POLICE%'),
                    DSCRRelatedPerson.agency_code == 'AD',
                    DSCRRelatedPerson.officer_id == seq_number,
                )
            )
        q2 = Case.query\
            .join(DSTRAF, Case.case_number == DSTRAF.case_number)\
            .filter(DSTRAF.officer_id == seq_number)
        query = q1.union(q2)

    # Apply filters
    table = Case.__table__
    if req:
        query = build_where(query, table, req)
        query = build_order_by(query, table, req)
        query = build_group_by(query, table, req)

    if total_only:
        return query.count()

    query = build_limit(query, req)
    results = query.all()

    results_len = len(results)
    start_row = int(req['startRow'])
    end_row = int(req['endRow'])
    page_size = end_row - start_row
    current_last_row = start_row + results_len
    last_row = current_last_row if current_last_row <= end_row else -1
    rows = results[:page_size]

    return {
        'rows': rows,
        'last_row': last_row
    }


def fetch_rows_from_model(cls, req, eager=False, total_only=False):
    start_row = int(req['startRow'])
    end_row = int(req['endRow'])
    page_size = end_row - start_row
    table = cls.__table__

    query = get_eager_query(cls) if eager else cls.query


    # query = build_select(table, req)
    query = build_where(query, table, req)
    query = build_order_by(query, table, req)
    query = build_group_by(query, table, req)

    if total_only:
        return query.count()
    
    query = build_limit(query, req)
    results = query.all()
    results_len = len(results)
    current_last_row = start_row + results_len
    last_row = current_last_row if current_last_row <= end_row else -1
    rows = results[:page_size]

    # filter defendant redacted fields
    private_fields = [column.name for column in cls.__table__.columns if hasattr(column, 'redacted') and column.redacted == True]
    if private_fields:
        for row in rows:
            for field in private_fields:
                try:
                    del row[field]
                except:
                    pass

    return {
        'rows': rows,
        'last_row': last_row
    }


def fetch_bail_stats(req, total_only=False):
    start_row = int(req['startRow'])
    end_row = int(req['endRow'])
    page_size = end_row - start_row

    class FauxTable:
        c = {**dict(DSCR.__table__.c), **dict(DSCRDefendant.__table__.c), **dict(DSCRBailEvent.__table__.c)}

    query, fields = build_bail_select(req)
    query = build_where(query, FauxTable, req)
    query = build_order_by(query, FauxTable, req)
    query = build_group_by(query, FauxTable, req)

    # if total_only:
        # return query.count()
    
    query = build_limit(query, req)
    # results = query.all()
    # print(query)
    with db_session() as db:
        results = list(db.execute(query))
    results_len = len(results)
    current_last_row = start_row + results_len
    last_row = current_last_row if current_last_row <= end_row else -1
    rows = results[:page_size]

    labeled_rows = []
    for row in decimal_to_float(rows):
        assert(len(fields) == len(row))
        labeled_row = {}
        for i in range(0, len(fields)):
            labeled_row[fields[i]] = row[i]
        labeled_rows.append(labeled_row)

    return {
        'rows': labeled_rows,
        'last_row': last_row
    }


def build_bail_select(req):
    row_group_cols = req['rowGroupCols']
    group_keys = req['groupKeys']
    value_cols = req['valueCols']

    available_cols = [
        DSCR.court_system,
        DSCRDefendant.race,
        DSCRDefendant.sex,
        DSCRBailEvent.event_name,
        DSCRBailEvent.code,
        DSCRBailEvent.type_of_bond,
        DSCRBailEvent.bail_amount,
        DSCRBailEvent.percentage_required
    ]
    cols_map = {col.name: col for col in available_cols}

    if is_grouping(row_group_cols, group_keys):
        cols = [cols_map[row_group_cols[len(group_keys)]['field']]]
        for value_col in value_cols:
            agg_func = value_col['aggFunc']
            field = value_col['field']
            try:
                col = getattr(func, agg_func)(cols_map[field]).label(field)
            except KeyError:
                raise Exception('Invalid column {}'.format(field))
            cols.append(col)
        ret = cols
    else:
        ret = available_cols
    
    fields = [col.name for col in ret]

    return select(ret).select_from(DSCRBailEvent)\
        .join(DSCRDefendant, DSCRBailEvent.case_number == DSCRDefendant.case_number)\
        .join(DSCR, DSCRBailEvent.case_number == DSCR.case_number), fields


def build_where(query, table, req):
    row_group_cols = req['rowGroupCols']
    group_keys = req['groupKeys']
    filter_model = req['filterModel']

    where_parts = []
    if len(group_keys) > 0:
        for idx, key in enumerate(group_keys):
            field = row_group_cols[idx]['field']
            where_parts.append(table.c[field] == key)

    if filter_model:
        for field, model in filter_model.items():
            filter = create_filter_sql(table.c[field], model)
            if filter is not None:
                where_parts.append(filter)

    if where_parts:
        for condition in where_parts:
            query = query.filter(condition)

    return query


def build_limit(query, req):
    start_row = req['startRow']
    end_row = req['endRow']
    page_size = end_row - start_row
    return query.limit(page_size + 1).offset(start_row)


def create_filter_sql(col, model):
    if 'operator' in model:
        op = model['operator']
        if op == 'AND':
            return and_(
                process_filter(col, model['condition1']),
                process_filter(col, model['condition2'])
            )
        elif op == 'OR':
            return or_(
                process_filter(col, model['condition1']),
                process_filter(col, model['condition2'])
            )
    elif 'filterType' in model:
        return process_filter(col, model)


def process_filter(col, model):
    filter_type = model['filterType']
    if filter_type == 'text':
        return process_text_filter(col, model)
    elif filter_type == 'number':
        return process_number_filter(col, model)
    elif filter_type == 'date':
        return process_date_filter(col, model)
    elif filter_type == 'set':
        return process_set_filter(col, model)
    raise Exception('Unknown filter type ' + filter_type)


def process_text_filter(col, model):
    op = model['type']
    filter = model['filter']
    if op == 'equals':
        return col == filter
    elif op == 'notEqual':
        return col != filter
    elif op == 'contains':
        return col.ilike('%{}%'.format(filter))
    elif op == 'notContains':
        return col.notilike('%{}%'.format(filter))
    elif op == 'startsWith':
        return col.ilike('{}%'.format(filter))
    elif op == 'endsWith':
        return col.ilike('%{}'.format(filter))
    raise Exception('Unknown text filter type ' + op)


def process_number_filter(col, model):
    op = model['type']
    filter = model['filter']
    if op == 'equals':
        return col == filter
    elif op == 'notEqual':
        return col != filter
    elif op == 'greaterThan':
        return col > filter
    elif op == 'greaterThanOrEqual':
        return col >= filter
    elif op == 'lessThan':
        return col < filter
    elif op == 'lessThanOrEqual':
        return col >= filter
    elif op == 'inRange':
        filter_to = model['filterTo']
        return and_(col >= filter, col <= filter_to)
    raise Exception('Unknown number filter type ' + op)


def process_date_filter(col, model):
    op = model['type']
    date_from = model['dateFrom']
    match = re.fullmatch(r'(\d\d\d\d)-(\d\d)-(\d\d) 00:00:00', date_from)
    if not match:
        raise Exception('Invalid date format ' + date_from)
    year = match.group(1)
    month = match.group(2)
    day = match.group(3)
    date_from = '{}/{}/{}'.format(month, day, year)
    if op == 'equals':
        return col == date_from
    elif op == 'notEqual':
        return col != date_from
    elif op == 'greaterThan':
        return col > date_from
    elif op == 'lessThan':
        return col < date_from
    elif op == 'inRange':
        date_to = model['dateTo']
        match = re.fullmatch(r'(\d\d\d\d)-(\d\d)-(\d\d) 00:00:00', date_to)
        if not match:
            raise Exception('Invalid date format ' + date_to)
        to_year = match.group(1)
        to_month = match.group(2)
        to_day = match.group(3)
        date_to = '{}/{}/{}'.format(to_month, to_day, to_year)
        return and_(
            col >= date_from,
            col <= date_to
        )
    raise Exception('Unknown date filter type ' + op)


def process_set_filter(col, model):
    filter = None
    vals = model['values']
    null = '' in vals
    if null:
        vals.remove('')
    if vals:
        filter = col.in_(vals)
        if null:
            filter = or_(
                filter,
                col == None
            )
    elif null:
        filter = col == None
    return filter


def build_order_by(query, table, req):
    sort_model = req['sortModel']
    row_group_cols = req['rowGroupCols']
    group_keys = req['groupKeys']
    grouping = is_grouping(row_group_cols, group_keys)

    if sort_model:
        sort_parts = []
        group_col_ids = [col['id'] for col in row_group_cols][:len(group_keys) + 1]
        for item in sort_model:
            col_id = item['colId']
            sort = item['sort']
            if not grouping or col_id in group_col_ids:
                if 'date_' in col_id:
                    if sort == 'asc':
                        query = query.order_by(cast(table.c[col_id], Date).asc())
                    elif sort == 'desc':
                        query = query.order_by(cast(table.c[col_id], Date).desc())
                    else:
                        raise Exception('Invalid sort ' + sort)
                else:
                    if sort == 'asc':
                        query = query.order_by(table.c[col_id].asc())
                    elif sort == 'desc':
                        query = query.order_by(table.c[col_id].desc())
                    else:
                        raise Exception('Invalid sort ' + sort)

    return query


def build_group_by(query, table, req):
    row_group_cols = req['rowGroupCols']
    group_keys = req['groupKeys']

    if is_grouping(row_group_cols, group_keys):
        field = row_group_cols[len(group_keys)]['field']
        query = query.group_by(table.c[field])

    return query


def is_grouping(row_group_cols, group_keys):
    return len(row_group_cols) > len(group_keys)


FC_CASE_TYPES = (
    'Foreclosure', 'Foreclosure - Residential',
    'Foreclosure - Commercial', 'Foreclosure - In Rem.',
    'Right of Redemption'
)

def fetch_foreclosure_active(req, date_from='2024-01-01', date_to='2026-12-31'):
    """Return foreclosure cases that had ANY activity between date_from and date_to.
    Activity = filed, hearing, document event, or case_status_date in that range.
    Older cases still ongoing in courts are included."""
    start_row = int(req['startRow'])
    end_row   = int(req['endRow'])
    page_size = end_row - start_row

    row_group_cols = req.get('rowGroupCols', [])
    group_keys     = req.get('groupKeys', [])
    sort_model     = req.get('sortModel', [])
    filter_model   = req.get('filterModel', {})

    grouping = len(row_group_cols) > len(group_keys)

    type_placeholders = ', '.join([f':ct{i}' for i in range(len(FC_CASE_TYPES))])
    params = {f'ct{i}': ct for i, ct in enumerate(FC_CASE_TYPES)}
    params['date_from'] = date_from
    params['date_to']   = date_to

    if grouping:
        group_field   = row_group_cols[len(group_keys)]['field']
        select_clause = f"c.{group_field}, COUNT(*) as count"
        group_by_clause = f'GROUP BY c.{group_field}'
    else:
        select_clause = (
            'c.case_number, c.case_type, COALESCE(m.case_title, c.caption) as case_title, '
            'COALESCE(m.court_name, c.court) as court_name, '
            'm.case_status, m.case_status_date, m.judge_assigned, c.filing_date, '
            'EXTRACT(YEAR FROM c.filing_date)::int AS filing_year, 1 as count'
        )
        group_by_clause = ''

    where_parts = [
        f'c.case_type IN ({type_placeholders})',
        'c.filing_date BETWEEN :date_from AND :date_to'
    ]

    # Group key filters
    for idx, key in enumerate(group_keys):
        field = row_group_cols[idx]['field']
        where_parts.append(f"{field} = :gk{idx}")
        params[f'gk{idx}'] = key

    # Column filter model
    for field, filt in filter_model.items():
        if filt.get('filterType') == 'text' and filt.get('filter'):
            where_parts.append(f"CAST({field} AS TEXT) ILIKE :f_{field}")
            params[f'f_{field}'] = f"%{filt['filter']}%"
        elif filt.get('filterType') == 'date':
            if filt.get('dateFrom'):
                where_parts.append(f"{field} >= :fd_{field}")
                params[f'fd_{field}'] = filt['dateFrom'][:10]
            if filt.get('dateTo'):
                where_parts.append(f"{field} <= :fdt_{field}")
                params[f'fdt_{field}'] = filt['dateTo'][:10]

    where_clause = 'WHERE ' + ' AND '.join(where_parts)

    if sort_model:
        order_clause = 'ORDER BY ' + ', '.join(
            f"{s['colId']} {s['sort'].upper()}" for s in sort_model
        )
    elif grouping:
        order_clause = 'ORDER BY count DESC'
    else:
        order_clause = 'ORDER BY filing_date DESC'

    sql = text(f"""
        SELECT {select_clause}
        FROM cases c
        LEFT JOIN mjcs2 m ON m.case_number = c.case_number
        {where_clause}
        {group_by_clause}
        {order_clause}
        LIMIT :lim OFFSET :off
    """)
    params['lim'] = page_size + 1
    params['off'] = start_row

    with db_session() as db:
        results = list(db.execute(sql, params))

    results_len = len(results)
    current_last_row = start_row + results_len
    last_row = current_last_row if current_last_row <= end_row else -1
    rows = results[:page_size]

    if grouping:
        group_field = row_group_cols[len(group_keys)]['field']
        labeled_rows = [{'group_field': r[0], group_field: r[0], 'count': int(r[1])} for r in rows]
    else:
        cols = ['case_number', 'case_type', 'case_title', 'court_name',
                'case_status', 'case_status_date', 'judge_assigned', 'filing_date',
                'filing_year', 'count']
        labeled_rows = []
        for row in rows:
            labeled_row = {}
            for i, col in enumerate(cols):
                val = row[i]
                if hasattr(val, 'isoformat'):
                    val = val.isoformat()
                labeled_row[col] = val
            labeled_rows.append(labeled_row)

    return {'rows': labeled_rows, 'last_row': last_row}


def fetch_mjcs2_stats(req, case_types, date_from=None, date_to=None):
    start_row = int(req['startRow'])
    end_row = int(req['endRow'])
    page_size = end_row - start_row

    row_group_cols = req.get('rowGroupCols', [])
    group_keys = req.get('groupKeys', [])
    value_cols = req.get('valueCols', [])
    sort_model = req.get('sortModel', [])
    filter_model = req.get('filterModel', {})

    type_placeholders = ', '.join([f':ct{i}' for i in range(len(case_types))])
    type_params = {f'ct{i}': ct for i, ct in enumerate(case_types)}

    grouping = len(row_group_cols) > len(group_keys)

    if grouping:
        group_field = row_group_cols[len(group_keys)]['field']
        select_fields = [group_field, 'COUNT(*) as count']
        group_by_clause = f'GROUP BY {group_field}'
    else:
        select_fields = [
            'case_number', 'case_type', 'case_title', 'court_name',
            'case_status', 'case_status_date', 'judge_assigned', 'filing_date',
            "EXTRACT(YEAR FROM filing_date)::int AS filing_year",
            '1 as count'
        ]
        group_by_clause = ''

    select_clause = ', '.join(select_fields)
    where_parts = [f'case_type IN ({type_placeholders})']
    if date_from:
        where_parts.append('filing_date >= :date_from')
        type_params['date_from'] = date_from
    if date_to:
        where_parts.append('filing_date <= :date_to')
        type_params['date_to'] = date_to
    params = dict(type_params)

    # Apply group key filters
    for idx, key in enumerate(group_keys):
        field = row_group_cols[idx]['field']
        where_parts.append(f"{field} = :gk{idx}")
        params[f'gk{idx}'] = key

    # Apply filter model
    for field, filt in filter_model.items():
        if filt.get('filterType') == 'text' and filt.get('filter'):
            where_parts.append(f"CAST({field} AS TEXT) ILIKE :f_{field}")
            params[f'f_{field}'] = f"%{filt['filter']}%"
        elif filt.get('filterType') == 'date':
            if filt.get('dateFrom'):
                where_parts.append(f"{field} >= :fd_{field}")
                params[f'fd_{field}'] = filt['dateFrom'][:10]
            if filt.get('dateTo'):
                where_parts.append(f"{field} <= :fdt_{field}")
                params[f'fdt_{field}'] = filt['dateTo'][:10]

    where_clause = 'WHERE ' + ' AND '.join(where_parts) if where_parts else ''

    order_clause = ''
    if sort_model:
        parts = [f"{s['colId']} {s['sort'].upper()}" for s in sort_model]
        order_clause = 'ORDER BY ' + ', '.join(parts)
    elif grouping:
        order_clause = 'ORDER BY count DESC'
    else:
        order_clause = 'ORDER BY filing_date DESC'

    limit_val = page_size + 1
    offset_val = start_row

    sql = text(f"""
        SELECT {select_clause}
        FROM cases c
        LEFT JOIN mjcs2 m ON m.case_number = c.case_number
        {where_clause}
        {group_by_clause}
        {order_clause}
        LIMIT :lim OFFSET :off
    """)
    params['lim'] = limit_val
    params['off'] = offset_val

    with db_session() as db:
        results = list(db.execute(sql, params))

    results_len = len(results)
    current_last_row = start_row + results_len
    last_row = current_last_row if current_last_row <= end_row else -1
    rows = results[:page_size]

    if grouping:
        labeled_rows = [{'group_field': r[0], group_field: r[0], 'count': int(r[1])} for r in rows]
    else:
        cols = ['case_number', 'case_type', 'case_title', 'court_name',
                'case_status', 'case_status_date', 'judge_assigned', 'filing_date',
                'filing_year', 'count']
        labeled_rows = []
        for row in rows:
            labeled_row = {}
            for i, col in enumerate(cols):
                val = row[i]
                if hasattr(val, 'isoformat'):
                    val = val.isoformat()
                labeled_row[col] = val
            labeled_rows.append(labeled_row)

    return {'rows': labeled_rows, 'last_row': last_row}


def fetch_case_stats_summary():
    with db_session() as db:
        totals = db.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE case_type ILIKE '%foreclos%') AS foreclosures,
                COUNT(*) FILTER (WHERE case_type = 'Right of Redemption') AS redemption,
                COUNT(*) FILTER (WHERE case_status ILIKE '%open%' OR case_status ILIKE '%active%') AS open,
                COUNT(*) FILTER (WHERE case_status ILIKE '%close%' OR case_status ILIKE '%dismiss%') AS closed,
                COUNT(*) FILTER (WHERE filing_date >= '2025-01-01') AS y2025,
                COUNT(*) FILTER (WHERE filing_date >= '2026-01-01') AS y2026
            FROM mjcs2
        """)).fetchone()

        by_type = db.execute(text("""
            SELECT case_type, COUNT(*) as count
            FROM mjcs2
            WHERE case_type IS NOT NULL
            GROUP BY case_type
            ORDER BY count DESC
            LIMIT 25
        """)).fetchall()

        by_court = db.execute(text("""
            SELECT court_name, COUNT(*) as count
            FROM mjcs2
            WHERE court_name IS NOT NULL
            GROUP BY court_name
            ORDER BY count DESC
            LIMIT 20
        """)).fetchall()

        by_year = db.execute(text("""
            SELECT EXTRACT(YEAR FROM filing_date)::int AS year, COUNT(*) as count
            FROM mjcs2
            WHERE filing_date IS NOT NULL
              AND EXTRACT(YEAR FROM filing_date) >= 2000
            GROUP BY year
            ORDER BY year
        """)).fetchall()

        by_status = db.execute(text("""
            SELECT case_status, COUNT(*) as count
            FROM mjcs2
            WHERE case_status IS NOT NULL
            GROUP BY case_status
            ORDER BY count DESC
        """)).fetchall()

    return {
        'totals': {
            'total': totals[0], 'foreclosures': totals[1],
            'redemption': totals[2], 'open': totals[3],
            'closed': totals[4], 'y2025': totals[5], 'y2026': totals[6]
        },
        'by_type':   [{'case_type': r[0], 'count': r[1]} for r in by_type],
        'by_court':  [{'court_name': r[0], 'count': r[1]} for r in by_court],
        'by_year':   [{'year': r[0], 'count': r[1]} for r in by_year],
        'by_status': [{'case_status': r[0], 'count': r[1]} for r in by_status],
    }
