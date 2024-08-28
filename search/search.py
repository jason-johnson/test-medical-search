import argparse
from search.dynamed import Dynamed
from search.semantic_scholar import SemanticScholar

def main():
    parser = argparse.ArgumentParser(description='Script to perform medical search.')
    parser.add_argument('query', help='The search query')
    parser.add_argument('-l', '--limit', type=int, default=10, help='Limit the number of search results (default: 10)')
    parser.add_argument('-s', '--sort', choices=['relevance', 'date'], default='relevance', help='Sort the search results by relevance or date (default: relevance)')
    parser.add_argument('-f', '--filter', choices=['all', 'articles', 'videos'], default='all', help='Filter the search results by all, articles, or videos (default: all)')
    
    args = parser.parse_args()
    
    # Your code to perform the medical search goes here
    
    print(f'Search query: {args.query}')
    print(f'Limit: {args.limit}')
    print(f'Sort: {args.sort}')
    print(f'Filter: {args.filter}')

    dynamed = Dynamed()
    data = dynamed.search(args.query, args.limit, args.sort, args.filter)
    print(data)

    semantic_scholar = SemanticScholar()
    data = semantic_scholar.search(args.query, args.limit)
    print(data)

if __name__ == '__main__':
    main()