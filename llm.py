"""
LLM suggestion engine for multitask_helper.
Abstracts LLM implementation details and provides clean interface.
Uses qnn_sample_apps-main library following the pattern in main.py.
"""

import sys
import logging
from pathlib import Path
from typing import List, Tuple, Optional

from windows import WindowInfo

# Add QNN path following the pattern from qnn_sample_apps-main/src/llm/main.py
qnn_src_path = Path(__file__).parent / "qnn_sample_apps-main" / "src"
sys.path.append(str(qnn_src_path))

try:
    from model_loader import ModelLoader
    
    # Add llm subdirectory to path
    llm_path = Path(__file__).parent / "qnn_sample_apps-main" / "src" / "llm"
    sys.path.append(str(llm_path))
    
    from deepseek_model_inference import DeepSeekModelInference
    from gemma_model_inference import GemmaModelInference
    LLM_AVAILABLE = True
except ImportError as e:
    logging.warning(f"LLM components not available: {e}")
    LLM_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMSuggestionEngine:
    """LLM-powered window suggestion engine using qnn_sample_apps-main library"""
    
    def __init__(self, model: str = "deepseek_1.5b", processor: str = "npu", model_type: str = "default"):
        self.model = model
        self.processor = processor
        self.model_type = model_type
        self.model_inference = None
        self.is_initialized = False
        self.max_tokens_per_query = 64  # Token limit per query
        
        if LLM_AVAILABLE:
            self._initialize_model()
    
    def get_suggestions(self, clipboard_content: str, current_window: Optional[WindowInfo], 
                       available_windows: List[WindowInfo]) -> Optional[List[Tuple[str, WindowInfo, str]]]:
        """
        Get LLM-powered window suggestions.
        Returns None if LLM fails or suggests using rule-based fallback.
        """
        if not self.is_initialized or not available_windows:
            return None
        
        try:
            logger.info("Starting LLM multi-step analysis...")
            
            # Step 1: Classify content with LLM
            content_type = self._classify_content(clipboard_content)
            if not content_type:
                logger.warning("Content classification failed, falling back to rules")
                return None
            
            logger.info(f"LLM classified content as: {content_type}")
            
            # Step 2: Score each window individually
            window_scores = []
            for window in available_windows[:5]:  # Limit to 5 windows for efficiency
                score = self._score_window(clipboard_content, content_type, window)
                if score is not None:
                    window_scores.append((window, score))
                    logger.info(f"LLM scored {window.process_name[:8]}: {score:.2f}")
            
            # If LLM scored fewer than 2 windows, fall back to rules
            if len(window_scores) < 2:
                logger.warning(f"LLM only scored {len(window_scores)} windows, falling back to rules")
                return None
            
            # Step 3: Sort by score and create suggestions
            window_scores.sort(key=lambda x: x[1], reverse=True)
            suggestions = []
            
            for i, (window, score) in enumerate(window_scores[:3]):
                reason = f"AI Rank #{i+1}"
                confidence = f"Score: {score:.2f}"
                suggestions.append((reason, window, confidence))
            
            logger.info(f"LLM generated {len(suggestions)} suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"LLM suggestion failed: {e}")
            return None
    
    def _initialize_model(self):
        """Initialize the model using qnn_sample_apps-main pattern"""
        try:
            logger.info(f"Initializing {self.model} with {self.processor} processor...")
            
            # Change to QNN directory for model loading (following main.py pattern)
            original_cwd = Path.cwd()
            qnn_dir = Path(__file__).parent / "qnn_sample_apps-main"
            
            import os
            os.chdir(str(qnn_dir))
            
            try:
                # Initialize model loader following main.py pattern
                iLoad = ModelLoader(
                    model=self.model,
                    processor=self.processor,
                    model_type=self.model_type
                )
                
                model_subdirectory = iLoad.model_subdirectory_path
                graphs = iLoad.graphs
                
                # Load model sessions following main.py pattern
                model_sessions = {
                    graph_name: iLoad.load_model(graph, htp_performance_mode="sustained_high_performance") 
                    for graph_name, graph in graphs.items() 
                    if str(graph).endswith(".onnx")
                }
                
                tokenizer = next((file for file in graphs.values() if file.endswith("tokenizer.json")), None)
                meta_data = graphs["META_DATA"]
                
                # Initialize inference engine following main.py pattern
                if "deepseek" in self.model.lower():
                    self.model_inference = DeepSeekModelInference(
                        model_sessions=model_sessions,
                        tokenizer=tokenizer,
                        model_subdirectory=model_subdirectory,
                        model_meta=meta_data,
                        verbose=0  # Keep quiet for production
                    )
                elif "gemma" in self.model.lower():
                    self.model_inference = GemmaModelInference(
                        model_sessions=model_sessions,
                        tokenizer=tokenizer,
                        model_subdirectory=model_subdirectory,
                        model_meta=meta_data
                    )
                else:
                    raise ValueError(f"Unsupported model type: {self.model}")
                
                self.is_initialized = True
                logger.info("LLM initialized successfully!")
                
            finally:
                os.chdir(str(original_cwd))
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.is_initialized = False
    
    def _classify_content(self, clipboard_content: str) -> Optional[str]:
        """Step 1: Hybrid classification - rule-based for clear cases, LLM for ambiguous"""
        
        # First try rule-based classification
        from rule import ContentClassifier
        classifier = ContentClassifier()
        rule_type, rule_confidence = classifier.classify_content(clipboard_content)
        
        # If rule-based is very confident, use it
        if rule_confidence >= 0.8:
            logger.info(f"Rule-based classification: {rule_type} (confidence: {rule_confidence:.2f})")
            return rule_type
        
        # For ambiguous cases, use LLM with simplified approach
        content_preview = clipboard_content[:35] + "..." if len(clipboard_content) > 35 else clipboard_content
        
        # Try a simpler LLM approach - just ask for the most likely type
        prompt = f'Text:"{content_preview}".Most likely: code/web/email/file/data/password/text'
        
        try:
            response = self._query_llm(prompt, max_tokens=32, temperature=0.1)
            if response:
                response_lower = response.lower().strip()
                
                # Look for keywords in response
                type_keywords = {
                    'code': 'CODE',
                    'web': 'WEB',
                    'url': 'WEB',  # fallback for old responses
                    'email': 'EMAIL', 
                    'file': 'FILE',
                    'data': 'DATA',
                    'password': 'PASSWORD',
                    'text': 'TEXT'
                }
                
                for keyword, result_type in type_keywords.items():
                    if keyword in response_lower:
                        logger.info(f"LLM classification: {result_type} (response: '{response.strip()}')")
                        return result_type
            
            # If LLM fails, fall back to rule-based result
            logger.info(f"LLM failed, using rule-based: {rule_type} (confidence: {rule_confidence:.2f})")
            return rule_type
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}, using rule-based: {rule_type}")
            return rule_type
    
    
    def _get_app_context(self, process_name: str) -> str:
        """Get contextual information about what the application does"""
        app_name = process_name.lower().replace('.exe', '')
        
        # Common application categories
        app_contexts = {
            'msedge': 'browser',
            'chrome': 'browser', 
            'firefox': 'browser',
            'notepad': 'text editor',
            'notepad++': 'code editor',
            'code': 'code editor',
            'excel': 'spreadsheet',
            'word': 'document editor',
            'outlook': 'email client',
            'olk': 'email client',  # Outlook (olk.exe)
            'winmail': 'email client',  # Windows Mail
            'hxmail': 'email client',  # Modern Outlook
            'hxoutlook': 'email client',  # Modern Outlook
            'outlookforwindows': 'email client',  # Modern Outlook
            'thunderbird': 'email client',
            'mailspring': 'email client',
            'spark': 'email client',
            'teams': 'communication',
            'discord': 'communication',
            'slack': 'communication',
            'cmd': 'command terminal',
            'powershell': 'command terminal',
            'explorer': 'file manager',
            'calculator': 'calculator',
            'paint': 'image editor',
            'photoshop': 'image editor'
        }
        
        # Look for partial matches
        for app_key, context in app_contexts.items():
            if app_key in app_name:
                return context
                
        return 'application'
    
    def _score_window(self, clipboard_content: str, content_type: str, window: WindowInfo) -> Optional[float]:
        """Step 2: Score window likelihood based on content class with app context"""
        app_name = window.process_name.replace('.exe', '')[:8]
        app_context = self._get_app_context(window.process_name)
        
        # Simple scoring prompt for production
        prompt = f'{app_name} for {content_type.lower()} (0-5):'
        
        try:
            response = self._query_llm(prompt, max_tokens=10, temperature=0.1)
            if not response or not response.strip():
                logger.warning(f"Empty response from LLM for {app_name}")
                return None
            
            # Extract numeric score (0-5) with improved parsing
            import re
            response_clean = response.strip()
            logger.info(f"Raw LLM response for {app_name}: '{response_clean}'")
            
            # Remove think tags and cleanup formatting
            response_clean = re.sub(r'</think>.*?<think>', '', response_clean, flags=re.DOTALL)
            response_clean = re.sub(r'</?think>.*?</think>', '', response_clean, flags=re.DOTALL)
            response_clean = re.sub(r'</?think>', '', response_clean)
            response_clean = re.sub(r'[/-]+', ' ', response_clean)  # Remove formatting chars
            response_clean = response_clean.strip()
            
            if not response_clean:
                logger.warning(f"Response empty after cleaning for {app_name}")
                return None
            
            # Handle yes/no responses first
            if 'yes' in response_clean.lower():
                normalized = 0.8  # High score for yes
                logger.info(f"App scoring ({app_context}): {app_name} for {content_type} -> yes (0.80)")
                return normalized
            elif 'no' in response_clean.lower():
                normalized = 0.2  # Low score for no
                logger.info(f"App scoring ({app_context}): {app_name} for {content_type} -> no (0.20)")
                return normalized
            
            # Special handling for "12345" pattern - means score 5
            if '12345' in response_clean:
                normalized = 1.0  # Score 5/5
                logger.info(f"App scoring ({app_context}): {app_name} for {content_type} -> 5/5 (1.00) [12345 pattern]")
                return normalized
            
            # Look for explicit numeric scores (0-5, including decimals)
            scores = re.findall(r'([0-5](?:\.[0-9]+)?)', response_clean)
            if scores:
                # Convert to floats and get the highest valid score
                valid_scores = []
                for score_str in scores:
                    try:
                        score = float(score_str)
                        if 0 <= score <= 5:
                            valid_scores.append(score)
                    except ValueError:
                        continue
                
                if valid_scores:
                    highest = max(valid_scores)
                    normalized = min(1.0, highest / 5.0)  # Normalize to 0-1 scale
                    logger.info(f"App scoring ({app_context}): {app_name} for {content_type} -> {highest}/5 ({normalized:.2f})")
                    return normalized

            # Handle conversational responses with numbers
            conversational_match = re.search(r'(?:okay|sure|yes|alright)[,\s]*([0-5](?:\.[0-9])?)', response_clean.lower())
            if conversational_match:
                score = float(conversational_match.group(1))
                normalized = min(1.0, score / 5.0)
                logger.info(f"App scoring (conversational): {app_name} for {content_type} -> {score}/5 ({normalized:.2f})")
                return normalized
            
            # Look for rating words and convert to 0-5 scale
            rating_words = {
                'perfect': 5, 'excellent': 5, 'great': 4, 'good': 3, 'decent': 3,
                'fair': 2, 'poor': 2, 'bad': 1, 'terrible': 1, 'awful': 0, 'none': 0
            }
            for word, score in rating_words.items():
                if word in response_clean.lower():
                    normalized = score / 5.0
                    logger.info(f"App scoring (word): {app_name} for {content_type} -> {word}={score}/5 ({normalized:.2f})")
                    return normalized
            
            logger.warning(f"No valid score found in response for {app_name}: '{response_clean}'")
            return None
            
        except Exception as e:
            logger.error(f"Window scoring failed for {app_name}: {e}")
            return None
    
    def _query_llm(self, prompt: str, max_tokens: int = 10, temperature: float = 0.2) -> Optional[str]:
        """Query the LLM with token limit enforcement"""
        if not self.is_initialized:
            return None
        
        try:
            # Following main.py pattern for run_inference call
            response = self.model_inference.run_inference(
                query=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_k=10,
                repetition_penalty=1.1,
                io_binding=True
            )
            
            return response.strip() if response else None
            
        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            return None
    
    def is_ready(self) -> bool:
        """Check if LLM is ready to process queries"""
        return self.is_initialized and LLM_AVAILABLE
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            'model': self.model,
            'processor': self.processor,
            'model_type': self.model_type,
            'available': LLM_AVAILABLE,
            'initialized': self.is_initialized,
            'max_tokens_per_query': self.max_tokens_per_query
        }