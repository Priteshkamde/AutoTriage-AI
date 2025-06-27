
from .intelligent_router import IntelligentBugRouter
from .github_integration import GitHubBugRouter
import os

def handle_bug_report(bug_data: Dict) -> Dict:
    """Main entry point for bug routing system"""
    
    router = IntelligentBugRouter(
        github_token=os.getenv('GITHUB_TOKEN'),
        slack_token=os.getenv('SLACK_TOKEN')
    )
    
    github_router = GitHubBugRouter(os.getenv('GITHUB_TOKEN'))
    
    # Routing
    routing_decision = router.route_bug_report(bug_data)
    
    # Create GitHub issue with assignment
    result = github_router.create_issue_with_assignment(
        bug_data['repository'],
        bug_data,
        routing_decision
    )
    
    return {
        'routing_decision': routing_decision,
        'github_result': result
    }

# Example usage:
if __name__ == "__main__":
    sample_bug = {
        'title': 'Authentication API returning 500 error',
        'description': 'The /api/auth/login endpoint is throwing a TokenExpiredError when users try to log in.',
        'repository': 'company/backend-api',
        'priority': 'high',
        'affected_files': ['src/auth/token_manager.py', 'src/api/auth_routes.py']
    }
    
    result = handle_bug_report(sample_bug)
    print(f"Bug routed to: {result['routing_decision']['assigned_to']['developer']}")
    print(f"GitHub issue: {result['github_result']['issue_url']}")