import { useState, useEffect, useRef } from "react";
import RatingComponent from "./RatingComponent";

/**
 * IntegratedAnalysisViewer - Combined Quarto viewer with collapsible debug panel
 * Features a subtle triangle toggle to fold/unfold debug content within the same box
 */
export default function IntegratedAnalysisViewer({ quartoContent, quartoRawContent, metadata, response, rendered = false, analysisId = null }) {
    const [showRaw, setShowRaw] = useState(false);
    const [showDebug, setShowDebug] = useState(false);
    const [showTools, setShowTools] = useState(false);
    const [rawSource, setRawSource] = useState(null);
    const [loadingRaw, setLoadingRaw] = useState(false);
    const htmlRef = useRef(null);
    
    // Use quartoRawContent if provided, otherwise fall back to quartoContent
    const initialRawContent = quartoRawContent || quartoContent;
    
    // When user toggles to source view, fetch the raw .qmd file
    useEffect(() => {
        if (showRaw && analysisId && !quartoRawContent) {
            // If we don't have raw content and user wants to see source, fetch it
            const fetchRawContent = async () => {
                setLoadingRaw(true);
                try {
                    const result = await fetch(`/quarto/${analysisId}`);
                    if (result.ok) {
                        const rawQmd = await result.text();
                        setRawSource(rawQmd);
                    }
                } catch (error) {
                    console.error('Failed to fetch raw content:', error);
                } finally {
                    setLoadingRaw(false);
                }
            };
            fetchRawContent();
        }
    }, [showRaw, analysisId, quartoRawContent]);
    
    // Determine which raw content to display
    const rawContent = rawSource || quartoRawContent || initialRawContent;

    // Extract tool sequence from metadata
    const toolSequence = metadata?.tool_sequence || [];
    const successfulTools = toolSequence.filter(tool => tool.success);
    const failedTools = toolSequence.filter(tool => !tool.success);

    // Extract analysis configuration
    const analysisConfig = metadata?.analysis_config || {};

    // Format tool duration for display
    const formatDuration = (ms) => {
        if (ms < 1000) return `${ms.toFixed(0)}ms`;
        return `${(ms / 1000).toFixed(2)}s`;
    };

    return (
        <div className="card integrated-viewer">
            {/* Main Content Header */}
            <div className="viewer-header">
                <h2 className="card-title">Analysis Content</h2>
                <div className="viewer-actions">
                    {analysisId && (
                        <button
                            className="pdf-download-button"
                            onClick={() => {
                                window.location.href = `/quarto/${analysisId}/word`;
                            }}
                            title="Download as Word document"
                        >
                            📥 Word
                        </button>
                    )}
                    <button
                        className="viewer-toggle"
                        onClick={() => setShowRaw(!showRaw)}
                        title={showRaw ? 'Show rendered HTML' : 'Show source code'}
                    >
                        {showRaw ? '📄 Rendered' : 'Source Code'}
                    </button>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="viewer-content">
                {showRaw ? (
                    <div className="viewer-source">
                        {loadingRaw ? (
                            <p className="loading-raw">Loading source code...</p>
                        ) : (
                            <>
                                <pre className="viewer-raw">{rawContent}</pre>
                                <div className="source-actions">
                                    <button
                                        className="copy-button"
                                        onClick={() => {
                                            navigator.clipboard.writeText(rawContent);
                                            alert('Quarto source copied to clipboard!');
                                        }}
                                    >
                                        📋 Copy Source
                                    </button>
                                    <button
                                        className="download-button"
                                        onClick={() => {
                                            const blob = new Blob([rawContent], { type: 'text/markdown' });
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement('a');
                                            a.href = url;
                                            a.download = `analysis_${new Date().toISOString().split('T')[0]}.qmd`;
                                            document.body.appendChild(a);
                                            a.click();
                                            document.body.removeChild(a);
                                            URL.revokeObjectURL(url);
                                        }}
                                    >
                                        💾 Download .qmd
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                ) : (
                    <div
                        className="viewer-rendered"
                        ref={htmlRef}
                        dangerouslySetInnerHTML={{ __html: quartoContent }}
                    />
                )}
            </div>

            {/* Rating Component - Allow users to rate the analysis */}
            {analysisId && (
                <div className="viewer-rating">
                    <RatingComponent
                        analysisId={analysisId}
                        onRatingSubmitted={(data) => {
                            console.log('Rating submitted:', data);
                        }}
                    />
                </div>
            )}

            {/* Debug Panel - Integrated within same box with triangle toggle */}
            <div className="debug-integration">
                <button
                    className="debug-triangle-toggle"
                    onClick={() => setShowDebug(!showDebug)}
                    title={showDebug ? 'Collapse debug information' : 'Expand debug information'}
                >
                    <span className="triangle-icon">{showDebug ? '▼' : '▶'}</span>
                    <span className="toggle-text">Observability {showDebug ? 'Details' : 'Summary'}</span>
                </button>

                {showDebug && (
                    <div className="debug-content-integrated">
                        {/* Tool Execution Summary */}
                        <div className="debug-section">
                            <h5>🔧 Tool Execution Summary</h5>
                            <div className="tool-summary-grid">
                                <div className="tool-summary-item">
                                    <span className="tool-summary-label">Total Tools:</span>
                                    <span className="tool-summary-value">{toolSequence.length}</span>
                                </div>
                                <div className="tool-summary-item success">
                                    <span className="tool-summary-label">Successful:</span>
                                    <span className="tool-summary-value">{successfulTools.length}</span>
                                </div>
                                <div className="tool-summary-item failed">
                                    <span className="tool-summary-label">Failed:</span>
                                    <span className="tool-summary-value">{failedTools.length}</span>
                                </div>
                                <div className="tool-summary-item">
                                    <span className="tool-summary-label">Total Duration:</span>
                                    <span className="tool-summary-value">
                                        {formatDuration(toolSequence.reduce((sum, tool) => sum + (tool.duration_ms || 0), 0))}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Analysis Configuration */}
                        <div className="debug-section">
                            <h5>🎯 Audience Configuration</h5>
                            <div className="config-grid">
                                <div className="config-item">
                                    <span className="config-label">Tone:</span>
                                    <span className="config-value">{analysisConfig.tone || 'N/A'}</span>
                                </div>
                                <div className="config-item">
                                    <span className="config-label">Length:</span>
                                    <span className="config-value">{analysisConfig.length?.wordRange || 'N/A'}</span>
                                </div>
                                <div className="config-item">
                                    <span className="config-label">Reading Time:</span>
                                    <span className="config-value">{analysisConfig.length?.readingTime || 'N/A'}</span>
                                </div>
                                <div className="config-item">
                                    <span className="config-label">Structure:</span>
                                    <span className="config-value">
                                        {analysisConfig.structure ? analysisConfig.structure.join(' → ') : 'N/A'}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Raw Response Data - User Friendly */}
                        <div className="debug-section">
                            <h5>📊 Response Data</h5>
                            <div className="response-info">
                                <div className="response-item">
                                    <span className="response-label">Analysis Type:</span>
                                    <span className="response-value">{metadata?.analysis_type || 'N/A'}</span>
                                </div>
                                <div className="response-item">
                                    <span className="response-label">Format:</span>
                                    <span className="response-value">{metadata?.format || 'N/A'}</span>
                                </div>
                                <div className="response-item">
                                    <span className="response-label">Question:</span>
                                    <span className="response-value">{response?.question || 'N/A'}</span>
                                </div>
                            </div>

                            <button
                                className="copy-json-button"
                                onClick={() => {
                                    navigator.clipboard.writeText(JSON.stringify(response, null, 2));
                                    alert('Full response data copied to clipboard!');
                                }}
                            >
                                📋 Copy Full Response JSON
                            </button>

                            {/* User-friendly JSON preview */}
                            <div className="json-preview">
                                <pre className="pretty-json">
                                    {JSON.stringify({
                                        question: response?.question,
                                        audience: response?.audience,
                                        document_type: response?.document_type,
                                        analysis_type: response?.analysis_type,
                                        generated_at: response?.generated_at,
                                        tools_used: response?.tools_used
                                    }, null, 2)}
                                </pre>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}