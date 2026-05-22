'use strict';
/**
 * inject_anchors.js — jscodeshift transform for Vibe-Walk M4
 *
 * Auto-injects `data-tour="<anchor-name>"` on JSX elements that pass all four
 * D6 gates.  Routes everything else to a REVIEW_NEEDED entry with a reason code.
 *
 * Usage (CLI):
 *   jscodeshift -t inject_anchors.js --parser tsx --plan='{"path/to/file.jsx":{"anchorName":"my-anchor"}}' src/
 *
 * Usage (programmatic / tests):
 *   const transform = require('./inject_anchors.js');
 *   transform._lastReviewEntries = [];
 *   const result = applyTransform(transform, { plan }, fileInfo, { parser: 'tsx' });
 *   const skips = transform._lastReviewEntries;
 *
 * The four D6 AUTO-INJECT gates:
 *   (A) The root return is an intrinsic HTML element OR a directly-imported named component.
 *   (B) The function has a single unambiguous root return (no multiple top-level returns).
 *   (C) No HOC wrapping / dynamic import / render-prop at the injection site.
 *   (D) The element does not already have a `data-tour` attribute (idempotency).
 *
 * NEVER modifies logic — additive attribute only.
 * Idempotent — re-running on an already-processed file produces no further changes.
 */

// ---------------------------------------------------------------------------
// Reason codes (exported so consumers and tests can reference them symbolically)
// ---------------------------------------------------------------------------
const REASON_CODES = {
  HOC_WRAPPED: 'HOC_WRAPPED',
  FRAGMENT_ROOT: 'FRAGMENT_ROOT',
  CONDITIONAL_ROOT: 'CONDITIONAL_ROOT',
  MULTIPLE_ROOTS: 'MULTIPLE_ROOTS',
  DYNAMIC_COMPONENT: 'DYNAMIC_COMPONENT',
  RENDER_PROP: 'RENDER_PROP',
  THIRD_PARTY_COMPONENT: 'THIRD_PARTY_COMPONENT',
  ALREADY_ANCHORED: 'ALREADY_ANCHORED',
  SHADOW_DOM: 'SHADOW_DOM',
  CSS_MODULE_ONLY_ID: 'CSS_MODULE_ONLY_ID',
  SPREAD_PROPS_UNTYPED: 'SPREAD_PROPS_UNTYPED',
  UNKNOWN: 'UNKNOWN',
};

// ---------------------------------------------------------------------------
// Well-known intrinsic HTML element names (lower-case = intrinsic in JSX)
// ---------------------------------------------------------------------------
const INTRINSIC_HTML_ELEMENTS = new Set([
  'a', 'abbr', 'address', 'area', 'article', 'aside', 'audio',
  'b', 'bdi', 'bdo', 'blockquote', 'br', 'button',
  'canvas', 'caption', 'cite', 'code', 'col', 'colgroup',
  'data', 'datalist', 'dd', 'del', 'details', 'dfn', 'dialog', 'div', 'dl', 'dt',
  'em', 'embed',
  'fieldset', 'figcaption', 'figure', 'footer', 'form',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hr',
  'i', 'iframe', 'img', 'input', 'ins',
  'kbd',
  'label', 'legend', 'li', 'link',
  'main', 'map', 'mark', 'menu', 'meta', 'meter',
  'nav', 'noscript',
  'object', 'ol', 'optgroup', 'option', 'output',
  'p', 'picture', 'pre', 'progress',
  'q',
  's', 'samp', 'script', 'search', 'section', 'select', 'small', 'source', 'span',
  'strong', 'style', 'sub', 'summary', 'sup',
  'table', 'tbody', 'td', 'template', 'textarea', 'tfoot', 'th', 'thead', 'time',
  'title', 'tr', 'track',
  'u', 'ul',
  'var', 'video',
  'wbr',
]);

// ---------------------------------------------------------------------------
// Transform entry point (jscodeshift API)
// ---------------------------------------------------------------------------

/**
 * @param {import('jscodeshift').FileInfo} fileInfo
 * @param {import('jscodeshift').API} api
 * @param {{ plan: Record<string, { anchorName: string, targetHint?: string }> }} options
 * @returns {string | null}  null = no changes
 */
function transform(fileInfo, api, options) {
  const j = api.jscodeshift;
  const filePath = fileInfo.path;
  const plan = options && options.plan ? options.plan : {};

  // Look up by exact path and also by basename (tests use 'test-fixture.jsx').
  const planEntry = plan[filePath] || plan[require('path').basename(filePath)];
  if (!planEntry || !planEntry.anchorName) {
    // File not in plan — nothing to do.
    return null;
  }

  const { anchorName } = planEntry;
  const reviewEntries = [];

  const root = j(fileInfo.source);
  let modified = false;

  // ---------------------------------------------------------------------------
  // 1. HOC detection — look for HOC-wrapped default exports.
  //    Pattern: `export default <CallExpression>(<ComponentIdentifier>)`
  //    If the file has such a pattern, the component is HOC-wrapped.
  // ---------------------------------------------------------------------------
  const hocExportDefault = root.find(j.ExportDefaultDeclaration, {
    declaration: { type: 'CallExpression' },
  });

  if (hocExportDefault.length > 0) {
    recordReview(reviewEntries, filePath, anchorName, REASON_CODES.HOC_WRAPPED, planEntry);
    commitReview(reviewEntries);
    return null;
  }

  // ---------------------------------------------------------------------------
  // 2. Dynamic component detection — React.lazy / variable-assigned components.
  //    If the file top-level contains `lazy(...)` call or `import(...)` dynamic
  //    import at variable declaration level, flag it.
  // ---------------------------------------------------------------------------
  const lazyCallsAtTopLevel = root.find(j.VariableDeclaration).filter((path) => {
    return path.value.declarations.some((decl) => {
      if (!decl.init) return false;
      // const X = lazy(() => import('...'))
      if (
        decl.init.type === 'CallExpression' &&
        decl.init.callee.type === 'Identifier' &&
        decl.init.callee.name === 'lazy'
      ) {
        return true;
      }
      // const X = React.lazy(...)
      if (
        decl.init.type === 'CallExpression' &&
        decl.init.callee.type === 'MemberExpression' &&
        decl.init.callee.property.name === 'lazy'
      ) {
        return true;
      }
      return false;
    });
  });

  if (lazyCallsAtTopLevel.length > 0) {
    recordReview(reviewEntries, filePath, anchorName, REASON_CODES.DYNAMIC_COMPONENT, planEntry);
    commitReview(reviewEntries);
    return null;
  }

  // ---------------------------------------------------------------------------
  // 3. Build the set of directly-imported named component identifiers.
  //    We look at all import statements: anything imported with a capital-letter
  //    name qualifies as a directly-imported named component (Gate A, custom).
  // ---------------------------------------------------------------------------
  const directlyImportedComponents = new Set();

  root.find(j.ImportDeclaration).forEach((path) => {
    path.value.specifiers.forEach((spec) => {
      if (
        spec.type === 'ImportDefaultSpecifier' ||
        spec.type === 'ImportSpecifier' ||
        spec.type === 'ImportNamespaceSpecifier'
      ) {
        const localName = spec.local && spec.local.name;
        if (localName && /^[A-Z]/.test(localName)) {
          directlyImportedComponents.add(localName);
        }
      }
    });
  });

  // ---------------------------------------------------------------------------
  // 4. Find all function/arrow-function components in the file and analyse each.
  // ---------------------------------------------------------------------------

  // Collect all top-level function declarations and variable declarations
  // that resolve to arrow functions or function expressions.
  const functionDeclarations = root.find(j.FunctionDeclaration);
  const arrowFunctions = root.find(j.VariableDeclarator).filter((path) => {
    return (
      path.value.init &&
      (path.value.init.type === 'ArrowFunctionExpression' ||
        path.value.init.type === 'FunctionExpression')
    );
  });

  // Process each candidate component body.
  let processed = false;

  const processBody = (fnNode) => {
    const body = fnNode.body;
    if (!body) return;

    // Collect all return statements in this function's body (not nested).
    const returnStatements = collectDirectReturns(body, j);

    if (returnStatements.length === 0) {
      // No return statement — not a component.
      return;
    }

    if (returnStatements.length > 1) {
      // Multiple return statements → Gate B failure (CONDITIONAL_ROOT).
      recordReview(
        reviewEntries,
        filePath,
        anchorName,
        REASON_CODES.CONDITIONAL_ROOT,
        planEntry,
      );
      processed = true;
      return;
    }

    // Single return statement — examine the returned value.
    const returned = returnStatements[0].value.argument;

    if (!returned) {
      // Returns null/undefined — not a JSX component.
      return;
    }

    // ---------------------------------------------------------------------------
    // Gate B — single root check
    // Fragment root (`<>...</>` or `<React.Fragment>`) → FRAGMENT_ROOT
    // ---------------------------------------------------------------------------
    if (
      returned.type === 'JSXFragment' ||
      (returned.type === 'JSXElement' &&
        returned.openingElement &&
        returned.openingElement.name &&
        ((returned.openingElement.name.type === 'JSXMemberExpression' &&
          returned.openingElement.name.object.name === 'React' &&
          returned.openingElement.name.property.name === 'Fragment') ||
          (returned.openingElement.name.type === 'JSXIdentifier' &&
            returned.openingElement.name.name === 'Fragment')))
    ) {
      recordReview(reviewEntries, filePath, anchorName, REASON_CODES.FRAGMENT_ROOT, planEntry);
      processed = true;
      return;
    }

    // Unwrap parenthesized expressions.
    const rootJSX = unwrapParens(returned);

    if (!rootJSX || rootJSX.type !== 'JSXElement') {
      // Not a JSX element root (e.g., conditional expression at root level).
      recordReview(
        reviewEntries,
        filePath,
        anchorName,
        REASON_CODES.CONDITIONAL_ROOT,
        planEntry,
      );
      processed = true;
      return;
    }

    const openingEl = rootJSX.openingElement;
    const elementName = getJSXElementName(openingEl);

    // ---------------------------------------------------------------------------
    // Gate C — render-prop detection.
    // If the root element's children contain an arrow function / function expression
    // as a direct child (children-as-function pattern), flag RENDER_PROP.
    // ---------------------------------------------------------------------------
    if (hasRenderPropChildren(rootJSX, j)) {
      recordReview(reviewEntries, filePath, anchorName, REASON_CODES.RENDER_PROP, planEntry);
      processed = true;
      return;
    }

    // ---------------------------------------------------------------------------
    // Gate A — element must be intrinsic HTML or directly-imported named component.
    // Third-party components not in our import set → THIRD_PARTY_COMPONENT.
    // (Note: a component defined in the same file would NOT be in directlyImportedComponents,
    //  but would be a locally-defined component — treat as safe if it's PascalCase and
    //  locally declared. For safety we only allow intrinsic + directly imported.)
    // ---------------------------------------------------------------------------
    const isIntrinsic = INTRINSIC_HTML_ELEMENTS.has(elementName);
    const isDirectlyImported = directlyImportedComponents.has(elementName);

    if (!isIntrinsic && !isDirectlyImported) {
      // Could be a locally-defined sub-component — still ambiguous without typing.
      // Route to THIRD_PARTY_COMPONENT (the catch-all for non-intrinsic, non-imported).
      recordReview(
        reviewEntries,
        filePath,
        anchorName,
        REASON_CODES.THIRD_PARTY_COMPONENT,
        planEntry,
      );
      processed = true;
      return;
    }

    // ---------------------------------------------------------------------------
    // Gate D — idempotency: check if data-tour is already present.
    // ---------------------------------------------------------------------------
    const existingDataTour = openingEl.attributes.find(
      (attr) =>
        attr.type === 'JSXAttribute' &&
        attr.name &&
        attr.name.type === 'JSXIdentifier' &&
        attr.name.name === 'data-tour',
    );

    if (existingDataTour) {
      recordReview(reviewEntries, filePath, anchorName, REASON_CODES.ALREADY_ANCHORED, planEntry);
      processed = true;
      return;
    }

    // ---------------------------------------------------------------------------
    // All four gates pass → AUTO-INJECT
    // ---------------------------------------------------------------------------
    const newAttr = j.jsxAttribute(
      j.jsxIdentifier('data-tour'),
      j.literal(anchorName),
    );

    // Insert as the first attribute for visibility.
    openingEl.attributes.unshift(newAttr);
    modified = true;
    processed = true;
  };

  // Process named function declarations.
  functionDeclarations.forEach((path) => {
    if (!processed) {
      processBody(path.value);
    }
  });

  // Process arrow/function-expression variable declarators.
  if (!processed) {
    arrowFunctions.forEach((path) => {
      if (!processed) {
        const fn = path.value.init;
        processBody(fn);
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Commit review entries to the side-channel for test inspection.
  // ---------------------------------------------------------------------------
  commitReview(reviewEntries);

  if (!modified) {
    return null;
  }

  return root.toSource({ quote: 'double' });
}

// ---------------------------------------------------------------------------
// Side-channel for test access to review entries
// ---------------------------------------------------------------------------
transform._lastReviewEntries = [];

function commitReview(entries) {
  transform._lastReviewEntries = entries.slice();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Collect all `return` statements that are direct children of the given
 * function body (not nested inside inner functions).
 */
function collectDirectReturns(body, j) {
  const returns = [];

  function visit(node) {
    if (!node || typeof node !== 'object') return;

    if (node.type === 'ReturnStatement') {
      returns.push({ value: node });
      return; // Don't recurse into the returned expression.
    }

    // Don't recurse into nested functions.
    if (
      node.type === 'FunctionDeclaration' ||
      node.type === 'FunctionExpression' ||
      node.type === 'ArrowFunctionExpression'
    ) {
      return;
    }

    // Recurse into block statements and common control-flow nodes.
    if (node.type === 'BlockStatement') {
      node.body.forEach(visit);
      return;
    }
    if (node.type === 'IfStatement') {
      visit(node.consequent);
      if (node.alternate) visit(node.alternate);
      return;
    }
    if (node.type === 'SwitchStatement') {
      node.cases.forEach((c) => c.consequent.forEach(visit));
      return;
    }
    if (node.type === 'TryStatement') {
      visit(node.block);
      if (node.handler) visit(node.handler.body);
      if (node.finalizer) visit(node.finalizer);
      return;
    }
  }

  if (body.type === 'BlockStatement') {
    body.body.forEach(visit);
  } else {
    // Arrow function with expression body — the expression IS the return value.
    returns.push({ value: { argument: body } });
  }

  return returns;
}

/**
 * Unwrap JSXExpressionContainer or ParenthesizedExpression around a JSX node.
 */
function unwrapParens(node) {
  if (!node) return node;
  if (node.type === 'JSXExpressionContainer') return unwrapParens(node.expression);
  // jscodeshift/recast sometimes wraps in extra nodes; peel them away.
  return node;
}

/**
 * Get the string name of a JSX element's opening tag.
 * Handles both simple identifiers (<div>) and member expressions (<Foo.Bar>).
 */
function getJSXElementName(openingElement) {
  const name = openingElement.name;
  if (!name) return '';
  if (name.type === 'JSXIdentifier') return name.name;
  if (name.type === 'JSXMemberExpression') {
    return `${name.object.name}.${name.property.name}`;
  }
  return '';
}

/**
 * Detect render-prop / children-as-function pattern.
 * Returns true if any direct child of the JSXElement is an ArrowFunctionExpression
 * or FunctionExpression wrapped in a JSXExpressionContainer.
 */
function hasRenderPropChildren(jsxElement, j) {
  if (!jsxElement.children) return false;
  return jsxElement.children.some((child) => {
    if (child.type !== 'JSXExpressionContainer') return false;
    const expr = child.expression;
    return (
      expr.type === 'ArrowFunctionExpression' || expr.type === 'FunctionExpression'
    );
  });
}

/**
 * Push a review entry to the accumulator.
 */
function recordReview(entries, file, anchorName, reasonCode, planEntry) {
  entries.push({
    file,
    anchorName,
    reasonCode,
    targetHint: (planEntry && planEntry.targetHint) || '',
  });
}

// ---------------------------------------------------------------------------
// buildPlan helper — builds the plan object from an array of mappings.
// Exported for consumers that want to construct a plan programmatically.
// ---------------------------------------------------------------------------
function buildPlan(mappings) {
  const plan = {};
  mappings.forEach(({ filePath, anchorName, targetHint }) => {
    plan[filePath] = { anchorName, targetHint: targetHint || '' };
  });
  return plan;
}

// ---------------------------------------------------------------------------
// REVIEW_NEEDED.md emitter — used by the CLI runner (not by tests).
// Generates the markdown report from accumulated review entries.
// ---------------------------------------------------------------------------
function emitReviewNeededMd(entries, outputPath) {
  if (entries.length === 0) return;

  const fs = require('fs');
  const path = require('path');

  const lines = [
    '# REVIEW_NEEDED — Anchor-Injection Manual Review Required',
    '',
    '> Generated by `inject_anchors.js` (Vibe-Walk M4).',
    '> Phase 2 does not proceed until every item below is resolved.',
    '> For each item: manually add `data-tour="<anchor-name>"` to the correct element,',
    '> or document why the stop should be removed from the tour plan.',
    '',
    '## Why items end up here',
    '',
    '`inject_anchors.js` auto-injects only when all four D6 gates pass:',
    '(A) intrinsic HTML element or directly-imported named component',
    '(B) single unambiguous root return',
    '(C) no HOC wrapping / dynamic import / render-prop',
    '(D) `data-tour` attribute absent (idempotency guard)',
    '',
    '---',
    '',
    '## Items requiring human resolution',
    '',
    '| # | File | Anchor name | Reason code | Target hint |',
    '|---|------|-------------|-------------|-------------|',
  ];

  entries.forEach((entry, i) => {
    lines.push(
      `| ${i + 1} | \`${entry.file}\` | \`${entry.anchorName}\` | \`${entry.reasonCode}\` | ${entry.targetHint || ''} |`,
    );
  });

  lines.push('');
  lines.push('---');
  lines.push('');
  lines.push('## Reason code reference');
  lines.push('');
  lines.push('| Code | Meaning | Suggested resolution |');
  lines.push('|------|---------|----------------------|');
  lines.push('| `HOC_WRAPPED` | Export is wrapped in a HOC — `data-tour` forwarding cannot be verified statically | Check if the HOC spreads props; if yes, add `data-tour` at the usage site manually |');
  lines.push('| `FRAGMENT_ROOT` | Component returns a React fragment — no single root element to annotate | Choose which child element should carry `data-tour` |');
  lines.push('| `CONDITIONAL_ROOT` | Multiple return statements with different root elements | Annotate each return path individually or restructure to a single root |');
  lines.push('| `MULTIPLE_ROOTS` | Multiple JSX root returns detected | Same as CONDITIONAL_ROOT |');
  lines.push('| `DYNAMIC_COMPONENT` | Component identity resolved at runtime (`React.lazy`, variable-assigned) | Trace to the actual rendered component and annotate there |');
  lines.push('| `RENDER_PROP` | Children-as-function or render-prop pattern | Annotate the element inside the callback directly |');
  lines.push('| `THIRD_PARTY_COMPONENT` | Root is a third-party component — `data-tour` at usage site may not reach the DOM | Wrap in a `<span data-tour="x">` or annotate inside the component\'s own source |');
  lines.push('| `ALREADY_ANCHORED` | `data-tour` attribute already present — idempotency skip | Confirm the existing anchor name is correct; no action needed if it matches |');
  lines.push('| `SHADOW_DOM` | Element is inside a shadow DOM boundary | No substrate fixes this; remove or scope the tour stop |');
  lines.push('| `CSS_MODULE_ONLY_ID` | Stop was identified only by a CSS Module class name | Add a stable `data-tour` or `id` attribute manually |');

  const out = outputPath || path.join(process.cwd(), 'REVIEW_NEEDED.md');
  fs.writeFileSync(out, lines.join('\n') + '\n', 'utf8');
  process.stderr.write(`[vibe-walk] REVIEW_NEEDED.md written: ${out} (${entries.length} item${entries.length === 1 ? '' : 's'})\n`);
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------
transform.REASON_CODES = REASON_CODES;
transform.buildPlan = buildPlan;
transform.emitReviewNeededMd = emitReviewNeededMd;
// Named export for convenience.
module.exports = transform;
module.exports.REASON_CODES = REASON_CODES;
module.exports.buildPlan = buildPlan;
module.exports.emitReviewNeededMd = emitReviewNeededMd;
