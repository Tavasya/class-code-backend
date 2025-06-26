class FlowDashboard {
    constructor() {
        this.currentData = null;
        this.currentScenario = null;
        this.viewMode = 'tree';
        this.init();
    }

    async init() {
        await this.loadData();
        this.renderStats();
        this.renderScenarios();
    }

    async loadData() {
        try {
            // In a real app, this would load from your backend
            // For now, we'll use placeholder data
            this.currentData = {
                metadata: {
                    total_functions: 127,
                    entry_points: 8,
                    scenarios: 12
                },
                scenarios: [
                    {
                        id: 'user_registration',
                        name: 'User Registration',
                        business_purpose: 'Creates new user accounts with validation and welcome email',
                        user_description: 'Validates user input → Creates database record → Sends welcome email',
                        estimated_complexity: 15,
                        potential_bottlenecks: ['Database operation: Create User', 'External call: Send Email'],
                        flow_tree: {
                            name: 'register_user',
                            display_name: 'Register User',
                            type: 'api_endpoint',
                            complexity: 3,
                            children: [
                                {
                                    name: 'validate_input',
                                    display_name: 'Validate Input',
                                    type: 'business_logic',
                                    complexity: 2,
                                    children: []
                                },
                                {
                                    name: 'create_user_account',
                                    display_name: 'Create Account',
                                    type: 'database',
                                    complexity: 3,
                                    children: [
                                        {
                                            name: 'check_duplicates',
                                            display_name: 'Check Duplicates',
                                            type: 'database',
                                            complexity: 2,
                                            children: []
                                        },
                                        {
                                            name: 'save_user',
                                            display_name: 'Save User',
                                            type: 'database',
                                            complexity: 2,
                                            children: []
                                        }
                                    ]
                                },
                                {
                                    name: 'send_welcome_email',
                                    display_name: 'Send Welcome Email',
                                    type: 'external',
                                    complexity: 2,
                                    children: []
                                }
                            ]
                        }
                    },
                    {
                        id: 'payment_processing',
                        name: 'Payment Processing',
                        business_purpose: 'Processes customer payments through multiple validation steps',
                        user_description: 'Validates payment → Charges card → Updates order → Sends receipt',
                        estimated_complexity: 22,
                        potential_bottlenecks: ['External call: Charge Card', 'Database operation: Update Order'],
                        flow_tree: {
                            name: 'process_payment',
                            display_name: 'Process Payment',
                            type: 'api_endpoint',
                            complexity: 4,
                            children: [
                                {
                                    name: 'validate_payment',
                                    display_name: 'Validate Payment',
                                    type: 'business_logic',
                                    complexity: 3,
                                    children: []
                                },
                                {
                                    name: 'charge_card',
                                    display_name: 'Charge Card',
                                    type: 'external',
                                    complexity: 4,
                                    children: []
                                },
                                {
                                    name: 'update_order',
                                    display_name: 'Update Order',
                                    type: 'database',
                                    complexity: 3,
                                    children: []
                                },
                                {
                                    name: 'send_receipt',
                                    display_name: 'Send Receipt',
                                    type: 'external',
                                    complexity: 2,
                                    children: []
                                }
                            ]
                        }
                    }
                ]
            };
        } catch (error) {
            console.error('Failed to load data:', error);
            this.showError('Failed to load visualization data');
        }
    }

    renderStats() {
        if (!this.currentData) return;

        const { metadata } = this.currentData;
        document.getElementById('total-functions').textContent = metadata.total_functions;
        document.getElementById('entry-points').textContent = metadata.entry_points;
        document.getElementById('scenarios').textContent = metadata.scenarios;
    }

    renderScenarios() {
        if (!this.currentData) return;

        const scenarioList = document.getElementById('scenario-list');
        scenarioList.innerHTML = '';

        this.currentData.scenarios.forEach(scenario => {
            const item = document.createElement('div');
            item.className = 'scenario-item';
            item.onclick = () => this.selectScenario(scenario);

            item.innerHTML = `
                <div class="scenario-title">${scenario.name}</div>
                <div class="scenario-desc">${scenario.business_purpose}</div>
                <div style="margin-top: 0.5rem; font-size: 0.75rem; color: #64748b;">
                    Complexity: ${scenario.estimated_complexity} | 
                    Bottlenecks: ${scenario.potential_bottlenecks.length}
                </div>
            `;

            scenarioList.appendChild(item);
        });
    }

    selectScenario(scenario) {
        // Update active state
        document.querySelectorAll('.scenario-item').forEach(item => {
            item.classList.remove('active');
        });
        event.target.closest('.scenario-item').classList.add('active');

        this.currentScenario = scenario;
        this.renderVisualization();
    }

    renderVisualization() {
        if (!this.currentScenario) return;

        const diagram = document.getElementById('flow-diagram');
        diagram.innerHTML = '';

        if (this.viewMode === 'tree') {
            this.renderTreeView(diagram);
        } else {
            this.renderGraphView(diagram);
        }
    }

    renderTreeView(container) {
        const width = container.clientWidth;
        const height = 600;

        const svg = d3.select(container)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Define arrow marker
        svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '-0 -5 10 10')
            .attr('refX', 13)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
            .attr('fill', '#64748b')
            .style('stroke', 'none');

        const g = svg.append('g')
            .attr('transform', 'translate(40,40)');

        // Create tree layout
        const tree = d3.tree()
            .size([height - 80, width - 80]);

        const root = d3.hierarchy(this.currentScenario.flow_tree);
        tree(root);

        // Draw links
        const links = g.selectAll('.flow-link')
            .data(root.links())
            .enter().append('path')
            .attr('class', 'flow-link')
            .attr('d', d3.linkHorizontal()
                .x(d => d.y)
                .y(d => d.x));

        // Draw nodes
        const nodes = g.selectAll('.node')
            .data(root.descendants())
            .enter().append('g')
            .attr('class', 'node')
            .attr('transform', d => `translate(${d.y},${d.x})`);

        nodes.append('rect')
            .attr('class', 'flow-node')
            .attr('x', -60)
            .attr('y', -15)
            .attr('width', 120)
            .attr('height', 30)
            .attr('rx', 5)
            .style('fill', d => this.getNodeColor(d.data.type))
            .on('click', (event, d) => this.showNodeDetails(d.data));

        nodes.append('text')
            .attr('class', 'flow-text') 
            .attr('dy', '0.35em')
            .text(d => d.data.display_name)
            .style('font-size', '11px');

        // Add complexity indicators
        nodes.append('circle')
            .attr('cx', 65)
            .attr('cy', 0)
            .attr('r', 8)
            .style('fill', d => this.getComplexityColor(d.data.complexity))
            .style('stroke', '#1e293b')
            .style('stroke-width', 1);

        nodes.append('text')
            .attr('x', 65)
            .attr('y', 0)
            .attr('dy', '0.35em')
            .style('text-anchor', 'middle')
            .style('font-size', '10px')
            .style('fill', '#1e293b')
            .text(d => d.data.complexity);
    }

    renderGraphView(container) {
        // Simplified graph view - in practice you'd use force-directed layout
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #94a3b8;">
                <h4>Graph View</h4>
                <p>Force-directed graph visualization would go here</p>
                <p>Showing function relationships and data flow patterns</p>
            </div>
        `;
    }

    getNodeColor(type) {
        const colors = {
            'api_endpoint': '#3b82f6',
            'database': '#10b981',
            'external': '#f59e0b',
            'business_logic': '#8b5cf6'
        };
        return colors[type] || '#64748b';
    }

    getComplexityColor(complexity) {
        if (complexity <= 2) return '#10b981';
        if (complexity <= 3) return '#f59e0b';
        return '#ef4444';
    }

    showNodeDetails(nodeData) {
        // In a real app, this would show detailed information about the function
        alert(`Function: ${nodeData.display_name}\nType: ${nodeData.type}\nComplexity: ${nodeData.complexity}`);
    }

    showError(message) {
        const diagram = document.getElementById('flow-diagram');
        diagram.innerHTML = `<div class="error">${message}</div>`;
    }
}

// Global functions
function toggleView(mode) {
    window.dashboard.viewMode = mode;
    
    // Update button states
    document.querySelectorAll('.btn').forEach(btn => {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-secondary');
    });
    
    event.target.classList.remove('btn-secondary');
    event.target.classList.add('btn-primary');
    
    if (window.dashboard.currentScenario) {
        window.dashboard.renderVisualization();
    }
}

function exportDiagram() {
    if (!window.dashboard.currentScenario) {
        alert('Please select a scenario first');
        return;
    }
    
    // In a real app, this would export the diagram as SVG/PNG
    const data = JSON.stringify(window.dashboard.currentScenario, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'flow-scenario.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Initialize dashboard when page loads
window.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new FlowDashboard();
});