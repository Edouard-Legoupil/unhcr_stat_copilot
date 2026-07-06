import { useState, useEffect, useRef } from "react";

export default function QuartoViewer({ quartoContent, quartoRawContent, metadata, rendered = false, analysisId = null }) {
    const [showRaw, setShowRaw] = useState(false);
    const [displayContent, setDisplayContent] = useState('');
    const [isRendered, setIsRendered] = useState(rendered);
    const [showTools, setShowTools] = useState(false);
    const htmlRef = useRef(null);
    
    // Use quartoRawContent if provided, otherwise fall back to quartoContent
    const rawContent = quartoRawContent || quartoContent;

    if (!quartoContent) {
        return (
            <div className="card">
                <h2 className="card-title">Analysis Ready</h2>
                <p>No Quarto content available.</p>
            </div>
        );
    }

    // Handle content display based on whether it's already rendered
    useEffect(() => {
        try {
            // If the content is already pre-rendered HTML from the server
        if (isRendered && analysisId) {
            // fetch pre-rendered HTML via API endpoint
            fetch(`/quarto/${analysisId}/rendered`)
                .then(res => res.text())
                .then(html => setDisplayContent(html))
                .catch(err => {
                    console.warn('Failed to load server-rendered HTML', err);
                    // fallback to client-side markdown render
                    const htmlFallback = simpleMarkdownToHtml(quartoContent);
                    setDisplayContent(`<div class="quarto-rendered">${htmlFallback}</div>`);
                    setIsRendered(false);
                });
        } else {
            // client-side rendering of markdown
            const htmlContent = simpleMarkdownToHtml(quartoContent);
            setDisplayContent(`<div class="quarto-rendered">${htmlContent}</div>`);
            setIsRendered(false);
        }
        } catch (error) {
            console.error("Error rendering Quarto content:", error);
            setDisplayContent('<p>Error rendering content. Showing raw format.</p>');
            setIsRendered(false);
        }
    }, [quartoContent, isRendered, analysisId]);

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

    return (
        <div className="card quarto-viewer">
            <div className="quarto-header">
                <h2 className="card-title">Content</h2>
                <div className="quarto-meta">
                    <div className="quarto-actions">
                        <button
                            className="quarto-toggle"
                            onClick={() => setShowRaw(!showRaw)}
                            title={showRaw ? 'Show rendered HTML' : 'Show source code'}
                        >
                            {showRaw ? '📄 Rendered' : 'Source'}
                        </button>
                        {isRendered && (
                            <span className="quarto-rendered-badge" title="This content is pre-rendered with Quarto CLI">
                                ✅ Pre-rendered
                            </span>
                        )}
                        {isRendered && analysisId && (
                            <a
                                className="quarto-tools-toggle"
                                href={`/quarto/${analysisId}/rendered`}
                                target="_blank"
                                rel="noopener noreferrer"
                                title="View HTML"
                            >
                                🌐 HTML
                            </a>
                        )}
                        {analysisId && (
                            <a
                                className="pdf-download-button"
                                href={`/quarto/${analysisId}/pdf`}
                                target="_blank"
                                rel="noopener noreferrer"
                                title="Download as PDF"
                            >
                                📥 PDF
                            </a>
                        )}
                        {hasTools && (
                            <button
                                className="quarto-tools-toggle"
                                onClick={() => setShowTools(!showTools)}
                                title="Toggle tools used"
                            >
                                {showTools ? '🔧 Hide Tools' : '🔧 Show Tools'}
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <div className="quarto-content">
                {showRaw ? (
                    <div className="quarto-source">
                        <pre className="quarto-raw">{rawContent}</pre>
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
                    </div>
                ) : (
                    <div
                        className="quarto-rendered"
                        ref={htmlRef}
                        dangerouslySetInnerHTML={{ __html: displayContent }}
                    />
                )}
            </div>

            {(metadata && showTools) && (
                <div className="quarto-tools-section">
                    <h4>🔧 Tools Used in This Analysis</h4>
                    <ul className="tools-list">
                        {toolsUsed.map((tool, index) => (
                            <li key={index} className="tool-item">
                                <span className="tool-name">{tool}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {metadata && (
                <div className="quarto-footer">
                    <p className="quarto-metadata">
                        📅 Generated: {new Date(metadata.generated_at).toLocaleString()}<br />
                        📊 Type: {metadata.analysis_type}<br />
                        📄 Format: {metadata.format}
                        {metadata.llm_model && <><br />🤖 Model: {metadata.llm_model}</>}
                        {metadata.llm_version && <> Version: {metadata.llm_version}</>}
                        {hasTools && <br />}
                        {hasTools && <>🔧 Tools: {toolsUsed.length} used</>}
                    </p>
                </div>
            )}
        </div>
    );
}
