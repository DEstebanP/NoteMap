from cli.render import render_search_results
from core.services import SearchService

if __name__ == "__main__":
    service = SearchService()
    
    results = service.search(["SMB"])
    render_search_results(results, ["SMB"])