import React from 'react';
import { Nav, INavLinkGroup } from 'office-ui-fabric-react/lib/Nav';
import { toTitleCase, getURLLastPart } from './utils';
import CopFinder from './CopFinder';
import CaseFinder from './CaseFinder';
import apiName from './ApiName';
import { mergeStyleSets, Text } from '@fluentui/react';
import { FontIcon } from '@fluentui/react/lib/Icon';
import {
  TooltipHost,
  TooltipDelay,
  DirectionalHint,
  ITooltipProps
} from '@fluentui/react';

let navLinkGroups = [
  {
    name: 'Case Data',
    key: 'Case Data',
    links: [
      { name: 'All Cases', url: '/', key: 'cases' },
      {
        name: 'Foreclosure Explorer',
        url: '/foreclosures',
        key: 'Foreclosure Explorer'
      },
      {
        name: 'Right of Redemption',
        url: '/redemption',
        key: 'Right of Redemption'
      },
      { name: 'Case Statistics', url: '/statistics', key: 'Case Statistics' }
    ],
    isExpanded: true
  },
  {
    name: 'Search By Case Number',
    key: 'Search By Case Number'
  },
  {
    name: 'Search By BPD Officer',
    key: 'Search By BPD Officer'
  },
  {
    name: 'API',
    key: 'API',
    links: [
      { name: 'GraphQL', url: '/graphql', key: 'graphql' },
      { name: 'REST', key: 'REST', url: '/rest' }
    ],
    isExpanded: false
  },
  {
    name: 'Admin',
    key: 'Admin',
    links: [{ name: 'Harvest & Scrape', url: '/admin', key: 'admin' }],
    isExpanded: true
  }
];

const genNavItem = (metadata, currentTable, table) => {
  const table_metadata = metadata[table];
  let links = [{ name: 'Overview', url: '/' + table, key: table }];
  for (const subtable of table_metadata.subtables) {
    const label = toTitleCase(subtable.replace(/^[^_]+_/, ''));
    links.push({
      name: label,
      url: '/' + subtable,
      key: subtable
    });
  }
  return {
    name: table_metadata.description,
    expandAriaLabel: 'Expand section',
    collapseAriaLabel: 'Collapse section',
    links: links,
    isExpanded: table === currentTable ? true : false
  };
};

export const genNavStructure = metadata => {
  let currentTable = getURLLastPart();
  if (currentTable.indexOf('_') !== -1)
    currentTable = currentTable.substring(0, currentTable.indexOf('_'));
};

const NavBar = props => {
  function _onRenderGroupHeader(group) {
    if (group.name === 'Search By BPD Officer') {
      return (
        <>
          <h3>{group.name}</h3>
          <CopFinder apiName={apiName} />
        </>
      );
    } else if (group.name === 'Search By Case Number') {
      return (
        <>
          <h3>{group.name}</h3>
          <CaseFinder />
        </>
      );
    } else {
      return <h3>{group.name}</h3>;
    }
  }

  function _onRenderLink(link) {
    if (link.name === 'MDEC') {
      return (
        <>
          <span className={styles.mdec}>MDEC</span>
          <TooltipHost
            tooltipProps={tooltipProps}
            delay={TooltipDelay.zero}
            directionalHint={DirectionalHint.rightCenter}
            className={styles.tooltip}
          >
            <FontIcon
              aria-label="MDEC"
              iconName="Info"
              className={styles.icon}
            />
          </TooltipHost>
        </>
      );
    }
    return link.name;
  }

  return (
    <Nav
      onRenderGroupHeader={_onRenderGroupHeader}
      onRenderLink={_onRenderLink}
      groups={navLinkGroups}
      styles={props => ({
        chevronIcon: {
          transform: props.isExpanded ? 'rotate(0deg)' : 'rotate(-90deg)'
        }
      })}
    />
  );
};
export default NavBar;

const styles = mergeStyleSets({
  tooltip: {
    lineHeight: '1.4',
    padding: '20px'
  },
  mdec: {
    margin: '0 4px'
  },
  icon: {
    margin: '0 4px',
    fontSize: '16px',
    position: 'relative',
    top: '2px'
  }
});

const tooltipProps = {
  onRenderContent: () => (
    <Text block variant="medium">
      <a target="_blank" href="https://mdcourts.gov/mdec/about">
        Maryland Electronic Courts (MDEC)
      </a>{' '}
      is a single Judiciary-wide integrated case management system that will be
      used by all the courts in the state court system.
    </Text>
  )
};
