import React from 'react';

// Fixture: multiple conditional returns — ambiguous which element to annotate.
// EXPECTED: NO injection; REVIEW_NEEDED reason=CONDITIONAL_ROOT.
export function Panel({ isLoading, data }) {
  if (isLoading) {
    return <div className="loading-spinner">Loading...</div>;
  }

  if (!data) {
    return <div className="empty-state">No data available</div>;
  }

  return (
    <section className="panel">
      <h2>{data.title}</h2>
    </section>
  );
}
