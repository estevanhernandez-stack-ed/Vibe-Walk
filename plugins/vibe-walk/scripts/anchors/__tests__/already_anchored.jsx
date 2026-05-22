import React from 'react';

// Fixture: element already has data-tour attribute — idempotency guard.
// EXPECTED: NO second injection; REVIEW_NEEDED reason=ALREADY_ANCHORED.
export function NavMenu({ items }) {
  return (
    <nav data-tour="nav-menu" className="nav-menu">
      {items.map((item) => (
        <a key={item.id} href={item.href}>{item.label}</a>
      ))}
    </nav>
  );
}
