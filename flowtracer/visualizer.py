import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from .analyzer import CodebaseMap, FunctionInfo
from .client import FlowClient
import openai


class FlowVisualizer:
    def __init__(self, codebase_map: CodebaseMap, openai_api_key: str):
        self.codebase_map = codebase_map
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
    
    def generate_flow_scenarios(self) -> List[Dict[str, Any]]:
        """Generate likely data flow scenarios using AI"""
        scenarios = []
        
        # For each entry point, trace potential paths
        for entry_point in self.codebase_map.entry_points:
            scenario = self._trace_flow_from_entry_point(entry_point)
            if scenario:
                scenarios.append(scenario)
        
        # Enhance scenarios with AI understanding
        enhanced_scenarios = self._enhance_scenarios_with_ai(scenarios)
        
        return enhanced_scenarios
    
    def _trace_flow_from_entry_point(self, entry_point: str) -> Optional[Dict[str, Any]]:
        """Trace data flow from an entry point"""
        if entry_point not in self.codebase_map.functions:
            return None
        
        entry_func = self.codebase_map.functions[entry_point]
        
        # Build flow tree using BFS
        flow_tree = self._build_flow_tree(entry_point)
        
        # Identify data transformations
        data_flow = self._identify_data_transformations(flow_tree)
        
        return {
            'id': entry_point,
            'name': getattr(entry_func, 'display_name', entry_func.name),
            'entry_point': entry_point,
            'flow_tree': flow_tree,
            'data_flow': data_flow,
            'estimated_complexity': self._calculate_flow_complexity(flow_tree),
            'potential_bottlenecks': self._identify_bottlenecks(flow_tree)
        }
    
    def _build_flow_tree(self, start_function: str, max_depth: int = 5) -> Dict[str, Any]:
        """Build a tree of function calls starting from a function"""
        if max_depth <= 0 or start_function not in self.codebase_map.functions:
            return {}
        
        func_info = self.codebase_map.functions[start_function]
        
        tree = {
            'name': start_function,
            'display_name': getattr(func_info, 'display_name', func_info.name),
            'type': self._get_function_type(func_info),
            'complexity': func_info.complexity_score,
            'file': func_info.file_path,
            'line': func_info.line_number,
            'children': []
        }
        
        # Add children (functions this function calls)
        if start_function in self.codebase_map.call_graph:
            for called_func in self.codebase_map.call_graph[start_function]:
                if called_func in self.codebase_map.functions:
                    child_tree = self._build_flow_tree(called_func, max_depth - 1)
                    if child_tree:
                        tree['children'].append(child_tree)
        
        return tree
    
    def _get_function_type(self, func_info: FunctionInfo) -> str:
        """Classify function type for visualization"""
        if func_info.is_api_endpoint:
            return 'api_endpoint'
        elif func_info.is_database_related:
            return 'database'
        elif func_info.is_external_call:
            return 'external'
        else:
            return 'business_logic'
    
    def _identify_data_transformations(self, flow_tree: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify likely data transformation steps"""
        transformations = []
        
        def extract_transformations(node, path=[]):
            current_path = path + [node.get('display_name', node.get('name', 'Unknown'))]
            
            node_type = node.get('type', 'business_logic')
            if node_type in ['database', 'external', 'api_endpoint']:
                transformations.append({
                    'step': len(transformations) + 1,
                    'action': node.get('display_name', node.get('name')),
                    'type': node_type,
                    'path': ' → '.join(current_path)
                })
            
            for child in node.get('children', []):
                extract_transformations(child, current_path)
        
        extract_transformations(flow_tree)
        return transformations
    
    def _calculate_flow_complexity(self, flow_tree: Dict[str, Any]) -> int:
        """Calculate estimated complexity of the flow"""
        def sum_complexity(node):
            complexity = node.get('complexity', 1)
            for child in node.get('children', []):
                complexity += sum_complexity(child)
            return complexity
        
        return sum_complexity(flow_tree)
    
    def _identify_bottlenecks(self, flow_tree: Dict[str, Any]) -> List[str]:
        """Identify potential bottlenecks in the flow"""
        bottlenecks = []
        
        def find_bottlenecks(node, depth=0):
            # Functions with high complexity
            if node.get('complexity', 0) >= 4:
                bottlenecks.append(f"High complexity: {node.get('display_name')}")
            
            # Database operations (potentially slow)
            if node.get('type') == 'database':
                bottlenecks.append(f"Database operation: {node.get('display_name')}")
            
            # External calls (network latency)
            if node.get('type') == 'external':
                bottlenecks.append(f"External call: {node.get('display_name')}")
            
            # Deep nesting (complex flow)
            if depth > 3:
                bottlenecks.append(f"Deep nesting: {node.get('display_name')}")
            
            for child in node.get('children', []):
                find_bottlenecks(child, depth + 1)
        
        find_bottlenecks(flow_tree)
        return bottlenecks
    
    def _enhance_scenarios_with_ai(self, scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use AI to add business context to scenarios"""
        for scenario in scenarios:
            try:
                # Prepare scenario summary for AI
                transformations = scenario.get('data_flow', [])
                flow_summary = ' → '.join([t['action'] for t in transformations])
                
                prompt = f"""Analyze this code flow and provide business context:

Flow: {flow_summary}

Entry Point: {scenario.get('name', 'Unknown')}
Transformations: {len(transformations)} steps
Complexity: {scenario.get('estimated_complexity', 0)}

Provide:
1. Business purpose (1 sentence)
2. User-friendly flow description
3. Potential issues or improvements

Format as JSON: {{"purpose": "...", "description": "...", "suggestions": ["..."]}}"""

                response = self.openai_client.chat.completions.create(
                    model="gpt-5-nano",
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=200
                )
                
                ai_analysis = json.loads(response.choices[0].message.content)
                scenario.update({
                    'business_purpose': ai_analysis.get('purpose', 'Unknown purpose'),
                    'user_description': ai_analysis.get('description', 'No description'),
                    'suggestions': ai_analysis.get('suggestions', [])
                })
                
            except Exception as e:
                print(f"AI enhancement failed for scenario: {e}")
                scenario.update({
                    'business_purpose': 'Analysis not available',
                    'user_description': flow_summary,
                    'suggestions': []
                })
        
        return scenarios
    
    def export_for_dashboard(self, output_path: str):
        """Export visualization data for web dashboard"""
        scenarios = self.generate_flow_scenarios()
        
        dashboard_data = {
            'metadata': {
                'total_functions': len(self.codebase_map.functions),
                'entry_points': len(self.codebase_map.entry_points),
                'scenarios': len(scenarios)
            },
            'scenarios': scenarios,
            'functions': {
                name: {
                    'name': func.name,
                    'display_name': getattr(func, 'display_name', func.name),
                    'file': func.file_path,
                    'line': func.line_number,
                    'type': self._get_function_type(func),
                    'complexity': func.complexity_score
                }
                for name, func in self.codebase_map.functions.items()
            },
            'call_graph': self.codebase_map.call_graph
        }
        
        with open(output_path, 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        print(f"📊 Dashboard data exported to {output_path}")
        return dashboard_data
    
    def generate_mermaid_diagram(self, scenario_id: str) -> str:
        """Generate Mermaid diagram for a specific scenario"""
        scenario = None
        scenarios = self.generate_flow_scenarios()
        
        for s in scenarios:
            if s['id'] == scenario_id:
                scenario = s
                break
        
        if not scenario:
            return "Scenario not found"
        
        mermaid = ["graph TD"]
        
        def add_node_to_mermaid(node, parent_id=None):
            node_id = node['name'].replace('.', '_').replace(' ', '_')
            node_type = node.get('type', 'business_logic')
            
            # Style based on type
            if node_type == 'api_endpoint':
                shape = f"{node_id}[🌐 {node.get('display_name', node['name'])}]"
            elif node_type == 'database':
                shape = f"{node_id}[💾 {node.get('display_name', node['name'])}]"
            elif node_type == 'external':
                shape = f"{node_id}[🔗 {node.get('display_name', node['name'])}]"
            else:
                shape = f"{node_id}[⚙️ {node.get('display_name', node['name'])}]"
            
            mermaid.append(f"    {shape}")
            
            if parent_id:
                mermaid.append(f"    {parent_id} --> {node_id}")
            
            for child in node.get('children', []):
                add_node_to_mermaid(child, node_id)
        
        add_node_to_mermaid(scenario['flow_tree'])
        
        return '\n'.join(mermaid)