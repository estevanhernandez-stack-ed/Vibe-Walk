import React from "react";
import NatalChartPanel from "../components/NatalChartPanel";
import TransitCalendar from "../components/TransitCalendar";
import CompatibilityWidget from "../components/CompatibilityWidget";
import SavedChartsSidebar from "../components/SavedChartsSidebar";

export default function Dashboard() {
  return (
    <div id="dashboard-root" data-tour="dashboard-root">
      <header id="top-nav" data-tour="top-nav">
        <h1>AstroBoard</h1>
      </header>
      <main className="dashboard-layout">
        <NatalChartPanel />
        <TransitCalendar />
        <CompatibilityWidget />
        <SavedChartsSidebar />
      </main>
    </div>
  );
}
