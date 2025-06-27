
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from .ownership_analyzer import CodeOwnershipAnalyzer, Developer
import re
import json

class IntelligentBugRouter:
    def __init__(self, github_token: str, slack_token: str):
        self.ownership_analyzer = CodeOwnershipAnalyzer(github_token)
        self.slack_token = slack_token
        self.developer_cache = {}
    
    def route_bug_report(self, bug_data: Dict) -> Dict:
        """
        Intelligently route a bug report to the most appropriate developer
        
        Args:
            bug_data: {
                'title': str,
                'description': str,
                'labels': List[str],
                'repository': str,
                'affected_files': List[str],  # Optional: if known
                'stack_trace': str,  # Optional
                'priority': str  # low, medium, high, critical
            }
        """
        
        repo_name = bug_data['repository']
        
        # 1. Analyze repository ownership
        ownership_data = self.ownership_analyzer.analyze_repository_ownership(repo_name)
        
        # 2. Extract context from bug report
        context = self._extract_bug_context(bug_data)
        
        # 3. Find relevant files and potential owners
        potential_assignees = self._find_potential_assignees(
            context, 
            ownership_data, 
            bug_data.get('affected_files', [])
        )
        
        # 4. Score and rank assignees
        ranked_assignees = self._rank_assignees(potential_assignees, bug_data)
        
        # 5. Check availability and workload
        final_assignee = self._select_final_assignee(ranked_assignees, repo_name)
        
        # 6. Generate routing decision
        routing_decision = {
            'assigned_to': final_assignee,
            'backup_assignees': ranked_assignees[1:3],
            'confidence_score': self._calculate_confidence(final_assignee, context),
            'routing_reason': self._generate_routing_reason(final_assignee, context),
            'escalation_needed': final_assignee is None,
            'suggested_labels': self._suggest_labels(context),
            'estimated_complexity': self._estimate_complexity(context, ownership_data)
        }
        
        return routing_decision
    
    def _extract_bug_context(self, bug_data: Dict) -> Dict:
        """Extract technical context from bug report"""
        context = {
            'mentioned_files': [],
            'mentioned_functions': [],
            'mentioned_modules': [],
            'error_types': [],
            'affected_areas': [],
            'keywords': []
        }
        
        text = f"{bug_data['title']} {bug_data['description']}"
        
        # Extract file paths
        file_pattern = r'[\w\/\-\.]+\.(py|js|ts|java|go|rs|cpp|c|h)'
        context['mentioned_files'] = re.findall(file_pattern, text, re.IGNORECASE)
        
        # Extract function names
        function_pattern = r'def\s+(\w+)|function\s+(\w+)|(\w+)\s*\('
        matches = re.findall(function_pattern, text)
        context['mentioned_functions'] = [match for group in matches for match in group if match]
        
        # Extract error types
        error_pattern = r'(\w*Error|\w*Exception)'
        context['error_types'] = re.findall(error_pattern, text)
        
        # Extract stack trace info if present
        if bug_data.get('stack_trace'):
            stack_files = re.findall(file_pattern, bug_data['stack_trace'])
            context['mentioned_files'].extend(stack_files)
        
        # Identify technical areas based on keywords
        area_keywords = {
            'authentication': ['auth', 'login', 'token', 'jwt', 'oauth'],
            'database': ['sql', 'query', 'database', 'db', 'migration'],
            'api': ['api', 'endpoint', 'rest', 'graphql', 'request'],
            'frontend': ['ui', 'component', 'render', 'dom', 'css'],
            'backend': ['server', 'service', 'worker', 'job', 'queue'],
            'security': ['security', 'vulnerability', 'xss', 'csrf', 'injection'],
            'performance': ['slow', 'performance', 'memory', 'cpu', 'optimization']
        }
        
        text_lower = text.lower()
        for area, keywords in area_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                context['affected_areas'].append(area)
        
        return context
    
    def _find_potential_assignees(
        self, 
        context: Dict, 
        ownership_data: Dict, 
        affected_files: List[str]
    ) -> List[Dict]:
        """Find developers who could potentially handle this bug"""
        
        candidates = defaultdict(lambda: {
            'ownership_score': 0,
            'expertise_score': 0,
            'relevance_score': 0,
            'files_owned': [],
            'areas_of_expertise': []
        })
        
        file_ownership = ownership_data['file_ownership']
        repository_experts = ownership_data['repository_experts']
        
        # Score based on file ownership
        relevant_files = affected_files + context['mentioned_files']
        for file_path in relevant_files:
            if file_path in file_ownership:
                ownership = file_ownership[file_path]
                primary = ownership.primary_owner
                
                if primary:
                    candidates[primary]['ownership_score'] += ownership.complexity_score * 3
                    candidates[primary]['files_owned'].append(file_path)
                
                for secondary in ownership.secondary_owners:
                    candidates[secondary]['ownership_score'] += ownership.complexity_score * 1
                    candidates[secondary]['files_owned'].append(file_path)
        
        # Score based on domain expertise
        for area in context['affected_areas']:
            if area in repository_experts:
                for expert, score in repository_experts[area][:3]:
                    candidates[expert]['expertise_score'] += score * 0.5
                    candidates[expert]['areas_of_expertise'].append(area)
        
        # Convert to list with additional metadata
        potential_assignees = []
        for developer, scores in candidates.items():
            if scores['ownership_score'] > 0 or scores['expertise_score'] > 0:
                assignee_info = {
                    'developer': developer,
                    'total_score': scores['ownership_score'] + scores['expertise_score'],
                    'ownership_score': scores['ownership_score'],
                    'expertise_score': scores['expertise_score'],
                    'files_owned': scores['files_owned'],
                    'areas_of_expertise': scores['areas_of_expertise']
                }
                potential_assignees.append(assignee_info)
        
        return potential_assignees
    
    def _rank_assignees(self, potential_assignees: List[Dict], bug_data: Dict) -> List[Dict]:
        """Rank assignees based on multiple factors"""
        
        # Add priority multiplier
        priority_multipliers = {
            'critical': 1.5,
            'high': 1.2,
            'medium': 1.0,
            'low': 0.8
        }
        
        priority = bug_data.get('priority', 'medium')
        multiplier = priority_multipliers.get(priority, 1.0)
        
        # Apply priority multiplier and sort
        for assignee in potential_assignees:
            assignee['final_score'] = assignee['total_score'] * multiplier
        
        return sorted(potential_assignees, key=lambda x: x['final_score'], reverse=True)
    
    def _select_final_assignee(self, ranked_assignees: List[Dict], repo_name: str) -> Optional[Dict]:
        """Select final assignee considering availability and workload"""
        
        if not ranked_assignees:
            return None
        
        # For now, select the top-ranked available developer
        # In production, this would check Slack status, current PR load, etc.
        for assignee in ranked_assignees[:3]:
            developer = assignee['developer']
            
            # Check if developer is available (simplified)
            if self._is_developer_available(developer):
                return assignee
        
        # Fallback to top candidate if no availability data
        return ranked_assignees[0] if ranked_assignees else None
    
    def _is_developer_available(self, developer_email: str) -> bool:
        """Check if developer is available (simplified implementation)"""
        # In production, this would integrate with:
        # - Slack status API
        # - Calendar APIs
        # - Current workload from project management tools
        # - PTO systems
        
        # For now, assume all developers are available
        return True
    
    def _calculate_confidence(self, assignee: Optional[Dict], context: Dict) -> float:
        """Calculate confidence score for the assignment"""
        if not assignee:
            return 0.0
        
        base_confidence = min(assignee['final_score'] / 10, 1.0)
        
        # Boost confidence if we have specific file matches
        if assignee['files_owned']:
            base_confidence = min(base_confidence + 0.2, 1.0)
        
        # Boost confidence if we have domain expertise matches
        if assignee['areas_of_expertise']:
            base_confidence = min(base_confidence + 0.1, 1.0)
        
        return round(base_confidence, 2)
    
    def _generate_routing_reason(self, assignee: Optional[Dict], context: Dict) -> str:
        """Generate human-readable explanation for routing decision"""
        if not assignee:
            return "No clear owner identified. Escalating to team lead."
        
        reasons = []
        
        if assignee['files_owned']:
            reasons.append(f"Primary owner of {len(assignee['files_owned'])} affected files")
        
        if assignee['areas_of_expertise']:
            areas = ', '.join(assignee['areas_of_expertise'])
            reasons.append(f"Subject matter expert in: {areas}")
        
        if assignee['ownership_score'] > 5:
            reasons.append("High code ownership score in affected areas")
        
        return "; ".join(reasons) if reasons else "Best available match based on repository activity"
    
    def _suggest_labels(self, context: Dict) -> List[str]:
        """Suggest appropriate labels for the bug"""
        labels = []
        
        # Add area labels
        for area in context['affected_areas']:
            labels.append(f"area:{area}")
        
        # Add error type labels
        if context['error_types']:
            labels.append("bug:error")
        
        return labels
    
    def _estimate_complexity(self, context: Dict, ownership_data: Dict) -> str:
        """Estimate bug complexity based on context"""
        complexity_score = 0
        
        # Multiple files affected = higher complexity
        complexity_score += len(context['mentioned_files']) * 0.5
        
        # Multiple areas affected = higher complexity
        complexity_score += len(context['affected_areas']) * 1
        
        # Error types indicate complexity
        complexity_score += len(context['error_types']) * 0.3
        
        if complexity_score < 1:
            return "low"
        elif complexity_score < 3:
            return "medium"
        elif complexity_score < 5:
            return "high"
        else:
            return "critical"
