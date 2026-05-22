import React from 'react';

// Fixture: fragment root — no single element to annotate.
// EXPECTED: NO injection; REVIEW_NEEDED reason=FRAGMENT_ROOT.
export function Layout({ children }) {
  return (
    <>
      <header className="app-header">Header</header>
      <main className="app-main">{children}</main>
      <footer className="app-footer">Footer</footer>
    </>
  );
}
