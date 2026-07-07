export default function AboutSection() {
    return (
        <div className="card about-section">

            <div style={{ marginBottom: '24px' }}>
                <p style={{ marginBottom: '16px' }}>
                    This assistant provides statistical analysis and insights <strong>strictly based on publicly available UNHCR data</strong> and previously published reports and analyses. As such, the resulting output could be potentially created by any analyst working for Donors, Governments or Medias. It also means the content generated can be used in official and public capacity, but it remains the responsibility of the user to ensure its accuracy and appropriateness as it does not replace existing reporting lines and review processes.
                    As any other employee, to ensure quality and consistency, this new colleague follows a detailed and documented <a href="https://github.com/Edouard-Legoupil/unhcr_stat_copilot/blob/main/terms_of_reference_and_sop_unhcr.md" target="_blank" rel="noopener noreferrer"><strong>Terms of Reference and Standard Operating Procedure</strong></a> that describes in a transparent way both its scope and deliverables.
                    More than the model behind, that can be replaced based on a cost-efficiency calculation, those agentic components are where the real capacity and expertise of the assistant lies. </p>
                <p style={{ marginBottom: '16px' }}>
                    The assistant allows to:
                </p>

                <ul style={{ marginBottom: '20px', paddingLeft: '20px' }}>
                    <li><strong>View Available Insights:</strong> Browse previously generated analyses and insights</li>
                    <li><strong>Generate New Analysis:</strong> Create custom analyses by asking specific questions about UNHCR data</li>
                    <li><strong>Explore Results:</strong> View detailed analysis results including charts, tables, and narrative explanations</li>
                    <li><strong>Provide Reviews:</strong> Share your thoughts and suggestions to help improving the ToR and SOPs used by the assistant.</li>
                </ul>

                <h3>Key Features</h3>
                <ul style={{ marginBottom: '20px', paddingLeft: '20px' }}>
                    <li><strong>Natural Language Interface:</strong> Ask questions in plain English and the assistant will convert them into computer instructions to process and analyze data</li>
                    <li><strong>Visual Integration:</strong> Generates comprehensive reports with reproducible code and brand compliant visualizations.</li>
                    <li><strong>Guardrailed Narrative:</strong> Generates comprehensive narratives precisely aligned with statistical definitions.</li>
                    <li><strong>Contextual Adaptation:</strong> Each analysis is adapted in tone, depth, and format to best fit its intended audience and purpose.</li>
                    <li><strong>Shared Analysis:</strong> Access and review previous analyses. Content is also built on insights from published reports</li>
                    <li><strong>Observability:</strong> Understand the thinking process of the AI agents.</li>
                    <li><strong>Continuous Improvement:</strong> Designed to learn from user interactions and feedback to auto generate instructions tuning and improve future analyses.</li>
                </ul>

                <h3>Technical Details</h3>
                <ul style={{ paddingLeft: '20px' }}>
                    <li>The application complies with the <a href="https://unite.un.org/news/osi-first-endorse-united-nations-open-source-principles" target="_blank" rel="noopener noreferrer">UN Open Source Principles</a> as well as <a href="https://intranet.unhcr.org/content/dam/unhcr/intranet/staff%20support/information-communication-technology/documents/english/genai/GenAI%20-%20Technical%20Guidance%20Note.pdf " target="_blank" rel="noopener noreferrer">UNHCR Guidance to develop AI solutions</a>.</li>
                    <li>You can <strong>transparently review</strong> and learn from the  <a href="https://github.com/edouard-legoupil/unhcr_stat_copilot/" target="_blank" rel="noopener noreferrer" data-testid="github-link">source code</a> and share comments and suggestions through <a href="https://github.com/Edouard-Legoupil/unhcr_stat_copilot/issues/new" target="_blank" rel="noopener noreferrer" data-testid="github-link">GitHub Issues</a></li>
                    <li>The application builds on existing UNHCR Open Source Tools for datavisualisation: <a href="https://github.com/unhcr-dataviz/unhcrpyplotstyle" target="_blank" rel="noopener noreferrer">unhcrpyplotstyle</a> and <a href="https://github.com/unhcr-dataviz/quarto-html-unhcr" target="_blank" rel="noopener noreferrer">quarto-html-unhcr</a>, as well as previous explorations like <a href="https://github.com/matheus-hardt/unhcrreports" target="_blank" rel="noopener noreferrer">unhcrreports</a> and <a href="https://github.com/edouard-legoupil/unhcrviz" target="_blank" rel="noopener noreferrer">unhcrviz</a></li>
                    <li>Send an email to the assistant developper (i.e. his supervisor!): <a href="mailto:legoupil@unhcr.org" target="_blank" rel="noopener noreferrer" data-testid="github-link">legoupil@unhcr.org</a> if you have more extensive feedback</li>
                </ul>
            </div>


        </div>
    );
}