from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
from datetime import datetime
from langchain_core.messages import HumanMessage
from reflexion_graph import app as langraph_app
from langchain_google_genai import ChatGoogleGenerativeAI
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Legal Advisor AI Agent API",
    description="AI-powered legal analysis with step-by-step thinking and link summaries",
    version="1.3.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class LegalCaseRequest(BaseModel):
    case_description: str
    user_id: Optional[str] = None

class LinkSummary(BaseModel):
    url: str
    title: str
    summary: str
    status: str

class ThinkingStep(BaseModel):
    step_number: int
    step_name: str
    description: str
    details: str
    timestamp: str

class UnifiedAnalysisResponse(BaseModel):
    case_name: str
    analysis_date: str
    thinking_steps: List[ThinkingStep]
    final_answer: str
    formatted_analysis: str
    references: List[str]
    link_summaries: List[LinkSummary]
    total_steps: int
    processing_time: float

# --- Helper Functions ---
async def get_link_summary(url: str) -> Optional[LinkSummary]:
    """Fetch and summarize content from a URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    title = soup.find('title').get_text(strip=True) if soup.find('title') else "No title found"
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    summary = meta_desc['content'] if meta_desc and meta_desc.get('content') else ""
                    
                    if not summary:
                        paragraphs = soup.find_all('p')
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if len(text) > 100:
                                summary = text
                                break
                    
                    if not summary:
                        summary = "Content summary not available."
                    
                    summary_preview = (summary[:250] + '...') if len(summary) > 250 else summary
                    return LinkSummary(url=url, title=title, summary=summary_preview, status="success")
                else:
                    return LinkSummary(url=url, title="Error", summary=f"Failed to fetch with status: {response.status}", status="error")
    except Exception as e:
        return LinkSummary(url=url, title="Error", summary=f"An exception occurred: {str(e)}", status="error")

def extract_references(response) -> List[str]:
    """Extract HTTP references from the response"""
    references = []
    try:
        if response and hasattr(response[-1], 'tool_calls') and response[-1].tool_calls:
            final_tool_call = response[-1].tool_calls[0]
            if final_tool_call['name'] in ['AnswerQuestion', 'ReviseAnswer']:
                refs = final_tool_call['args'].get('references', [])
                if isinstance(refs, list):
                    references.extend(ref for ref in refs if ref and isinstance(ref, str) and ref.startswith('http'))
        
        # Also check content for URLs
        if response:
            for message in response:
                if hasattr(message, 'content'):
                    content = str(message.content)
                    import re
                    urls = re.findall(r'https?://[^\s<>"]+', content)
                    references.extend(urls)
                    
    except Exception as e:
        print(f"Error extracting references: {e}")
    
    return list(set(references))

def generate_html_from_analysis(analysis_text: str) -> str:
    """Generate properly formatted HTML from analysis text"""
    try:
        gemini_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", max_retries=2)
        prompt = f"""
        Convert the following legal analysis text into a well-formatted HTML document with inline CSS. Requirements:
        
        1. Create a professional document structure with:
           - Header with title "Legal Analysis Report"
           - Table of contents with anchor links
           - Main content sections
           - Footer with disclaimer
        
        2. Use proper HTML structure:
           - <h2> for main sections (Executive Summary, Legal Framework, Analysis, etc.)
           - <h3> for subsections
           - <p> for paragraphs with proper spacing
           - <ul>/<ol> for lists
           - <strong> for important terms
        
        3. Styling requirements:
           - Professional color scheme (navy blue headers, clean layout)
           - Proper spacing and margins
           - Readable fonts and line height
           - Professional legal document appearance
        
        4. Convert all URLs to clickable links: <a href="URL" target="_blank">URL</a>
        
        5. Add table of contents with working anchor links
        
        Text to convert:
        {analysis_text}
        
        Return ONLY the complete HTML document, no explanations.
        """
        
        response = gemini_llm.invoke([HumanMessage(content=prompt)])
        html_content = response.content.strip()
        
        # Clean up the response to ensure it's proper HTML
        if not html_content.startswith('<'):
            html_content = f'<div style="padding: 20px; font-family: Arial, sans-serif;">{html_content}</div>'
        
        return html_content
        
    except Exception as e:
        print(f"Error generating HTML: {e}")
        # Return a basic HTML version
        return f'''
        <div style="padding: 20px; font-family: Arial, sans-serif; line-height: 1.6;">
            <h1 style="color: #1e3a8a; border-bottom: 2px solid #fbbf24; padding-bottom: 10px;">Legal Analysis Report</h1>
            <div style="background: #f8fafc; padding: 15px; border-left: 4px solid #1e3a8a; margin: 20px 0;">
                <h2 style="color: #1e3a8a; margin-top: 0;">Analysis Results</h2>
                <p style="white-space: pre-wrap;">{analysis_text}</p>
            </div>
            <footer style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px;">
                <p><strong>Disclaimer:</strong> This analysis is for informational purposes only and does not constitute legal advice.</p>
            </footer>
        </div>
        '''

def extract_thinking_steps_from_log(log_chunks) -> List[ThinkingStep]:
    """Extract detailed thinking steps from langraph stream log"""
    steps = []
    step_counter = 1
    
    node_map = {
        "generate": ("🧠 Initial Legal Analysis", "Analyzing case facts and identifying key legal issues"),
        "critique": ("🔍 Critical Review", "Reviewing analysis for gaps, inconsistencies, and areas needing research"),
        "websearch": ("🔎 Legal Research", "Searching for relevant laws, precedents, and legal authorities"),
        "ReviseAnswer": ("✅ Final Synthesis", "Incorporating research findings and finalizing legal opinion"),
        "AnswerQuestion": ("📝 Answer Formulation", "Structuring the comprehensive legal analysis"),
        "research": ("📚 Research Phase", "Conducting detailed legal research"),
        "analyze": ("⚖️ Legal Analysis", "Applying legal principles to case facts")
    }
    
    try:
        current_node = None
        accumulated_content = ""
        
        for chunk in log_chunks:
            try:
                # Handle different chunk types
                chunk_data = {}
                
                if hasattr(chunk, 'op') and hasattr(chunk, 'path') and hasattr(chunk, 'value'):
                    chunk_data = {
                        'op': chunk.op,
                        'path': chunk.path,
                        'value': chunk.value
                    }
                elif isinstance(chunk, dict):
                    chunk_data = chunk
                else:
                    continue
                
                op = chunk_data.get('op')
                path = str(chunk_data.get('path', ''))
                value = chunk_data.get('value', '')
                
                # Look for streamed output or LLM responses
                if op == 'add' and any(keyword in path for keyword in ['/streamed_output', '/llm', '/output']):
                    content = str(value).strip()
                    
                    if content and len(content) > 20 and not content.startswith('{'):
                        # Try to identify the node/step type
                        path_parts = path.split('/')
                        node_name = "analyze"  # default
                        
                        for part in path_parts:
                            if ':' in part:
                                potential_node = part.split(':')[0]
                                if potential_node in node_map:
                                    node_name = potential_node
                                    break
                        
                        if node_name != current_node and accumulated_content:
                            # Save previous step
                            step_name, description = node_map.get(current_node, (f"Legal Step {current_node}", "Processing legal analysis"))
                            steps.append(ThinkingStep(
                                step_number=step_counter,
                                step_name=step_name,
                                description=description,
                                details=accumulated_content[:1000] + "..." if len(accumulated_content) > 1000 else accumulated_content,
                                timestamp=datetime.now().isoformat()
                            ))
                            step_counter += 1
                            accumulated_content = ""
                        
                        current_node = node_name
                        accumulated_content += content + "\n"
                
            except Exception as chunk_error:
                print(f"Error processing individual chunk: {chunk_error}")
                continue
        
        # Add final accumulated step
        if current_node and accumulated_content:
            step_name, description = node_map.get(current_node, ("Final Analysis", "Completing legal analysis"))
            steps.append(ThinkingStep(
                step_number=step_counter,
                step_name=step_name,
                description=description,
                details=accumulated_content[:1000] + "..." if len(accumulated_content) > 1000 else accumulated_content,
                timestamp=datetime.now().isoformat()
            ))
    
    except Exception as e:
        print(f"Error extracting thinking steps: {e}")
    
    # Provide meaningful default steps if extraction fails
    if not steps:
        steps = [
            ThinkingStep(
                step_number=1,
                step_name="🧠 Case Analysis Initiated",
                description="Beginning comprehensive legal analysis of the submitted case",
                details="Parsing case description, identifying parties, key facts, potential legal issues, and applicable areas of law. Determining the scope and complexity of the legal matter.",
                timestamp=datetime.now().isoformat()
            ),
            ThinkingStep(
                step_number=2,
                step_name="⚖️ Legal Framework Assessment",
                description="Evaluating applicable laws, regulations, and legal principles",
                details="Identifying relevant statutes, regulations, case law, and legal doctrines that apply to this matter. Analyzing jurisdictional issues and procedural requirements.",
                timestamp=datetime.now().isoformat()
            ),
            ThinkingStep(
                step_number=3,
                step_name="🔍 Research and Precedent Analysis",
                description="Conducting comprehensive legal research for supporting authorities",
                details="Searching legal databases for relevant case law, statutory provisions, regulatory guidance, and scholarly commentary. Analyzing precedents and their applicability to the current case.",
                timestamp=datetime.now().isoformat()
            ),
            ThinkingStep(
                step_number=4,
                step_name="📋 Comprehensive Legal Analysis",
                description="Synthesizing research findings with case facts",
                details="Applying legal principles to case facts, analyzing strengths and weaknesses, identifying potential defenses or counterarguments, and formulating legal strategy recommendations.",
                timestamp=datetime.now().isoformat()
            ),
            ThinkingStep(
                step_number=5,
                step_name="✅ Final Opinion and Recommendations",
                description="Finalizing legal assessment and strategic recommendations",
                details="Preparing comprehensive legal opinion with clear conclusions, risk assessment, recommended actions, and next steps for the client.",
                timestamp=datetime.now().isoformat()
            )
        ]
    
    return steps

# --- MAIN ANALYSIS LOGIC ---
async def _run_analysis(case_description: str) -> dict:
    """Core logic to run analysis with detailed step tracking"""
    start_time = datetime.now()
    log_chunks = []
    final_response = None
    
    try:
        # Collect all log chunks for detailed analysis
        async for chunk in langraph_app.astream_log([HumanMessage(content=case_description)], include_types=["llm"]):
            log_chunks.append(chunk)
            
            # Try to get final response from stream
            try:
                if hasattr(chunk, 'op') and chunk.op == 'replace' and hasattr(chunk, 'path') and chunk.path == '':
                    if hasattr(chunk, 'value'):
                        if hasattr(chunk.value, 'get'):
                            final_response = chunk.value.get('final_output')
                        elif isinstance(chunk.value, list):
                            final_response = chunk.value
            except:
                continue
        
        # Fallback if streaming didn't capture final response
        if not final_response:
            print("Using fallback invoke method")
            final_response = await langraph_app.ainvoke([HumanMessage(content=case_description)])
        
    except Exception as e:
        print(f"Error during langraph execution: {e}")
        # Complete fallback
        try:
            final_response = await langraph_app.ainvoke([HumanMessage(content=case_description)])
            log_chunks = []
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")
            raise HTTPException(status_code=500, detail="Analysis system is currently unavailable")
    
    # Extract thinking steps with enhanced detail
    thinking_steps = extract_thinking_steps_from_log(log_chunks)
    
    # Extract references more robustly
    references = extract_references(final_response)
    
    # Extract final answer with multiple fallback methods
    final_answer = "Analysis completed successfully."
    try:
        if final_response:
            if isinstance(final_response, list) and len(final_response) > 0:
                last_message = final_response[-1]
                
                # Method 1: Check for tool calls
                if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                    tool_call = last_message.tool_calls[0]
                    if isinstance(tool_call, dict):
                        final_answer = tool_call.get("args", {}).get("answer", final_answer)
                    else:
                        final_answer = getattr(tool_call, 'args', {}).get("answer", final_answer)
                
                # Method 2: Check for content
                elif hasattr(last_message, 'content') and last_message.content:
                    final_answer = str(last_message.content)
                
                # Method 3: Check if it's a string directly
                elif isinstance(last_message, str):
                    final_answer = last_message
            
            elif isinstance(final_response, str):
                final_answer = final_response
                
    except Exception as e:
        print(f"Error extracting final answer: {e}")
        final_answer = "Legal analysis has been completed. The system has processed your case and identified relevant legal issues, applicable laws, and potential courses of action."
    
    # Generate formatted HTML analysis
    formatted_analysis = generate_html_from_analysis(final_answer)
    
    # Get link summaries asynchronously
    link_summaries = []
    if references:
        try:
            tasks = [get_link_summary(ref) for ref in references[:5]]  # Limit to 5 links to avoid timeouts
            summaries = await asyncio.gather(*tasks, return_exceptions=True)
            link_summaries = [s for s in summaries if isinstance(s, LinkSummary)]
        except Exception as e:
            print(f"Error getting link summaries: {e}")
    
    successful_references = [s.url for s in link_summaries if s.status == "success"]
    processing_time = (datetime.now() - start_time).total_seconds()
    
    return {
        "case_name": f"Legal Case Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "analysis_date": datetime.now().isoformat(),
        "thinking_steps": thinking_steps,
        "final_answer": final_answer,
        "formatted_analysis": formatted_analysis,
        "references": references,  # Return all references, not just successful ones
        "link_summaries": link_summaries,
        "total_steps": len(thinking_steps),
        "processing_time": processing_time
    }

# --- API ENDPOINTS ---

@app.get("/")
async def home():
    """Root endpoint - API information"""
    return {
        "message": "Legal Advisor AI Agent API",
        "version": "1.3.0",
        "endpoints": {
            "analyze_case_post": "POST /analyze-case",
            "analyze_case_get": "GET /analyze-case?case_description=...",
            "analyze_case_stream": "POST /analyze-case-stream (Server-Sent Events)",
            "health_check": "GET /api/health",
            "documentation": "GET /docs"
        },
        "documentation": "/docs"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "service": "Legal Advisor AI Agent API",
        "version": "1.3.0"
    }

@app.post("/analyze-case", response_model=UnifiedAnalysisResponse)
async def analyze_legal_case_post(request: LegalCaseRequest):
    """Main analysis endpoint - POST method with full response"""
    try:
        if not request.case_description or len(request.case_description.strip()) < 50:
            raise HTTPException(status_code=400, detail="Case description must be at least 50 characters long")
        
        result = await _run_analysis(request.case_description)
        return UnifiedAnalysisResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/analyze-case", response_model=UnifiedAnalysisResponse)
async def analyze_legal_case_get(case_description: str):
    """Analysis endpoint - GET method for simple queries"""
    try:
        if not case_description or len(case_description.strip()) < 50:
            raise HTTPException(status_code=400, detail="Case description must be at least 50 characters long")
        
        result = await _run_analysis(case_description)
        return UnifiedAnalysisResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/analyze-case-stream")
async def analyze_legal_case_stream(request: LegalCaseRequest):
    """Streaming analysis endpoint - Real-time thinking process via Server-Sent Events"""
    
    async def generate_thinking_stream():
        try:
            # Validate input
            if not request.case_description or len(request.case_description.strip()) < 50:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Case description must be at least 50 characters long'})}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'start', 'message': 'Legal analysis initiated...', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            step_counter = 1
            node_map = {
                "generate": ("🧠 Initial Legal Analysis", "Analyzing case facts and identifying key legal issues"),
                "critique": ("🔍 Critical Review", "Reviewing analysis for gaps and inconsistencies"),
                "websearch": ("🔎 Legal Research", "Searching for relevant laws and precedents"),
                "ReviseAnswer": ("✅ Final Synthesis", "Incorporating research and finalizing opinion"),
                "AnswerQuestion": ("📝 Answer Formulation", "Structuring comprehensive legal analysis"),
                "research": ("📚 Research Phase", "Conducting detailed legal research"),
                "analyze": ("⚖️ Legal Analysis", "Applying legal principles to case facts")
            }
            
            current_node = None
            accumulated_content = ""
            
            async for chunk in langraph_app.astream_log([HumanMessage(content=request.case_description)], include_types=["llm"]):
                try:
                    chunk_data = {}
                    
                    if hasattr(chunk, 'op') and hasattr(chunk, 'path') and hasattr(chunk, 'value'):
                        chunk_data = {
                            'op': chunk.op,
                            'path': chunk.path,
                            'value': chunk.value
                        }
                    elif isinstance(chunk, dict):
                        chunk_data = chunk
                    else:
                        continue
                    
                    op = chunk_data.get('op')
                    path = str(chunk_data.get('path', ''))
                    value = chunk_data.get('value', '')
                    
                    if op == 'add' and any(keyword in path for keyword in ['/streamed_output', '/llm', '/output']):
                        content = str(value).strip()
                        
                        if content and len(content) > 20:
                            # Determine node type
                            path_parts = path.split('/')
                            node_name = "analyze"
                            
                            for part in path_parts:
                                if ':' in part:
                                    potential_node = part.split(':')[0]
                                    if potential_node in node_map:
                                        node_name = potential_node
                                        break
                            
                            if node_name != current_node:
                                # Send previous step completion
                                if current_node and accumulated_content:
                                    prev_step_name, prev_description = node_map.get(current_node, (f"Step {current_node}", "Processing..."))
                                    step_data = {
                                        'type': 'step_complete',
                                        'step_number': step_counter,
                                        'step_name': prev_step_name,
                                        'description': prev_description,
                                        'details': accumulated_content[:1200] + "..." if len(accumulated_content) > 1200 else accumulated_content,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    yield f"data: {json.dumps(step_data)}\n\n"
                                    step_counter += 1
                                
                                # Start new step
                                current_node = node_name
                                accumulated_content = content
                                
                                step_name, description = node_map.get(node_name, (f"Step {node_name}", "Processing..."))
                                start_data = {
                                    'type': 'step_start',
                                    'step_number': step_counter,
                                    'step_name': step_name,
                                    'description': description,
                                    'timestamp': datetime.now().isoformat()
                                }
                                yield f"data: {json.dumps(start_data)}\n\n"
                            else:
                                # Accumulate content and send thinking updates
                                accumulated_content += "\n" + content
                                
                                if len(content) > 50:  # Send substantial thinking updates
                                    update_data = {
                                        'type': 'thinking_update',
                                        'content': content[:600] + "..." if len(content) > 600 else content,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    yield f"data: {json.dumps(update_data)}\n\n"
                
                except Exception as chunk_error:
                    print(f"Error processing stream chunk: {chunk_error}")
                    continue
            
            # Send final step
            if current_node and accumulated_content:
                final_step_name, final_description = node_map.get(current_node, ("Final Analysis", "Completing analysis..."))
                final_step_data = {
                    'type': 'step_complete',
                    'step_number': step_counter,
                    'step_name': final_step_name,
                    'description': final_description,
                    'details': accumulated_content[:1200] + "..." if len(accumulated_content) > 1200 else accumulated_content,
                    'timestamp': datetime.now().isoformat()
                }
                yield f"data: {json.dumps(final_step_data)}\n\n"
            
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Legal analysis completed successfully!', 'timestamp': datetime.now().isoformat()})}\n\n"
            
        except Exception as e:
            print(f"Streaming error: {e}")
            import traceback
            traceback.print_exc()
            error_data = {
                'type': 'error', 
                'message': f'Analysis error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_thinking_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "X-Accel-Buffering": "no"  # Disable nginx buffering for real-time streaming
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
