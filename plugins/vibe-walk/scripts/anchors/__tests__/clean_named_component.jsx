import React from 'react';
import { Card } from './Card';

// Fixture: clean component — single root is a directly-imported named component.
// EXPECTED: data-tour="dashboard-card" auto-injected on the root <Card>.
export function DashboardCard({ title }) {
  return (
    <Card className="dashboard-card">
      <h2>{title}</h2>
    </Card>
  );
}
