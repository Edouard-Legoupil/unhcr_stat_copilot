import { useState, useEffect } from "react";

import "./styles/unhcr.css";

import Layout from "./components/Layout";
import Header from "./components/Header";
import HeroSearch from "./components/HeroSearch";



import LoadingSpinner from "./components/LoadingSpinner";
import ErrorPanel from "./components/ErrorPanel";
import AboutSection from "./components/AboutSection";

export default function App() {

    const [message, setMessage] = useState("");

    const [loading, setLoading] = useState(false);

    const [response, setResponse] = useState(null);

    const [error, setError] = useState(null);

    const [previousAnalyses, setPreviousAnalyses] = useState([]);

    const [mode, setMode] = useState("previous"); // "previous" or "new" or "about"

    const [initialLoad, setInitialLoad] = useState(true);

    async function fetchPreviousAnalyses() {
        try {
            // Try to fetch history from backend
            const result = await fetch("/history");

            if (!result.ok) {
                // If backend is not available, try to load from local storage as fallback
                const localHistory = localStorage.getItem("analysisHistory");
                if (localHistory) {
                    const parsedHistory = JSON.parse(localHistory);
                    setPreviousAnalyses(parsedHistory);
                    return parsedHistory;
                }
                throw new Error(
                    `Failed to fetch history (${result.status})`
                );
            }

            const data = await result.json();

            if (data.status === "success") {
                // Cache the history in local storage for offline use
                localStorage.setItem("analysisHistory", JSON.stringify(data.analyses));
                setPreviousAnalyses(data.analyses);
                return data.analyses;
            }

            return [];
        } catch (err) {
            console.error("Failed to fetch previous analyses:", err);

            // Try to load from local storage as fallback
            try {
                const localHistory = localStorage.getItem("analysisHistory");
                if (localHistory) {
                    const parsedHistory = JSON.parse(localHistory);
                    setPreviousAnalyses(parsedHistory);
                    console.log("Loaded analysis history from local storage fallback");
                    return parsedHistory;
                }
            } catch (localError) {
                console.error("Failed to load from local storage:", localError);
            }

            // Only show error if we couldn't load from either source
            setError("Failed to load analysis history");
            return [];
        }
    }

    async function loadPreviousAnalysis(analysisId) {
        if (!analysisId) return;

        try {
            setLoading(true);
            setError(null);

            // Try to fetch from backend first
            const result = await fetch(`/history/${analysisId}`);

            if (!result.ok) {
                throw new Error(
                    `Failed to load analysis (${result.status})`
                );
            }

            const analysisData = await result.json();

            // Check if this is a Quarto analysis
            const quarto_types = ["quarto", "quarto_notebook", "comprehensive_quarto", "basic_quarto_fallback"];
            if (quarto_types.includes(analysisData.analysis_type)) {
                // For Quarto analyses, fetch the pre-rendered HTML
                // Try the rendered endpoint first, fall back to raw .qmd if needed
                let quartoContent = null;
                
                // First, try to get pre-rendered HTML
                try {
                    const renderedResult = await fetch(`/quarto/${analysisId}/rendered`);
                    if (renderedResult.ok) {
                        quartoContent = await renderedResult.text();
                        analysisData.quarto_rendered_html = quartoContent;
                        analysisData.rendered = true;
                    }
                } catch (renderErr) {
                    console.warn("Failed to fetch rendered HTML, falling back to raw .qmd:", renderErr);
                }
                
                // If rendered HTML not available, fall back to raw .qmd
                if (!quartoContent) {
                    const rawResult = await fetch(`/quarto/${analysisId}`);
                    if (rawResult.ok) {
                        quartoContent = await rawResult.text();
                        analysisData.quarto_content = quartoContent;
                        analysisData.rendered = false;
                    }
                }
            }

            // Always log raw response for debugging
            // Use JSON.stringify to capture full content without truncation
            console.log(
                "[UNHCR Copilot] Loaded analysis:",
                JSON.stringify(analysisData, null, 2)
            );

            setResponse(analysisData);

        } catch (err) {
            console.error("Failed to load analysis:", err);

            // Try to load from local storage as fallback
            try {
                const localHistory = localStorage.getItem("analysisHistory");
                if (localHistory) {
                    const parsedHistory = JSON.parse(localHistory);
                    const cachedAnalysis = parsedHistory.find(a => a.id === analysisId);
                    if (cachedAnalysis) {
                        // Try to load the full analysis from local storage
                        const fullAnalysis = localStorage.getItem(`analysis_${analysisId}`);
                        if (fullAnalysis) {
                            setResponse(JSON.parse(fullAnalysis));
                            console.log("Loaded analysis from local storage fallback");
                            setLoading(false);
                            return;
                        }
                    }
                }
            } catch (localError) {
                console.error("Failed to load from local storage:", localError);
            }

            setError("Failed to load the selected analysis");
        } finally {
            setLoading(false);
        }
    }

    // Function to infer basic parameters from the prompt for metadata
    function inferParametersFromPrompt(prompt) {
        const inferred = {};
        
        // Try to extract locations (origin/destination)
        const locationKeywords = ['from', 'to', 'between', 'in', 'at'];
        const locationPattern = new RegExp(`(${locationKeywords.join('|')})\\s+([A-Za-z\\s]+)`, 'i');
        const locationMatch = prompt.match(locationPattern);
        
        if (locationMatch) {
            const keyword = locationMatch[1].toLowerCase();
            const location = locationMatch[2].trim();
            
            if (keyword === 'from') {
                inferred.origin = location;
            } else if (keyword === 'to') {
                inferred.destination = location;
            }
        }
        
        // Try to extract time periods
        const timePatterns = [
            { pattern: /last\\s+(\\d+)\\s+(year|years|month|months|week|weeks)/i, type: 'recent' },
            { pattern: /(\\d{4})\\s*[-–]\\s*(\\d{4})/i, type: 'range' },
            { pattern: /since\\s+(\\d{4})/i, type: 'since' },
            { pattern: /in\\s+(\\d{4})/i, type: 'year' }
        ];
        
        for (const { pattern, type } of timePatterns) {
            const timeMatch = prompt.match(pattern);
            if (timeMatch) {
                if (type === 'recent') {
                    inferred.timespan = `last_${timeMatch[1]}_${timeMatch[2]}`;
                } else if (type === 'range') {
                    inferred.timespan = `${timeMatch[1]}-${timeMatch[2]}`;
                } else if (type === 'since') {
                    inferred.timespan = `since_${timeMatch[1]}`;
                } else if (type === 'year') {
                    inferred.timespan = timeMatch[1];
                }
                break;
            }
        }
        
        // Try to extract topics/themes
        const topicKeywords = ['trends', 'patterns', 'analysis', 'impact', 'changes', 'comparison'];
        for (const keyword of topicKeywords) {
            if (prompt.toLowerCase().includes(keyword)) {
                inferred.topic = keyword;
                break;
            }
        }
        
        return inferred;
    }

    async function askQuestion(formData = {}) {
        // Extract message from formData or use the state message
        const message = formData.question || formData.message || message;

        if (!message.trim()) {
            return;
        }

        setLoading(true);
        setError(null);

        try {

            // Infer parameters from the prompt for metadata
            const inferredParams = inferParametersFromPrompt(message);

            // Include structured parameters if provided, otherwise use inferred values
            const requestBody = {
                message,
                ...(formData.audience && { audience: formData.audience }),
                ...(formData.document_type && { document_type: formData.document_type }),
                // Include inferred parameters as metadata for the agent
                inferred_parameters: inferredParams
            };
            
            // Log what was inferred for debugging
            console.log('Inferred parameters from prompt:', inferredParams);

            const result = await fetch(
                "/chat",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(requestBody)
                }
            );

            if (!result.ok) {
                throw new Error(
                    `Backend request failed (${result.status})`
                );
            }

            const json =
                await result.json();

            // Always log raw response for debugging
            // Use JSON.stringify to capture full content without truncation
            console.log(
                "[UNHCR Copilot] Raw API response:",
                JSON.stringify(json, null, 2)
            );

            // Check for backend-level error in response body
            if (json.status === "error") {
                throw new Error(
                    json.message || "Backend processing error"
                );
            }

            setResponse(json);

            // Cache the full analysis in local storage
            if (json.id) {
                localStorage.setItem(`analysis_${json.id}`, JSON.stringify(json));
            }

            // Switch to content mode to show the generated analysis
            setMode("content");
            await fetchPreviousAnalyses();

        } catch (err) {

            console.error(
                "[UNHCR Copilot] Error:",
                err
            );

            setError(
                err.message ||
                "Unknown error"
            );

        } finally {

            setLoading(false);

        }
    }

    // Fetch previous analyses on initial load with retry logic
    useEffect(() => {
        if (initialLoad) {
            const tryFetchWithRetry = async () => {
                try {
                    await fetchPreviousAnalyses();
                } catch (error) {
                    console.log("Backend not ready, will retry...");
                    // Retry after a short delay if backend isn't ready
                    setTimeout(() => {
                        fetchPreviousAnalyses().catch(console.error);
                    }, 2000);
                }
            };

            tryFetchWithRetry();
            setInitialLoad(false);
        }
    }, [initialLoad]);



    const result =
        response?.result || {};

    const story =
        response?.story || null;

    const guardrails =
        response?.guardrails || null;







    return (

        <Layout>

            <Header />

            <HeroSearch
                message={message}
                setMessage={setMessage}
                askQuestion={askQuestion}
                loading={loading}
                previousAnalyses={previousAnalyses}
                loadPreviousAnalysis={loadPreviousAnalysis}
                mode={mode}
                setMode={setMode}
                AboutSectionComponent={AboutSection}
                response={response}
            />

            <ErrorPanel
                error={error}
            />

            {loading && (
                <LoadingSpinner />
            )}

        </Layout>

    );
}