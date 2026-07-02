import { useEffect, useState } from "react";

const messages = [
  "OK - let me work on this - should not take too long...",
  "Reading carefully to understand your request...",
  "Parsing UNHCR statistical streams...",
  "Retrieving data from multiple tables...",
  "Applying the correct filters...",
  "Cross-validating  datasets and looking for patterns...",
  "Applying statistical guardrails...",
  "Producing charts and  data tables...",
  "Synthesizing insights and tailoring to the audience...",
  "Generating the report..."
];

export default function LoadingSpinner() {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % messages.length);
    }, 2200); // rotate every ~2.2s

    return () => clearInterval(interval);
  }, []);

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "rgba(255, 255, 255, 0.9)",
        zIndex: 9999,
        fontFamily: "system-ui, sans-serif",
        color: "#1f2937"
      }}
    >
      {/* Animated AI Orb */}
      <div>
        <svg width="180" height="180" viewBox="0 0 100 100">
          <defs>
            <radialGradient id="grad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#60a5fa" />
              <stop offset="100%" stopColor="#1d4ed8" />
            </radialGradient>
          </defs>
          <circle
            cx="50"
            cy="50"
            r="20"
            fill="url(#grad)"
          >
            <animate
              attributeName="r"
              values="18;24;18"
              dur="2s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              values="0.7;1;0.7"
              dur="2s"
              repeatCount="indefinite"
            />
          </circle>
        </svg>
      </div>



      {/* Main text */}
      <div style={{ fontSize: 18, fontWeight: 500 }}>
        Working on it...
      </div>

      {/* Rotating sub-message */}
      <div
        style={{
          marginTop: 10,
          fontSize: 14,
          color: "#4b5563",
          minHeight: 20,
          transition: "opacity 0.5s ease"
        }}
      >
        {messages[messageIndex]}
      </div>
    </div>
  );
}
