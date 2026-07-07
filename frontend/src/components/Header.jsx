export default function Header() {

    return (

        <header
            style={{
                marginBottom: 0,
                marginTop: 0
            }}
        >

            <h1 style={{ color: "#0072BC" }}>UNHCR-Stat-Copilot</h1>
            <h3>⚠️ Beta Version  V0.1 - for Testing Purpose - Once validated, this assistant will be integrated in the AI proposal drafting app.  ⚠️</h3>
            <p>A Collaborative Virtual Assistant to generate Forced Displacement <b>Insights</b> carefully crafted for specific usages: Briefing Kit, Donors Proposals or Medias Post
                <b> |</b> Sourced from <b>publicly available</b> UNHCR Statistics <a href="https://api.unhcr.org/docs/refugee-statistics.html" target="_blank" rel="noopener noreferrer">Database</a> and <a href="https://www.unhcr.org/what-we-do/data-and-publications/reports-and-publications" target="_blank" rel="noopener noreferrer">Reports</a>
                <b> |</b> Powered by a <b>Model Context Protocol</b> AI <a href="/redoc" target="_blank" rel="noopener noreferrer">Server</a> and UNHCR Standard Data Visualisation Tools</p >

        </header >

    );
}