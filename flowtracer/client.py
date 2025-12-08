import asyncio
import time
from typing import Dict, List, Optional, Any
from supabase import create_client, Client
import openai
from threading import Lock


class FlowClient:
    def __init__(self, supabase_url: str, supabase_key: str, openai_api_key: str):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        
        # Cache for AI-generated names
        self._name_cache: Dict[str, str] = {}
        self._cache_lock = Lock()
        self._pending_names: List[str] = []
        self._batch_size = 10
    
    def create_flow(self, flow_data: Dict[str, Any]):
        """Create a new flow in Supabase"""
        try:
            self.supabase.table('flows').insert(flow_data).execute()
        except Exception as e:
            print(f"Error creating flow: {e}")
    
    def complete_flow(self, flow_id: str, completed_at: float):
        """Mark flow as completed"""
        try:
            self.supabase.table('flows').update({
                'completed_at': completed_at
            }).eq('id', flow_id).execute()
        except Exception as e:
            print(f"Error completing flow: {e}")
    
    def create_step(self, step_data: Dict[str, Any]):
        """Create a new step and get AI-generated display name"""
        function_name = step_data['function_name']
        
        # Get or generate display name
        display_name = self._get_display_name(function_name)
        step_data['display_name'] = display_name
        
        try:
            self.supabase.table('flow_steps').insert(step_data).execute()
        except Exception as e:
            print(f"Error creating step: {e}")
    
    def complete_step(self, step_id: str, completed_at: float, error: Optional[str] = None):
        """Mark step as completed"""
        try:
            update_data = {'completed_at': completed_at}
            if error:
                update_data['error'] = error
                
            self.supabase.table('flow_steps').update(update_data).eq('id', step_id).execute()
        except Exception as e:
            print(f"Error completing step: {e}")
    
    def _get_display_name(self, function_name: str) -> str:
        """Get AI-generated display name for function, with caching"""
        with self._cache_lock:
            # Check cache first
            if function_name in self._name_cache:
                return self._name_cache[function_name]
            
            # Add to pending batch
            if function_name not in self._pending_names:
                self._pending_names.append(function_name)
            
            # Process batch if full
            if len(self._pending_names) >= self._batch_size:
                self._process_name_batch()
            
            # Return cached name or fallback
            return self._name_cache.get(function_name, self._humanize_function_name(function_name))
    
    def _process_name_batch(self):
        """Process a batch of function names with OpenAI"""
        if not self._pending_names:
            return
        
        try:
            # Prepare prompt
            functions_list = "\n".join([f"- {name}" for name in self._pending_names])
            prompt = f"""Convert these technical function names into 2-3 word human-readable descriptions:

{functions_list}

Rules:
- Keep it simple and clear
- 2-3 words maximum
- Focus on what the function does
- Examples: "validate_user_input" → "Validate Input", "send_email_notification" → "Send Email"

Format as: function_name → Description"""

            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            # Parse response and update cache
            content = response.choices[0].message.content
            self._parse_ai_response(content)
            
        except Exception as e:
            print(f"Error getting AI names: {e}")
            # Fallback to humanized names
            for name in self._pending_names:
                if name not in self._name_cache:
                    self._name_cache[name] = self._humanize_function_name(name)
        
        finally:
            self._pending_names.clear()
    
    def _parse_ai_response(self, content: str):
        """Parse OpenAI response and update name cache"""
        lines = content.strip().split('\n')
        for line in lines:
            if '→' in line:
                parts = line.split('→')
                if len(parts) == 2:
                    original = parts[0].strip().replace('- ', '')
                    readable = parts[1].strip()
                    self._name_cache[original] = readable
    
    def _humanize_function_name(self, function_name: str) -> str:
        """Fallback function to humanize function names without AI"""
        # Remove common prefixes/suffixes
        name = function_name.replace('_async', '').replace('_sync', '')
        
        # Split on underscores and capitalize
        words = name.split('_')
        return ' '.join(word.capitalize() for word in words)
    
    def flush_pending_names(self):
        """Force process any pending names (useful for end of request)"""
        with self._cache_lock:
            if self._pending_names:
                self._process_name_batch()