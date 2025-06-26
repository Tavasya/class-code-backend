"""
Auto-tracer that combines static analysis with runtime tracing
"""

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional
from .tracer import FlowTracer
from .analyzer import CodebaseAnalyzer


class AutoTracer:
    """Automatically injects tracing into your codebase based on static analysis"""
    
    def __init__(self, project_root: str, supabase_url: str, supabase_key: str, openai_api_key: str):
        self.project_root = Path(project_root)
        self.tracer = FlowTracer(supabase_url, supabase_key, openai_api_key)
        self.analyzer = CodebaseAnalyzer(project_root, openai_api_key)
        self.instrumented_functions: Set[str] = set()
    
    def auto_instrument_codebase(self, 
                                entry_points_only: bool = True,
                                exclude_patterns: List[str] = None) -> Dict[str, int]:
        """Automatically add tracing to important functions in your codebase"""
        
        exclude_patterns = exclude_patterns or [
            '__pycache__', '.venv', 'venv', '.git', 'node_modules',
            'test_', '_test', 'tests/', '/tests'
        ]
        
        print("🔍 Analyzing codebase for auto-instrumentation...")
        codebase_map = self.analyzer.analyze_codebase()
        
        # Determine which functions to instrument
        functions_to_instrument = self._select_functions_for_tracing(
            codebase_map, entry_points_only
        )
        
        print(f"🎯 Selected {len(functions_to_instrument)} functions for instrumentation")
        
        # Group by file for efficient processing
        files_to_modify = {}
        for func_name in functions_to_instrument:
            func_info = codebase_map.functions[func_name]
            file_path = func_info.file_path
            
            if file_path not in files_to_modify:
                files_to_modify[file_path] = []
            files_to_modify[file_path].append(func_info)
        
        # Instrument each file
        instrumented_count = 0
        for file_path, functions in files_to_modify.items():
            if self._should_skip_file(file_path, exclude_patterns):
                continue
                
            try:
                count = self._instrument_file(file_path, functions)
                instrumented_count += count
                print(f"✅ Instrumented {count} functions in {file_path}")
            except Exception as e:
                print(f"⚠️  Failed to instrument {file_path}: {e}")
        
        return {
            'total_functions': len(codebase_map.functions),
            'selected_for_tracing': len(functions_to_instrument),
            'successfully_instrumented': instrumented_count,
            'files_modified': len(files_to_modify)
        }
    
    def _select_functions_for_tracing(self, codebase_map, entry_points_only: bool) -> List[str]:
        """Select which functions should be traced"""
        functions_to_instrument = []
        
        if entry_points_only:
            # Only instrument entry points and their immediate children
            for entry_point in codebase_map.entry_points:
                functions_to_instrument.append(entry_point)
                
                # Add direct children of entry points
                if entry_point in codebase_map.call_graph:
                    for called_func in codebase_map.call_graph[entry_point]:
                        if called_func in codebase_map.functions:
                            functions_to_instrument.append(called_func)
        else:
            # Instrument all important functions
            for func_name, func_info in codebase_map.functions.items():
                # Skip trivial functions
                if func_info.complexity_score < 2:
                    continue
                
                # Include API endpoints, database operations, external calls
                if (func_info.is_api_endpoint or 
                    func_info.is_database_related or 
                    func_info.is_external_call):
                    functions_to_instrument.append(func_name)
                
                # Include functions with high complexity
                elif func_info.complexity_score >= 3:
                    functions_to_instrument.append(func_name)
        
        return list(set(functions_to_instrument))  # Remove duplicates
    
    def _should_skip_file(self, file_path: str, exclude_patterns: List[str]) -> bool:
        """Check if file should be skipped based on patterns"""
        for pattern in exclude_patterns:
            if pattern in file_path:
                return True
        return False
    
    def _instrument_file(self, file_path: str, functions: List) -> int:
        """Add tracing decorators to functions in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Parse the AST
            tree = ast.parse(original_content)
            
            # Find functions to instrument
            instrumenter = FunctionInstrumenter(functions)
            new_tree = instrumenter.visit(tree)
            
            # Generate new code
            new_content = ast.unparse(new_tree)
            
            # Add import at the top if needed
            if instrumenter.needs_import:
                import_line = "from flowtracer import trace_flow\n"
                if not import_line.strip() in new_content:
                    new_content = import_line + new_content
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return instrumenter.instrumented_count
            
        except Exception as e:
            print(f"Error instrumenting {file_path}: {e}")
            return 0
    
    def create_instrumented_copy(self, output_dir: str = "./instrumented_code"):
        """Create a copy of your codebase with tracing added (safer option)"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Copy entire project structure
        import shutil
        shutil.copytree(self.project_root, output_path, dirs_exist_ok=True)
        
        # Now instrument the copy
        auto_tracer = AutoTracer(
            str(output_path),
            self.tracer.client.supabase.url,
            self.tracer.client.supabase.auth.api_key,
            self.tracer.client.openai_client.api_key
        )
        
        results = auto_tracer.auto_instrument_codebase()
        
        print(f"🎉 Instrumented copy created at: {output_path}")
        return results


class FunctionInstrumenter(ast.NodeTransformer):
    """AST transformer to add tracing decorators to functions"""
    
    def __init__(self, functions_to_instrument):
        self.functions_to_instrument = {f.name for f in functions_to_instrument}
        self.instrumented_count = 0
        self.needs_import = False
        self.current_class = None
    
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        return node
    
    def visit_FunctionDef(self, node):
        return self._instrument_function(node)
    
    def visit_AsyncFunctionDef(self, node):
        return self._instrument_function(node)
    
    def _instrument_function(self, node):
        # Check if this function should be instrumented
        if node.name in self.functions_to_instrument:
            # Check if already has trace_flow decorator
            has_trace_decorator = any(
                isinstance(decorator, ast.Name) and decorator.id == 'trace_flow'
                for decorator in node.decorator_list
            )
            
            if not has_trace_decorator:
                # Add trace_flow decorator
                trace_decorator = ast.Name(id='trace_flow', ctx=ast.Load())
                trace_call = ast.Call(func=trace_decorator, args=[], keywords=[])
                
                node.decorator_list.append(trace_call)
                self.instrumented_count += 1
                self.needs_import = True
        
        return node


def create_auto_tracer(project_root: str, 
                      supabase_url: str, 
                      supabase_key: str, 
                      openai_api_key: str) -> AutoTracer:
    """Factory function to create an AutoTracer instance"""
    return AutoTracer(project_root, supabase_url, supabase_key, openai_api_key)