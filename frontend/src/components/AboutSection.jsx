export default function AboutSection() {
    return (
        <div className="card about-section">

            <div style={{ marginBottom: '24px' }}>
                <p style={{ marginBottom: '16px' }}>
                    This assistant provides statistical analysis and insights based on UNHCR data and previously published reports and analyses.
                    It follows a detailed and documented <strong>Standard Operating Procedure</strong> to ensure quality and consistency of the analysis. It allows you to:
                </p>

                <ul style={{ marginBottom: '20px', paddingLeft: '20px' }}>
                    <li><strong>View Available Insights:</strong> Browse previously generated analyses and insights</li>
                    <li><strong>Generate New Analysis:</strong> Create custom analyses by asking specific questions about UNHCR data</li>
                    <li><strong>Explore Results:</strong> View detailed analysis results including charts, tables, and narrative explanations</li>
                    <li><strong>Provide Feedback:</strong> Share your thoughts and suggestions to help improving the SOPs used by the model.</li>
                </ul>

                <h3>Key Features</h3>
                <ul style={{ marginBottom: '20px', paddingLeft: '20px' }}>
                    <li><strong>Natural Language Interface:</strong> Ask questions in plain English and the assistant will convert them into computer instructions to process and analyze data</li>
                    <li><strong>Visual Integration:</strong> Generates comprehensive reports with reproducible code, compliant visualizations, and guardrailed narrative.</li>
                    <li><strong>Contextual Adaptation:</strong> Each analysis is adapted in tone, depth, and format to best fit its intended audience and purpose.</li>
                    <li><strong>Shared Analysis:</strong> Access and review previous analyses. Content is also built on insights from published reports</li>
                    <li><strong>Observability:</strong> Understand the thinking process of the AI agents.</li>
                    <li><strong>Continuous Improvement:</strong> Designed to learn from user interactions and feedback to auto generate instructions tuning and improve future analyses.</li>
                </ul>

                <h3>Technical Details</h3>
                <ul style={{ paddingLeft: '20px' }}>
                    <li>The application complies with the <a href="https://unite.un.org/news/osi-first-endorse-united-nations-open-source-principles" target="_blank" rel="noopener noreferrer">UN Open Source Principles:</a></li>
                    <li>The application builds upon the work of <a href="https://github.com/unhcr-dataviz" target="_blank" rel="noopener noreferrer">other UNHCR Open Source Tools</a></li>
                    <li>You can review and learn from the  <a href="https://github.com/edouard-legoupil/unhcr_stat_copilot/" target="_blank" rel="noopener noreferrer" data-testid="github-link">source code</a> and share comments and suggestions through <a href="https://github.com/edouard-legoupil/unhcr_stat_copilot/" target="_blank" rel="noopener noreferrer" data-testid="github-link">GitHub Issues</a></li>
                    <li>Send an email to the assistant developper and supervisor: <a href="mailto:[EMAIL_ADDRESS]" target="_blank" rel="noopener noreferrer" data-testid="github-link">[EMAIL_ADDRESS]</a> if you have more extensive feedback</li>
                </ul>
            </div>


        </div>
    );
}