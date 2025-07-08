import json
import logging
import os
import tempfile
from typing import Dict, Any

import networkx as nx
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Import custom modules
from graph.neo4j_graph_builder import Neo4jGraphBuilder
from llm_models.llm_openai import OpenAILLM
from llm_models.llm_bedrock import BedrockLLM
from prompt_templates.graph_prompt_template import format_prompt
from conversation.json_conversation_handler import JSONConversationHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Knowledge Graph Creator",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #ff7f0e;
        margin-bottom: 1rem;
    }
    .stButton > button {
        background-color: #1f77b4;
        color: white;
        border-radius: 5px;
    }
    .upload-section {
        padding: 0px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


class KnowledgeGraphCreator:
    def __init__(self):
        self.graph_builder = None
        self.llm_model = None
        self.initialize_components()

    def initialize_components(self):
        """Initialize graph builder and LLM model."""
        try:
            # Initialize Neo4j connection
            neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            neo4j_username = os.getenv('NEO4J_USER', 'neo4j')
            neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')

            self.graph_builder = Neo4jGraphBuilder(neo4j_uri, neo4j_username, neo4j_password)

            # Initialize LLM based on user preference
            self.llm_model = self._initialize_llm()

        except Exception as e:
            st.error(f"Error initializing components: {str(e)}")
            logger.error(f"Initialization error: {e}")

    def _initialize_llm(self):
        """Initialize LLM based on configuration."""
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        
        if llm_provider == 'bedrock':
            return self._initialize_bedrock_llm()
        elif llm_provider == 'openai':
            return self._initialize_openai_llm()
        else:
            # Default to OpenAI, but show warning
            st.warning(f"Unknown LLM provider '{llm_provider}'. Defaulting to OpenAI.")
            return self._initialize_openai_llm()
    
    def _initialize_openai_llm(self):
        """Initialize OpenAI LLM."""
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key:
            model = os.getenv('OPENAI_MODEL', 'gpt-4o')
            return OpenAILLM(openai_api_key, model)
        else:
            st.error("OpenAI API key not found in environment variables")
            return None
    
    def _initialize_bedrock_llm(self):
        """Initialize AWS Bedrock LLM."""
        try:
            region_name = os.getenv('AWS_REGION', 'us-east-1')
            model_id = os.getenv('BEDROCK_MODEL_ID', 'meta.llama3-70b-instruct-v1:0')
            
            # AWS credentials (optional - can use IAM roles)
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_session_token = os.getenv('AWS_SESSION_TOKEN')
            
            bedrock_llm = BedrockLLM(
                region_name=region_name,
                model_id=model_id,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token
            )
            
            st.success(f"✅ Initialized AWS Bedrock LLM: {model_id} in {region_name}")
            return bedrock_llm
            
        except Exception as e:
            st.error(f"Failed to initialize AWS Bedrock LLM: {str(e)}")
            logger.error(f"Bedrock initialization error: {e}")
            # Fallback to OpenAI if Bedrock fails
            st.info("Falling back to OpenAI LLM...")
            return self._initialize_openai_llm()

    def create_networkx_graph(self, graph_data: Dict[str, Any]) -> nx.Graph:
        """Create a NetworkX graph from graph data."""
        G = nx.Graph()

        # Add nodes
        for node in graph_data.get('nodes', []):
            G.add_node(node['id'], **node)

        # Add edges
        for rel in graph_data.get('relationships', []):
            G.add_edge(rel['source'], rel['target'], **rel)

        return G

    def create_plotly_graph(self, graph_data: Dict[str, Any]) -> go.Figure:
        """Create an enhanced interactive Plotly graph visualization."""
        G = self.create_networkx_graph(graph_data)
        
        if len(G.nodes()) == 0:
            # Return empty figure if no nodes
            fig = go.Figure()
            fig.add_annotation(
                text="No nodes to display",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=20, color="gray")
            )
            return fig

        # Use different layouts based on graph size
        try:
            if len(G.nodes()) < 20:
                pos = nx.spring_layout(G, k=3, iterations=100, seed=42)
            else:
                pos = nx.kamada_kawai_layout(G)
        except Exception as e:
            # Fallback to simple layout if advanced layouts fail
            logging.warning(f"Layout algorithm failed, using fallback: {e}")
            pos = nx.spring_layout(G, seed=42)

        # Create node traces with better styling - using discrete colors
        node_types = [G.nodes[node].get('type', 'Unknown') for node in G.nodes()]
        unique_types = list(set(node_types))
        
        # Create a color mapping for different node types
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                 '#DDA0DD', '#98D8C8', '#FFB6C1', '#87CEEB', '#F0E68C']
        color_map = {node_type: colors[i % len(colors)] for i, node_type in enumerate(unique_types)}
        
        node_colors = [color_map[node_type] for node_type in node_types]

        node_trace = go.Scatter(
            x=[pos[node][0] for node in G.nodes()],
            y=[pos[node][1] for node in G.nodes()],
            mode='markers+text',
            text=[self._truncate_text(G.nodes[node].get('name', node), 12) for node in G.nodes()],
            textposition="middle center",
            textfont=dict(size=10, color='white', family="Arial Black"),
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                         'Type: %{customdata[1]}<br>' +
                         'Description: %{customdata[2]}<br>' +
                         'ID: %{customdata[3]}<extra></extra>',
            customdata=[[G.nodes[node].get('name', node),
                        G.nodes[node].get('type', 'Unknown'),
                        self._truncate_text(G.nodes[node].get('description', 'No description'), 100),
                        node] for node in G.nodes()],
            marker=dict(
                size=50,  # Larger fixed size
                color=node_colors,  # Use our custom colors
                line=dict(width=3, color='white'),
                opacity=0.9
            ),
            name="Nodes"
        )

        # Create edge traces with relationship labels
        edge_traces = []
        
        # Main edge lines
        edge_x = []
        edge_y = []

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=3, color='rgba(100,100,100,0.6)'),
            hoverinfo='none',
            mode='lines',
            name="Relationships"
        )
        edge_traces.append(edge_trace)

        # Add relationship labels in the middle of edges
        rel_x = []
        rel_y = []
        rel_text = []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            # Calculate midpoint
            mid_x = (x0 + x1) / 2
            mid_y = (y0 + y1) / 2
            rel_x.append(mid_x)
            rel_y.append(mid_y)
            rel_text.append(self._truncate_text(G.edges[edge].get('type', ''), 8))

        if rel_x:  # Only add if there are relationships
            rel_trace = go.Scatter(
                x=rel_x, y=rel_y,
                mode='text',
                text=rel_text,
                textfont=dict(size=9, color='#2E86AB'),
                hoverinfo='none',
                name="Relationship Labels"
            )
            edge_traces.append(rel_trace)

        # Create figure with enhanced layout
        fig = go.Figure(data=edge_traces + [node_trace])
        
        fig.update_layout(
            title=dict(
                text='Interactive Knowledge Graph',
                font=dict(size=24),
                x=0.5
            ),
            showlegend=False,  # Hide legend for cleaner look
            hovermode='closest',
            margin=dict(b=20, l=20, r=20, t=60),
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(200,200,200,0.2)',
                zeroline=False,
                showticklabels=False
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(200,200,200,0.2)',
                zeroline=False,
                showticklabels=False
            ),
            plot_bgcolor='white',
            # Enhanced interactivity
            dragmode='pan',
            uirevision='constant'  # Preserves zoom/pan state
        )

        return fig
    
    def create_interactive_graph(self, graph_data: Dict[str, Any]) -> str:
        """Create an interactive network graph using vis.js directly."""
        if not graph_data or not graph_data.get('nodes'):
            return None
            
        # Convert graph data to vis.js format
        nodes = []
        edges = []
        
        # Node colors by type
        node_colors = {
            'Person': '#FF6B6B',
            'Organization': '#4ECDC4', 
            'Location': '#45B7D1',
            'Concept': '#96CEB4',
            'Event': '#FFEAA7',
            'Document': '#DDA0DD',
            'Process': '#98D8C8',
            'Technology': '#FFB6C1',
            'Unknown': '#87CEEB'
        }
        
        # Process nodes
        for node in graph_data.get('nodes', []):
            node_id = node.get('id', '')
            node_name = node.get('name', node_id)
            node_type = node.get('type', 'Unknown')
            node_desc = node.get('description', 'No description')
            
            # Truncate long names for display - shorter for less overlap
            display_name = node_name[:12] + "..." if len(node_name) > 12 else node_name
            
            color = node_colors.get(node_type, node_colors['Unknown'])
            
            # Create clean text tooltip for nodes
            node_tooltip = f"""┌─ {node_name} ─┐
│ Type: {node_type}
│ 
│ {node_desc}
│ 
└─ ID: {node_id} ─┘"""
            
            # Dynamic node size based on text length for better spacing
            node_size = max(35, min(50, len(display_name) * 3 + 25))
            
            nodes.append({
                'id': node_id,
                'label': display_name,
                'title': node_tooltip,
                'color': color,
                'size': node_size,
                'font': {'size': 14, 'color': '#1F2937', 'face': 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', 'strokeWidth': 1, 'strokeColor': 'white'},
                'margin': {'top': 5, 'right': 5, 'bottom': 5, 'left': 5}
            })
        
        # Process edges
        for rel in graph_data.get('relationships', []):
            source = rel.get('source', '')
            target = rel.get('target', '')
            rel_type = rel.get('type', 'connected')
            rel_desc = rel.get('description', '')
            
            if source and target:
                # Shorter edge labels to reduce overlap
                label = rel_type[:8] + "..." if len(rel_type) > 8 else rel_type
                # Hide edge labels if there are too many relationships to reduce clutter
                show_edge_label = len(graph_data.get('relationships', [])) <= 10
                
                # Create clean text tooltip for relationships
                rel_desc_text = f"\n│ Description: {rel_desc}" if rel_desc else ""
                rel_tooltip = f"""┌─ 🔗 RELATIONSHIP ─┐
│ {source} → {target}
│ 
│ Type: {rel_type}{rel_desc_text}
│ 
└─────────────────┘"""
                
                edges.append({
                    'from': source,
                    'to': target,
                    'label': label if show_edge_label else '',  # Hide labels when too many
                    'title': rel_tooltip,
                    'color': '#6B7280',
                    'width': 2,
                    'arrows': {'to': {'enabled': True, 'scaleFactor': 1.0}},
                    'font': {'size': 12, 'color': '#374151', 'face': 'Inter, sans-serif', 'strokeWidth': 0, 'background': 'rgba(255,255,255,0.8)'},
                    'smooth': {'type': 'continuous', 'forceDirection': 'none', 'roundness': 0.3}
                })
        
        # Create HTML with vis.js - properly escape JSON
        import json
        nodes_json = json.dumps(nodes)
        edges_json = json.dumps(edges)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <style type="text/css">
                #mynetworkid {{
                    width: 100%;
                    height: 800px;
                    border: 1px solid #E5E7EB;
                    border-radius: 8px;
                    background: white;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                }}
                .vis-tooltip {{
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
                    background: rgba(45, 45, 45, 0.95) !important;
                    color: #E5E7EB !important;
                    border: 1px solid #6B7280 !important;
                    border-radius: 6px !important;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
                    padding: 12px !important;
                    font-size: 12px !important;
                    line-height: 1.4 !important;
                    white-space: pre !important;
                    max-width: 400px !important;
                    z-index: 1000 !important;
                }}
            </style>
        </head>
        <body>
            <div id="mynetworkid"></div>
            <script type="text/javascript">
                try {{
                    var nodes = new vis.DataSet({nodes_json});
                    var edges = new vis.DataSet({edges_json});
                    
                    var container = document.getElementById('mynetworkid');
                    var data = {{
                        nodes: nodes,
                        edges: edges
                    }};
                    
                    var options = {{
                        physics: {{
                            enabled: true,
                            stabilization: {{iterations: 150, updateInterval: 10}},
                            barnesHut: {{
                                gravitationalConstant: -3000,
                                centralGravity: 0.1,
                                springLength: 150,
                                springConstant: 0.02,
                                damping: 0.15,
                                avoidOverlap: 1
                            }},
                            minVelocity: 0.75
                        }},
                        interaction: {{
                            dragNodes: true,
                            dragView: true,
                            zoomView: true,
                            selectConnectedEdges: false
                        }},
                        nodes: {{
                            font: {{
                                size: 14,
                                face: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
                                color: '#1F2937',
                                strokeWidth: 1,
                                strokeColor: 'white'
                            }},
                            borderWidth: 2,
                            shadow: {{
                                enabled: true,
                                color: 'rgba(0,0,0,0.2)',
                                size: 8,
                                x: 2,
                                y: 2
                            }},
                            shape: 'dot'
                        }},
                        edges: {{
                            font: {{
                                size: 14,
                                face: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
                                color: '#374151',
                                align: 'middle',
                                strokeWidth: 0.5,
                                strokeColor: 'white'
                            }},
                            smooth: {{
                                type: 'continuous',
                                forceDirection: 'none',
                                roundness: 0.5
                            }},
                            arrows: {{
                                to: {{
                                    enabled: true,
                                    scaleFactor: 1.2,
                                    type: 'arrow'
                                }}
                            }},
                            color: {{
                                color: '#6B7280',
                                highlight: '#3B82F6',
                                hover: '#4B5563'
                            }}
                        }}
                    }};
                    
                    var network = new vis.Network(container, data, options);
                    
                    // Add interaction events
                    network.on('click', function (params) {{
                        if (params.nodes.length > 0) {{
                            var nodeId = params.nodes[0];
                            var node = nodes.get(nodeId);
                            console.log('Clicked node:', node);
                        }}
                    }});
                    
                    network.on('doubleClick', function (params) {{
                        network.fit({{
                            animation: {{
                                duration: 800,
                                easingFunction: 'easeInOutQuad'
                            }}
                        }});
                    }});
                    
                    network.on('dragEnd', function (params) {{
                        if (params.nodes.length > 0) {{
                            console.log('Finished dragging nodes:', params.nodes);
                        }}
                    }});
                    
                    // Add stabilization complete event
                    network.on('stabilizationIterationsDone', function () {{
                        console.log('Network stabilized');
                        network.fit({{
                            animation: {{duration: 500}}
                        }});
                    }});
                    
                    // Debug info
                    console.log('Network initialized with', nodes.length, 'nodes and', edges.length, 'edges');
                    
                }} catch (error) {{
                    console.error('Error initializing network:', error);
                    document.getElementById('mynetworkid').innerHTML = '<p style="color: red; padding: 20px;">Error loading network: ' + error.message + '</p>';
                }}
            </script>
        </body>
        </html>
        """
        
        return html_content
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."

    def process_text_input(self, text: str, analysis_type: str) -> Dict[str, Any]:
        """Process text input and create knowledge graph."""
        try:
            # Format prompt based on analysis type
            print("text ", text )
            print("anlalysis ", analysis_type)
            formatted_prompt = format_prompt(text, analysis_type)

            # Generate graph data using LLM
            # Check if the LLM supports analysis_type parameter (Bedrock does, OpenAI doesn't need it)
            if hasattr(self.llm_model, 'get_model_info') and 'Bedrock' in self.llm_model.get_model_info().get('provider', ''):
                graph_data = self.llm_model.create_knowledge_graph(text, formatted_prompt, analysis_type)
            else:
                graph_data = self.llm_model.create_knowledge_graph(text, formatted_prompt)

            return graph_data
        except Exception as e:
            error_msg = str(e)
            st.error(f"Error processing text: {error_msg}")
            logger.error(f"Text processing error: {error_msg}")
            print(f"Full error details: {type(e).__name__}: {error_msg}")
            import traceback
            print("Full traceback:")
            traceback.print_exc()
            return {"nodes": [], "relationships": []}

    def process_text_file(self, text_file, analysis_type: str) -> Dict[str, Any]:
        """Process plain text file input and create knowledge graph."""
        try:
            # Read the text file content
            content = text_file.read()
            
            # Handle both bytes and string content
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Format prompt based on analysis type
            formatted_prompt = format_prompt(content, analysis_type)
            
            # Generate graph data using LLM
            # Check if the LLM supports analysis_type parameter (Bedrock does, OpenAI doesn't need it)
            if hasattr(self.llm_model, 'get_model_info') and 'Bedrock' in self.llm_model.get_model_info().get('provider', ''):
                graph_data = self.llm_model.create_knowledge_graph(content, formatted_prompt, analysis_type)
            else:
                graph_data = self.llm_model.create_knowledge_graph(content, formatted_prompt)
            
            return graph_data
        except Exception as e:
            st.error(f"Error processing text file: {str(e)}")
            logger.error(f"Text file processing error: {e}")
            return {"nodes": [], "relationships": []}

    def process_markdown_file(self, markdown_file, analysis_type: str) -> Dict[str, Any]:
        """Process markdown file input and create knowledge graph."""
        try:
            # Read the markdown file content
            content = markdown_file.read()
            
            # Handle both bytes and string content
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Format prompt based on analysis type
            formatted_prompt = format_prompt(content, analysis_type)
            
            # Generate graph data using LLM
            # Check if the LLM supports analysis_type parameter (Bedrock does, OpenAI doesn't need it)
            if hasattr(self.llm_model, 'get_model_info') and 'Bedrock' in self.llm_model.get_model_info().get('provider', ''):
                graph_data = self.llm_model.create_knowledge_graph(content, formatted_prompt, analysis_type)
            else:
                graph_data = self.llm_model.create_knowledge_graph(content, formatted_prompt)
            
            return graph_data
        except Exception as e:
            st.error(f"Error processing markdown file: {str(e)}")
            logger.error(f"Markdown processing error: {e}")
            return {"nodes": [], "relationships": []}

    def process_image_input(self, image_file) -> Dict[str, Any]:
        """Process image input and create knowledge graph."""
        try:
            # Check if the current LLM supports image analysis
            if hasattr(self.llm_model, 'get_model_info'):
                model_info = self.llm_model.get_model_info()
                if 'No image analysis' in model_info.get('limitations', ''):
                    st.error("❌ **Image analysis not supported** with the current LLM provider.")
                    st.info("💡 **Suggestion:** Switch to OpenAI GPT-4 in the sidebar for image analysis support.")
                    return {"nodes": [], "relationships": []}
            
            # Save uploaded image to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_file.write(image_file.getvalue())
                tmp_file_path = tmp_file.name

            # Analyze image using LLM
            graph_data = self.llm_model.analyze_process_image(tmp_file_path)

            # Clean up temporary file
            os.unlink(tmp_file_path)

            return graph_data
        except NotImplementedError as e:
            st.error(f"❌ **Image analysis not supported:** {str(e)}")
            return {"nodes": [], "relationships": []}
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
            logger.error(f"Image processing error: {e}")
            return {"nodes": [], "relationships": []}

    def save_to_neo4j(self, graph_data: Dict[str, Any]) -> bool:
        """Save graph data to Neo4j database."""
        try:
            # Clear existing graph (optional)
            if st.session_state.get('clear_existing', False):
                self.graph_builder.clear_graph()

            # Create nodes
            node_ids = {}
            for node in graph_data.get('nodes', []):
                node_id = self.graph_builder.create_node(
                    node.get('type', 'Unknown'),
                    node
                )
                node_ids[node['id']] = node_id

            # Create relationships
            for rel in graph_data.get('relationships', []):
                if rel['source'] in node_ids and rel['target'] in node_ids:
                    self.graph_builder.create_relationship(
                        node_ids[rel['source']],
                        node_ids[rel['target']],
                        rel.get('type', 'RELATED'),
                        rel.get('properties', {})
                    )

            return True
        except Exception as e:
            st.error(f"Error saving to Neo4j: {str(e)}")
            logger.error(f"Neo4j save error: {e}")
            return False


def main():
    # Initialize the knowledge graph creator
    kg_creator = KnowledgeGraphCreator()

    # Main header
    st.markdown('<h1 class="main-header">🧠 Knowledge Graph Creator</h1>', unsafe_allow_html=True)
    st.markdown("Transform unstructured data and images into interactive knowledge graphs")

    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")

    # Analysis type selection
    analysis_type = st.sidebar.selectbox(
        "Analysis Type",
        ["general", "knowledge_graph", "process_flow", "document"],
        help="Choose the type of analysis for your content"
    )

    # LLM Provider Selection
    st.sidebar.subheader("🤖 LLM Provider")
    current_llm_info = "Unknown"
    if kg_creator.llm_model:
        if hasattr(kg_creator.llm_model, 'get_model_info'):
            model_info = kg_creator.llm_model.get_model_info()
            current_llm_info = f"{model_info['provider']} - {model_info.get('model_id', 'N/A')}"
        elif hasattr(kg_creator.llm_model, 'model'):
            current_llm_info = f"OpenAI - {kg_creator.llm_model.model}"
        else:
            current_llm_info = "OpenAI"
    
    st.sidebar.info(f"**Current LLM:** {current_llm_info}")
    
    # LLM provider selection
    llm_provider = st.sidebar.selectbox(
        "Select LLM Provider",
        ["OpenAI GPT-4", "AWS Bedrock Llama 70B"],
        help="Choose the Large Language Model provider for analysis"
    )
    
    # Update environment variable based on selection and reinitialize if changed
    new_provider = 'bedrock' if llm_provider == "AWS Bedrock Llama 70B" else 'openai'
    current_provider = os.getenv('LLM_PROVIDER', 'openai')
    
    if new_provider != current_provider:
        os.environ['LLM_PROVIDER'] = new_provider
        # Reinitialize the LLM model
        try:
            kg_creator.llm_model = kg_creator._initialize_llm()
        except Exception as e:
            st.error(f"Failed to switch LLM provider: {str(e)}")
    else:
        os.environ['LLM_PROVIDER'] = new_provider
    
    # Show provider-specific information
    if llm_provider == "AWS Bedrock Llama 70B":
        with st.sidebar.expander("🔧 AWS Bedrock Settings"):
            st.write("**Required Environment Variables:**")
            st.code("""
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=meta.llama3-70b-instruct-v1:0
AWS_ACCESS_KEY_ID=your_key_id
AWS_SECRET_ACCESS_KEY=your_secret_key
# Optional: AWS_SESSION_TOKEN for temporary credentials
            """)
            st.info("💡 You can also use IAM roles instead of access keys")
            
            # Show current AWS configuration
            aws_region = os.getenv('AWS_REGION', 'Not set')
            model_id = os.getenv('BEDROCK_MODEL_ID', 'Not set')
            st.write(f"**Current Region:** {aws_region}")
            st.write(f"**Current Model:** {model_id}")
    else:
        with st.sidebar.expander("🔧 OpenAI Settings"):
            st.write("**Required Environment Variables:**")
            st.code("""
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o  # Optional, defaults to gpt-4o
            """)
            
            # Show current OpenAI configuration
            api_key_status = "✅ Set" if os.getenv('OPENAI_API_KEY') else "❌ Not set"
            model = os.getenv('OPENAI_MODEL', 'gpt-4o')
            st.write(f"**API Key:** {api_key_status}")
            st.write(f"**Model:** {model}")

    # Visualization options
    st.sidebar.subheader("📊 Visualization Options")
    viz_type = st.sidebar.radio(
        "Choose visualization type:",
        ["Interactive Network (Recommended)", "Static Plotly Graph"],
        help="Interactive Network allows dragging nodes and better exploration"
    )
    
    # Neo4j options
    st.sidebar.subheader("Neo4j Options")
    clear_existing = st.sidebar.checkbox("Clear existing graph", value=False)
    st.session_state['clear_existing'] = clear_existing

    # Input section (full width)
    st.markdown('<h2 class="sub-header">📝 Input Data</h2>', unsafe_allow_html=True)

    # Input method selection
    input_method = st.radio(
        "Choose input method:",
        ["Text Input", "Text File Upload", "Markdown File Upload", "Image Upload"],
        horizontal=True
    )

    graph_data = None

    if input_method == "Text Input":
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        text_input = st.text_area(
            "Enter your text:",
            height=200,
            placeholder="Paste your unstructured text here..."
        )

        if st.button("🔍 Analyze Text", type="primary"):
            if text_input.strip():
                with st.spinner("Analyzing text and creating knowledge graph..."):
                    graph_data = kg_creator.process_text_input(text_input, analysis_type)
                    st.session_state['graph_data'] = graph_data
                    st.session_state['original_text'] = text_input  # Store for conversation context
                    st.success("✅ Text analysis completed! Scroll down to view the knowledge graph.")
            else:
                st.warning("Please enter some text to analyze.")
        st.markdown('</div>', unsafe_allow_html=True)

    elif input_method == "Text File Upload":
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded_text_file = st.file_uploader(
            "Upload a text file:",
            type=['txt', 'text', 'log', 'csv', 'tsv'],
            help="Upload a plain text file (.txt) containing the content you want to analyze"
        )
        
        if uploaded_text_file is not None:
            # Display file info
            st.info(f"📄 File: {uploaded_text_file.name} ({uploaded_text_file.size} bytes)")
            
            # Show preview of content
            with st.expander("📖 Preview file content"):
                try:
                    content = uploaded_text_file.read()
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    # Reset file pointer for later processing
                    uploaded_text_file.seek(0)
                    
                    # Show first 1000 characters
                    preview_text = content[:1000]
                    if len(content) > 1000:
                        preview_text += "\n... (truncated)"
                    st.text(preview_text)
                except Exception as e:
                    st.error(f"Error reading file: {e}")
            
            if st.button("🔍 Analyze Text File", type="primary"):
                with st.spinner("Analyzing text file and creating knowledge graph..."):
                    # Read file content for storing original text
                    file_content = uploaded_text_file.read()
                    if isinstance(file_content, bytes):
                        file_content = file_content.decode('utf-8')
                    uploaded_text_file.seek(0)  # Reset for processing
                    
                    graph_data = kg_creator.process_text_file(uploaded_text_file, analysis_type)
                    st.session_state['graph_data'] = graph_data
                    st.session_state['original_text'] = file_content  # Store for conversation context
                    st.success("✅ Text file analysis completed! Scroll down to view the knowledge graph.")
        st.markdown('</div>', unsafe_allow_html=True)

    elif input_method == "Markdown File Upload":
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded_md_file = st.file_uploader(
            "Upload a markdown file:",
            type=['md', 'markdown', 'txt'],
            help="Upload a markdown (.md) file containing the content you want to analyze"
        )
        
        if uploaded_md_file is not None:
            # Display file info
            st.info(f"📄 File: {uploaded_md_file.name} ({uploaded_md_file.size} bytes)")
            
            # Show preview of content
            with st.expander("📖 Preview file content"):
                try:
                    content = uploaded_md_file.read()
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    # Reset file pointer for later processing
                    uploaded_md_file.seek(0)
                    
                    # Show first 1000 characters
                    preview_text = content[:1000]
                    if len(content) > 1000:
                        preview_text += "\n... (truncated)"
                    st.text(preview_text)
                except Exception as e:
                    st.error(f"Error reading file: {e}")
            
            if st.button("🔍 Analyze Markdown File", type="primary"):
                with st.spinner("Analyzing markdown file and creating knowledge graph..."):
                    # Read markdown content for storing original text
                    md_content = uploaded_md_file.read()
                    if isinstance(md_content, bytes):
                        md_content = md_content.decode('utf-8')
                    uploaded_md_file.seek(0)  # Reset for processing
                    
                    graph_data = kg_creator.process_markdown_file(uploaded_md_file, analysis_type)
                    st.session_state['graph_data'] = graph_data
                    st.session_state['original_text'] = md_content  # Store for conversation context
                    st.success("✅ Markdown file analysis completed! Scroll down to view the knowledge graph.")
        st.markdown('</div>', unsafe_allow_html=True)

    elif input_method == "Image Upload":
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        col_img1, col_img2 = st.columns([1, 1])
        
        with col_img1:
            uploaded_file = st.file_uploader(
                "Upload an image:",
                type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
                help="Upload a process diagram, flowchart, or any image containing structured information"
            )

        with col_img2:
            if uploaded_file is not None:
                # Display uploaded image
                st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

        if uploaded_file is not None:
            if st.button("🔍 Analyze Image", type="primary"):
                with st.spinner("Analyzing image and creating knowledge graph..."):
                    graph_data = kg_creator.process_image_input(uploaded_file)
                    st.session_state['graph_data'] = graph_data
                    st.success("✅ Image analysis completed! Scroll down to view the knowledge graph.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Get graph data from session state
    if 'graph_data' in st.session_state:
        graph_data = st.session_state['graph_data']

    # Knowledge Graph Visualization Section (Full Width at Bottom)
    if graph_data and (graph_data.get('nodes') or graph_data.get('relationships')):
        st.markdown("---")  # Separator
        st.markdown('<h2 class="sub-header">📊 Knowledge Graph Visualization</h2>', unsafe_allow_html=True)
        
        # Create and display the graph based on selected visualization type
        try:
            if viz_type == "Interactive Network (Recommended)":
                # Create interactive network
                st.markdown("### 🎯 Interactive Knowledge Graph")
                
                # Add user-friendly controls
                col_control1, col_control2, col_control3 = st.columns(3)
                with col_control1:
                    if len(graph_data.get('relationships', [])) > 10:
                        st.info("ℹ️ Edge labels hidden due to high density for better readability")
                with col_control2:
                    st.markdown(f"**Nodes:** {len(graph_data.get('nodes', []))} | **Edges:** {len(graph_data.get('relationships', []))}")
                with col_control3:
                    st.markdown("💡 **Tip:** Double-click to fit view")
                
                st.markdown("**Controls:** Drag nodes • Zoom with wheel • Pan by dragging background • Hover for details")
                
                html_content = kg_creator.create_interactive_graph(graph_data)
                if html_content:
                    # Display the interactive network
                    components.html(html_content, height=800, scrolling=False)
                    
                    # Add debug info
                    with st.expander("🔧 Debug Information"):
                        st.write(f"Nodes: {len(graph_data.get('nodes', []))}")
                        st.write(f"Relationships: {len(graph_data.get('relationships', []))}")
                        if st.checkbox("Show HTML source"):
                            st.code(html_content[:1000] + "..." if len(html_content) > 1000 else html_content, language="html")
                else:
                    st.error("Failed to create interactive graph. Falling back to static graph.")
                    fig = kg_creator.create_plotly_graph(graph_data)
                    st.plotly_chart(fig, use_container_width=True, height=800)
            else:
                # Create static Plotly graph
                st.markdown("### 📊 Static Knowledge Graph")
                fig = kg_creator.create_plotly_graph(graph_data)
                
                # Display the graph with enhanced configuration and full width
                st.plotly_chart(
                    fig, 
                    use_container_width=True,
                    height=800,  # Even larger height for better visibility
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToAdd': ['select2d', 'lasso2d'],
                        'modeBarButtonsToRemove': [],
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'knowledge_graph',
                            'height': 1000,
                            'width': 1600,
                            'scale': 2
                        }
                    }
                )

            # Graph Editing Interface
            if st.session_state.get('edit_mode', False):
                st.markdown("---")
                st.markdown("### ✏️ Edit Knowledge Graph")
                
                # Initialize edited data if not exists
                if 'edited_graph_data' not in st.session_state:
                    st.session_state['edited_graph_data'] = graph_data.copy()
                
                edited_data = st.session_state['edited_graph_data']
                
                # Tabs for editing nodes and relationships
                tab_nodes, tab_rels, tab_add, tab_json, tab_conversation = st.tabs(["📝 Edit Nodes", "🔗 Edit Relationships", "➕ Add New", "📋 JSON Editor", "💬 AI Conversation"])
                
                with tab_nodes:
                    st.subheader("Edit Existing Nodes")
                    
                    # Node selection and editing
                    node_options = {node['id']: f"{node.get('name', node['id'])} ({node.get('type', 'Unknown')})" 
                                  for node in edited_data.get('nodes', [])}
                    
                    if node_options:
                        selected_node_id = st.selectbox("Select node to edit:", options=list(node_options.keys()), 
                                                       format_func=lambda x: node_options[x])
                        
                        # Find the selected node
                        selected_node = next((n for n in edited_data['nodes'] if n['id'] == selected_node_id), None)
                        
                        if selected_node:
                            col_node1, col_node2 = st.columns(2)
                            
                            with col_node1:
                                new_name = st.text_input("Name:", value=selected_node.get('name', ''), key=f"edit_name_{selected_node_id}")
                                new_type = st.text_input("Type:", value=selected_node.get('type', ''), key=f"edit_type_{selected_node_id}")
                            
                            with col_node2:
                                new_desc = st.text_area("Description:", value=selected_node.get('description', ''), 
                                                       key=f"edit_desc_{selected_node_id}", height=100)
                                
                                col_update, col_delete = st.columns(2)
                                with col_update:
                                    if st.button("Update Node", type="primary", key=f"update_{selected_node_id}"):
                                        selected_node['name'] = new_name
                                        selected_node['type'] = new_type
                                        selected_node['description'] = new_desc
                                        # Sync JSON editor with updated data
                                        st.session_state['json_editor_content'] = json.dumps(edited_data, indent=2)
                                        st.success("Node updated!")
                                        st.rerun()
                                
                                with col_delete:
                                    if st.button("Delete Node", type="secondary", key=f"delete_{selected_node_id}"):
                                        # Remove node and its relationships
                                        edited_data['nodes'] = [n for n in edited_data['nodes'] if n['id'] != selected_node_id]
                                        edited_data['relationships'] = [r for r in edited_data['relationships'] 
                                                                      if r['source'] != selected_node_id and r['target'] != selected_node_id]
                                        # Sync JSON editor with updated data
                                        st.session_state['json_editor_content'] = json.dumps(edited_data, indent=2)
                                        st.success("Node deleted!")
                                        st.rerun()
                
                with tab_rels:
                    st.subheader("Edit Existing Relationships")
                    
                    # Relationship selection and editing
                    rel_options = {i: f"{rel['source']} → {rel['target']} ({rel.get('type', 'connected')})" 
                                 for i, rel in enumerate(edited_data.get('relationships', []))}
                    
                    if rel_options:
                        selected_rel_idx = st.selectbox("Select relationship to edit:", options=list(rel_options.keys()), 
                                                       format_func=lambda x: rel_options[x])
                        
                        selected_rel = edited_data['relationships'][selected_rel_idx]
                        
                        col_rel1, col_rel2 = st.columns(2)
                        
                        # Get available node IDs for source/target selection
                        node_ids = [node['id'] for node in edited_data['nodes']]
                        
                        with col_rel1:
                            new_source = st.selectbox("Source:", options=node_ids, 
                                                     index=node_ids.index(selected_rel['source']) if selected_rel['source'] in node_ids else 0,
                                                     key=f"edit_rel_source_{selected_rel_idx}")
                            new_target = st.selectbox("Target:", options=node_ids,
                                                     index=node_ids.index(selected_rel['target']) if selected_rel['target'] in node_ids else 0,
                                                     key=f"edit_rel_target_{selected_rel_idx}")
                        
                        with col_rel2:
                            new_rel_type = st.text_input("Relationship Type:", value=selected_rel.get('type', ''), 
                                                        key=f"edit_rel_type_{selected_rel_idx}")
                            new_rel_desc = st.text_area("Description:", value=selected_rel.get('description', ''), 
                                                       key=f"edit_rel_desc_{selected_rel_idx}", height=80)
                            
                            col_update_rel, col_delete_rel = st.columns(2)
                            with col_update_rel:
                                if st.button("Update Relationship", type="primary", key=f"update_rel_{selected_rel_idx}"):
                                    selected_rel['source'] = new_source
                                    selected_rel['target'] = new_target
                                    selected_rel['type'] = new_rel_type
                                    selected_rel['description'] = new_rel_desc
                                    # Sync JSON editor with updated data
                                    st.session_state['json_editor_content'] = json.dumps(edited_data, indent=2)
                                    st.success("Relationship updated!")
                                    st.rerun()
                            
                            with col_delete_rel:
                                if st.button("Delete Relationship", type="secondary", key=f"delete_rel_{selected_rel_idx}"):
                                    edited_data['relationships'].pop(selected_rel_idx)
                                    # Sync JSON editor with updated data
                                    st.session_state['json_editor_content'] = json.dumps(edited_data, indent=2)
                                    st.success("Relationship deleted!")
                                    st.rerun()
                
                with tab_add:
                    st.subheader("Add New Elements")
                    
                    # Add new node
                    st.markdown("**Add New Node**")
                    col_add1, col_add2 = st.columns(2)
                    
                    with col_add1:
                        new_node_id = st.text_input("Node ID:", key="new_node_id")
                        new_node_name = st.text_input("Node Name:", key="new_node_name")
                    
                    with col_add2:
                        new_node_type = st.text_input("Node Type:", key="new_node_type")
                        new_node_desc = st.text_area("Description:", key="new_node_desc", height=80)
                    
                    if st.button("Add Node", type="primary", key="add_new_node"):
                        if new_node_id and new_node_name:
                            new_node = {
                                'id': new_node_id,
                                'name': new_node_name,
                                'type': new_node_type or 'Unknown',
                                'description': new_node_desc or 'No description'
                            }
                            edited_data['nodes'].append(new_node)
                            # Sync JSON editor with updated data
                            st.session_state['json_editor_content'] = json.dumps(edited_data, indent=2)
                            st.success("Node added!")
                            st.rerun()
                        else:
                            st.error("Please provide both Node ID and Name")
                    
                    st.markdown("---")
                    
                    # Add new relationship
                    st.markdown("**Add New Relationship**")
                    if len(edited_data['nodes']) >= 2:
                        col_add_rel1, col_add_rel2 = st.columns(2)
                        
                        node_ids = [node['id'] for node in edited_data['nodes']]
                        
                        with col_add_rel1:
                            new_rel_source = st.selectbox("Source Node:", options=node_ids, key="new_rel_source")
                            new_rel_target = st.selectbox("Target Node:", options=node_ids, key="new_rel_target")
                        
                        with col_add_rel2:
                            new_rel_type_add = st.text_input("Relationship Type:", key="new_rel_type_add")
                            new_rel_desc_add = st.text_area("Description:", key="new_rel_desc_add", height=80)
                        
                        if st.button("Add Relationship", type="primary", key="add_new_rel"):
                            if new_rel_source != new_rel_target:
                                new_relationship = {
                                    'source': new_rel_source,
                                    'target': new_rel_target,
                                    'type': new_rel_type_add or 'connected',
                                    'description': new_rel_desc_add or ''
                                }
                                edited_data['relationships'].append(new_relationship)
                                # Sync JSON editor with updated data
                                st.session_state['json_editor_content'] = json.dumps(edited_data, indent=2)
                                st.success("Relationship added!")
                                st.rerun()
                            else:
                                st.error("Source and target must be different nodes")
                    else:
                        st.info("Add at least 2 nodes before creating relationships")
                
                with tab_json:
                    st.subheader("📋 Edit JSON Directly")
                    st.info("💡 **Tip:** Edit the JSON below and click 'Apply Changes' to update the graph visualization in real-time!")
                    
                    # Initialize JSON editor content
                    if 'json_editor_content' not in st.session_state:
                        st.session_state['json_editor_content'] = json.dumps(edited_data, indent=2)
                    
                    # JSON editor help
                    with st.expander("📖 JSON Structure Help"):
                        st.markdown("""
                        **Expected JSON Structure:**
                        ```json
                        {
                            "nodes": [
                                {
                                    "id": "unique_identifier",
                                    "name": "display_name",
                                    "type": "node_type",
                                    "description": "node_description"
                                }
                            ],
                            "relationships": [
                                {
                                    "source": "source_node_id",
                                    "target": "target_node_id", 
                                    "type": "relationship_type",
                                    "description": "relationship_description"
                                }
                            ]
                        }
                        ```
                        
                        **Tips:**
                        - Each node must have a unique `id`
                        - Relationships `source` and `target` must reference existing node `id`s
                        - Use descriptive `type` values for better visualization
                        - All fields except `id` are optional but recommended
                        """)
                    
                    # JSON text area with syntax highlighting
                    json_content = st.text_area(
                        "Edit Graph JSON:",
                        value=st.session_state['json_editor_content'],
                        height=400,
                        help="Edit the JSON structure directly. Click 'Validate & Preview' to check syntax and see changes.",
                        key="json_editor_input"
                    )
                    
                    # Update session state when content changes
                    if json_content != st.session_state['json_editor_content']:
                        st.session_state['json_editor_content'] = json_content
                    
                    # Action buttons for JSON editor
                    col_validate, col_apply, col_reset = st.columns(3)
                    
                    with col_validate:
                        if st.button("🔍 Validate JSON", type="secondary", use_container_width=True, key="validate_json_btn"):
                            try:
                                parsed_json = json.loads(json_content)
                                
                                # Validate structure
                                validation_errors = []
                                
                                # Check required top-level keys
                                if 'nodes' not in parsed_json:
                                    validation_errors.append("Missing 'nodes' array")
                                if 'relationships' not in parsed_json:
                                    validation_errors.append("Missing 'relationships' array")
                                
                                # Validate nodes
                                if 'nodes' in parsed_json:
                                    node_ids = set()
                                    for i, node in enumerate(parsed_json['nodes']):
                                        if not isinstance(node, dict):
                                            validation_errors.append(f"Node {i} is not an object")
                                            continue
                                        if 'id' not in node:
                                            validation_errors.append(f"Node {i} missing required 'id' field")
                                        else:
                                            if node['id'] in node_ids:
                                                validation_errors.append(f"Duplicate node id: '{node['id']}'")
                                            node_ids.add(node['id'])
                                
                                # Validate relationships
                                if 'relationships' in parsed_json and 'nodes' in parsed_json:
                                    for i, rel in enumerate(parsed_json['relationships']):
                                        if not isinstance(rel, dict):
                                            validation_errors.append(f"Relationship {i} is not an object")
                                            continue
                                        if 'source' not in rel:
                                            validation_errors.append(f"Relationship {i} missing 'source' field")
                                        elif rel['source'] not in node_ids:
                                            validation_errors.append(f"Relationship {i} source '{rel['source']}' not found in nodes")
                                        if 'target' not in rel:
                                            validation_errors.append(f"Relationship {i} missing 'target' field")
                                        elif rel['target'] not in node_ids:
                                            validation_errors.append(f"Relationship {i} target '{rel['target']}' not found in nodes")
                                
                                if validation_errors:
                                    st.error("❌ **Validation Errors:**")
                                    for error in validation_errors:
                                        st.error(f"• {error}")
                                else:
                                    st.success("✅ **JSON is valid!**")
                                    st.info(f"📊 Found {len(parsed_json.get('nodes', []))} nodes and {len(parsed_json.get('relationships', []))} relationships")
                                    
                            except json.JSONDecodeError as e:
                                st.error(f"❌ **JSON Syntax Error:** {str(e)}")
                            except Exception as e:
                                st.error(f"❌ **Validation Error:** {str(e)}")
                    
                    with col_apply:
                        if st.button("✅ Apply Changes", type="primary", use_container_width=True, key="apply_json_btn"):
                            try:
                                parsed_json = json.loads(json_content)
                                
                                # Basic validation
                                if 'nodes' not in parsed_json or 'relationships' not in parsed_json:
                                    st.error("❌ JSON must contain 'nodes' and 'relationships' arrays")
                                else:
                                    # Update the edited data
                                    st.session_state['edited_graph_data'] = parsed_json
                                    st.success("✅ **Changes applied!** The graph visualization will update.")
                                    st.info("💡 Click 'Save Changes' below to make the updates permanent.")
                                    # Force rerun to update the graph
                                    st.rerun()
                                    
                            except json.JSONDecodeError as e:
                                st.error(f"❌ **JSON Syntax Error:** {str(e)}")
                                st.error("Please fix the JSON syntax before applying changes.")
                            except Exception as e:
                                st.error(f"❌ **Error applying changes:** {str(e)}")
                    
                    with col_reset:
                        if st.button("🔄 Reset JSON", type="secondary", use_container_width=True, key="reset_json_btn"):
                            # Reset to current edited data
                            st.session_state['json_editor_content'] = json.dumps(edited_data, indent=2)
                            st.success("🔄 JSON reset to current graph state")
                            st.rerun()
                    
                    # Show JSON diff if changes were made
                    if 'edited_graph_data' in st.session_state:
                        current_json = json.dumps(st.session_state['edited_graph_data'], indent=2)
                        if current_json != json_content and json_content.strip():
                            with st.expander("📋 View Changes"):
                                st.info("**Current JSON in memory vs. Editor content:**")
                                col_current, col_editor = st.columns(2)
                                with col_current:
                                    st.markdown("**Current (Applied):**")
                                    st.code(current_json[:500] + "..." if len(current_json) > 500 else current_json, language="json")
                                with col_editor:
                                    st.markdown("**Editor (Pending):**")
                                    st.code(json_content[:500] + "..." if len(json_content) > 500 else json_content, language="json")
                
                with tab_conversation:
                    st.subheader("💬 AI-Powered Graph Refinement")
                    st.info("🤖 **Chat with GPT-4o** to refine your knowledge graph using natural language feedback!")
                    
                    # Initialize conversation handler
                    if 'conversation_handler' not in st.session_state:
                        openai_api_key = os.getenv('OPENAI_API_KEY')
                        if openai_api_key:
                            st.session_state['conversation_handler'] = JSONConversationHandler(openai_api_key)
                            # Start conversation with current graph data
                            original_text = st.session_state.get('original_text', '')
                            welcome_msg = st.session_state['conversation_handler'].start_conversation(edited_data, original_text)
                            st.session_state['conversation_welcome'] = welcome_msg
                        else:
                            st.error("OpenAI API key required for AI conversation. Please check your .env file.")
                            st.session_state['conversation_handler'] = None
                    
                    if st.session_state.get('conversation_handler'):
                        # Show welcome message or conversation
                        if 'conversation_welcome' in st.session_state:
                            st.markdown(st.session_state['conversation_welcome'])
                            st.markdown("---")
                        
                        # Initialize conversation history display
                        if 'conversation_messages' not in st.session_state:
                            st.session_state['conversation_messages'] = []
                        
                        # Display conversation history
                        if st.session_state['conversation_messages']:
                            st.markdown("### 📝 Conversation History")
                            for i, msg in enumerate(st.session_state['conversation_messages']):
                                if msg['role'] == 'user':
                                    st.chat_message("user").write(msg['content'])
                                else:
                                    st.chat_message("assistant").write(msg['content'])
                        
                        # User input for conversation
                        st.markdown("### 💭 What would you like to change?")
                        
                        # Examples of what users can ask
                        with st.expander("💡 Example requests you can make"):
                            st.markdown("""
                            **Adding entities:**
                            - "Add a new person named John Smith who works as a Data Scientist"
                            - "Create a Technology node for 'Machine Learning'"
                            
                            **Modifying relationships:**
                            - "Change the relationship between Alice and Google to 'leads team at'"
                            - "Add a relationship showing that SmartAssist uses Machine Learning"
                            
                            **Improving descriptions:**
                            - "Make the descriptions more detailed"
                            - "Add more context to the AI system entity"
                            
                            **Restructuring:**
                            - "Group related concepts together"
                            - "Split the large Organization node into separate departments"
                            """)
                        
                        # Chat input
                        user_input = st.text_area(
                            "Describe the changes you want to make:",
                            height=100,
                            placeholder="Example: 'Add a new relationship between Alice and Machine Learning showing she specializes in it'",
                            key="conversation_input"
                        )
                        
                        col_send, col_clear, col_undo = st.columns([2, 1, 1])
                        
                        with col_send:
                            if st.button("🚀 Send Message", type="primary", use_container_width=True, disabled=not user_input.strip()):
                                if user_input.strip():
                                    # Add user message to history
                                    st.session_state['conversation_messages'].append({
                                        'role': 'user',
                                        'content': user_input
                                    })
                                    
                                    # Process with conversation handler
                                    try:
                                        with st.spinner("🤔 AI is thinking..."):
                                            response, updated_json, is_valid = st.session_state['conversation_handler'].process_user_message(user_input)
                                        
                                        # Add assistant response to history
                                        st.session_state['conversation_messages'].append({
                                            'role': 'assistant',
                                            'content': response
                                        })
                                        
                                        if is_valid:
                                            # Update the edited data with AI changes
                                            st.session_state['edited_graph_data'] = updated_json
                                            # Update JSON editor content
                                            st.session_state['json_editor_content'] = json.dumps(updated_json, indent=2)
                                            st.success("✅ **Graph updated!** Check the JSON Editor tab or refresh the graph to see changes.")
                                        else:
                                            st.warning("⚠️ The AI's response contained invalid JSON. Please try rephrasing your request.")
                                    
                                    except Exception as e:
                                        st.error(f"❌ Error processing request: {str(e)}")
                                        st.session_state['conversation_messages'].append({
                                            'role': 'assistant',
                                            'content': f"I encountered an error: {str(e)}. Please try rephrasing your request."
                                        })
                                    
                                    # Clear input and rerun
                                    st.rerun()
                        
                        with col_clear:
                            if st.button("🗑️ Clear Chat", type="secondary", use_container_width=True):
                                st.session_state['conversation_messages'] = []
                                # Reset conversation handler
                                original_text = st.session_state.get('original_text', '')
                                welcome_msg = st.session_state['conversation_handler'].start_conversation(edited_data, original_text)
                                st.session_state['conversation_welcome'] = welcome_msg
                                st.rerun()
                        
                        with col_undo:
                            if st.button("↩️ Undo Last", type="secondary", use_container_width=True):
                                try:
                                    success, message = st.session_state['conversation_handler'].undo_last_change()
                                    if success:
                                        st.success(message)
                                        # Remove last assistant message from display
                                        if st.session_state['conversation_messages']:
                                            # Find and remove the last assistant message
                                            for i in range(len(st.session_state['conversation_messages']) - 1, -1, -1):
                                                if st.session_state['conversation_messages'][i]['role'] == 'assistant':
                                                    st.session_state['conversation_messages'] = st.session_state['conversation_messages'][:i]
                                                    break
                                        st.rerun()
                                    else:
                                        st.warning(message)
                                except Exception as e:
                                    st.error(f"Error undoing change: {str(e)}")
                        
                        # Conversation statistics
                        if st.session_state.get('conversation_handler'):
                            summary = st.session_state['conversation_handler'].get_conversation_summary()
                            if summary['total_messages'] > 0:
                                st.markdown("---")
                                col_stats1, col_stats2 = st.columns(2)
                                with col_stats1:
                                    st.metric("💬 Total Messages", summary['total_messages'])
                                    st.metric("📊 Current Nodes", summary['graph_stats']['nodes'])
                                with col_stats2:
                                    st.metric("🔗 Current Relationships", summary['graph_stats']['relationships'])
                                    if summary['graph_stats']['node_types']:
                                        st.write("**Node Types:**", ", ".join(summary['graph_stats']['node_types']))
                    
                    else:
                        st.error("💥 Conversation feature unavailable. Please ensure OpenAI API key is configured.")
                
                # Control buttons
                col_save_edit, col_cancel_edit, col_refresh = st.columns(3)
                
                with col_save_edit:
                    if st.button("💾 Save Changes", type="primary", use_container_width=True):
                        st.session_state['graph_data'] = edited_data.copy()
                        st.session_state['edit_mode'] = False
                        st.success("Changes saved! Graph updated.")
                        st.rerun()
                
                with col_cancel_edit:
                    if st.button("❌ Cancel Editing", type="secondary", use_container_width=True):
                        st.session_state['edit_mode'] = False
                        if 'edited_graph_data' in st.session_state:
                            del st.session_state['edited_graph_data']
                        st.rerun()
                
                with col_refresh:
                    if st.button("🔄 Refresh View", type="secondary", use_container_width=True):
                        # Update the displayed graph with edited data
                        st.session_state['graph_data'] = edited_data.copy()
                        # Sync JSON editor content with current edited data
                        st.session_state['json_editor_content'] = json.dumps(edited_data, indent=2)
                        st.rerun()

            # Actions and Statistics in columns below the graph
            st.markdown("---")
            col_actions, col_stats = st.columns([1, 1])
            
            with col_actions:
                st.subheader("🛠️ Actions")
                
                # Edit Graph button
                if st.button("✏️ Edit Graph", type="primary", use_container_width=True):
                    st.session_state['edit_mode'] = True
                    st.rerun()
                
                # Save to Neo4j option
                if st.button("💾 Save to Neo4j", type="secondary", use_container_width=True):
                    # Use edited data if available, otherwise original
                    save_data = st.session_state.get('edited_graph_data', graph_data)
                    with st.spinner("Saving to Neo4j database..."):
                        if kg_creator.save_to_neo4j(save_data):
                            st.success("Graph saved to Neo4j successfully!")
                        else:
                            st.error("Failed to save graph to Neo4j.")

                # JSON download
                download_data = st.session_state.get('edited_graph_data', graph_data)
                json_data = json.dumps(download_data, indent=2)
                st.download_button(
                    label="📥 Download as JSON",
                    data=json_data,
                    file_name="knowledge_graph.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col_stats:
                st.subheader("📈 Graph Statistics")
                
                col_stats1, col_stats2 = st.columns(2)
                with col_stats1:
                    st.metric("Nodes", len(graph_data.get('nodes', [])))
                    # Calculate unique node types
                    node_types = set(node.get('type', 'Unknown') for node in graph_data.get('nodes', []))
                    st.metric("Node Types", len(node_types))
                with col_stats2:
                    st.metric("Relationships", len(graph_data.get('relationships', [])))
                    # Calculate unique relationship types
                    rel_types = set(rel.get('type', 'Unknown') for rel in graph_data.get('relationships', []))
                    st.metric("Relationship Types", len(rel_types))

            # Additional information sections
            col_info1, col_info2, col_info3 = st.columns(3)
            
            with col_info1:
                # Additional graph information
                with st.expander("🔍 Detailed Graph Information"):
                    st.write("**Node Types:**")
                    for node_type in sorted(node_types):
                        count = sum(1 for node in graph_data.get('nodes', []) if node.get('type') == node_type)
                        st.write(f"• {node_type}: {count}")
                    
                    st.write("**Relationship Types:**")
                    for rel_type in sorted(rel_types):
                        count = sum(1 for rel in graph_data.get('relationships', []) if rel.get('type') == rel_type)
                        st.write(f"• {rel_type}: {count}")
            
            with col_info2:
                # Graph interaction tips
                with st.expander("💡 Interaction Tips"):
                    if viz_type == "Interactive Network (Recommended)":
                        st.write("**Interactive Network Controls:**")
                        st.write("• **Drag Nodes:** Click and drag any node to reposition")
                        st.write("• **Zoom:** Mouse wheel to zoom in/out")
                        st.write("• **Pan:** Click and drag empty space to move view")
                        st.write("• **Hover:** Mouse over nodes/edges for full details")
                        st.write("• **Physics:** Nodes will settle into natural positions")
                        st.write("• **Selection:** Click nodes to highlight connections")
                    else:
                        st.write("**Static Graph Controls:**")
                        st.write("• **Zoom:** Mouse wheel or toolbar buttons")
                        st.write("• **Pan:** Click and drag to move around")
                        st.write("• **Select:** Use toolbar to switch modes")
                        st.write("• **Hover:** Mouse over nodes for details")
                        st.write("• **Download:** Camera icon for high-res image")
            
            with col_info3:
                # Display raw data
                with st.expander("📄 View Raw Graph Data"):
                    st.json(graph_data)
                
        except Exception as e:
            st.error(f"Error creating graph visualization: {str(e)}")
            logger.error(f"Visualization error: {e}")
            import traceback
            st.text("Full error details:")
            st.code(traceback.format_exc())
    else:
        if 'graph_data' in st.session_state:
            st.info("🤔 No graph data to display. The analysis may not have generated any nodes or relationships.")
        else:
            st.info("👆 Choose an input method above and analyze your content to generate a knowledge graph.")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Built with ❤️ using Streamlit, Neo4j, and OpenAI GPT-4"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
