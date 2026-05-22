import React from "react";

export default function App() {
  return (
    <div id="app-root" data-tour="app-root">
      <header id="toolbar" data-tour="toolbar">
        <button id="pen-tool" data-tour="pen-tool">Pen</button>
        <button id="shape-tool" data-tour="shape-tool">Shape</button>
        <button id="text-tool" data-tour="text-tool">Text</button>
        <button id="share-btn" data-tour="share-btn">Share</button>
        <button id="collaborate-btn" data-tour="collaborate-btn">Invite</button>
      </header>
      <main id="canvas-area" data-tour="canvas-area">
        {/* Empty canvas on first run */}
      </main>
    </div>
  );
}
