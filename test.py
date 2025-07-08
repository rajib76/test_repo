"""
Llama-optimized prompt templates for knowledge graph creation.
These prompts are specifically tuned for Llama 3 70B model characteristics.
"""

# Llama-optimized Knowledge Graph Prompt
LLAMA_KNOWLEDGE_GRAPH_PROMPT = """Analyze the text below and extract entities and relationships to create a knowledge graph.

TASK:
Create a JSON knowledge graph with nodes (entities) and relationships.

INPUT TEXT:
{text}

REQUIREMENTS:
1. Extract ALL important entities: people, places, organizations, concepts, events, technologies, etc.
2. Identify relationships between entities
3. Use clear, descriptive names and types
4. Create unique IDs using format: type_name (e.g., "person_alice", "company_google")

OUTPUT FORMAT:
Return ONLY valid JSON in this exact structure:

{{
    "nodes": [
        {{
            "id": "unique_id",
            "name": "Entity Name",
            "type": "EntityType",
            "description": "Brief description"
        }}
    ],
    "relationships": [
        {{
            "source": "source_id",
            "target": "target_id",
            "type": "relationship_type",
            "description": "How they are related"
        }}
    ]
}}

ENTITY TYPES TO USE:
- Person, Organization, Location, Technology, Concept, Event, Product, Process

RELATIONSHIP TYPES TO USE:
- works_for, located_in, created_by, part_of, leads_to, enables, requires, related_to

IMPORTANT: Return only the JSON object, no additional text or explanation."""

# Llama-optimized Process Flow Prompt
LLAMA_PROCESS_FLOW_PROMPT = """Analyze the text below and create a process flow graph showing steps, decisions, and workflow.

INPUT TEXT:
{text}

TASK:
Extract process steps, decision points, and their sequence to create a workflow graph.

STEP-BY-STEP APPROACH:
1. Identify all process steps and activities
2. Find decision points and conditions
3. Determine the sequence and flow
4. Identify start and end points

OUTPUT FORMAT:
Return ONLY valid JSON:

{{
    "nodes": [
        {{
            "id": "step_id",
            "name": "Step Name",
            "type": "start|process|decision|end",
            "description": "What happens in this step"
        }}
    ],
    "relationships": [
        {{
            "source": "from_step",
            "target": "to_step", 
            "type": "flows_to|leads_to|decides|branches_to",
            "description": "Condition or trigger"
        }}
    ]
}}

NODE TYPES:
- start: Beginning of process
- process: Action or task step  
- decision: Choice or condition point
- end: Completion of process

RELATIONSHIP TYPES:
- flows_to: Normal sequence
- leads_to: Causal connection
- decides: Decision outcome
- branches_to: Alternative path

Return only the JSON, no other text."""

# Llama-optimized Document Analysis Prompt  
LLAMA_DOCUMENT_ANALYSIS_PROMPT = """Analyze the document content below and create a knowledge graph representing its structure and key concepts.

DOCUMENT CONTENT:
{text}

OBJECTIVE:
Extract the document's hierarchical structure, main concepts, and their relationships.

ANALYSIS STEPS:
1. Identify document sections and hierarchy
2. Extract key concepts and terms
3. Find relationships between concepts
4. Map document structure

OUTPUT FORMAT:
Return ONLY valid JSON:

{{
    "nodes": [
        {{
            "id": "concept_id",
            "name": "Concept Name",
            "type": "document|section|concept|term",
            "description": "Explanation of the concept"
        }}
    ],
    "relationships": [
        {{
            "source": "parent_id",
            "target": "child_id",
            "type": "contains|references|defines|relates_to",
            "description": "Nature of relationship"
        }}
    ]
}}

NODE TYPES:
- document: Top-level document
- section: Major sections/chapters
- concept: Key ideas or topics
- term: Important definitions

RELATIONSHIP TYPES:
- contains: Hierarchical containment
- references: Cross-references
- defines: Definitions
- relates_to: Conceptual connections

Return only JSON, no additional text."""

# Llama-optimized General Graph Prompt
LLAMA_GENERAL_GRAPH_PROMPT = """Create a knowledge graph from the content below by extracting entities and their relationships.

CONTENT:
{text}

INSTRUCTIONS:
1. Read and understand the content
2. Extract important entities (people, places, things, concepts)
3. Identify how entities are connected
4. Structure as a graph with nodes and relationships

JSON OUTPUT FORMAT:
{{
    "nodes": [
        {{
            "id": "entity_id",
            "name": "Entity Name", 
            "type": "entity_type",
            "description": "Brief description"
        }}
    ],
    "relationships": [
        {{
            "source": "entity1_id",
            "target": "entity2_id",
            "type": "relationship_type",
            "description": "How they connect"
        }}
    ]
}}

GUIDELINES:
- Use clear, unique IDs
- Choose specific entity types
- Use descriptive relationship types
- Include meaningful descriptions
- Focus on the most important connections

Return only the JSON structure."""

# System prompts optimized for Llama
LLAMA_SYSTEM_PROMPTS = {
    "knowledge_graph": """You are an expert knowledge graph analyst. You extract entities and relationships from text with high precision. You always return valid JSON in the exact format requested. You focus on accuracy and completeness.""",
    
    "process_flow": """You are a process analysis expert. You understand workflows, decision points, and process sequences. You create clear process flow graphs that capture the logical flow of activities. You always return valid JSON.""",
    
    "document": """You are a document structure analyst. You understand hierarchical information, concept relationships, and document organization. You create knowledge graphs that represent both structure and content relationships.""",
    
    "general": """You are a knowledge extraction specialist. You identify important entities and their relationships in any type of content. You create well-structured knowledge graphs with clear entity types and meaningful connections."""
}

# Function to get Llama-optimized prompts
def get_llama_prompt_template(analysis_type: str = "general") -> str:
    """
    Get Llama-optimized prompt template based on analysis type.
    
    Args:
        analysis_type: Type of analysis ('knowledge_graph', 'process_flow', 'document', 'general')
    
    Returns:
        Llama-optimized prompt template string
    """
    llama_templates = {
        'knowledge_graph': LLAMA_KNOWLEDGE_GRAPH_PROMPT,
        'process_flow': LLAMA_PROCESS_FLOW_PROMPT,
        'document': LLAMA_DOCUMENT_ANALYSIS_PROMPT,
        'general': LLAMA_GENERAL_GRAPH_PROMPT
    }
    
    return llama_templates.get(analysis_type, LLAMA_GENERAL_GRAPH_PROMPT)

def get_llama_system_prompt(analysis_type: str = "general") -> str:
    """
    Get Llama-optimized system prompt for the analysis type.
    
    Args:
        analysis_type: Type of analysis
        
    Returns:
        System prompt optimized for Llama models
    """
    return LLAMA_SYSTEM_PROMPTS.get(analysis_type, LLAMA_SYSTEM_PROMPTS["general"])

def format_llama_prompt(text: str, analysis_type: str = "general") -> str:
    """
    Format a Llama-optimized prompt template with the given text.
    
    Args:
        text: The text to analyze
        analysis_type: Type of analysis
    
    Returns:
        Formatted prompt string optimized for Llama
    """
    try:
        template = get_llama_prompt_template(analysis_type)
        return template.format(text=text)
    except KeyError as e:
        print(f"Llama template formatting error: {e}")
        print(f"Template: {template[:200]}...")
        raise
    except Exception as e:
        print(f"Unexpected Llama formatting error: {e}")
        print(f"Template: {template[:200]}...")
        raise

# Comparison prompt for testing both models
COMPARISON_TEST_PROMPT = """Test prompt for comparing OpenAI vs Llama performance:

Text: "Alice works at Google as a software engineer. She is developing a new AI system called 'SmartAssist' that helps users manage their schedules. The system uses machine learning algorithms to predict user preferences and integrates with calendar applications."

Expected output: Entities for Alice (Person), Google (Organization), SmartAssist (Product), AI system (Technology), machine learning (Technology), calendar applications (Technology). Relationships like works_for, develops, uses, integrates_with."""
