import { useState, useEffect, useRef } from "react";

/**
 * IntegratedAnalysisViewer - Combined Quarto viewer with collapsible debug panel
 * Features a subtle triangle toggle to fold/unfold debug content within the same box
 */
export default function IntegratedAnalysisViewer({ quartoContent, metadata, response }) {
    const [showRaw, setShowRaw] = useState(false);
    const [showDebug, setShowDebug] = useState(false);
    const [showTools, setShowTools] = useState(false);
    const [renderedHtml, setRenderedHtml] = useState('');
    const htmlRef = useRef(null);

    if (!quartoContent) {
        return (
            <div className="card integrated-viewer">
                <h2 className="card-title">Analysis Ready</h2>
                <p>No Quarto content available.</p>
            </div>
        );
    }

    // Extract and render HTML content from Quarto markdown
    useEffect(() => {
        try {
            // Simple markdown to HTML conversion for basic rendering
            const htmlContent = quartoContent
                .replace(/^#\s+(.*)$/gm, '<h2>$1</h2>')
                .replace(/^##\s+(.*)$/gm, '<h3>$1</h3>')
                .replace(/^###\s+(.*)$/gm, '<h4>$1</h4>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n\n/g, '</p><p>')
                .replace(/\n/g, '<br>');

            setRenderedHtml(`<div class="quarto-rendered">${htmlContent}</div>`);
        } catch (error) {
            console.error("Error rendering Quarto content:", error);
            setRenderedHtml('<p>Error rendering content. Showing raw format.</p>');
        }
    }, [quartoContent]);

    // Extract tools used from metadata
    const toolsUsed = metadata?.tools_used || metadata?.mcp_tools || [];
    const hasTools = Array.isArray(toolsUsed) && toolsUsed.length > 0;

    // Extract tool sequence from metadata
    const toolSequence = metadata?.tool_sequence || [];
    const successfulTools = toolSequence.filter(tool => tool.success);
    const failedTools = toolSequence.filter(tool => !tool.success);

    // Extract analysis configuration
    const analysisConfig = metadata?.analysis_config || {};
    const audience = metadata?.audience || "unknown";
    const documentType = metadata?.document_type || "unknown";

    // Format tool duration for display
    const formatDuration = (ms) => {
        if (ms < 1000) return `${ms.toFixed(0)}ms`;
        return `${(ms / 1000).toFixed(2)}s`;
    };

    // Format timestamp for display
    const formatTimestamp = (isoString) => {
        try {
            return new Date(isoString).toLocaleString();
        } catch (e) {
            return isoString;
        }
    };

    return (
        <div className="card integrated-viewer">
            {/* Main Content Header */}
            <div className="viewer-header">
                <h2 className="card-title">Analysis Content</h2>
                <div className="viewer-actions">
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
                        <pre className="viewer-raw">{quartoContent}</pre>
                        <button
                            className="copy-button"
                            onClick={() => {
                                navigator.clipboard.writeText(quartoContent);
                                alert('Quarto source copied to clipboard!');
                            }}
                        >
                            📋 Copy Source
                        </button>
                    </div>
                ) : (
                    <div
                        className="viewer-rendered"
                        ref={htmlRef}
                        dangerouslySetInnerHTML={{ __html: renderedHtml }}
                    />
                )}
            </div>

            {/* Metadata Section */}
            <div className="viewer-metadata">
                <h4>📋 Analysis Metadata</h4>
                <div className="metadata-grid">
                    <div className="metadata-item">
                        <span className="metadata-label">Audience:</span>
                        <span className="metadata-value">{audience}</span>
                    </div>
                    <div className="metadata-item">
                        <span className="metadata-label">Document Type:</span>
                        <span className="metadata-value">{documentType}</span>
                    </div>
                    <div className="metadata-item">
                        <span className="metadata-label">Generated:</span>
                        <span className="metadata-value">{formatTimestamp(metadata?.generated_at)}</span>
                    </div>
                </div>
            </div>

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