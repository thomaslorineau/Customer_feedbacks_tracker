// API client for backend communication
export class API {
    constructor() {
        this.baseURL = this.getApiBase();
    }
    
    getApiBase() {
        // Si on est sur localhost, utiliser le port 8000 par défaut
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            return `http://${window.location.hostname}:8000`;
        }
        // Sinon, utiliser le même hostname et port que la page actuelle
        const port = window.location.port || '11840';
        return `${window.location.protocol}//${window.location.hostname}:${port}`;
    }
    
    async getPosts(limit = 100, offset = 0) {
        const response = await fetch(`${this.baseURL}/posts?limit=${limit}&offset=${offset}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch posts: ${response.statusText}`);
        }
        return response.json();
    }
    
    async scrape(source, query = 'OVH', limit = 50) {
        const response = await fetch(`${this.baseURL}/scrape/${source}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, limit })
        });
        if (!response.ok) {
            throw new Error(`Failed to scrape ${source}: ${response.statusText}`);
        }
        return response.json();
    }
    
    async getUIVersion() {
        const response = await fetch(`${this.baseURL}/admin/get-ui-version`);
        if (!response.ok) {
            return { version: 'v1' };
        }
        return response.json();
    }
    
    async setUIVersion(version) {
        const response = await fetch(`${this.baseURL}/admin/set-ui-version`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(version)
        });
        if (!response.ok) {
            throw new Error(`Failed to set UI version: ${response.statusText}`);
        }
        return response.json();
    }
}






















