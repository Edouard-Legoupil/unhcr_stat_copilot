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
      {/* Animated UNHCR */}
      <div>
        <svg
          width="180"
          height="180"
          viewBox="250 125 35 40"
          aria-label="Loading"
        >
          <g transform="translate(0 290) scale(1 -1)">

            {/* Left hand */}
            <g transform-origin="262px 144px">
              <animateTransform
                attributeName="transform"
                type="scale"
                values="1;0.88;1"
                dur="1.8s"
                repeatCount="indefinite"
              />
              <path
                d="m 259.36163,150.26327 c -0.985,-1.049 -2.573,-3.559 -1.557,-5.656 2.129,-0.794 1.97,6.705 4.608,6.578 1.271,-1.208 -0.413,-4.735 -0.922,-6.292 -0.667,-1.938 -1.175,-5.941 -2.415,-7.911 -1.016,-1.621 -0.254,-6.705 -0.571,-8.484 -0.89,-0.858 -3.241,-0.254 -4.258,-0.095 0,2.033 -0.254,3.622 -0.572,6.831 -0.064,0.636 -0.731,10.581 -0.191,11.788 1.144,2.51 7.34,7.276 8.198,8.198 0.762,0.794 3.368,3.495 4.385,3.495 0.73,-0.477 0.286,-1.621 0.127,-2.065 -1.017,-2.51 -5.37,-4.989 -6.832,-6.387 z"
                fill="#005FAF"
              />
            </g>

            {/* Right hand */}
            <g transform-origin="272px 144px">
              <animateTransform
                attributeName="transform"
                type="scale"
                values="1;0.88;1"
                dur="1.8s"
                repeatCount="indefinite"
              />
              <path
                d="m 274.51863,150.26327 c 0.984,-1.049 2.573,-3.559 1.556,-5.656 -2.128,-0.794 -1.97,6.705 -4.607,6.578 -1.271,-1.208 0.413,-4.735 0.922,-6.292 0.667,-1.938 1.175,-5.941 2.415,-7.911 1.016,-1.621 0.254,-6.705 0.571,-8.484 0.89,-0.858 3.241,-0.254 4.258,-0.095 0,2.033 0.254,3.622 0.572,6.831 0.064,0.636 0.731,10.581 0.191,11.788 -1.144,2.51 -7.34,7.276 -8.198,8.198 -0.763,0.794 -3.368,3.495 -4.385,3.495 -0.731,-0.477 -0.286,-1.621 -0.127,-2.065 1.017,-2.51 5.37,-4.989 6.832,-6.387 z"
                fill="#005FAF"
              />
            </g>

            {/* Person */}
            <g transform-origin="267px 141px">
              <animateTransform
                attributeName="transform"
                type="scale"
                values="1;1.25;1"
                dur="1.8s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="0.7;1;0.7"
                dur="1.8s"
                repeatCount="indefinite"
              />
              <path
                d="m 264.67363,132.37627 c -1.493,0 -1.415,0.59 -1.415,1.162 v 10.101 c 0,2.764 1.926,2.27 2.496,3.288 0.442,0.789 -0.325,1.47 -0.728,2.317 -0.294,0.618 -0.303,1.344 -0.001,2.004 0.3,0.659 1.144,1.118 1.914,1.118 0.771,0 1.615,-0.459 1.915,-1.118 0.301,-0.66 0.293,-1.386 -0.001,-2.004 -0.403,-0.847 -1.17,-1.528 -0.728,-2.317 0.57,-1.018 2.496,-0.524 2.496,-3.288 v -10.101 c 0,-0.572 0.078,-1.162 -1.416,-1.162 -0.179,0.013 -0.347,-0.169 -0.347,-0.482 v -3.807 h -3.837 v 3.819 c 0,0 0.038,0.47 -0.348,0.47 z"
                fill="#005FAF"
              />
            </g>

          </g>
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
