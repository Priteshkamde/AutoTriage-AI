
import requests
from typing import Dict, List, Optional

class GitHubBugRouter:
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def create_issue_with_assignment(
        self, 
        repo_name: str, 
        bug_data: Dict, 
        routing_decision: Dict
    ) -> Dict:
        """Create GitHub issue with intelligent assignment"""
        
        assignee = routing_decision['assigned_to']
        
        # Prepare issue body with routing context
        issue_body = self._format_issue_body(bug_data, routing_decision)
        
        issue_data = {
            'title': bug_data['title'],
            'body': issue_body,
            'labels': routing_decision['suggested_labels'] + ['auto-routed'],
            'assignees': [self._get_github_username(assignee['developer'])] if assignee else []
        }
        
        # Create the issue
        url = f"https://api.github.com/repos/{repo_name}/issues"
        response = requests.post(url, headers=self.headers, json=issue_data)
        
        if response.status_code == 201:
            issue = response.json()
            
            # Add routing comment
            self._add_routing_comment(repo_name, issue['number'], routing_decision)
            
            return {
                'success': True,
                'issue_url': issue['html_url'],
                'issue_number': issue['number'],
                'assigned_to': assignee['developer'] if assignee else None
            }
        
        return {'success': False, 'error': response.text}
    
    def _format_issue_body(self, bug_data: Dict, routing_decision: Dict) -> str:
        """Format issue body with routing information"""
        
        body = bug_data['description']
        
        # Add routing information
        body += "\n\n---\n\n"
        body += "## 🤖 Automated Routing Information\n\n"
        
        assignee = routing_decision['assigned_to']
        if assignee:
            body += f"**Assigned to:** @{self._get_github_username(assignee['developer'])}\n"
            body += f"**Confidence:** {routing_decision['confidence_score']*100:.0f}%\n"
            body += f"**Reason:** {routing_decision['routing_reason']}\n"
            
            if assignee['files_owned']:
                body += f"**Owned Files:** `{'`, `'.join(assignee['files_owned'][:3])}`"
                if len(assignee['files_owned']) > 3:
                    body += f" (+{len(assignee['files_owned'])-3} more)"
                body += "\n"
        
        if routing_decision['backup_assignees']:
            backups = [self._get_github_username(b['developer']) for b in routing_decision['backup_assignees']]
            body += f"**Backup Assignees:** @{', @'.join(backups)}\n"
        
        body += f"**Estimated Complexity:** {routing_decision['estimated_complexity']}\n"
        
        return body
    
    def _add_routing_comment(self, repo_name: str, issue_number: int, routing_decision: Dict):
        """Add a comment explaining the routing decision"""
        
        assignee = routing_decision['assigned_to']
        if not assignee:
            return
        
        comment = f"""🎯 **Intelligent Bug Routing**

This issue has been automatically assigned to @{self._get_github_username(assignee['developer'])} based on:

- **Ownership Score:** {assignee['ownership_score']:.1f}
- **Expertise Score:** {assignee['expertise_score']:.1f}
- **Files Owned:** {len(assignee['files_owned'])}
- **Areas of Expertise:** {', '.join(assignee['areas_of_expertise']) if assignee['areas_of_expertise'] else 'General'}

If you're unable to handle this issue, please reassign to one of the backup assignees or escalate to the team lead.
"""
        
        url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments"
        requests.post(url, headers=self.headers, json={'body': comment})
    
    def _get_github_username(self, email: str) -> str:
        """Convert email to GitHub username (simplified)"""
        # In production, this would maintain a mapping of emails to GitHub usernames
        # For now, extract username from email
        return email.split('@')[0].replace('.', '-')