import React from 'react';

// Fixture: clean component — single root intrinsic HTML element.
// EXPECTED: data-tour="sidebar" auto-injected on the root <nav>.
export function Sidebar({ children }) {
  return (
    <nav className="sidebar">
      {children}
    </nav>
  );
}
