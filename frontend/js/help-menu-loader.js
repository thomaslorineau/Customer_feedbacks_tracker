/**
 * Help Menu Loader
 * Loads the unified help menu content and injects it into the help menu on all pages.
 */

const HELP_MENU_CONTENT = `
<!-- Introduction -->
<h3>💬 Customer Feedbacks Tracker</h3>
<p>
    Real-time monitoring platform that collects and analyzes customer feedback on OVH services from multiple online sources. 
    Get insights, track sentiment, and identify improvement opportunities automatically.
</p>
<p style="background: #e7f3ff; padding: 0.75rem; border-radius: 6px; border-left: 3px solid #0099ff; margin: 1rem 0;">
    <strong>🎨 Built with VibeCoding:</strong> This project was developed 100% with VibeCoding (Cursor AI).
</p>

<!-- Project Overview -->
<h3>📊 Project Overview</h3>
<ul>
    <li><strong>Version:</strong> 1.0.8 (Beta)</li>
    <li><strong>Status:</strong> Fully Functional ✅</li>
    <li><strong>Database:</strong> DuckDB</li>
    <li><strong>Backend:</strong> FastAPI (Python 3.11+)</li>
    <li><strong>Frontend:</strong> Vanilla JavaScript (ES6 Modules)</li>
</ul>

<!-- Core Features -->
<h3>🎯 Core Features</h3>
<ul>
    <li><strong>📥 Multi-source Scraping:</strong> Collect feedback from 10+ sources automatically</li>
    <li><strong>🧠 Smart Analysis:</strong> Automatic sentiment analysis, relevance scoring, and language detection</li>
    <li><strong>📊 Interactive Dashboard:</strong> Visual analytics with charts, filters, and real-time insights</li>
    <li><strong>🤖 AI-Powered Insights:</strong> Get recommended actions and product analysis using LLM</li>
    <li><strong>📧 Email Notifications:</strong> Automatic alerts for problematic posts with configurable triggers</li>
    <li><strong>💡 Improvement Opportunities:</strong> Identify pain points, filter by product, and prioritize actions with opportunity scores (0-100)</li>
    <li><strong>🔍 Product Filtering:</strong> Click on a product to filter LLM analysis and posts automatically</li>
    <li><strong>👁️ Post Preview:</strong> View full post content in a modal with link to original source</li>
</ul>

<!-- How Scraping Works -->
<h3>⚙️ How Scraping Works</h3>
<p><strong>The scraping process follows these steps:</strong></p>
<ol>
    <li><strong>Keyword Combination:</strong> Base keywords (brands, products, problems, leadership) are automatically combined with your custom keywords</li>
    <li><strong>Multi-source Collection:</strong> Each keyword is searched across all 10 sources simultaneously</li>
    <li><strong>Fallback Strategies:</strong> If primary method fails, scrapers try:
        <ul>
            <li>Google Search fallback (<code>site:domain.com query</code>)</li>
            <li>RSS/Atom feed detection and parsing</li>
        </ul>
    </li>
    <li><strong>Relevance Filtering:</strong> Posts with relevance score &lt; 30% are automatically filtered out</li>
    <li><strong>Analysis:</strong> Remaining posts are analyzed for sentiment, language, and country</li>
    <li><strong>Storage:</strong> Valid posts are stored in the database with metadata</li>
    <li><strong>Notification:</strong> If email triggers are configured, notifications are sent for problematic posts</li>
</ol>

<!-- Supported Sources -->
<h3>📥 Supported Sources</h3>
<ul>
    <li><strong>X/Twitter:</strong> Via Nitter instances (10+ instances with rotation) or Twitter API v2</li>
    <li><strong>Reddit:</strong> Via API JSON and RSS feeds</li>
    <li><strong>GitHub:</strong> Issues and discussions via API v3 (requires API key)</li>
    <li><strong>Stack Overflow:</strong> Questions via API v2.3</li>
    <li><strong>Trustpilot:</strong> Reviews via HTML scraping and API (requires API key)</li>
    <li><strong>Google News:</strong> Articles via RSS feeds (requires API key)</li>
    <li><strong>OVH Forum:</strong> Community discussions via HTML scraping</li>
    <li><strong>Mastodon:</strong> Posts via Mastodon API</li>
    <li><strong>G2 Crowd:</strong> Software reviews via HTML scraping</li>
    <li><strong>LinkedIn:</strong> Public posts via API (requires API key)</li>
    <li><strong>Discord:</strong> Messages from Discord servers via Discord API (requires bot token)</li>
</ul>

<!-- Keywords System -->
<h3>🔑 Keywords System</h3>
<p><strong>Two types of keywords work together:</strong></p>
<ul>
    <li><strong>Base Keywords:</strong> <a href="/settings#base-keywords" style="color: var(--accent-primary); text-decoration: underline;">Configure in Settings</a>
        <ul>
            <li><strong>Brands:</strong> OVH, OVHCloud, Kimsufi, etc.</li>
            <li><strong>Products:</strong> OVH domain, OVH hosting, OVH VPS, etc.</li>
            <li><strong>Problems:</strong> OVH complaint, OVH support, OVH billing, etc.</li>
            <li><strong>Leadership:</strong> Michel Paulin, Octave Klaba, OVH CEO, etc.</li>
        </ul>
        These are always included in scraping operations.
    </li>
    <li><strong>Custom Keywords (Feedbacks Collection):</strong> Additional keywords you define are combined with base keywords</li>
</ul>
<p><strong>Example:</strong> If you add "downtime" as custom keyword, the system will search for "OVH downtime", "OVHCloud downtime", "Kimsufi downtime", etc. across all sources.</p>

<!-- Relevance & Scoring -->
<h3>📈 Relevance & Scoring</h3>
<ul>
    <li><strong>Relevance Score (0-100%):</strong>
        <ul>
            <li>OVH Brands: 35%</li>
            <li>OVH URLs: 25%</li>
            <li>OVH Leadership: 20%</li>
            <li>OVH Products: 20%</li>
        </ul>
        Posts with score &lt; 30% are automatically filtered.
    </li>
    <li><strong>Sentiment Analysis:</strong> VADER-based classification (Positive/Negative/Neutral)</li>
    <li><strong>Opportunity Score (0-100):</strong> Additive score combining:
        <ul>
            <li>Relevance (0-30 points): Based on post relevance score</li>
            <li>Sentiment (0-40 points): Negative = 40, Neutral = 15, Positive = 5</li>
            <li>Recency (0-20 points): Recent posts score higher</li>
            <li>Engagement (0-10 points): Based on views, comments, reactions</li>
        </ul>
        Used to prioritize posts requiring attention.
    </li>
</ul>

<!-- Settings Configuration -->
<h3>⚙️ Settings Configuration</h3>

<h4>🔐 API Keys (Required for some sources)</h4>
<ul>
    <li><strong>OpenAI API Key:</strong> For AI-powered features (recommended actions, insights, product analysis)</li>
    <li><strong>Anthropic API Key:</strong> Alternative LLM provider</li>
    <li><strong>Google API Key:</strong> Required for Google News scraping</li>
    <li><strong>GitHub API Key:</strong> Required for GitHub issues and discussions</li>
    <li><strong>Trustpilot API Key:</strong> Required for Trustpilot reviews</li>
    <li><strong>Twitter Bearer Token:</strong> Optional, for Twitter API v2 (otherwise uses Nitter)</li>
    <li><strong>Discord Bot Token:</strong> Required for Discord scraping (requires bot token and guild ID)</li>
</ul>

<h4>📧 Email Notifications</h4>
<ul>
    <li><strong>SMTP Configuration:</strong> Set in <code>.env</code> file:
        <ul>
            <li><code>SMTP_HOST</code>, <code>SMTP_PORT</code>, <code>SMTP_USER</code>, <code>SMTP_PASSWORD</code></li>
            <li><code>SMTP_FROM_EMAIL</code>, <code>SMTP_FROM_NAME</code></li>
        </ul>
    </li>
    <li><strong>Notification Triggers:</strong> Create rules to automatically send emails when:
        <ul>
            <li>Posts match specific sentiment (negative, positive, neutral, or all)</li>
            <li>Relevance score exceeds threshold</li>
            <li>Posts come from specific sources</li>
            <li>Language matches (optional)</li>
        </ul>
    </li>
    <li><strong>Cooldown System:</strong> Prevents spam by limiting notification frequency (configurable per trigger)</li>
</ul>

<h4>🔍 Base Keywords</h4>
<ul>
    <li>Configure default keywords that are always used in scraping</li>
    <li>Organized by categories: Brands, Products, Problems, Leadership</li>
    <li>These are combined with your custom keywords automatically</li>
    <li><a href="/settings#base-keywords" style="color: var(--accent-primary); text-decoration: underline;">Go to Base Keywords settings →</a></li>
</ul>

<h4>⏱️ Rate Limiting</h4>
<ul>
    <li>Configure maximum API requests per minute</li>
    <li>Prevents exceeding API quotas and protects against abuse</li>
    <li>Each source can have different rate limits</li>
</ul>

<!-- Pages Overview -->
<h3>📄 Pages Overview</h3>
<ul>
    <li><strong>📊 Dashboard Analytics:</strong> Visual insights, charts, timeline, and post management with advanced filtering</li>
    <li><strong>💡 Improvements Opportunities:</strong> Pain points analysis (auto-detected), product distribution with opportunity scores, interactive product filtering, LLM analysis, and prioritized posts to review with preview modal</li>
    <li><strong>📥 Feedbacks Collection:</strong> Configure keywords, launch scrapers, view progress, and export data</li>
    <li><strong>📋 Scraping Logs:</strong> Real-time monitoring of scraping operations, errors, and success rates</li>
    <li><strong>⚙️ Settings:</strong> Configure API keys, email notifications, base keywords, and application settings</li>
</ul>

<!-- Workflow -->
<h3>🔄 Typical Workflow</h3>
<ol>
    <li><strong>Initial Setup:</strong> Configure API keys in Settings (for sources that require them)</li>
    <li><strong>Configure Keywords:</strong> Add custom keywords in Feedbacks Collection (base keywords are already configured)</li>
    <li><strong>Launch Scraping:</strong> Click "Scrape New Data" to collect feedback from all sources</li>
    <li><strong>Monitor Progress:</strong> Watch real-time progress in Feedbacks Collection or check Scraping Logs</li>
    <li><strong>Analyze Results:</strong> View collected feedback in Dashboard Analytics with interactive charts and filters</li>
    <li><strong>Get Insights:</strong> Check Improvements Opportunities for auto-detected pain points, product distribution, and recommended actions</li>
    <li><strong>Filter by Product:</strong> Click on a product in the distribution chart to filter LLM analysis and posts automatically</li>
    <li><strong>Preview Posts:</strong> Click on any post in Improvements Opportunities to see full content in a preview modal</li>
    <li><strong>Set Up Alerts:</strong> Configure email notification triggers in Settings to get notified of problematic posts</li>
</ol>

<!-- Tips -->
<h3>💡 Pro Tips</h3>
<ul>
    <li>Start with base keywords - they cover most OVH-related content automatically</li>
    <li>Use custom keywords for specific campaigns, products, or events</li>
    <li>Enable auto-refresh in Scraping Logs to monitor jobs in real-time</li>
    <li>Configure email triggers to stay informed about critical feedback without checking manually</li>
    <li>Use the Dashboard timeline to identify trends and spikes in feedback</li>
    <li>Export filtered posts to CSV for external analysis or reporting</li>
    <li>Check Improvements Opportunities regularly to identify recurring issues (auto-detected pain points)</li>
    <li>Click on products in the distribution chart to focus analysis on specific products</li>
    <li>Use the post preview modal to quickly review full content without leaving the page</li>
    <li>Opportunity scores (0-100) help prioritize which posts need immediate attention</li>
</ul>

<!-- Security -->
<h3>🔒 Security & Privacy</h3>
<ul>
    <li><strong>API Keys:</strong> Stored securely in the database, never exposed in frontend</li>
    <li><strong>Environment Variables:</strong> Sensitive data (SMTP credentials) stored in <code>.env</code> file (not committed to Git)</li>
    <li><strong>Data Storage:</strong> All data stored locally in DuckDB database</li>
    <li><strong>No External Sharing:</strong> Collected data remains private and is not shared with third parties</li>
</ul>

<!-- Troubleshooting -->
<h3>🔧 Troubleshooting</h3>
<ul>
    <li><strong>No posts collected:</strong> Check API keys are configured, verify keywords are valid, check Scraping Logs for errors</li>
    <li><strong>Scraping fails:</strong> Check Scraping Logs for specific error messages, verify API keys are valid, check rate limits</li>
    <li><strong>Email not sending:</strong> Verify SMTP configuration in <code>.env</code>, use "Test Email Sending" feature</li>
    <li><strong>Low relevance posts:</strong> Adjust base keywords or add more specific custom keywords</li>
</ul>

<!-- Documentation -->
<h3>📚 Documentation</h3>
<p>For detailed guides, check the <code>docs/</code> folder in the project repository:</p>
<ul>
    <li>Quick Start Guide</li>
    <li>API Keys Configuration</li>
    <li>Architecture Documentation</li>
    <li>Security Overview</li>
</ul>

<!-- GitHub Link -->
<h3>🔗 GitHub Repository</h3>
<p>
    <strong>Source Code:</strong> 
    <a href="https://github.com/thomaslorineau/Customer_feedbacks_tracker" target="_blank" rel="noopener noreferrer" style="color: var(--accent-primary); text-decoration: underline;">
        https://github.com/thomaslorineau/Customer_feedbacks_tracker
    </a>
</p>
<p style="color: var(--text-muted); font-size: 0.9em; margin-top: 0.5rem;">
    Visit the repository for issues, contributions, and the latest updates.
</p>
`;

function loadHelpMenuContent() {
    const helpMenuContent = document.querySelector('.help-menu-content');
    if (!helpMenuContent) {
        console.warn('Help menu content container not found');
        return;
    }

    // Check if content is already loaded (avoid duplicate loads)
    if (helpMenuContent.dataset.loaded === 'true') {
        return;
    }

    try {
        helpMenuContent.innerHTML = HELP_MENU_CONTENT;
        helpMenuContent.dataset.loaded = 'true';
    } catch (error) {
        console.error('Error loading help menu content:', error);
        // Fallback: show error message
        helpMenuContent.innerHTML = `
            <h3>❌ Error Loading Help Content</h3>
            <p>Unable to load help documentation. Please refresh the page or contact support.</p>
            <p style="color: var(--text-muted); font-size: 0.9em;">Error: ${error.message}</p>
        `;
    }
}

// Load help menu content when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadHelpMenuContent);
} else {
    loadHelpMenuContent();
}
