
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
from dataclasses import dataclass

@dataclass
class Developer:
    username: str
    email: str
    full_name: str
    expertise_score: float
    recent_activity: int
    availability_score: float

@dataclass
class FileOwnership:
    file_path: str
    primary_owner: str
    secondary_owners: List[str]
    last_modified: datetime
    modification_count: int
    complexity_score: float

class CodeOwnershipAnalyzer:
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.cache = {}
    
    def analyze_repository_ownership(self, repo_name: str, lookback_days: int = 90) -> Dict:
        """Analyze code ownership patterns in a repository"""
        
        # Get all commits in the lookback period
        since_date = (datetime.now() - timedelta(days=lookback_days)).isoformat()
        commits = self._get_recent_commits(repo_name, since_date)
        
        # Build ownership data
        file_ownership = defaultdict(lambda: defaultdict(int))
        developer_activity = defaultdict(int)
        file_complexity = {}
        
        for commit in commits:
            commit_details = self._get_commit_details(repo_name, commit['sha'])
            author = commit['commit']['author']['email']
            
            for file_info in commit_details.get('files', []):
                file_path = file_info['filename']
                changes = file_info.get('changes', 0)
                
                # Track ownership by commit frequency and change volume
                file_ownership[file_path][author] += changes
                developer_activity[author] += changes
                
                # Calculate file complexity (lines changed, additions/deletions)
                if file_path not in file_complexity:
                    file_complexity[file_path] = {
                        'total_changes': 0,
                        'unique_contributors': set(),
                        'avg_change_size': 0
                    }
                
                file_complexity[file_path]['total_changes'] += changes
                file_complexity[file_path]['unique_contributors'].add(author)
        
        # Process ownership data
        ownership_map = {}
        for file_path, contributors in file_ownership.items():
            sorted_contributors = sorted(
                contributors.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            ownership_map[file_path] = FileOwnership(
                file_path=file_path,
                primary_owner=sorted_contributors[0][0] if sorted_contributors else None,
                secondary_owners=[c[0] for c in sorted_contributors[1:3]],
                last_modified=self._get_file_last_modified(repo_name, file_path),
                modification_count=sum(contributors.values()),
                complexity_score=self._calculate_complexity_score(file_complexity[file_path])
            )
        
        return {
            'file_ownership': ownership_map,
            'developer_activity': dict(developer_activity),
            'repository_experts': self._identify_experts(developer_activity, file_ownership)
        }
    
    def _get_recent_commits(self, repo_name: str, since_date: str) -> List[Dict]:
        """Fetch recent commits from GitHub API"""
        url = f"https://api.github.com/repos/{repo_name}/commits"
        params = {'since': since_date, 'per_page': 100}
        
        all_commits = []
        page = 1
        
        while page <= 10:  # Limit to prevent API rate limiting
            params['page'] = page
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                break
            
            commits = response.json()
            if not commits:
                break
                
            all_commits.extend(commits)
            page += 1
        
        return all_commits
    
    def _get_commit_details(self, repo_name: str, commit_sha: str) -> Dict:
        """Get detailed commit information including file changes"""
        if commit_sha in self.cache:
            return self.cache[commit_sha]
        
        url = f"https://api.github.com/repos/{repo_name}/commits/{commit_sha}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            self.cache[commit_sha] = data
            return data
        
        return {}
    
    def _get_file_last_modified(self, repo_name: str, file_path: str) -> datetime:
        """Get the last modification date of a file"""
        url = f"https://api.github.com/repos/{repo_name}/commits"
        params = {'path': file_path, 'per_page': 1}
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            commits = response.json()
            if commits:
                return datetime.fromisoformat(
                    commits[0]['commit']['author']['date'].replace('Z', '+00:00')
                )
        
        return datetime.now()
    
    def _calculate_complexity_score(self, complexity_data: Dict) -> float:
        """Calculate a complexity score for a file based on change patterns"""
        total_changes = complexity_data['total_changes']
        unique_contributors = len(complexity_data['unique_contributors'])
        
        # Higher score = more complex/critical file
        base_score = min(total_changes / 100, 1.0)  # Normalize to 0-1
        contributor_factor = min(unique_contributors / 5, 1.0)  # More contributors = more complex
        
        return (base_score * 0.7) + (contributor_factor * 0.3)
    
    def _identify_experts(self, developer_activity: Dict, file_ownership: Dict) -> Dict:
        """Identify domain experts based on activity and ownership patterns"""
        experts = defaultdict(lambda: defaultdict(int))
        
        # Analyze by file patterns/directories
        for file_path, ownership in file_ownership.items():
            directory = '/'.join(file_path.split('/')[:-1])
            file_ext = file_path.split('.')[-1] if '.' in file_path else 'unknown'
            
            for contributor, changes in ownership.items():
                experts[directory][contributor] += changes
                experts[f"*.{file_ext}"][contributor] += changes
        
        # Convert to ranked lists
        ranked_experts = {}
        for domain, contributors in experts.items():
            ranked_experts[domain] = sorted(
                contributors.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]  # Top 3 experts per domain
        
        return ranked_experts
