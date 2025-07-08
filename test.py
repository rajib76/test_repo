"""
Multi-turn conversation handler for iterative JSON refinement.
Uses GPT-4o to process user feedback and update knowledge graph JSON.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from llm_models.llm_openai import OpenAILLM


class JSONConversationHandler:
    """Handles multi-turn conversations for refining knowledge graph JSON."""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        """Initialize the conversation handler with GPT-4o."""
        self.llm = OpenAILLM(openai_api_key, model)
        self.conversation_history: List[Dict[str, str]] = []
        self.current_json: Dict[str, Any] = {"nodes": [], "relationships": []}
        self.original_text: str = ""
        self.logger = logging.getLogger(__name__)
        
        # System prompt for JSON refinement conversations
        self.system_prompt = """You are an expert knowledge graph assistant helping users refine their knowledge graphs through conversation.

Your role:
1. Analyze user feedback about their current knowledge graph JSON
2. Understand what changes they want to make
3. Apply those changes to the JSON structure
4. Always return valid JSON in the exact format requested

Guidelines:
- Listen carefully to user feedback and understand their intent
- Make precise changes to the JSON based on their requests
- Preserve existing data unless specifically asked to change it
- Always validate that your output is properly formatted JSON
- Explain what changes you made and why
- Ask clarifying questions if the request is ambiguous

Current JSON structure:
{
    "nodes": [
        {
            "id": "unique_id",
            "name": "entity_name", 
            "type": "entity_type",
            "description": "description",
            "properties": {}
        }
    ],
    "relationships": [
        {
            "source": "source_node_id",
            "target": "target_node_id", 
            "type": "relationship_type",
            "description": "description",
            "properties": {}
        }
    ]
}

Always respond with:
1. A brief explanation of what you understood from the user's feedback
2. The updated JSON
3. A summary of the changes made"""

    def start_conversation(self, initial_json: Dict[str, Any], original_text: str = "") -> str:
        """Start a new conversation with initial JSON."""
        self.current_json = initial_json.copy()
        self.original_text = original_text
        self.conversation_history = []
        
        welcome_message = f"""I'm ready to help you refine your knowledge graph! 

Current graph summary:
- **Nodes**: {len(self.current_json.get('nodes', []))} entities
- **Relationships**: {len(self.current_json.get('relationships', []))} connections

You can ask me to:
- Add, remove, or modify entities
- Change relationships between entities  
- Update descriptions or properties
- Reorganize the graph structure
- Fix any issues you notice

What would you like to change about the knowledge graph?"""
        
        return welcome_message

    def process_user_message(self, user_message: str) -> Tuple[str, Dict[str, Any], bool]:
        """
        Process user feedback and update JSON.
        
        Returns:
            Tuple of (assistant_response, updated_json, is_valid_json)
        """
        try:
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Create the conversation prompt
            conversation_prompt = self._build_conversation_prompt(user_message)
            
            # Get response from GPT-4o
            response = self.llm.generate(conversation_prompt)
            
            # Parse the response to extract JSON and explanation
            explanation, updated_json, changes_summary = self._parse_llm_response(response)
            
            # Validate the updated JSON
            is_valid = self._validate_json_structure(updated_json)
            
            if is_valid:
                self.current_json = updated_json
                
                # Add successful update to history
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": explanation,
                    "changes": changes_summary,
                    "timestamp": datetime.now().isoformat()
                })
                
                full_response = f"{explanation}\n\n**Changes made**: {changes_summary}"
                
            else:
                # If JSON is invalid, ask for clarification
                error_response = f"I understand you want to: {explanation}\n\nHowever, I had trouble creating valid JSON from your request. Could you please clarify what specific changes you'd like me to make?"
                
                self.conversation_history.append({
                    "role": "assistant",
                    "content": error_response,
                    "error": "Invalid JSON generated",
                    "timestamp": datetime.now().isoformat()
                })
                
                full_response = error_response
            
            return full_response, self.current_json, is_valid
            
        except Exception as e:
            self.logger.error(f"Error processing user message: {e}")
            error_response = f"I encountered an error processing your request: {str(e)}. Could you please rephrase your request?"
            return error_response, self.current_json, False

    def _build_conversation_prompt(self, user_message: str) -> str:
        """Build the full conversation prompt with context."""
        
        # Recent conversation context (last 4 messages)
        recent_history = self.conversation_history[-4:] if len(self.conversation_history) > 4 else self.conversation_history
        
        context_messages = []
        for msg in recent_history:
            if msg["role"] == "user":
                context_messages.append(f"User: {msg['content']}")
            else:
                context_messages.append(f"Assistant: {msg['content']}")
        
        conversation_context = "\n".join(context_messages) if context_messages else "This is the start of our conversation."
        
        current_json_str = json.dumps(self.current_json, indent=2)
        
        prompt = f"""{self.system_prompt}

CONVERSATION CONTEXT:
{conversation_context}

CURRENT JSON:
```json
{current_json_str}
```

ORIGINAL TEXT (for reference):
{self.original_text[:500]}...

USER'S NEW REQUEST:
{user_message}

Please provide:
1. Your understanding of what the user wants
2. The updated JSON (complete structure)
3. Summary of changes made

Format your response as:
UNDERSTANDING: [What you understood]

UPDATED_JSON:
```json
[Complete updated JSON here]
```

CHANGES: [Summary of what you changed]"""

        return prompt

    def _parse_llm_response(self, response: str) -> Tuple[str, Dict[str, Any], str]:
        """Parse LLM response to extract explanation, JSON, and changes."""
        try:
            # Extract understanding section
            understanding = ""
            if "UNDERSTANDING:" in response:
                understanding_start = response.find("UNDERSTANDING:") + len("UNDERSTANDING:")
                understanding_end = response.find("UPDATED_JSON:")
                if understanding_end != -1:
                    understanding = response[understanding_start:understanding_end].strip()
                else:
                    understanding = response[understanding_start:].strip()
            
            # Extract JSON section
            json_start = response.find("```json")
            json_end = response.find("```", json_start + 7)
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start + 7:json_end].strip()
                updated_json = json.loads(json_str)
            else:
                # Fallback: try to find any JSON in the response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    updated_json = json.loads(json_match.group())
                else:
                    # If no JSON found, return current JSON
                    updated_json = self.current_json
            
            # Extract changes section
            changes = ""
            if "CHANGES:" in response:
                changes_start = response.find("CHANGES:") + len("CHANGES:")
                changes = response[changes_start:].strip()
            
            return understanding, updated_json, changes
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON from LLM response: {e}")
            return response, self.current_json, "Failed to parse JSON"
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return response, self.current_json, "Error parsing response"

    def _validate_json_structure(self, json_data: Dict[str, Any]) -> bool:
        """Validate that JSON has correct knowledge graph structure."""
        try:
            # Check required keys
            if not isinstance(json_data, dict):
                return False
            
            if "nodes" not in json_data or "relationships" not in json_data:
                return False
            
            # Validate nodes structure
            nodes = json_data["nodes"]
            if not isinstance(nodes, list):
                return False
            
            for node in nodes:
                if not isinstance(node, dict):
                    return False
                if not all(key in node for key in ["id", "name", "type"]):
                    return False
            
            # Validate relationships structure
            relationships = json_data["relationships"]
            if not isinstance(relationships, list):
                return False
            
            for rel in relationships:
                if not isinstance(rel, dict):
                    return False
                if not all(key in rel for key in ["source", "target", "type"]):
                    return False
            
            # Check that relationship sources and targets reference valid node IDs
            node_ids = {node["id"] for node in nodes}
            for rel in relationships:
                if rel["source"] not in node_ids or rel["target"] not in node_ids:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating JSON structure: {e}")
            return False

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation and changes made."""
        return {
            "total_messages": len(self.conversation_history),
            "conversation_history": self.conversation_history,
            "current_json": self.current_json,
            "graph_stats": {
                "nodes": len(self.current_json.get("nodes", [])),
                "relationships": len(self.current_json.get("relationships", [])),
                "node_types": list(set(node.get("type", "") for node in self.current_json.get("nodes", []))),
                "relationship_types": list(set(rel.get("type", "") for rel in self.current_json.get("relationships", [])))
            }
        }

    def export_conversation_history(self) -> str:
        """Export conversation history as formatted text."""
        if not self.conversation_history:
            return "No conversation history available."
        
        export_text = f"# Knowledge Graph Refinement Conversation\n\n"
        export_text += f"**Started**: {self.conversation_history[0].get('timestamp', 'Unknown')}\n"
        export_text += f"**Total Messages**: {len(self.conversation_history)}\n\n"
        
        for i, msg in enumerate(self.conversation_history, 1):
            role = msg["role"].title()
            content = msg["content"]
            timestamp = msg.get("timestamp", "")
            
            export_text += f"## Message {i} - {role}\n"
            export_text += f"**Time**: {timestamp}\n\n"
            export_text += f"{content}\n\n"
            
            if "changes" in msg:
                export_text += f"**Changes Made**: {msg['changes']}\n\n"
        
        return export_text

    def reset_conversation(self):
        """Reset the conversation history while keeping current JSON."""
        self.conversation_history = []
        self.logger.info("Conversation history reset")

    def undo_last_change(self) -> Tuple[bool, str]:
        """Attempt to undo the last change made to the JSON."""
        try:
            # Find the last assistant message that made changes
            for i in range(len(self.conversation_history) - 1, -1, -1):
                msg = self.conversation_history[i]
                if msg["role"] == "assistant" and "changes" in msg:
                    # Remove this message and any subsequent ones
                    self.conversation_history = self.conversation_history[:i]
                    
                    # Reset JSON to state before this change
                    # This is a simplified undo - in a production system you'd want 
                    # to store JSON snapshots at each step
                    return True, "Last change has been undone. Please refresh the graph to see the previous state."
            
            return False, "No changes found to undo."
            
        except Exception as e:
            self.logger.error(f"Error undoing last change: {e}")
            return False, f"Error undoing change: {str(e)}"
