import { useState, useEffect, useRef } from "react";

/**
 * AnalysisViewer - Integrated viewer for Quarto content with debug information
 * Combines QuartoViewer and DebugPanel functionality with a collapsible debug section
 */
export default function AnalysisViewer({ quartoContent, metadata, response, rendered = false }) {
    const [showRaw, setShowRaw] = useState(false);
    const [showDebug, setShowDebug] = useState(false);
    const [showTools, setShowTools] = useState(false);
    const [displayContent, setDisplayContent] = useState('');
    const [isRendered, setIsRendered] = useState(rendered);
    const htmlRef = useRef(null);

    if (!quartoContent) {
        return (
            <div className="card analysis-viewer">
                <h2 className="card-title">Analysis Ready</h2>
                <p>No Quarto content available.</p>
            </div>
        );
    }

    // Handle content display based on whether it's already rendered
    useEffect(() => {
        try {
            // If the content is already pre-rendered HTML from the server
            if (rendered) {
                // Check if it looks like HTML (starts with < or contains <html>)
                const isHtml = quartoContent.trim().startsWith('<') || 
                              quartoContent.includes('<html>') ||
                              quartoContent.includes('<!DOCTYPE');
                
                if (isHtml) {
                    setDisplayContent(quartoContent);
                    setIsRendered(true);
                } else {
                    // Fall back to client-side rendering if it's actually raw markdown
                    const htmlContent = simpleMarkdownToHtml(quartoContent);
                    setDisplayContent(`<div class="quarto-rendered">${htmlContent}</div>`);
                    setIsRendered(false);
                }
            } else {
                // Client-side rendering for raw markdown (fallback)
                const htmlContent = simpleMarkdownToHtml(quartoContent);
                setDisplayContent(`<div class="quarto-rendered">${htmlContent}</div>`);
                setIsRendered(false);
            }
        } catch (error) {
            console.error("Error rendering Quarto content:", error);
            setDisplayContent('<p>Error rendering content. Showing raw format.</p>');
            setIsRendered(false);
        }
    }, [quartoContent, rendered]);

    // Simple markdown to HTML conversion for fallback rendering
    // Only used when server-side rendering is not available
    const simpleMarkdownToHtml = (markdown) => {
        return markdown
            .replace(/^#\s+(.*)$/gm, '<h2>$1</h2>')
            .replace(/^##\s+(.*)$/gm, '<h3>$1</h3>')
            .replace(/^###\s+(.*)$/gm, '<h4>$1</h4>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
    };

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
        <div className="card analysis-viewer">
            <div className="analysis-header">
                <h2 className="card-title">Generated Content</h2>
                <div className="analysis-actions">
                    <button
                        className="analysis-toggle"
                        onClick={() => setShowRaw(!showRaw)}
                        title={showRaw ? 'Show rendered HTML' : 'Show source code'}
                    >
                        {showRaw ? '📄 Rendered' : 'Source Code'}
                    </button>
                    
                    {isRendered && (
                        <span className="quarto-rendered-badge" title="This content is pre-rendered with Quarto CLI">
                            ✅ Pre-rendered
                        </span>
                    )}

                    <button
                        className="debug-toggle"
                        onClick={() => setShowDebug(!showDebug)}
                        title={showDebug ? 'Hide debug information' : 'Show debug information'}
                    >
                        {showDebug ? '🔽 Hide Observability' : '🔼 Show Observability'}
                    </button>
                </div>
            </div>

            <div className="analysis-content">
                {showRaw ? (
                    <div className="analysis-source">
                        <pre className="analysis-raw">{quartoContent}</pre>
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
                        className="analysis-rendered"
                        ref={htmlRef}
                        dangerouslySetInnerHTML={{ __html: displayContent }}
                    />
                )}
            </div>

            {/* Analysis Metadata Section */}
            <div className="analysis-metadata">
                <h4>📋 Analysis Details</h4>
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
                        <span className="metadata-label">Tone:</span>
                        <span className="metadata-value">{analysisConfig.tone || 'N/A'}</span>
                    </div>
                    <div className="metadata-item">
                        <span className="metadata-label">Length:</span>
                        <span className="metadata-value">{analysisConfig.length?.wordRange || 'N/A'}</span>
                    </div>
                    <div className="metadata-item">
                        <span className="metadata-label">Reading Time:</span>
                        <span className="metadata-value">{analysisConfig.length?.readingTime || 'N/A'}</span>
                    </div>
                    <div className="metadata-item">
                        <span className="metadata-label">Generated:</span>
                        <span className="metadata-value">{formatTimestamp(metadata?.generated_at)}</span>
                    </div>
                </div>
            </div>

            {/* Debug Panel - Collapsible */}
            {showDebug && (
                <div className="debug-section">
                    <div className="debug-header">
                        <h4>🔍 Observability & Debug Information</h4>
                        <p className="debug-description">
                            Understand how this analysis was generated and troubleshoot any issues.
                        </p>
                    </div>

                    {/* Tool Execution Summary */}
                    <div className="debug-card">
                        <h5>🔧 Tool Execution Summary</h5>
                        <div className="tool-summary-grid">
                            <div className="tool-summary-item">
                                <span className="tool-summary-label">Total Tools Called:</span>
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

                    {/* Tool Execution Details */}
                    {toolSequence.length > 0 && (
                        <div className="debug-card">
                            <h5>📋 Tool Execution Details</h5>
                            <div className="tool-sequence">
                                {toolSequence.map((tool, index) => (
                                    <div key={index} className={`tool-execution ${tool.success ? 'success' : 'failed'}`}>
                                        <div className="tool-header">
                                            <span className="tool-name">🔧 {tool.tool}</span>
                                            <span className={`tool-status ${tool.success ? 'success' : 'failed'}`}>
                                                {tool.success ? '✅ Success' : '❌ Failed'}
                                            </span>
                                            <span className="tool-duration">
                                                {formatDuration(tool.duration_ms || 0)}
                                            </span>
                                        </div>
                                        {tool.success ? (
                                            <div className="tool-result">
                                                <pre className="tool-summary">{tool.result_summary || 'No details'}</pre>
                                            </div>
                                        ) : (
                                            <div className="tool-error">
                                                <pre className="error-message">{tool.error || 'Unknown error'}</pre>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Analysis Configuration */}
                    <div className="debug-card">
                        <h5>🎯 Target Audience Configuration</h5>
                        <div className="config-section">
                            <div className="config-item">
                                <span className="config-label">Audience:</span>
                                <span className="config-value">{audience}</span>
                            </div>
                            <div className="config-item">
                                <span className="config-label">Document Type:</span>
                                <span className="config-value">{documentType}</span>
                            </div>
                            <div className="config-item">
                                <span className="config-label">Tone & Style:</span>
                                <span className="config-value">{analysisConfig.tone || 'N/A'}</span>
                            </div>
                            <div className="config-item">
                                <span className="config-label">Recommended Length:</span>
                                <span className="config-value">{analysisConfig.length?.wordRange || 'N/A'}</span>
                            </div>
                            <div className="config-item">
                                <span className="config-label">Reading Time:</span>
                                <span className="config-value">{analysisConfig.length?.readingTime || 'N/A'}</span>
                            </div>
                            <div className="config-item">
                                <span className="config-label">Content Density:</span>
                                <span className="config-value">{analysisConfig.length?.density || 'N/A'}</span>
                            </div>
                            <div className="config-item">
                                <span className="config-label">Recommended Structure:</span>
                                <span className="config-value">
                                    {analysisConfig.structure ? analysisConfig.structure.join(' → ') : 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Raw Response Data */}
                    <div className="debug-card">
                        <h5>📊 Raw Response Data</h5>
                        <div className="raw-data-controls">
                            <button
                                className="copy-json-button"
                                onClick={() => {
                                    navigator.clipboard.writeText(JSON.stringify(response, null, 2));
                                    alert('Full response data copied to clipboard!');
                                }}
                            >
                                📋 Copy Full JSON
                            </button>
                        </div>
                        <pre className="raw-json">
                            {JSON.stringify(response, null, 2)}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
}