/**
 * World Map visualization module using Leaflet.js
 * Displays posts distribution by country on an interactive world map
 */

import { API } from './api.js';

let map = null;
let countryLayers = {};

// GeoJSON data for world countries
// Using a more reliable source with ISO_A2 codes
const WORLD_COUNTRIES_GEOJSON_URL = 'https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson';

/**
 * Initialize the world map
 */
export function initWorldMap() {
    const mapContainer = document.getElementById('worldMap');
    if (!mapContainer) {
        console.warn('World map container not found');
        return;
    }

    // Initialize Leaflet map
    map = L.map('worldMap', {
        center: [20, 0],
        zoom: 2,
        minZoom: 2,
        maxZoom: 5,
        zoomControl: true,
        attributionControl: true
    });

    // Add tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Load and render country data
    loadAndRenderMap();
}

/**
 * Load country data from API and render on map
 */
async function loadAndRenderMap() {
    try {
        const api = new API();
        const response = await fetch(`${api.baseURL}/api/posts-by-country`);
        if (!response.ok) {
            throw new Error(`Failed to fetch country data: ${response.statusText}`);
        }
        
        const data = await response.json();
        const countryData = data.countries || {};
        const countryNames = data.country_names || {};
        
        console.log('Country data loaded:', {
            total: data.total,
            total_with_country: data.total_with_country,
            countries: Object.keys(countryData).length,
            sample: Object.entries(countryData).slice(0, 5)
        });
        
        // Check if we have any country data
        if (Object.keys(countryData).length === 0) {
            console.warn('No country data available. Posts may need country detection.');
            const mapContainer = document.getElementById('worldMap');
            if (mapContainer && map) {
                mapContainer.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); flex-direction: column; gap: 16px;">
                        <div style="text-align: center;">
                            <p style="font-size: 1.2em; margin-bottom: 8px;">🌍 No country data available</p>
                            <p style="font-size: 0.9em;">Your existing posts don't have country information yet.</p>
                            <p style="font-size: 0.9em; margin-top: 8px;">
                                <strong>To fix this:</strong><br>
                                1. Run the migration script: <code>python -m app.migrate_add_country</code><br>
                                2. Or scrape new posts (they will have country detection automatically)
                            </p>
                        </div>
                    </div>
                `;
            }
            updateLegend(countryData, countryNames, 0);
            return;
        }
        
        // Update legend
        updateLegend(countryData, countryNames, data.total_with_country || 0);
        
        // Load GeoJSON and render countries
        await loadGeoJSONAndRender(countryData, countryNames);
        
    } catch (error) {
        console.error('Error loading world map data:', error);
        const mapContainer = document.getElementById('worldMap');
        if (mapContainer) {
            mapContainer.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">
                    <div style="text-align: center;">
                        <p>⚠️ Unable to load map data</p>
                        <p style="font-size: 0.9em;">${error.message}</p>
                    </div>
                </div>
            `;
        }
    }
}

/**
 * Load GeoJSON data and render countries with colors
 */
async function loadGeoJSONAndRender(countryData, countryNames) {
    try {
        console.log('Loading GeoJSON from:', WORLD_COUNTRIES_GEOJSON_URL);
        const response = await fetch(WORLD_COUNTRIES_GEOJSON_URL);
        if (!response.ok) {
            throw new Error('Failed to load world GeoJSON');
        }
        
        const geojson = await response.json();
        console.log('GeoJSON loaded:', {
            features: geojson.features?.length || 0,
            sample_properties: geojson.features?.[0]?.properties
        });
        
        // Clear existing layers
        Object.values(countryLayers).forEach(layer => {
            if (map) {
                map.removeLayer(layer);
            }
        });
        countryLayers = {};
        
        // Find max count for color scaling
        const maxCount = Math.max(...Object.values(countryData), 1);
        console.log('Max count for scaling:', maxCount);
        
        let renderedCount = 0;
        let matchedCount = 0;
        
        // Render each country
        geojson.features.forEach(feature => {
            // Try multiple property names for country code
            const countryCode = feature.properties.ISO_A2 || 
                               feature.properties.iso_a2 || 
                               feature.properties.ISO_A2_EH ||
                               feature.properties.iso_a2_eh ||
                               feature.properties.id ||
                               feature.properties.ISO ||
                               feature.properties.ISO_A3?.substring(0, 2) ||
                               feature.properties.iso_a3?.substring(0, 2);
            const count = countryData[countryCode] || 0;
            
            if (countryCode) {
                if (count > 0) {
                    matchedCount++;
                }
                
                const layer = L.geoJSON(feature, {
                    style: getCountryStyle(count, maxCount),
                    onEachFeature: (feature, layer) => {
                        const code = feature.properties.ISO_A2 || 
                                    feature.properties.iso_a2 || 
                                    feature.properties.ISO_A2_EH ||
                                    feature.properties.iso_a2_eh ||
                                    feature.properties.id ||
                                    feature.properties.ISO ||
                                    feature.properties.ISO_A3?.substring(0, 2) ||
                                    feature.properties.iso_a3?.substring(0, 2);
                        const name = countryNames[code] || 
                                    feature.properties.NAME || 
                                    feature.properties.name || 
                                    feature.properties.NAME_LONG ||
                                    feature.properties.name_long ||
                                    feature.properties.ADMIN ||
                                    feature.properties.admin ||
                                    code;
                        const postCount = countryData[code] || 0;
                        
                        layer.bindPopup(`
                            <div style="text-align: center; padding: 8px;">
                                <strong>${name}</strong><br>
                                <span style="font-size: 1.2em; font-weight: bold; color: var(--primary-color);">
                                    ${postCount} post${postCount !== 1 ? 's' : ''}
                                </span>
                            </div>
                        `);
                        
                        // Hover effect
                        layer.on({
                            mouseover: function(e) {
                                const layer = e.target;
                                layer.setStyle({
                                    weight: 3,
                                    color: '#00d4ff',
                                    fillOpacity: 0.8
                                });
                                if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                                    layer.bringToFront();
                                }
                            },
                            mouseout: function(e) {
                                const code = feature.properties.ISO_A2 || feature.properties.iso_a2;
                                const count = countryData[code] || 0;
                                layer.setStyle(getCountryStyle(count, maxCount));
                            }
                        });
                    }
                });
                
                if (map) {
                    layer.addTo(map);
                    countryLayers[countryCode] = layer;
                    renderedCount++;
                }
            }
        });
        
        console.log('Map rendering complete:', {
            total_features: geojson.features.length,
            rendered: renderedCount,
            matched_with_data: matchedCount,
            country_data_keys: Object.keys(countryData)
        });
        
        // If no countries matched, show a message
        if (matchedCount === 0 && Object.keys(countryData).length > 0) {
            console.warn('No countries matched! This might be a code mismatch issue.');
            console.log('Sample country codes from data:', Object.keys(countryData).slice(0, 10));
            console.log('Sample country codes from GeoJSON:', 
                geojson.features.slice(0, 5).map(f => ({
                    ISO_A2: f.properties.ISO_A2,
                    iso_a2: f.properties.iso_a2,
                    ISO: f.properties.ISO,
                    id: f.properties.id
                }))
            );
        }
        
    } catch (error) {
        console.error('Error loading GeoJSON:', error);
        // Fallback: show a simple message
        const mapContainer = document.getElementById('worldMap');
        if (mapContainer && map) {
            map.remove();
            mapContainer.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">
                    <div style="text-align: center;">
                        <p>⚠️ Unable to load world map</p>
                        <p style="font-size: 0.9em;">${error.message}</p>
                    </div>
                </div>
            `;
        }
    }
}

/**
 * Get style for a country based on post count
 */
function getCountryStyle(count, maxCount) {
    const opacity = count > 0 ? 0.7 : 0.2;
    const color = getColorForCount(count, maxCount);
    
    return {
        fillColor: color,
        fillOpacity: opacity,
        color: '#333',
        weight: 1,
        opacity: 0.8
    };
}

/**
 * Get color for a post count (gradient from light to dark)
 */
function getColorForCount(count, maxCount) {
    if (count === 0) {
        return '#f0f0f0'; // Light gray for no posts
    }
    
    // Calculate intensity (0 to 1)
    const intensity = Math.min(count / maxCount, 1);
    
    // Color gradient: light blue -> blue -> dark blue -> red (for high counts)
    if (intensity < 0.25) {
        // Light blue
        const factor = intensity / 0.25;
        return `rgb(${Math.round(200 + (55 * (1 - factor)))}, ${Math.round(220 + (35 * (1 - factor)))}, ${Math.round(255)})`;
    } else if (intensity < 0.5) {
        // Blue
        const factor = (intensity - 0.25) / 0.25;
        return `rgb(${Math.round(100 + (100 * (1 - factor)))}, ${Math.round(150 + (105 * (1 - factor)))}, ${Math.round(255)})`;
    } else if (intensity < 0.75) {
        // Dark blue
        const factor = (intensity - 0.5) / 0.25;
        return `rgb(${Math.round(18 + (82 * (1 - factor)))}, ${Math.round(52 + (98 * (1 - factor)))}, ${Math.round(109 + (146 * (1 - factor)))})`;
    } else {
        // Red for very high counts
        const factor = (intensity - 0.75) / 0.25;
        return `rgb(${Math.round(203 + (52 * factor))}, ${Math.round(24 + (28 * factor))}, ${Math.round(29 + (28 * factor))})`;
    }
}

/**
 * Update the map legend
 */
function updateLegend(countryData, countryNames, totalWithCountry) {
    const legendContainer = document.getElementById('mapLegend');
    if (!legendContainer) return;
    
    // Sort countries by count
    const sortedCountries = Object.entries(countryData)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5); // Top 5
    
    if (sortedCountries.length === 0) {
        legendContainer.innerHTML = '<span style="color: var(--text-muted);">No country data available</span>';
        return;
    }
    
    const maxCount = Math.max(...Object.values(countryData));
    
    let legendHTML = `
        <div style="display: flex; flex-direction: column; gap: 4px; font-size: 0.85em;">
            <div style="font-weight: bold; margin-bottom: 4px;">Top Countries:</div>
    `;
    
    sortedCountries.forEach(([code, count]) => {
        const name = countryNames[code] || code;
        const percentage = totalWithCountry > 0 ? Math.round((count / totalWithCountry) * 100) : 0;
        legendHTML += `
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 12px; height: 12px; background: ${getColorForCount(count, maxCount)}; border: 1px solid #333; border-radius: 2px;"></div>
                <span>${name}: <strong>${count}</strong> (${percentage}%)</span>
            </div>
        `;
    });
    
    legendHTML += `
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-color); font-size: 0.9em; color: var(--text-muted);">
                Total: <strong>${totalWithCountry}</strong> posts with country
            </div>
        </div>
    `;
    
    legendContainer.innerHTML = legendHTML;
}

/**
 * Refresh the map data
 */
export function refreshWorldMap() {
    if (map) {
        loadAndRenderMap();
    }
}

