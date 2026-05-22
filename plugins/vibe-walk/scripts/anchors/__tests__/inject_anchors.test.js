'use strict';
/**
 * TDD tests for inject_anchors.js — the M4 jscodeshift codemod.
 *
 * Uses jscodeshift's built-in applyTransform testUtils.  Fixture source is
 * inlined as strings so Jest never tries to parse JSX itself.
 *
 * Gate coverage (D6):
 *   Gate A — intrinsic HTML element or directly-imported named component
 *   Gate B — single unambiguous root return
 *   Gate C — no HOC / dynamic import / render-prop at injection site
 *   Gate D — data-tour attribute absent (idempotency)
 *
 * All four gates pass → AUTO-INJECT.
 * Any gate failure → REVIEW_NEEDED entry with accurate reason code.
 */

const { applyTransform } = require('jscodeshift/src/testUtils.js');
const transform = require('../inject_anchors.js');
const { REASON_CODES } = transform;

// ---------------------------------------------------------------------------
// Helper — run the transform and collect any REVIEW_NEEDED entries.
// ---------------------------------------------------------------------------
function runTransform(source, plan, filePath = 'test-fixture.jsx') {
  // Reset the side-channel before each run.
  transform._lastReviewEntries = [];
  const fileInfo = { path: filePath, source };
  const options = { plan };
  // applyTransform returns `(output || '').trim()`.
  // When the transform returns null (no changes), it returns '' (empty string).
  const result = applyTransform(transform, options, fileInfo, { parser: 'tsx' });
  const reviewNeeded = transform._lastReviewEntries || [];
  const changed = result !== '';
  // Fall back to original source when no changes.
  return { code: changed ? result : source, reviewNeeded, changed };
}

// ---------------------------------------------------------------------------
// REASON_CODES export
// ---------------------------------------------------------------------------
describe('REASON_CODES export', () => {
  test('exports the expected reason code strings', () => {
    expect(REASON_CODES.HOC_WRAPPED).toBe('HOC_WRAPPED');
    expect(REASON_CODES.FRAGMENT_ROOT).toBe('FRAGMENT_ROOT');
    expect(REASON_CODES.CONDITIONAL_ROOT).toBe('CONDITIONAL_ROOT');
    expect(REASON_CODES.ALREADY_ANCHORED).toBe('ALREADY_ANCHORED');
    expect(REASON_CODES.MULTIPLE_ROOTS).toBe('MULTIPLE_ROOTS');
    expect(REASON_CODES.DYNAMIC_COMPONENT).toBe('DYNAMIC_COMPONENT');
    expect(REASON_CODES.RENDER_PROP).toBe('RENDER_PROP');
    expect(REASON_CODES.THIRD_PARTY_COMPONENT).toBe('THIRD_PARTY_COMPONENT');
  });
});

// ---------------------------------------------------------------------------
// Test 1 — clean intrinsic element → AUTO-INJECT
// ---------------------------------------------------------------------------
describe('clean intrinsic element (all four gates pass)', () => {
  const source = [
    "import React from 'react';",
    'export function Sidebar({ children }) {',
    '  return (',
    '    <nav className="sidebar">',
    '      {children}',
    '    </nav>',
    '  );',
    '}',
  ].join('\n');

  const plan = {
    'test-fixture.jsx': { anchorName: 'sidebar', targetHint: 'Sidebar nav root' },
  };

  test('injects data-tour on the root <nav>', () => {
    const { code } = runTransform(source, plan);
    expect(code).toContain('data-tour="sidebar"');
  });

  test('preserves existing className attribute', () => {
    const { code } = runTransform(source, plan);
    expect(code).toContain('className="sidebar"');
  });

  test('does not add a REVIEW_NEEDED entry', () => {
    const { reviewNeeded } = runTransform(source, plan);
    expect(reviewNeeded).toHaveLength(0);
  });

  test('reports a change was made', () => {
    const { changed } = runTransform(source, plan);
    expect(changed).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Test 2 — directly-imported named component → AUTO-INJECT
// ---------------------------------------------------------------------------
describe('directly-imported named component root (Gate A named-component path)', () => {
  const source = [
    "import React from 'react';",
    "import { Card } from './Card';",
    'export function DashboardCard({ title }) {',
    '  return (',
    '    <Card className="dashboard-card">',
    '      <h2>{title}</h2>',
    '    </Card>',
    '  );',
    '}',
  ].join('\n');

  const plan = {
    'test-fixture.jsx': { anchorName: 'dashboard-card', targetHint: 'DashboardCard root' },
  };

  test('injects data-tour on the root <Card>', () => {
    const { code } = runTransform(source, plan);
    expect(code).toContain('data-tour="dashboard-card"');
  });

  test('does not add a REVIEW_NEEDED entry', () => {
    const { reviewNeeded } = runTransform(source, plan);
    expect(reviewNeeded).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Test 3 — HOC-wrapped export → REVIEW_NEEDED HOC_WRAPPED
// ---------------------------------------------------------------------------
describe('HOC-wrapped export (Gate C failure)', () => {
  const source = [
    "import React from 'react';",
    "import { withAuth } from './withAuth';",
    'function Dashboard({ user }) {',
    '  return (',
    '    <div className="dashboard">',
    '      <h1>Welcome, {user.name}</h1>',
    '    </div>',
    '  );',
    '}',
    'export default withAuth(Dashboard);',
  ].join('\n');

  const plan = {
    'test-fixture.jsx': { anchorName: 'dashboard', targetHint: 'Dashboard root' },
  };

  test('does NOT inject data-tour', () => {
    const { code } = runTransform(source, plan);
    expect(code).not.toContain('data-tour=');
  });

  test('emits a REVIEW_NEEDED entry with reason HOC_WRAPPED', () => {
    const { reviewNeeded } = runTransform(source, plan);
    const entry = reviewNeeded.find((e) => e.reasonCode === REASON_CODES.HOC_WRAPPED);
    expect(entry).toBeDefined();
    expect(entry.file).toBe('test-fixture.jsx');
    expect(entry.anchorName).toBe('dashboard');
  });

  test('reports no change was made', () => {
    const { changed } = runTransform(source, plan);
    expect(changed).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Test 4 — fragment root → REVIEW_NEEDED FRAGMENT_ROOT
// ---------------------------------------------------------------------------
describe('fragment root (Gate B failure — no single root element)', () => {
  const source = [
    "import React from 'react';",
    'export function Layout({ children }) {',
    '  return (',
    '    <>',
    '      <header className="app-header">Header</header>',
    '      <main className="app-main">{children}</main>',
    '      <footer className="app-footer">Footer</footer>',
    '    </>',
    '  );',
    '}',
  ].join('\n');

  const plan = {
    'test-fixture.jsx': { anchorName: 'layout', targetHint: 'Layout root' },
  };

  test('does NOT inject data-tour', () => {
    const { code } = runTransform(source, plan);
    expect(code).not.toContain('data-tour=');
  });

  test('emits a REVIEW_NEEDED entry with reason FRAGMENT_ROOT', () => {
    const { reviewNeeded } = runTransform(source, plan);
    const entry = reviewNeeded.find((e) => e.reasonCode === REASON_CODES.FRAGMENT_ROOT);
    expect(entry).toBeDefined();
    expect(entry.anchorName).toBe('layout');
  });
});

// ---------------------------------------------------------------------------
// Test 5 — multiple conditional returns → REVIEW_NEEDED CONDITIONAL_ROOT
// ---------------------------------------------------------------------------
describe('multiple conditional returns (Gate B failure — ambiguous root)', () => {
  const source = [
    "import React from 'react';",
    'export function Panel({ isLoading, data }) {',
    '  if (isLoading) {',
    '    return <div className="loading-spinner">Loading...</div>;',
    '  }',
    '  if (!data) {',
    '    return <div className="empty-state">No data available</div>;',
    '  }',
    '  return (',
    '    <section className="panel">',
    '      <h2>{data.title}</h2>',
    '    </section>',
    '  );',
    '}',
  ].join('\n');

  const plan = {
    'test-fixture.jsx': { anchorName: 'panel', targetHint: 'Panel root' },
  };

  test('does NOT inject data-tour', () => {
    const { code } = runTransform(source, plan);
    expect(code).not.toContain('data-tour=');
  });

  test('emits a REVIEW_NEEDED entry with reason CONDITIONAL_ROOT or MULTIPLE_ROOTS', () => {
    const { reviewNeeded } = runTransform(source, plan);
    const entry = reviewNeeded.find(
      (e) =>
        e.reasonCode === REASON_CODES.CONDITIONAL_ROOT ||
        e.reasonCode === REASON_CODES.MULTIPLE_ROOTS,
    );
    expect(entry).toBeDefined();
    expect(entry.anchorName).toBe('panel');
  });
});

// ---------------------------------------------------------------------------
// Test 6 — already-anchored element → skip (idempotent), ALREADY_ANCHORED
// ---------------------------------------------------------------------------
describe('already-anchored element (Gate D failure — idempotency)', () => {
  const source = [
    "import React from 'react';",
    'export function NavMenu({ items }) {',
    '  return (',
    '    <nav data-tour="nav-menu" className="nav-menu">',
    '      {items.map((item) => (',
    '        <a key={item.id} href={item.href}>{item.label}</a>',
    '      ))}',
    '    </nav>',
    '  );',
    '}',
  ].join('\n');

  const plan = {
    'test-fixture.jsx': { anchorName: 'nav-menu', targetHint: 'NavMenu root' },
  };

  test('does NOT duplicate the data-tour attribute', () => {
    const { code } = runTransform(source, plan);
    const matches = (code.match(/data-tour=/g) || []).length;
    expect(matches).toBe(1);
  });

  test('emits a REVIEW_NEEDED entry with reason ALREADY_ANCHORED', () => {
    const { reviewNeeded } = runTransform(source, plan);
    const entry = reviewNeeded.find((e) => e.reasonCode === REASON_CODES.ALREADY_ANCHORED);
    expect(entry).toBeDefined();
    expect(entry.anchorName).toBe('nav-menu');
  });

  test('reports no change (idempotent)', () => {
    const { changed } = runTransform(source, plan);
    expect(changed).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Test 7 — idempotency — re-running on already-processed file → no changes
// ---------------------------------------------------------------------------
describe('idempotency — re-running on a file already processed', () => {
  const alreadyProcessed = [
    "import React from 'react';",
    'export function Sidebar({ children }) {',
    '  return (',
    '    <nav data-tour="sidebar" className="sidebar">',
    '      {children}',
    '    </nav>',
    '  );',
    '}',
  ].join('\n');

  const plan = {
    'test-fixture.jsx': { anchorName: 'sidebar', targetHint: 'Sidebar nav root' },
  };

  test('produces no additional data-tour attributes', () => {
    const { code } = runTransform(alreadyProcessed, plan);
    const matches = (code.match(/data-tour=/g) || []).length;
    expect(matches).toBe(1);
  });

  test('reports no change (transform returns null)', () => {
    const { changed } = runTransform(alreadyProcessed, plan);
    expect(changed).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Test 8 — React.lazy dynamic component → REVIEW_NEEDED DYNAMIC_COMPONENT
// ---------------------------------------------------------------------------
describe('React.lazy dynamic component (Gate C failure — dynamic)', () => {
  const source = [
    "import React, { lazy, Suspense } from 'react';",
    "const Panel = lazy(() => import('./Panel'));",
    'export function App() {',
    '  return (',
    '    <Suspense fallback={<div>Loading...</div>}>',
    '      <Panel />',
    '    </Suspense>',
    '  );',
    '}',
  ].join('\n');

  const plan = {
    'test-fixture.jsx': { anchorName: 'panel', targetHint: 'Lazy Panel component' },
  };

  test('does NOT inject data-tour', () => {
    const { code } = runTransform(source, plan);
    expect(code).not.toContain('data-tour=');
  });

  test('emits REVIEW_NEEDED with reason DYNAMIC_COMPONENT', () => {
    const { reviewNeeded } = runTransform(source, plan);
    const entry = reviewNeeded.find((e) => e.reasonCode === REASON_CODES.DYNAMIC_COMPONENT);
    expect(entry).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Test 9 — render-prop / children-as-function → REVIEW_NEEDED RENDER_PROP
// ---------------------------------------------------------------------------
describe('render-prop / children-as-function (Gate C failure)', () => {
  const source = [
    "import React from 'react';",
    "import { DataProvider } from './DataProvider';",
    'export function Feed() {',
    '  return (',
    '    <DataProvider>',
    '      {({ data }) => (',
    '        <section className="feed">',
    '          {data.map((item) => <div key={item.id}>{item.title}</div>)}',
    '        </section>',
    '      )}',
    '    </DataProvider>',
    '  );',
    '}',
  ].join('\n');

  const plan = {
    'test-fixture.jsx': { anchorName: 'feed', targetHint: 'Feed section' },
  };

  test('does NOT inject data-tour', () => {
    const { code } = runTransform(source, plan);
    expect(code).not.toContain('data-tour=');
  });

  test('emits REVIEW_NEEDED with reason RENDER_PROP', () => {
    const { reviewNeeded } = runTransform(source, plan);
    const entry = reviewNeeded.find((e) => e.reasonCode === REASON_CODES.RENDER_PROP);
    expect(entry).toBeDefined();
    expect(entry.anchorName).toBe('feed');
  });
});
