"""
Rule-based suggestion engine for multitask_helper.
Provides fallback suggestions when LLM is unavailable or returns None.
"""

import re
from typing import List, Tuple, Optional
from windows import WindowInfo


class ContentClassifier:
    """Classifies clipboard content using rule-based patterns"""
    
    def __init__(self):
        # Enhanced code patterns with weights
        self.code_patterns = {
            'high': ['def ', 'function ', 'class ', 'import ', 'from ', '#include', 
                    'public class', 'SELECT ', 'FROM ', 'CREATE TABLE', 'INSERT INTO'],
            'medium': ['private ', 'public ', 'var ', 'let ', 'const ', '=>', 'function(',
                      'if (', 'for (', 'while (', 'catch (', 'try {'],
            'low': ['{', '}', '==', '!=', '&&', '||', '++', '--']
        }
        
        self.file_extensions = [
            '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', 
            '.csv', '.xlsx', '.pdf', '.doc', '.ppt', '.zip', '.rar'
        ]
    
    def classify_content(self, content: str) -> Tuple[str, float]:
        """Classify clipboard content type with confidence score"""
        content_lower = content.lower().strip()
        content_clean = content.strip()
        
        # URL detection with confidence
        url_indicators = ['http://', 'https://', 'www.', 'ftp://']
        if any(content_lower.startswith(indicator) for indicator in url_indicators):
            confidence = 0.95 if content_lower.startswith(('http://', 'https://')) else 0.85
            return "WEB", confidence
        
        # Domain name detection (like qualcomm.com, github.io, etc.)
        domain_tlds = ['.com', '.org', '.net', '.edu', '.gov', '.io', '.co', '.ai', '.dev']
        if ('.' in content and ' ' not in content.strip() and 
            any(content_lower.endswith(tld) for tld in domain_tlds) and
            len(content.split('.')) >= 2):
            confidence = 0.85
            return "WEB", confidence
        
        # Enhanced email detection - both addresses and content
        if '@' in content and '.' in content:
            parts = content.split('@')
            if len(parts) == 2 and '.' in parts[1] and len(parts[1].split('.')) >= 2:
                domain_parts = parts[1].split('.')
                confidence = 0.9 if len(domain_parts[-1]) >= 2 else 0.7
                return "EMAIL", confidence
        
        # Email content patterns
        email_patterns = [
            'dear ', 'hello ', 'hi ', 'greetings',
            'sincerely', 'best regards', 'kind regards', 'yours truly',
            'subject:', 'to:', 'from:', 'cc:', 'bcc:',
            '[recipient', 'dear sir', 'dear madam'
        ]
        content_words = content_lower.replace('\n', ' ')
        email_indicators = sum(1 for pattern in email_patterns if pattern in content_words)
        if email_indicators >= 2 or (email_indicators >= 1 and len(content.split('\n')) > 2):
            confidence = min(0.9, 0.6 + (email_indicators * 0.1))
            return "EMAIL", confidence
        
        # Enhanced file path detection
        if ('\\\\' in content or '/' in content) and len(content.split()) == 1:
            has_extension = any(content_lower.endswith(ext) for ext in self.file_extensions)
            confidence = 0.9 if has_extension else 0.7
            return "FILE", confidence
        
        # Enhanced password detection
        if (len(content) < 50 and ' ' not in content and 
            any(c.isdigit() for c in content) and any(c.isalpha() for c in content)):
            has_special = any(c in '!@#$%^&*()_+-=' for c in content)
            mixed_case = any(c.isupper() for c in content) and any(c.islower() for c in content)
            confidence = 0.8 if has_special and mixed_case else 0.6
            return "PASSWORD", confidence
        
        # Code pattern detection with scoring
        code_score = 0
        for weight, patterns in self.code_patterns.items():
            matches = sum(1 for pattern in patterns if pattern in content_lower)
            if weight == 'high':
                code_score += matches * 0.4
            elif weight == 'medium':
                code_score += matches * 0.25
            else:
                code_score += matches * 0.1
        
        if code_score >= 0.3:
            confidence = min(0.95, 0.5 + code_score)
            return "CODE", confidence
        
        # Enhanced data detection
        data_indicators = ['\t', ',', '|', ';']  # Common data separators
        lines = content.split('\n')
        if len(lines) > 3:  # Multiple lines
            # Check for tabular data patterns
            separator_count = sum(1 for line in lines[:5] for sep in data_indicators if sep in line)
            if separator_count >= 3:
                confidence = 0.8 if '\t' in content or ',' in content else 0.6
                return "DATA", confidence
        
        # Check for numeric patterns
        numbers = len([c for c in content if c.isdigit()])
        if numbers > len(content) * 0.3 and len(content) > 10:
            return "DATA", 0.7
        
        # Default to text with varying confidence
        text_confidence = 0.9 if len(content) > 20 else 0.6
        return "TEXT", text_confidence


class RuleBasedSuggestionEngine:
    """Rule-based window suggestion engine"""
    
    def __init__(self):
        self.classifier = ContentClassifier()
        
        # Content type to window process mapping
        self.content_mappings = {
            'CODE': {
                'high_priority': ['code', 'pycharm', 'idea', 'sublime', 'atom', 'vim'],
                'medium_priority': ['notepad++', 'notepad', 'wordpad'],
                'keywords': ['editor', 'ide', 'development']
            },
            'WEB': {
                'high_priority': ['chrome', 'firefox', 'edge', 'safari', 'opera', 'brave'],
                'medium_priority': ['iexplore'],
                'keywords': ['browser', 'web']
            },
            'EMAIL': {
                'high_priority': ['outlook', 'thunderbird', 'mailspring'],
                'medium_priority': ['chrome', 'firefox', 'edge'],  # Webmail
                'keywords': ['mail', 'email']
            },
            'FILE_PATH': {
                'high_priority': ['explorer', 'nautilus', 'finder'],
                'medium_priority': ['cmd', 'powershell', 'terminal'],
                'keywords': ['file', 'folder', 'directory']
            },
            'PASSWORD': {
                'high_priority': ['chrome', 'firefox', 'edge', '1password', 'bitwarden'],
                'medium_priority': ['notepad', 'keepass'],
                'keywords': ['password', 'login', 'auth']
            },
            'DATA': {
                'high_priority': ['excel', 'calc', 'tableau', 'powerbi'],
                'medium_priority': ['notepad', 'word', 'chrome'],
                'keywords': ['data', 'spreadsheet', 'csv', 'table']
            },
            'TEXT': {
                'high_priority': ['notepad', 'wordpad', 'word', 'writer'],
                'medium_priority': ['chrome', 'firefox', 'edge'],
                'keywords': ['text', 'document', 'note']
            }
        }
    
    def get_suggestions(self, clipboard_content: str, current_window: Optional[WindowInfo], 
                       available_windows: List[WindowInfo]) -> Optional[List[Tuple[str, WindowInfo, str]]]:
        """
        Get rule-based window suggestions.
        Returns None if fallback should be used, otherwise returns list of suggestions.
        """
        if not available_windows:
            return None
        
        # Classify content
        content_type, confidence = self.classifier.classify_content(clipboard_content)
        
        # Get suggestions based on content type
        suggestions = self._get_suggestions_for_type(
            content_type, confidence, clipboard_content, available_windows
        )
        
        # Add recent windows if not enough suggestions
        if len(suggestions) < 3:
            recent_suggestions = self._get_recent_windows(available_windows, exclude=suggestions)
            suggestions.extend(recent_suggestions[:3-len(suggestions)])
        
        return suggestions[:3] if suggestions else None
    
    def _get_suggestions_for_type(self, content_type: str, confidence: float, 
                                content: str, windows: List[WindowInfo]) -> List[Tuple[str, WindowInfo, str]]:
        """Get suggestions for specific content type"""
        suggestions = []
        
        if content_type not in self.content_mappings:
            return suggestions
        
        mapping = self.content_mappings[content_type]
        
        # Score windows based on process name and title
        scored_windows = []
        for window in windows:
            score = self._calculate_window_score(window, mapping, content)
            if score > 0:
                scored_windows.append((window, score))
        
        # Sort by score and create suggestions
        scored_windows.sort(key=lambda x: x[1], reverse=True)
        
        for i, (window, score) in enumerate(scored_windows[:3]):
            priority = "High" if score >= 0.8 else "Medium" if score >= 0.5 else "Low"
            reason = f"{content_type} -> {window.process_name}"
            confidence_text = f"{priority} ({confidence:.2f})"
            suggestions.append((reason, window, confidence_text))
        
        return suggestions
    
    def _calculate_window_score(self, window: WindowInfo, mapping: dict, content: str) -> float:
        """Calculate relevance score for a window"""
        process_lower = window.process_name.lower().replace('.exe', '')
        title_lower = window.title.lower()
        
        score = 0.0
        
        # High priority process match
        if any(proc in process_lower for proc in mapping['high_priority']):
            score += 0.8
        
        # Medium priority process match
        elif any(proc in process_lower for proc in mapping['medium_priority']):
            score += 0.5
        
        # Keyword matching in title
        keyword_matches = sum(1 for keyword in mapping['keywords'] 
                            if keyword in title_lower)
        score += keyword_matches * 0.2
        
        # Content-specific scoring
        score += self._get_content_specific_score(window, content)
        
        return min(1.0, score)
    
    def _get_content_specific_score(self, window: WindowInfo, content: str) -> float:
        """Get additional score based on content analysis"""
        title_lower = window.title.lower()
        content_lower = content.lower()
        
        # URL content scoring
        if content_lower.startswith(('http', 'www')):
            # Extract domain from URL
            try:
                domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/\s]+)', content_lower)
                if domain_match:
                    domain = domain_match.group(1)
                    if domain in title_lower:
                        return 0.3
            except:
                pass
        
        # File path scoring
        if '\\\\' in content or '/' in content:
            if any(keyword in title_lower for keyword in ['file', 'folder', 'explorer']):
                return 0.2
        
        # Code scoring
        if any(keyword in content_lower for keyword in ['def ', 'function', 'class ']):
            if any(keyword in title_lower for keyword in ['code', 'editor', 'ide']):
                return 0.2
        
        return 0.0
    
    def _get_recent_windows(self, windows: List[WindowInfo], 
                          exclude: List[Tuple[str, WindowInfo, str]]) -> List[Tuple[str, WindowInfo, str]]:
        """Get suggestions based on recently used windows"""
        excluded_hwnds = {suggestion[1].hwnd for suggestion in exclude}
        
        suggestions = []
        for window in windows:
            if window.hwnd not in excluded_hwnds and not window.is_minimized:
                reason = f"Recent -> {window.process_name}"
                confidence = "Recent"
                suggestions.append((reason, window, confidence))
        
        return suggestions