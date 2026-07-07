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
    const [analysisMetadata, setAnalysisMetadata] = useState(null);
    const htmlRef = useRef(null);

    // Use quartoRawContent if provided, otherwise fall back to quartoContent
    const initialRawContent = quartoRawContent || quartoContent;

    // Fetch full analysis metadata when component mounts or analysisId changes
    useEffect(() => {
        if (analysisId) {
            const fetchMetadata = async () => {
                try {
                    const result = await fetch(`/history/${analysisId}`);
                    if (result.ok) {
                        const data = await result.json();
                        setAnalysisMetadata(data);
                    }
                } catch (error) {
                    console.error('Failed to fetch analysis metadata:', error);
                }
            };
            fetchMetadata();
        }
    }, [analysisId]);

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

    // Sanitize the Quarto HTML to prevent global CSS conflicts
    // Remove <style> tags that could affect the header and other components
    const sanitizeQuartoHtml = (html) => {
        if (!html) return html;

        // Remove <style> tags that contain global CSS
        let sanitized = html.replace(/<style[^>]*>.*?<\/style>/gmis, '');

        return sanitized;
    };

    const sanitizedQuartoContent = sanitizeQuartoHtml(quartoContent);

    // Extract tool sequence from metadata or response
    // Handle both array and string (JSON string) formats
    let toolSequence = [];
    if (metadata?.tool_sequence) {
        toolSequence = Array.isArray(metadata.tool_sequence)
            ? metadata.tool_sequence
            : [];
    } else if (response?.tool_sequence) {
        toolSequence = Array.isArray(response.tool_sequence)
            ? response.tool_sequence
            : [];
    }

    // Also try to parse from response.tools_used if it's a string
    if (toolSequence.length === 0 && response?.tools_used) {
        try {
            if (typeof response.tools_used === 'string') {
                toolSequence = JSON.parse(response.tools_used);
            } else if (Array.isArray(response.tools_used)) {
                toolSequence = response.tools_used;
            }
        } catch (e) {
            console.warn('Failed to parse tools_used:', e);
        }
    }

    const successfulTools = toolSequence.filter(tool => tool?.success);
    const failedTools = toolSequence.filter(tool => tool && !tool.success);

    // Extract analysis configuration
    const analysisConfig = metadata?.analysis_config || response?.analysis_config || {};

    // Get ratings from analysis metadata
    const ratings = analysisMetadata?.ratings || response?.ratings || [];
    const averageRating = analysisMetadata?.average_rating || response?.average_rating;
    const ratingCount = analysisMetadata?.rating_count || response?.rating_count || ratings.length;

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
                            Download as Word
                        </button>
                    )}
                    <button
                        className="viewer-toggle"
                        onClick={() => setShowRaw(!showRaw)}
                        title={showRaw ? 'Show rendered HTML' : 'Show source code'}
                    >
                        {showRaw ? ' Rendered' : 'Source Code'}
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
                                        Copy Source
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
                                        Download Quarto notebook
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                ) : (
                    <div
                        className="viewer-rendered"
                        ref={htmlRef}
                        dangerouslySetInnerHTML={{ __html: sanitizedQuartoContent }}
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
                        {/* Ratings Section - Display user ratings and feedback */}
                        {ratings.length > 0 && (
                            <div className="debug-section">
                                <h5>⭐ User Ratings</h5>
                                <div className="ratings-summary">
                                    <div className="rating-stat">
                                        <span className="rating-stat-label">Average Rating:</span>
                                        <span className="rating-stat-value">
                                            {averageRating ? averageRating.toFixed(1) : 'N/A'} / 5
                                        </span>
                                    </div>
                                    <div className="rating-stat">
                                        <span className="rating-stat-label">Total Ratings:</span>
                                        <span className="rating-stat-value">{ratingCount}</span>
                                    </div>
                                </div>
                                {ratings.map((rating, index) => (
                                    <div key={index} className="rating-entry">
                                        <span className="rating-stars">
                                            {'★'.repeat(rating.rating || 0)}
                                            {'☆'.repeat(5 - (rating.rating || 0))}
                                        </span>
                                        <span className="rating-timestamp">
                                            {rating.timestamp ? new Date(rating.timestamp).toLocaleString() : 'Unknown'}
                                        </span>
                                        {rating.feedback && (
                                            <div className="rating-feedback">
                                                <strong>Feedback:</strong> {rating.feedback}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Tool Execution Summary */}
                        <div className="debug-section">
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
                                        {formatDuration(toolSequence.reduce((sum, tool) => sum + (tool?.duration_ms || 0), 0))}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Tool Execution Details */}
                        {toolSequence.length > 0 && (
                            <div className="debug-section">
                                <h5>📋 Tool Execution Details</h5>
                                <div className="tool-sequence">
                                    {toolSequence.map((tool, index) => {
                                        const toolName = tool?.tool || tool?.name || `Tool ${index + 1}`;
                                        const success = tool?.success !== undefined ? tool.success : true;
                                        const duration = tool?.duration_ms || 0;
                                        const error = tool?.error || tool?.error_message;
                                        const resultSummary = tool?.result_summary || tool?.result || '';

                                        return (
                                            <div key={index} className={`tool-execution ${success ? 'success' : 'failed'}`}>
                                                <div className="tool-header">
                                                    <span className="tool-name">🔧 {toolName}</span>
                                                    <span className={`tool-status ${success ? 'success' : 'failed'}`}>
                                                        {success ? '✅ Success' : '❌ Failed'}
                                                    </span>
                                                    {duration > 0 && (
                                                        <span className="tool-duration">
                                                            {formatDuration(duration)}
                                                        </span>
                                                    )}
                                                </div>
                                                {success && resultSummary && (
                                                    <div className="tool-result">
                                                        <pre className="tool-summary">{resultSummary}</pre>
                                                    </div>
                                                )}
                                                {error && (
                                                    <div className="tool-error">
                                                        <pre className="error-message">{error}</pre>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {/* Analysis Configuration */}
                        <div className="debug-section">
                            <h5>🎯 Audience Configuration</h5>
                            <div className="config-grid">
                                <div className="config-item">
                                    <span className="config-label">Audience:</span>
                                    <span className="config-value">{response?.audience || metadata?.audience || 'N/A'}</span>
                                </div>
                                <div className="config-item">
                                    <span className="config-label">Document Type:</span>
                                    <span className="config-value">{response?.document_type || metadata?.document_type || 'N/A'}</span>
                                </div>
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

                        {/* Raw Response Data */}
                        <div className="debug-section">
                            <h5>📊 Response Metadata</h5>
                            <div className="response-info">
                                <div className="response-item">
                                    <span className="response-label">Analysis Type:</span>
                                    <span className="response-value">{response?.analysis_type || metadata?.analysis_type || 'N/A'}</span>
                                </div>
                                <div className="response-item">
                                    <span className="response-label">Format:</span>
                                    <span className="response-value">{response?.format || metadata?.format || 'N/A'}</span>
                                </div>
                                <div className="response-item">
                                    <span className="response-label">Question:</span>
                                    <span className="response-value">{response?.question || metadata?.question || 'N/A'}</span>
                                </div>
                                <div className="response-item">
                                    <span className="response-label">Generated:</span>
                                    <span className="response-value">
                                        {response?.generated_at ? new Date(response.generated_at).toLocaleString() : 'N/A'}
                                    </span>
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
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}