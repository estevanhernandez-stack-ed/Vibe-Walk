import React from "react";
import TaskList from "../components/TaskList";
import ProjectPanel from "../components/ProjectPanel";
import CalendarWidget from "../components/CalendarWidget";
import NotesPanel from "../components/NotesPanel";
import ActivityFeed from "../components/ActivityFeed";
import QuickActions from "../components/QuickActions";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <header className="bg-white shadow p-4">
        <h1 className="text-xl font-bold">QuickBoard</h1>
      </header>
      <main className="grid grid-cols-3 gap-4 p-4">
        <TaskList />
        <ProjectPanel />
        <CalendarWidget />
        <NotesPanel />
        <ActivityFeed />
        <QuickActions />
      </main>
    </div>
  );
}
