#!/usr/bin/env python3
"""
Fund Daily CLI - Command line interface
Refactored version with modular structure
"""

import sys
import json
import logging
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fetcher import (
    fetch_fund_data,
    fetch_fund_detail,
    fetch_market_news,
    fetch_hot_sectors,
    clear_cache,
)

from src.analyzer import (
    get_market_sentiment,
    get_commodity_sentiment,
    calculate_expected_return,
)

from src.advice import (
    analyze_fund,
    generate_daily_report,
    format_report_for_share,
    generate_advice,
    get_fund_detail_info,
)


def setup_logging(level=logging.INFO):
    """Setup logging"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('fund-daily')


logger = setup_logging()


def main():
    if len(sys.argv) < 2:
        print("""Usage: fund-daily <command> [options]

Commands:
  fetch <fund_code>           Fetch single fund data
  analyze <fund_code>         Analyze single fund
  report <code1,code2,...>    Generate daily report for multiple funds
  share <code1,code2,...>     Generate shareable report
  news [limit]                Get market hot news
  sectors [limit]             Get hot sectors
  advice                      Generate investment advice
  detail <code>               Get detailed fund info
  clear-cache                 Clear data cache

Examples:
  fund-daily fetch 000001
  fund-daily analyze 000001
  fund-daily report 000001,000002,000003
  fund-daily share 000001,000002
  fund-daily news 10
  fund-daily sectors
  fund-daily advice
  fund-daily detail 000001
""", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "fetch" and len(sys.argv) > 2:
        result = fetch_fund_data(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "analyze" and len(sys.argv) > 2:
        data = fetch_fund_data(sys.argv[2])
        result = analyze_fund(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "report" and len(sys.argv) > 2:
        codes = sys.argv[2].split(",")
        result = generate_daily_report(codes)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "share" and len(sys.argv) > 2:
        codes = sys.argv[2].split(",")
        report = generate_daily_report(codes)
        result = format_report_for_share(report)
        print(result)
        
    elif command == "news":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 8
        news = fetch_market_news(limit)
        print(json.dumps(news, ensure_ascii=False, indent=2))
        
    elif command == "sectors":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        sectors = fetch_hot_sectors(limit)
        print(json.dumps(sectors, ensure_ascii=False, indent=2))
        
    elif command == "advice":
        funds_data = generate_daily_report(['000001', '110022', '161725'])
        advice = generate_advice(funds_data.get('funds', []))
        print(json.dumps(advice, ensure_ascii=False, indent=2))
        
    elif command == "detail" and len(sys.argv) > 2:
        code = sys.argv[2]
        detail = get_fund_detail_info(code)
        print(json.dumps(detail, ensure_ascii=False, indent=2))
        
    elif command == "clear-cache":
        clear_cache()
        print("Cache cleared")
        
    else:
        print("Error: Invalid command or missing arguments", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
