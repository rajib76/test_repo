import boto3
import json
import base64
import logging
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel
from botocore.exceptions import ClientError, BotoCoreError
from .base import LLMBase


class BedrockLLM(LLMBase):
    """AWS Bedrock Llama 70B implementation of the LLMBase abstract class."""
    
    def __init__(self, 
                 region_name: str = "us-east-1",
                 model_id: str = "meta.llama3-70b-instruct-v1:0",
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 aws_session_token: Optional[str] = None):
        """Initialize AWS Bedrock client.
        
        Args:
            region_name: AWS region for Bedrock service
            model_id: Bedrock model identifier for Llama 70B
            aws_access_key_id: AWS access key (optional, can use IAM roles)
            aws_secret_access_key: AWS secret key (optional, can use IAM roles)
            aws_session_token: AWS session token (optional, for temporary credentials)
        """
        self.region_name = region_name
        self.model_id = model_id
        
        # Initialize AWS Bedrock client
        session_kwargs = {'region_name': region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                'aws_access_key_id': aws_access_key_id,
                'aws_secret_access_key': aws_secret_access_key
            })
            if aws_session_token:
                session_kwargs['aws_session_token'] = aws_session_token
        
        try:
            session = boto3.Session(**session_kwargs)
            self.bedrock_client = session.client('bedrock-runtime')
            logging.info(f"Initialized AWS Bedrock client with model: {model_id} in region: {region_name}")
        except Exception as e:
            logging.error(f"Failed to initialize Bedrock client: {e}")
            raise
    
    def _prepare_llama_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Prepare prompt in Llama 3 chat format.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            Formatted prompt for Llama model
        """
        if system_prompt:
            formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        else:
            formatted_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        
        return formatted_prompt
    
    def _invoke_bedrock_model(self, prompt: str, **kwargs) -> str:
        """Invoke Bedrock model with the given prompt.
        
        Args:
            prompt: The formatted prompt
            **kwargs: Additional parameters for the model
            
        Returns:
            Generated response text
        """
        # Default parameters for Llama 70B
        default_params = {
            "max_gen_len": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.1),
            "top_p": kwargs.get("top_p", 0.9)
        }
        
        # Update with any provided parameters
        model_params = {**default_params, **{k: v for k, v in kwargs.items() if k in ['max_gen_len', 'temperature', 'top_p']}}
        
        body = {
            "prompt": prompt,
            **model_params
        }
        
        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            
            # Extract the generated text
            if 'generation' in response_body:
                return response_body['generation'].strip()
            else:
                logging.warning(f"Unexpected response format: {response_body}")
                return str(response_body)
                
        except ClientError as e:
            logging.error(f"AWS Bedrock API error: {e}")
            raise
        except Exception as e:
            logging.error(f"Error invoking Bedrock model: {e}")
            raise
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text response from the Llama model."""
        try:
            # Format prompt for Llama
            formatted_prompt = self._prepare_llama_prompt(prompt)
            
            # Invoke the model
            response = self._invoke_bedrock_model(formatted_prompt, **kwargs)
            
            logging.info("Successfully generated response from Bedrock Llama model")
            return response
            
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            raise
    
    def generate_structured(self, prompt: str, response_model: BaseModel, **kwargs) -> BaseModel:
        """Generate structured response using a Pydantic model.
        
        Note: AWS Bedrock doesn't have native structured output like OpenAI,
        so we'll use prompt engineering to request JSON format.
        """
        try:
            # Create a system prompt that requests JSON format
            system_prompt = """You are a helpful assistant that always responds with valid JSON matching the requested schema. 
            Your response must be valid JSON only, with no additional text or explanation."""
            
            # Add JSON schema instructions to the prompt
            schema_prompt = f"""
            {prompt}
            
            Please respond with valid JSON only that matches this structure:
            {response_model.model_json_schema()}
            
            Return only the JSON object, no additional text or explanation.
            """
            
            # Format prompt for Llama
            formatted_prompt = self._prepare_llama_prompt(schema_prompt, system_prompt)
            
            # Generate response
            response = self._invoke_bedrock_model(formatted_prompt, **kwargs)
            
            # Parse and validate the JSON response
            try:
                # Try to extract JSON from the response
                response_json = self._extract_json_from_response(response)
                return response_model.model_validate(response_json)
            except Exception as parse_error:
                logging.warning(f"Failed to parse structured response: {parse_error}")
                # Fallback: try to create a minimal valid response
                try:
                    return response_model()
                except:
                    raise ValueError(f"Could not generate valid structured response: {response}")
                    
        except Exception as e:
            logging.error(f"Error generating structured response: {e}")
            raise
    
    def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """Analyze an image with a text prompt.
        
        Note: Llama 70B is primarily a text model. For image analysis,
        you might want to use a multimodal model like Claude 3 on Bedrock.
        This implementation will raise an error suggesting alternatives.
        """
        raise NotImplementedError(
            "Llama 70B model does not support image analysis. "
            "Consider using a multimodal model like Claude 3 (anthropic.claude-3-sonnet-20240229-v1:0) "
            "or Claude 3 Haiku (anthropic.claude-3-haiku-20240307-v1:0) on Bedrock for image analysis."
        )
    
    def extract_entities(self, text: str, entity_types: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Extract named entities from text."""
        system_prompt = "You are an expert at named entity recognition. Extract entities accurately and return them as valid JSON."
        
        prompt = f"""
        Extract entities of the following types from the given text: {', '.join(entity_types)}
        
        Text: {text}
        
        Return the entities in JSON format as a list of objects with the following structure:
        {{
            "entity": "entity_name",
            "type": "entity_type",
            "description": "brief description",
            "properties": {{}}
        }}
        
        Return only the JSON array, nothing else.
        """
        
        try:
            formatted_prompt = self._prepare_llama_prompt(prompt, system_prompt)
            response = self._invoke_bedrock_model(formatted_prompt, **kwargs)
            
            # Extract and parse JSON response
            try:
                entities = json.loads(response)
                if isinstance(entities, list):
                    return entities
                elif isinstance(entities, dict) and 'entities' in entities:
                    return entities['entities']
                else:
                    return []
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                extracted_data = self._extract_json_from_response(response)
                if 'nodes' in extracted_data:
                    return extracted_data['nodes']
                return []
        except Exception as e:
            logging.error(f"Error extracting entities: {e}")
            return []
    
    def extract_relationships(self, text: str, entities: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """Extract relationships between entities."""
        entity_names = [entity['entity'] for entity in entities]
        
        system_prompt = "You are an expert at relationship extraction. Identify relationships between entities accurately and return them as valid JSON."
        
        prompt = f"""
        Given the following entities: {', '.join(entity_names)}
        
        Extract relationships between these entities from the text: {text}
        
        Return the relationships in JSON format as a list of objects with the following structure:
        {{
            "source": "source_entity",
            "target": "target_entity",
            "relationship": "relationship_type",
            "description": "brief description",
            "properties": {{}}
        }}
        
        Return only the JSON array, nothing else.
        """
        
        try:
            formatted_prompt = self._prepare_llama_prompt(prompt, system_prompt)
            response = self._invoke_bedrock_model(formatted_prompt, **kwargs)
            
            # Extract and parse JSON response
            try:
                relationships = json.loads(response)
                if isinstance(relationships, list):
                    return relationships
                elif isinstance(relationships, dict) and 'relationships' in relationships:
                    return relationships['relationships']
                else:
                    return []
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                extracted_data = self._extract_json_from_response(response)
                if 'relationships' in extracted_data:
                    return extracted_data['relationships']
                return []
        except Exception as e:
            logging.error(f"Error extracting relationships: {e}")
            return []
    
    def summarize(self, text: str, max_length: Optional[int] = None, **kwargs) -> str:
        """Summarize the input text."""
        length_instruction = f" in maximum {max_length} words" if max_length else ""
        system_prompt = "You are an expert at text summarization. Provide clear, concise summaries that capture the key points."
        
        prompt = f"Summarize the following text{length_instruction}:\n\n{text}"
        
        formatted_prompt = self._prepare_llama_prompt(prompt, system_prompt)
        return self._invoke_bedrock_model(formatted_prompt, **kwargs)
    
    def validate_response(self, response: str, expected_format: str, **kwargs) -> bool:
        """Validate if the response matches expected format."""
        system_prompt = "You are an expert validator. Analyze the given response and determine if it matches the expected format."
        
        prompt = f"""
        Validate if the following response matches the expected format: {expected_format}
        
        Response: {response}
        
        Return only 'true' or 'false'.
        """
        
        try:
            formatted_prompt = self._prepare_llama_prompt(prompt, system_prompt)
            validation_result = self._invoke_bedrock_model(formatted_prompt, **kwargs)
            return validation_result.lower().strip() == 'true'
        except Exception as e:
            logging.error(f"Error validating response: {e}")
            return False
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response that might contain extra text."""
        try:
            # First, try to parse the response directly
            return json.loads(response)
        except json.JSONDecodeError:
            # If that fails, try to find JSON within the response
            import re
            
            # Look for JSON object starting with { and ending with }
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Look for JSON array starting with [ and ending with ]
            json_array_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_array_match:
                try:
                    array_data = json.loads(json_array_match.group())
                    # If it's an array, wrap it in a nodes structure
                    return {"nodes": array_data, "relationships": []}
                except json.JSONDecodeError:
                    pass
            
            # If all else fails, return empty structure
            logging.warning(f"Could not extract JSON from response: {response[:200]}...")
            return {"nodes": [], "relationships": []}
    
    def create_knowledge_graph(self, text: str, prompt_template: str, analysis_type: str = "general", **kwargs) -> Dict[str, Any]:
        """Create a knowledge graph from text using a prompt template."""
        try:
            # Get Llama-optimized system prompt based on analysis type
            try:
                from prompt_templates.llama_prompt_templates import get_llama_system_prompt
                system_prompt = get_llama_system_prompt(analysis_type)
            except ImportError:
                # Fallback system prompt
                system_prompt = """You are an expert knowledge graph creator. Analyze text and extract entities and relationships to create comprehensive knowledge graphs. 
                Always respond with valid JSON only, containing 'nodes' and 'relationships' arrays."""
            
            # The prompt_template should already be formatted, so use it directly
            formatted_prompt = self._prepare_llama_prompt(prompt_template, system_prompt)
            
            response = self._invoke_bedrock_model(formatted_prompt, **kwargs)
            
            # Extract and parse JSON response
            graph_data = self._extract_json_from_response(response)
            
            # Ensure the response has the expected structure
            if not isinstance(graph_data, dict):
                graph_data = {"nodes": [], "relationships": []}
            
            if "nodes" not in graph_data:
                graph_data["nodes"] = []
            if "relationships" not in graph_data:
                graph_data["relationships"] = []
                
            return graph_data
        except Exception as e:
            logging.error(f"Error creating knowledge graph: {e}")
            return {"nodes": [], "relationships": []}
    
    def analyze_process_image(self, image_path: str, **kwargs) -> Dict[str, Any]:
        """Analyze a process flow image and extract graph structure.
        
        Note: Llama 70B doesn't support image analysis. This method will raise an error.
        """
        raise NotImplementedError(
            "Llama 70B model does not support image analysis. "
            "Consider using a multimodal model like Claude 3 on Bedrock for image analysis, "
            "or use the OpenAI implementation for image processing."
        )
    
    def get_model_info(self) -> Dict[str, str]:
        """Get information about the current model."""
        return {
            "provider": "AWS Bedrock",
            "model_id": self.model_id,
            "region": self.region_name,
            "capabilities": "Text generation, knowledge graphs, entity extraction, summarization",
            "limitations": "No image analysis, no native structured output"
        }
