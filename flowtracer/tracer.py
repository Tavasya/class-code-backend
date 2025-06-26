import functools
import uuid
import time
import threading
import asyncio
from typing import Any, Optional, Dict, List
from contextlib import contextmanager
from .client import FlowClient


class FlowTracer:
    def __init__(self, 
                 supabase_url: str, 
                 supabase_key: str, 
                 openai_api_key: str,
                 enabled: bool = True):
        self.client = FlowClient(supabase_url, supabase_key, openai_api_key)
        self.enabled = enabled
        self._current_flow = threading.local()
        self._step_stack = threading.local()
    
    @contextmanager
    def start_flow(self, request_id: str, endpoint: str):
        """Start a new flow session for tracking data through your system"""
        if not self.enabled:
            yield None
            return
            
        flow_id = str(uuid.uuid4())
        flow_data = {
            'id': flow_id,
            'request_id': request_id,
            'endpoint': endpoint,
            'started_at': time.time()
        }
        
        # Store flow context
        self._current_flow.flow_id = flow_id
        self._current_flow.data = flow_data
        if not hasattr(self._step_stack, 'stack'):
            self._step_stack.stack = []
        
        # Send to Supabase
        self.client.create_flow(flow_data)
        
        try:
            yield flow_id
        finally:
            # End flow
            flow_data['completed_at'] = time.time()
            self.client.complete_flow(flow_id, flow_data['completed_at'])
            
            # Clean up thread local
            if hasattr(self._current_flow, 'flow_id'):
                delattr(self._current_flow, 'flow_id')

    def trace(self, name: Optional[str] = None):
        """Decorator to trace function calls in your data flow"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled or not hasattr(self._current_flow, 'flow_id'):
                    return func(*args, **kwargs)
                
                return self._trace_sync(func, name or func.__name__, args, kwargs)
            
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enabled or not hasattr(self._current_flow, 'flow_id'):
                    return await func(*args, **kwargs)
                
                return await self._trace_async(func, name or func.__name__, args, kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
        return decorator
    
    def _trace_sync(self, func, name: str, args, kwargs):
        step_id = str(uuid.uuid4())
        parent_id = self._get_parent_step_id()
        
        step_data = {
            'id': step_id,
            'flow_id': self._current_flow.flow_id,
            'function_name': name,
            'parent_step_id': parent_id,
            'thread_id': threading.get_ident(),
            'started_at': time.time()
        }
        
        self._step_stack.stack.append(step_id)
        self.client.create_step(step_data)
        
        try:
            result = func(*args, **kwargs)
            step_data['completed_at'] = time.time()
            self.client.complete_step(step_id, step_data['completed_at'])
            return result
        except Exception as e:
            step_data['completed_at'] = time.time()
            step_data['error'] = str(e)
            self.client.complete_step(step_id, step_data['completed_at'], str(e))
            raise
        finally:
            self._step_stack.stack.pop()
    
    async def _trace_async(self, func, name: str, args, kwargs):
        step_id = str(uuid.uuid4())
        parent_id = self._get_parent_step_id()
        
        step_data = {
            'id': step_id,
            'flow_id': self._current_flow.flow_id,
            'function_name': name,
            'parent_step_id': parent_id,
            'thread_id': threading.get_ident(),
            'task_id': id(asyncio.current_task()),
            'started_at': time.time()
        }
        
        self._step_stack.stack.append(step_id)
        self.client.create_step(step_data)
        
        try:
            result = await func(*args, **kwargs)
            step_data['completed_at'] = time.time()
            self.client.complete_step(step_id, step_data['completed_at'])
            return result
        except Exception as e:
            step_data['completed_at'] = time.time()
            step_data['error'] = str(e)
            self.client.complete_step(step_id, step_data['completed_at'], str(e))
            raise
        finally:
            self._step_stack.stack.pop()
    
    def _get_parent_step_id(self) -> Optional[str]:
        if hasattr(self._step_stack, 'stack') and self._step_stack.stack:
            return self._step_stack.stack[-1]
        return None


# Global tracer instance
_tracer: Optional[FlowTracer] = None

def init_tracer(supabase_url: str, supabase_key: str, openai_api_key: str, enabled: bool = True):
    """Initialize the global flow tracer"""
    global _tracer
    _tracer = FlowTracer(supabase_url, supabase_key, openai_api_key, enabled)

def trace_flow(name: Optional[str] = None):
    """Convenient decorator using global tracer"""
    if _tracer is None:
        raise RuntimeError("FlowTracer not initialized. Call init_tracer() first.")
    return _tracer.trace(name)

def start_flow(request_id: str, endpoint: str):
    """Start a flow using global tracer"""
    if _tracer is None:
        raise RuntimeError("FlowTracer not initialized. Call init_tracer() first.")
    return _tracer.start_flow(request_id, endpoint)