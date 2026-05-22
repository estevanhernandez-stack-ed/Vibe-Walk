import React from "react";

export default function TaskList() {
  return (
    <section className="bg-white rounded shadow p-4">
      <h2 className="text-lg font-semibold mb-2">Tasks</h2>
      <ul className="space-y-2">
        <li className="flex items-center gap-2">
          <input type="checkbox" className="rounded" />
          <span className="text-sm">Sample task</span>
        </li>
      </ul>
      <button className="mt-4 bg-blue-500 text-white px-3 py-1 rounded text-sm">
        Add Task
      </button>
    </section>
  );
}
