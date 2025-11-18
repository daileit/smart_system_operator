/**
 * Smart System Operator - Chart.js Utilities
 * Reusable chart creation functions for consistent styling across the application
 */

// Default chart colors
const CHART_COLORS = {
    blue: 'rgba(59, 130, 246, 0.8)',
    purple: 'rgba(168, 85, 247, 0.8)',
    green: 'rgba(34, 197, 94, 0.8)',
    orange: 'rgba(249, 115, 22, 0.8)',
    red: 'rgba(239, 68, 68, 0.8)',
    indigo: 'rgba(99, 102, 241, 0.8)',
    cyan: 'rgba(6, 182, 212, 0.8)'
};

// Default chart options
const DEFAULT_OPTIONS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'top'
        }
    }
};

/**
 * Create a stacked bar chart for risk levels over time
 * @param {string} canvasId - Canvas element ID
 * @param {Array} dates - Array of date labels
 * @param {Array} low - Low risk count data
 * @param {Array} medium - Medium risk count data
 * @param {Array} high - High risk count data
 */
function createRiskTimelineChart(canvasId, dates, low, medium, high) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [{
                label: 'Low Risk',
                data: low,
                backgroundColor: CHART_COLORS.green
            }, {
                label: 'Medium Risk',
                data: medium,
                backgroundColor: CHART_COLORS.orange
            }, {
                label: 'High Risk',
                data: high,
                backgroundColor: CHART_COLORS.red
            }]
        },
        options: {
            ...DEFAULT_OPTIONS,
            scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true }
            }
        }
    });
}

/**
 * Create a doughnut chart for action type distribution
 * @param {string} canvasId - Canvas element ID
 * @param {Array} labels - Type labels
 * @param {Array} data - Count data
 */
function createActionTypePieChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    CHART_COLORS.blue,
                    CHART_COLORS.purple,
                    CHART_COLORS.green
                ]
            }]
        },
        options: {
            ...DEFAULT_OPTIONS,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

/**
 * Create a horizontal bar chart for success rates
 * @param {string} canvasId - Canvas element ID
 * @param {Array} labels - Action names
 * @param {Array} successRates - Success rate percentages
 */
function createSuccessRateChart(canvasId, labels, successRates) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Success Rate (%)',
                data: successRates,
                backgroundColor: CHART_COLORS.green,
                borderColor: 'rgba(34, 197, 94, 1)',
                borderWidth: 1
            }]
        },
        options: {
            ...DEFAULT_OPTIONS,
            indexAxis: 'y',
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { beginAtZero: true, max: 100 }
            }
        }
    });
}

/**
 * Create a simple bar chart for server executions
 * @param {string} canvasId - Canvas element ID
 * @param {Array} labels - Server names
 * @param {Array} data - Execution counts
 */
function createServerExecutionsChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total Executions',
                data: data,
                backgroundColor: CHART_COLORS.blue
            }]
        },
        options: {
            ...DEFAULT_OPTIONS,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

/**
 * Create a stacked bar chart for success vs failed executions
 * @param {string} canvasId - Canvas element ID
 * @param {Array} labels - Server names
 * @param {Array} successData - Success counts
 * @param {Array} failedData - Failed counts
 */
function createSuccessVsFailedChart(canvasId, labels, successData, failedData) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Success',
                data: successData,
                backgroundColor: CHART_COLORS.green
            }, {
                label: 'Failed',
                data: failedData,
                backgroundColor: CHART_COLORS.red
            }]
        },
        options: {
            ...DEFAULT_OPTIONS,
            scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true }
            }
        }
    });
}

/**
 * Create a time-series line chart
 * @param {string} canvasId - Canvas element ID
 * @param {Array} dates - Date labels
 * @param {Object} datasets - Object with label as key and data array as value
 */
function createTimeSeriesChart(canvasId, dates, datasets) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const colors = Object.values(CHART_COLORS);
    
    const chartDatasets = Object.entries(datasets).map(([label, data], index) => ({
        label: label,
        data: data,
        borderColor: colors[index % colors.length],
        backgroundColor: colors[index % colors.length].replace('0.8', '0.3'),
        fill: false,
        tension: 0.4
    }));
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: chartDatasets
        },
        options: {
            ...DEFAULT_OPTIONS,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day'
                    }
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Export for use in other scripts if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CHART_COLORS,
        createRiskTimelineChart,
        createActionTypePieChart,
        createSuccessRateChart,
        createServerExecutionsChart,
        createSuccessVsFailedChart,
        createTimeSeriesChart
    };
}
