import ast
import os
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
import json
from dataclasses import dataclass, asdict
from collections import defaultdict
import openai


@dataclass
class FunctionInfo:
    name: str
    full_name: str  # module.class.function
    file_path: str
    line_number: int
    class_name: Optional[str] = None
    is_async: bool = False
    parameters: List[str] = None
    calls: List[str] = None  # Functions this function calls
    called_by: List[str] = None  # Functions that call this
    docstring: Optional[str] = None
    complexity_score: int = 0
    is_api_endpoint: bool = False
    is_database_related: bool = False
    is_external_call: bool = False


@dataclass
class CodebaseMap:
    functions: Dict[str, FunctionInfo]
    call_graph: Dict[str, List[str]]  # function -> list of functions it calls
    reverse_call_graph: Dict[str, List[str]]  # function -> list of functions that call it
    entry_points: List[str]  # API endpoints, main functions
    data_sources: List[str]  # Database/file/API reading functions
    data_sinks: List[str]  # Database/file/API writing functions


class CodebaseAnalyzer:
    def __init__(self, project_root: str, openai_api_key: str):
        self.project_root = Path(project_root)
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.functions: Dict[str, FunctionInfo] = {}
        self.call_graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_call_graph: Dict[str, List[str]] = defaultdict(list)
        
        # Patterns to identify special function types
        self.api_patterns = ['route', 'endpoint', 'api', 'post', 'get', 'put', 'delete']
        self.db_patterns = ['query', 'select', 'insert', 'update', 'delete', 'save', 'create', 'find']
        self.external_patterns = ['request', 'fetch', 'call', 'send', 'http', 'client']
    
    def analyze_codebase(self) -> CodebaseMap:
        """Main entry point - analyze entire codebase"""
        print("🔍 Scanning codebase...")
        self._scan_python_files()
        
        print("🧠 Analyzing with AI...")
        self._enhance_with_ai()
        
        print("📊 Building call graph...")
        self._build_call_graphs()
        
        print("🎯 Identifying entry points...")
        entry_points = self._find_entry_points()
        
        print("💾 Finding data sources/sinks...")
        data_sources, data_sinks = self._find_data_flow_points()
        
        return CodebaseMap(
            functions=self.functions,
            call_graph=dict(self.call_graph),
            reverse_call_graph=dict(self.reverse_call_graph),
            entry_points=entry_points,
            data_sources=data_sources,
            data_sinks=data_sinks
        )
    
    def _scan_python_files(self):
        """Scan all Python files and extract function information"""
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            # Skip common non-source directories
            if any(part in file_path.parts for part in ['.venv', 'venv', '__pycache__', '.git', 'node_modules']):
                continue
                
            try:
                self._analyze_file(file_path)
            except Exception as e:
                print(f"⚠️  Error analyzing {file_path}: {e}")
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file using AST"""
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                content = f.read()
                tree = ast.parse(content)
            except SyntaxError:
                return  # Skip files with syntax errors
        
        visitor = FunctionVisitor(str(file_path), str(file_path.relative_to(self.project_root)))
        visitor.visit(tree)
        
        # Add functions to our collection
        for func_info in visitor.functions:
            self.functions[func_info.full_name] = func_info
    
    def _enhance_with_ai(self):
        """Use AI to better understand function purposes and relationships"""
        # Group functions for batch processing
        function_batches = [list(self.functions.values())[i:i+20] 
                          for i in range(0, len(self.functions), 20)]
        
        for batch in function_batches:
            self._analyze_function_batch_with_ai(batch)
    
    def _analyze_function_batch_with_ai(self, functions: List[FunctionInfo]):
        """Analyze a batch of functions with AI to understand their purpose"""
        try:
            # Prepare function descriptions
            func_descriptions = []
            for func in functions:
                desc = f"- {func.full_name}({', '.join(func.parameters or [])})"
                if func.docstring:
                    desc += f" # {func.docstring[:100]}"
                func_descriptions.append(desc)
            
            prompt = f"""Analyze these Python functions and classify them:

{chr(10).join(func_descriptions)}

For each function, determine:
1. Human-readable purpose (2-3 words)
2. Category: API_ENDPOINT, DATABASE, EXTERNAL_CALL, BUSINESS_LOGIC, UTILITY
3. Complexity (1-5, where 5 is most complex)

Format as JSON:
{{"function_name": {{"purpose": "...", "category": "...", "complexity": 3}}}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.1
            )
            
            # Parse AI response and update function info
            try:
                ai_analysis = json.loads(response.choices[0].message.content)
                for func in functions:
                    if func.full_name in ai_analysis:
                        analysis = ai_analysis[func.full_name]
                        func.display_name = analysis.get('purpose', func.name)
                        func.complexity_score = analysis.get('complexity', 1)
                        
                        category = analysis.get('category', '')
                        func.is_api_endpoint = category == 'API_ENDPOINT'
                        func.is_database_related = category == 'DATABASE'
                        func.is_external_call = category == 'EXTERNAL_CALL'
            except:
                # Fallback if AI response is malformed
                for func in functions:
                    func.display_name = self._generate_display_name(func.name)
                    
        except Exception as e:
            print(f"AI analysis failed: {e}")
            # Fallback to rule-based classification
            for func in functions:
                func.display_name = self._generate_display_name(func.name)
                self._classify_function_by_rules(func)
    
    def _generate_display_name(self, func_name: str) -> str:
        """Generate human-readable name from function name"""
        # Split on underscores and capitalize
        words = func_name.split('_')
        return ' '.join(word.capitalize() for word in words)
    
    def _classify_function_by_rules(self, func: FunctionInfo):
        """Rule-based function classification as fallback"""
        name_lower = func.name.lower()
        
        func.is_api_endpoint = any(pattern in name_lower for pattern in self.api_patterns)
        func.is_database_related = any(pattern in name_lower for pattern in self.db_patterns)
        func.is_external_call = any(pattern in name_lower for pattern in self.external_patterns)
        
        # Simple complexity based on number of calls
        func.complexity_score = min(len(func.calls or []) + 1, 5)
    
    def _build_call_graphs(self):
        """Build function call relationships"""
        for func_name, func_info in self.functions.items():
            if func_info.calls:
                for called_func in func_info.calls:
                    self.call_graph[func_name].append(called_func)
                    self.reverse_call_graph[called_func].append(func_name)
    
    def _find_entry_points(self) -> List[str]:
        """Find likely entry points (API endpoints, main functions)"""
        entry_points = []
        
        for func_name, func_info in self.functions.items():
            # API endpoints
            if func_info.is_api_endpoint:
                entry_points.append(func_name)
            
            # Main functions
            elif func_info.name in ['main', 'run', 'start', 'handler']:
                entry_points.append(func_name)
            
            # Functions with no callers (potential entry points)
            elif func_name not in self.reverse_call_graph:
                entry_points.append(func_name)
        
        return entry_points
    
    def _find_data_flow_points(self) -> Tuple[List[str], List[str]]:
        """Find functions that read/write data"""
        data_sources = []
        data_sinks = []
        
        for func_name, func_info in self.functions.items():
            if func_info.is_database_related:
                name_lower = func_info.name.lower()
                if any(pattern in name_lower for pattern in ['select', 'get', 'find', 'read', 'fetch']):
                    data_sources.append(func_name)
                elif any(pattern in name_lower for pattern in ['insert', 'create', 'save', 'update', 'delete', 'write']):
                    data_sinks.append(func_name)
        
        return data_sources, data_sinks


class FunctionVisitor(ast.NodeVisitor):
    """AST visitor to extract function information"""
    
    def __init__(self, file_path: str, relative_path: str):
        self.file_path = file_path
        self.relative_path = relative_path
        self.functions: List[FunctionInfo] = []
        self.current_class = None
        self.module_name = relative_path.replace('/', '.').replace('.py', '')
    
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node):
        self._process_function(node, is_async=False)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        self._process_function(node, is_async=True)
        self.generic_visit(node)
    
    def _process_function(self, node, is_async: bool):
        # Build full function name
        if self.current_class:
            full_name = f"{self.module_name}.{self.current_class}.{node.name}"
        else:
            full_name = f"{self.module_name}.{node.name}"
        
        # Extract parameters
        parameters = [arg.arg for arg in node.args.args]
        
        # Extract docstring
        docstring = None
        if (node.body and isinstance(node.body[0], ast.Expr) 
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        # Find function calls within this function
        call_visitor = CallVisitor()
        for child in node.body:
            call_visitor.visit(child)
        
        func_info = FunctionInfo(
            name=node.name,
            full_name=full_name,
            file_path=self.file_path,
            line_number=node.lineno,
            class_name=self.current_class,
            is_async=is_async,
            parameters=parameters,
            calls=call_visitor.calls,
            docstring=docstring
        )
        
        self.functions.append(func_info)


class CallVisitor(ast.NodeVisitor):
    """Visitor to extract function calls within a function"""
    
    def __init__(self):
        self.calls = []
    
    def visit_Call(self, node):
        # Extract function name from call
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Handle method calls like obj.method()
            if isinstance(node.func.value, ast.Name):
                self.calls.append(f"{node.func.value.id}.{node.func.attr}")
            else:
                self.calls.append(node.func.attr)
        
        self.generic_visit(node)