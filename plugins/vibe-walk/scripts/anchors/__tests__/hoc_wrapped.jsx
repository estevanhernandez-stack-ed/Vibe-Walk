import React from 'react';
import { withAuth } from './withAuth';

// Fixture: HOC-wrapped export — forwarding cannot be guaranteed by the codemod.
// EXPECTED: NO injection; REVIEW_NEEDED reason=HOC_WRAPPED.
function Dashboard({ user }) {
  return (
    <div className="dashboard">
      <h1>Welcome, {user.name}</h1>
    </div>
  );
}

export default withAuth(Dashboard);
