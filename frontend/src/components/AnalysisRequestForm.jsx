import { useState, useEffect } from "react";

/**
 * AnalysisRequestForm - Simple form for analysis generation
 * Users provide a prompt, target audience, and document type.
 * The agent automatically infers origin, destination, timespan, and other parameters from the prompt.
 * Document types are conditional based on the selected audience.
 */
export default function AnalysisRequestForm({
    onSubmit,
    loading = false,
    defaultQuestion = ""
}) {
    const [formData, setFormData] = useState({
        question: defaultQuestion,
        origin: "",
        destination: "",
        timespan: "last_year",
        audience: "internal",
        document_type: "long_read",
        style: "formal"
    });
    
    const [documentTypes, setDocumentTypes] = useState([]);
    const [isLoadingConfig, setIsLoadingConfig] = useState(false);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };
    
    // Check if backend is available
    const checkBackendAvailability = async () => {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
            
            const response = await fetch('/health', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                console.warn('Backend health check failed, using fallback document types');
                return false;
            }
            
            try {
                const data = await response.json();
                return data.status === 'ok';
            } catch (e) {
                console.warn('Backend response is not valid JSON, using fallback document types');
                return false;
            }
        } catch (error) {
            console.warn('Backend not available, using fallback document types:', error.message);
            return false;
        }
    };
    
    // Initialize document types based on backend availability
    useEffect(() => {
        const initializeDocumentTypes = async () => {
            const backendAvailable = await checkBackendAvailability();
            
            if (!backendAvailable) {
                console.info('Using fallback document types - backend not available');
                setDocumentTypes([
                    "long_read",
                    "technical_report", 
                    "executive_summary",
                    "social_media",
                    "linkedin_post"
                ]);
            }
        };
        
        initializeDocumentTypes();
    }, []);

    // Fetch document types based on selected audience
    useEffect(() => {
        const fetchDocumentTypes = async () => {
            if (!formData.audience) return;
            
            setIsLoadingConfig(true);
            try {
                console.log(`Fetching document types for audience: ${formData.audience}`);
                
                // Add timeout for the request
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
                
                // Fetch the configuration for the selected audience
                const response = await fetch(`/analysis-config/${formData.audience}`, {
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                // Check if response is valid JSON
                const contentType = response.headers.get('content-type');
                let data;
                try {
                    data = await response.json();
                } catch (e) {
                    // Response is not valid JSON
                    console.error('Failed to parse response as JSON:', e);
                    throw new Error('Response is not valid JSON');
                }
                
                // Verify expected structure
                if (!data || typeof data !== 'object') {
                    throw new Error('Invalid response structure');
                }
                
                if (!data.available_document_types || !Array.isArray(data.available_document_types)) {
                    throw new Error('Invalid document types data');
                }
                
                console.log(`Received document types: ${data.available_document_types.join(', ')}`);
                setDocumentTypes(data.available_document_types);
                
                // If the current document type is not available for this audience,
                // switch to the default document type
                if (data.default_document_type && !data.available_document_types.includes(formData.document_type)) {
                    console.log(`Switching to default document type: ${data.default_document_type}`);
                    setFormData(prev => ({
                        ...prev,
                        document_type: data.default_document_type
                    }));
                }
                
            } catch (error) {
                console.error("Error fetching document types:", error);
                
                // Use audience-specific fallback document types based on the configuration
                const audienceFallbacks = {
                    'internal': ['technical_report', 'long_read', 'executive_summary'],
                    'public_donors': ['executive_summary', 'long_read', 'social_media'],
                    'private_donors': ['executive_summary', 'long_read', 'linkedin_post'],
                    'government': ['technical_report', 'executive_summary', 'long_read'],
                    'media': ['executive_summary', 'long_read', 'social_media']
                };
                
                const fallbackTypes = audienceFallbacks[formData.audience] || 
                                      ['long_read', 'technical_report', 'executive_summary', 'social_media', 'linkedin_post'];
                
                console.log(`Using fallback document types: ${fallbackTypes.join(', ')}`);
                setDocumentTypes(fallbackTypes);
            } finally {
                setIsLoadingConfig(false);
            }
        };
        
        fetchDocumentTypes();
    }, [formData.audience]);

    const handleSubmit = (e) => {
        e.preventDefault();
        onSubmit(formData);
    };



    // Common timespans
    const timespans = [
        { value: "last_year", label: "Last Year" },
        { value: "last_5_years", label: "Last 5 Years" },
        { value: "last_10_years", label: "Last 10 Years" },
        { value: "2020-2024", label: "2020-2024" },
        { value: "2015-2024", label: "2015-2024" }
    ];

    // Audience options
    const audiences = [
        { value: "internal", label: "Internal Use" },
        { value: "public_donors", label: "Public Donors" },
        { value: "private_donors", label: "Private Donors" },
        { value: "government", label: "Government" },
        { value: "media", label: "Media" }
    ];

    // Document type labels mapping
    const documentTypeLabels = {
        long_read: "Long Read Report",
        technical_report: "Technical Report",
        executive_summary: "Executive Summary",
        social_media: "Social Media Post",
        linkedin_post: "LinkedIn Post"
    };

    return (
        <div className="analysis-request-form">

            <form onSubmit={handleSubmit} className="request-form">
                <div className="form-group">
                    <textarea
                        id="question"
                        name="question"
                        value={formData.question}
                        onChange={handleInputChange}
                        placeholder="Describe your analysis request. The AI will automatically extract locations, time periods, and other details from your prompt. Example: What are the refugee trends from Syria to Lebanon in the last 5 years?"
                        required
                        rows={4}
                    />
                </div>

                <div className="form-row">
                    <div className="form-group">
                        <label htmlFor="audience">Target Audience</label>
                        <p className="hint">
                            Who will read this analysis? The content will be tailored accordingly.
                        </p>
                        <select
                            id="audience"
                            name="audience"
                            value={formData.audience}
                            onChange={handleInputChange}
                        >
                            {audiences.map(option => (
                                <option key={option.value} value={option.value}>{option.label}</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label htmlFor="document_type">Document Type</label>
                        <p className="hint">
                            How will this analysis be used? Format will be optimized for the chosen type.
                        </p>
                        <select
                            id="document_type"
                            name="document_type"
                            value={formData.document_type}
                            onChange={handleInputChange}
                            disabled={isLoadingConfig || documentTypes.length === 0}
                        >
                            {isLoadingConfig ? (
                                <option value="">Loading document types...</option>
                            ) : documentTypes.length > 0 ? (
                                documentTypes.map(type => (
                                    <option key={type} value={type}>{documentTypeLabels[type] || type}</option>
                                ))
                            ) : (
                                <option value="">No document types available</option>
                            )}
                        </select>
                        {isLoadingConfig && (
                            <div className="loading-hint">
                                <small>Updating document types for selected audience...</small>
                            </div>
                        )}
                    </div>
                </div>



                <div className="form-actions">
                    <button
                        type="submit"
                        className="primary-button"
                        disabled={loading || !formData.question.trim()}
                    >
                        {loading ? "Generating Analysis..." : "Generate Analysis"}
                    </button>

                    {loading && (
                        <div className="loading-indicator">
                            🤖 AI is processing your request...
                        </div>
                    )}
                </div>

            </form>
        </div>
    );
}