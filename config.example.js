/**
 * Configuration for Local Development
 * 
 * Copy this file to 'config.js' and add your GitHub Personal Access Token.
 * 'config.js' is git-ignored (if configured) to prevent leaking secrets.
 */

const CONFIG = {
    // Your GitHub Personal Access Token with 'repo' scope
    // Create one at: https://github.com/settings/tokens
    GITHUB_PAT: "" 
};

// Export for use in index.html
if (typeof window !== 'undefined') {
    window.APP_CONFIG = CONFIG;
}
