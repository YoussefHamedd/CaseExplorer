from marshmallow import Schema, fields

class RowGroupColumn(Schema):
    id = fields.String(allow_none=True)
    displayName = fields.String(allow_none=True)
    field = fields.String(required=True)
    aggFunc = fields.String(allow_none=True, load_default=None)

class ValueColumn(Schema):
    id = fields.String(allow_none=True)
    displayName = fields.String(allow_none=True)
    field = fields.String(required=True)
    aggFunc = fields.String(allow_none=True, load_default=None)

class SortColumn(Schema):
    colId = fields.String(required=True)
    sort = fields.String(allow_none=True)

class QueryParams(Schema):
    startRow = fields.Number(load_default=0)
    endRow = fields.Number(load_default=100)
    rowGroupCols = fields.List(fields.Nested(RowGroupColumn), load_default=list)
    valueCols = fields.List(fields.Nested(ValueColumn), load_default=list)
    pivotCols = fields.List(fields.Nested(RowGroupColumn), load_default=list)
    pivotMode = fields.Boolean(load_default=False)
    groupKeys = fields.List(fields.String(), load_default=list)
    sortModel = fields.List(fields.Nested(SortColumn), load_default=list)
    filterModel = fields.Dict(load_default=dict)
    date_from = fields.String(allow_none=True, load_default=None)
    date_to = fields.String(allow_none=True, load_default=None)
