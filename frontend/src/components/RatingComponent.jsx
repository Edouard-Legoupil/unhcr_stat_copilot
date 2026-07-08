import { useState, useEffect } from "react";

/**
 * Helper function to safely set items in localStorage with quota management
 */
function safeSetItem(key, value) {
    try {
        const valueStr = JSON.stringify(value);
        const estimatedSize = key.length + valueStr.length;
        
        // Check current usage
        let totalSize = 0;
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            const v = localStorage.getItem(k);
            totalSize += k.length + v.length;
        }
        
        // Estimate available space (5MB is typical limit, use 4MB as safe threshold)
        const MAX_STORAGE = 4 * 1024 * 1024; // 4MB
        
        if (totalSize + estimatedSize >= MAX_STORAGE) {
            // Clean up old rating entries
            const ratingKeys = [];
            for (let i = 0; i < localStorage.length; i++) {
                const k = localStorage.key(i);
                if (k && k.startsWith('rating_')) {
                    ratingKeys.push(k);
                }
            }
            // Remove oldest ratings (keep only 50 most recent)
            ratingKeys.sort().slice(0, -50).forEach(k => localStorage.removeItem(k));
            
            // Check again
            totalSize = 0;
            for (let i = 0; i < localStorage.length; i++) {
                const k = localStorage.key(i);
                const v = localStorage.getItem(k);
                totalSize += k.length + v.length;
            }
            
            if (totalSize + estimatedSize >= MAX_STORAGE) {
                throw new Error("Storage quota exceeded. Please clear your browser cache.");
            }
        }
        
        localStorage.setItem(key, valueStr);
        return true;
    } catch (e) {
        console.error(`Failed to set localStorage item '${key}':`, e);
        // Don't fail the rating submission, just log the error
        return false;
    }
}

/**
 * RatingComponent - Five-star rating component for analyses
 * Allows users to rate an analysis with 1-5 stars
 * Shows feedback textarea when rating is less than 4 stars
 * Automatically saves the rating to the analysis log
 */
export default function RatingComponent({ analysisId, onRatingSubmitted }) {
    const [rating, setRating] = useState(null);
    const [hoverRating, setHoverRating] = useState(null);
    const [feedback, setFeedback] = useState('');
    const [showFeedback, setShowFeedback] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState(null);
    const [existingRating, setExistingRating] = useState(null);

    // Check if user has already rated this analysis
    useEffect(() => {
        if (analysisId) {
            // Check local storage for existing rating
            const savedRating = localStorage.getItem(`rating_${analysisId}`);
            if (savedRating) {
                try {
                    const ratingData = JSON.parse(savedRating);
                    setExistingRating(ratingData.rating);
                    setFeedback(ratingData.feedback || '');
                    setSubmitted(true);
                } catch (e) {
                    console.error('Failed to parse saved rating:', e);
                }
            }
        }
    }, [analysisId]);

    // Handle star click
    const handleStarClick = (value) => {
        setRating(value);
        // Show feedback if rating is less than 4
        setShowFeedback(value < 4);
    };

    // Handle star hover
    const handleStarHover = (value) => {
        setHoverRating(value);
    };

    // Handle star hover end
    const handleStarHoverEnd = () => {
        setHoverRating(null);
    };

    // Handle feedback change
    const handleFeedbackChange = (e) => {
        setFeedback(e.target.value);
    };

    // Submit rating to backend
    const submitRating = async () => {
        if (!rating || !analysisId) return;

        // For ratings < 4, require feedback
        if (rating < 4 && !feedback.trim()) {
            setError('Please provide feedback for ratings less than 4 stars');
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            const response = await fetch('/analysis/rate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    analysis_id: analysisId,
                    rating: rating,
                    feedback: rating < 4 ? feedback.trim() : null
                }),
            });

            if (!response.ok) {
                let errorMessage = 'Failed to submit rating';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorMessage;
                } catch (e) {
                    // If response is not JSON, use status text
                    errorMessage = response.statusText || errorMessage;
                }
                throw new Error(errorMessage);
            }

            // Try to parse JSON response, but don't fail if it's empty
            let result;
            try {
                const text = await response.text();
                if (text) {
                    result = JSON.parse(text);
                }
            } catch (e) {
                // If response is not JSON, that's okay - rating was still submitted
                result = { status: 'success' };
            }
            
            // Save to local storage to prevent multiple ratings
            safeSetItem(`rating_${analysisId}`, {
                rating: rating,
                feedback: feedback,
                timestamp: new Date().toISOString()
            });

            setSubmitted(true);
            setExistingRating(rating);
            
            // Notify parent component
            if (onRatingSubmitted) {
                onRatingSubmitted({ rating, feedback });
            }

        } catch (err) {
            console.error('Failed to submit rating:', err);
            setError(err.message || 'Failed to submit rating. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    // Handle cancel
    const handleCancel = () => {
        setRating(null);
        setHoverRating(null);
        setFeedback('');
        setShowFeedback(false);
        setError(null);
    };

    // Star component
    const Star = ({ value, filled, onClick, onHover, onHoverEnd }) => {
        return (
            <span
                className={`rating-star ${filled ? 'filled' : 'empty'}`}
                onClick={() => onClick(value)}
                onMouseEnter={() => onHover(value)}
                onMouseLeave={onHoverEnd}
                style={{ cursor: 'pointer', fontSize: '24px' }}
            >
                {filled ? '★' : '☆'}
            </span>
        );
    };

    if (!analysisId) {
        return null;
    }

    // If already submitted, show the existing rating
    if (submitted || existingRating) {
        const displayRating = existingRating || rating;
        return (
            <div className="rating-component submitted">
                <div className="rating-summary">
                    <span className="rating-text">Your Rating:</span>
                    <div className="stars-display">
                        {[1, 2, 3, 4, 5].map((star) => (
                            <span
                                key={star}
                                className={`rating-star ${star <= displayRating ? 'filled' : 'empty'}`}
                                style={{ fontSize: '20px' }}
                            >
                                {star <= displayRating ? '★' : '☆'}
                            </span>
                        ))}
                    </div>
                    {existingRating && existingRating < 4 && (
                        <div className="rating-feedback-display">
                            <strong>Feedback:</strong> {feedback}
                        </div>
                    )}
                </div>
                <p className="thank-you">Thank you for your feedback!</p>
            </div>
        );
    }

    return (
        <div className="rating-component">
            <div className="rating-header">
                <h4>Rate This Analysis</h4>
                <p className="rating-description">Help us improve by rating this analysis</p>
            </div>

            {error && (
                <div className="rating-error">
                    <span className="error-icon">⚠️</span> {error}
                </div>
            )}

            <div className="stars-container">
                {[1, 2, 3, 4, 5].map((star) => {
                    const filled = star <= (hoverRating || rating);
                    return (
                        <Star
                            key={star}
                            value={star}
                            filled={filled}
                            onClick={handleStarClick}
                            onHover={handleStarHover}
                            onHoverEnd={handleStarHoverEnd}
                        />
                    );
                })}
            </div>

            {rating && (
                <div className="rating-selection-info">
                    <p>You selected: <strong>{rating} star{rating !== 1 ? 's' : ''}</strong></p>
                    {rating >= 4 ? (
                        <p className="rating-message">Great! Thank you for the positive rating.</p>
                    ) : (
                        <p className="rating-message">Please let us know how we can improve.</p>
                    )}
                </div>
            )}

            {showFeedback && (
                <div className="feedback-section">
                    <textarea
                        value={feedback}
                        onChange={handleFeedbackChange}
                        placeholder="Please provide your feedback (required for ratings less than 4 stars)"
                        className="feedback-textarea"
                        rows={3}
                    />
                </div>
            )}

            {rating && (
                <div className="rating-actions">
                    <button
                        onClick={submitRating}
                        disabled={submitting || (rating < 4 && !feedback.trim())}
                        className="submit-button"
                    >
                        {submitting ? 'Submitting...' : 'Submit Rating'}
                    </button>
                    <button
                        onClick={handleCancel}
                        className="cancel-button"
                        disabled={submitting}
                    >
                        Cancel
                    </button>
                </div>
            )}
        </div>
    );
}
