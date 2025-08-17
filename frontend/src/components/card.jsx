import React, { useState } from "react";
import { ToggleSwitch } from "./toggle-switch";

export function ToolCard({ name, description }) {
  const [enabled, setEnabled] = useState(true);

  return (
    <div
      className="card shadow-sm rounded-3"
      style={{
        minHeight: "12rem",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div className="card-body d-flex flex-column">
        <h5
          className="card-title fw-bold text-truncate"
          title={name}
          style={{ maxWidth: "100%" }}
        >
          {name}
        </h5>
        <p
          className="card-text text-muted"
          style={{
            overflow: "hidden",
            display: "-webkit-box",
            WebkitLineClamp: 3,
            WebkitBoxOrient: "vertical",
            minHeight: "4.5rem",
          }}
          title={description}
        >
          {description}
        </p>
      </div>
      <div className="d-flex justify-content-end align-items-center p-2">
        <ToggleSwitch
          id={`enable-toggle-${name}`}
          checked={enabled}
          onChange={setEnabled}
          label="Enable"
        />
      </div>
    </div>
  );
}
