import { useState, useEffect, useRef } from "react";
import CompactAnalysisTable from "./CompactAnalysisTable";
import AnalysisRequestForm from "./AnalysisRequestForm";

export default function HeroSearch({

    message,

    setMessage,

    askQuestion,

    loading,

    previousAnalyses = [],

    loadPreviousAnalysis,

    mode = "previous",

    setMode,

    AboutSectionComponent = null

}) {

    const [selectedAnalysis, setSelectedAnalysis] = useState(null);

    // Ref to access current previousAnalyses without causing re-renders
    const previousAnalysesRef = useRef(previousAnalyses);
    useEffect(() => {
        previousAnalysesRef.current = previousAnalyses;
    }, [previousAnalyses]);

    // Ref to track the last loaded analysis ID to prevent duplicate loads
    const lastLoadedAnalysisId = useRef(null);
    const lastSelectedAnalysisId = useRef(null);

    // When mode changes to "previous", select the most recent analysis
    useEffect(() => {
        if (mode === "previous" && previousAnalysesRef.current.length > 0) {
            const latestAnalysis = previousAnalysesRef.current[0];

            // Only update selected analysis if it's different from the current one
            if (latestAnalysis.id !== lastSelectedAnalysisId.current) {
                lastSelectedAnalysisId.current = latestAnalysis.id;
                setSelectedAnalysis(latestAnalysis);

                // Load the most recent analysis by default, but only if it's different from last time
                if (loadPreviousAnalysis && latestAnalysis.id !== lastLoadedAnalysisId.current) {
                    lastLoadedAnalysisId.current = latestAnalysis.id;
                    loadPreviousAnalysis(latestAnalysis.id);
                }
            }
        }
    }, [mode, loadPreviousAnalysis]); // Only depend on mode and loadPreviousAnalysis to prevent infinite loops

    const handleAnalysisSelect = (analysis) => {
        setSelectedAnalysis(analysis);
        if (loadPreviousAnalysis) {
            loadPreviousAnalysis(analysis.id);
        }
    };

    return (

        <div className="hero-search-card">

            <div className="tab-header">
                <button
                    className={`tab-button ${mode === "previous" ? "active" : ""}`}
                    onClick={() => setMode("previous")}
                    disabled={loading}
                >
                    Available Insights
                </button>
                <button
                    className={`tab-button ${mode === "new" ? "active" : ""}`}
                    onClick={() => setMode("new")}
                    disabled={loading}
                >
                    Generate New Analysis
                </button>
                <button
                    className={`tab-button ${mode === "about" ? "active" : ""}`}
                    onClick={() => setMode("about")}
                    disabled={loading}
                >
                    About
                </button>
            </div>

            <div className="tab-content">
                {mode === "new" ? (
                    <AnalysisRequestForm
                        onSubmit={askQuestion}
                        loading={loading}
                        defaultQuestion={message}
                    />
                ) : mode === "about" ? (
                    AboutSectionComponent && <AboutSectionComponent />
                ) : (
                    previousAnalyses.length === 0 ? (
                        <div className="tab-content-empty">
                            <p>No previous insights found.</p>
                            <button
                                className="secondary-button"
                                onClick={() => setMode("new")}
                                style={{ marginTop: '16px' }}
                            >
                                Create New Analysis
                            </button>
                        </div>
                    ) : (
                        <CompactAnalysisTable
                            analyses={previousAnalyses}
                            onSelectAnalysis={handleAnalysisSelect}
                        />
                    )
                )}
            </div>

        </div>

    );
}