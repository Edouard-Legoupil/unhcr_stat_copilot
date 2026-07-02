import { useState } from "react";

export default function DebugPanel({ response }) {
    const [showDebug, setShowDebug] = useState(false);

    if (!response) {
        return null;
    }

    const toggleDebug = () => {
        setShowDebug(!showDebug);
    };

    return (
        <div className="card debug-panel">
            <div className="debug-header">
                <h3 className="card-title">
                    <b>Observability:</b> Understand how the analysis was generated
                </h3>
                <button
                    className="debug-toggle"
                    onClick={toggleDebug}
                >
                    {showDebug ? "Hide" : "Show"} Details
                </button>
            </div>

            {showDebug && (
                <div className="debug-content">
                    <pre className="code-block debug-json">
                        {JSON.stringify(response, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
}