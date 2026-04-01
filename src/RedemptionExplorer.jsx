import React from 'react';
import environment from './config';
import { AgGridReact } from 'ag-grid-react';
import SortableHeaderComponent from './SortableHeaderComponent.jsx';
import 'ag-grid-community/dist/styles/ag-grid.css';
import 'ag-grid-community/dist/styles/ag-theme-balham.css';
import 'ag-grid-enterprise';
import { checkStatus } from './utils';
import ExportToolPanel from './ExportToolPanel';
import { API } from 'aws-amplify';
import apiName from './ApiName';

const sideBarConfig = {
  toolPanels: [
    {
      id: 'columns',
      labelDefault: 'Columns',
      labelKey: 'columns',
      iconKey: 'columns',
      toolPanel: 'agColumnsToolPanel',
      toolPanelParams: { suppressPivots: true, suppressPivotMode: true }
    },
    {
      id: 'filters',
      labelDefault: 'Filters',
      labelKey: 'filters',
      iconKey: 'filter',
      toolPanel: 'agFiltersToolPanel'
    },
    {
      id: 'export',
      labelDefault: 'Export',
      labelKey: 'export',
      iconKey: 'save',
      toolPanel: 'exportToolPanel'
    }
  ],
  position: 'right'
};

const RedemptionExplorer = props => {
  let api;
  const { metadata } = props;
  const path = '/api/v1/redemption_stats';

  const getRows = params => {
    let promise;
    if (environment === 'amplify') {
      promise = API.post(apiName, path, { body: params.request });
    } else {
      promise = fetch(path, {
        method: 'post',
        body: JSON.stringify(params.request),
        headers: { 'Content-Type': 'application/json; charset=utf-8' }
      })
        .then(checkStatus)
        .then(r => r.json());
    }
    promise
      .then(response => {
        params.success({ rowData: response.rows, rowCount: response.lastRow });
        params.columnApi.autoSizeAllColumns();
      })
      .catch(error => {
        console.error(error);
        params.fail();
      });
  };

  const onGridReady = params => {
    api = params.api;
    params.api.setServerSideDatasource({ getRows });
  };

  if (metadata) {
    return (
      <div style={{ height: '100vh' }} className="ag-theme-balham">
        <AgGridReact
          onGridReady={onGridReady}
          suppressColumnVirtualisation
          rowSelection="multiple"
          enableRangeSelection
          suppressPivotMode
          rowModelType="serverSide"
          animateRows
          sideBar={sideBarConfig}
          serverSideStoreType="partial"
          frameworkComponents={{
            exportToolPanel: () => (
              <ExportToolPanel
                csvCallback={() => api.exportDataAsCsv()}
                excelCallback={() => api.exportDataAsExcel()}
              />
            )
          }}
          defaultColDef={{
            resizable: true,
            sortable: true,
            filter: 'agTextColumnFilter',
            headerComponentFramework: SortableHeaderComponent,
            headerComponentParams: { menuIcon: 'fa-bars' },
            width: 200
          }}
          groupDisplayType="singleColumn"
          rowGroupPanelShow="always"
          columnDefs={[
            {
              field: 'court_name',
              headerName: 'Court / County',
              enableRowGroup: true,
              rowGroup: true,
              hide: true
            },
            {
              field: 'case_status',
              headerName: 'Status',
              enableRowGroup: true,
              rowGroup: true,
              hide: true
            },
            {
              field: 'judge_assigned',
              headerName: 'Judge',
              enableRowGroup: true,
              hide: true
            },
            {
              field: 'filing_year',
              headerName: 'Filing Year',
              enableRowGroup: true,
              hide: true
            },
            {
              field: 'case_number',
              headerName: 'Case Number'
            },
            {
              field: 'case_title',
              headerName: 'Case Title',
              width: 300
            },
            {
              field: 'filing_date',
              headerName: 'Filing Date',
              filter: 'agDateColumnFilter'
            },
            {
              field: 'case_status_date',
              headerName: 'Status Date',
              filter: 'agDateColumnFilter'
            },
            {
              field: 'count',
              headerName: 'Count',
              allowedAggFuncs: ['sum', 'count'],
              aggFunc: 'sum',
              enableValue: true,
              filter: 'agNumberColumnFilter'
            }
          ]}
        />
      </div>
    );
  } else {
    return (
      <div className="ag-theme-balham" style={{ height: '100%' }}>
        <div className="ag-stub-cell">
          <span className="ag-loading-icon">
            <span className="ag-icon ag-icon-loading" unselectable="on"></span>
          </span>
          <span className="ag-loading-text">Loading...</span>
        </div>
      </div>
    );
  }
};

export default RedemptionExplorer;
