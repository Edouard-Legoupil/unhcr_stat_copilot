import { useState, useEffect, useRef } from "react";

export default function QuartoViewer({ quartoContent, metadata }) {
    const [showRaw, setShowRaw] = useState(false);
    const [renderedHtml, setRenderedHtml] = useState('');
    const [showTools, setShowTools] = useState(false);
    const htmlRef = useRef(null);

    if (!quartoContent) {
        return (
            <div className="card">
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

            setRenderedHtml(`<div className="quarto-rendered">${htmlContent}</div>`);
        } catch (error) {
            console.error("Error rendering Quarto content:", error);
            setRenderedHtml('<p>Error rendering content. Showing raw format.</p>');
        }
    }, [quartoContent]);

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
                        <pre className="quarto-raw">{quartoContent}</pre>
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
                        className="quarto-rendered"
                        ref={htmlRef}
                        dangerouslySetInnerHTML={{ __html: renderedHtml }}
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