import React from "react";

export default function QuickActions() {
  return (
    <section className="bg-white rounded shadow p-4">
      <h2 className="text-lg font-semibold mb-2">Quick Actions</h2>
      <div className="flex gap-2 flex-wrap">
        <button className="bg-indigo-500 text-white px-3 py-1 rounded text-sm">New Task</button>
        <button className="bg-green-500 text-white px-3 py-1 rounded text-sm">New Project</button>
        <button className="bg-yellow-500 text-white px-3 py-1 rounded text-sm">New Note</button>
      </div>
    </section>
  );
}
