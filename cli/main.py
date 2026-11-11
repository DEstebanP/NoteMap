from core.services import SearchService, PHASES, OS_TYPES, Filters
import argparse, sys
from cli.render import render_search_results, render_entry_detail, render_entry_not_found

class CustomHelpFormatter(argparse.RawTextHelpFormatter):

    def _format_action_invocation(self, action):
        if not action.option_strings:
            return super()._format_action_invocation(action)

        if action.nargs == 0:
            return ", ".join(action.option_strings)

        metavar = self._format_args(
            action,
            self._get_default_metavar_for_optional(action)
        )

        return f"{', '.join(action.option_strings)} {metavar}"

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="notemap",
        description="A command-line tool to search and manage your technical notes.",
        usage="%(prog)s [search_terms ...] [options]",
        epilog="""Examples:
    notemap smb
    notemap "active directory" -p recon
    notemap smb enumeration -t smbclient -t impacket -o linux
    notemap --show 15
""",
        formatter_class=CustomHelpFormatter
    )
    
    parser.add_argument(
        "search_term",
        nargs="*",
        type=str,
        help="The term or terms to search for."
    )
    
    parser.add_argument(
        "-t", "--tag",
        action="append",
        help="Filter by tag (partial, case-insensitive). Repeat to require\nall of them: -t smb -t netexec."
    )
    
    parser.add_argument(
        "-p", "--phase",
        choices=PHASES,
        metavar="PHASE",
        help="Filter results by phase: %(choices)s."
    )
    
    parser.add_argument(
        "-o", "--os",
        choices=OS_TYPES,
        metavar="OS",
        help="Filter results by operating system: %(choices)s."
    )
    
    parser.add_argument(
        "-m", "--machine",
        help="Filter results by machine name."
    )
    
    parser.add_argument(
        "-s", "--show",
        type=int,
        metavar="ID",
        help="Show detailed information for a specific entry by its ID."
    )

    parser.add_argument(
        "-n", "--no-pager",
        action="store_true",
        help="With -s: print the entry straight to the terminal instead of\nopening it in a pager (lets you scroll and select long scripts)."
    )

    args = parser.parse_args()
    if args.search_term and args.show is not None:
        parser.error("Search and show cannot be used together.")
        
    if args.show is not None and (args.tag or args.phase or args.os or args.machine):
        parser.error("Show cannot be combined with other filters.")

    if args.no_pager and args.show is None:
        parser.error("-n only works together with -s.")

    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit()
    
    return args

def main():
    args = parse_arguments()
    service = SearchService()

    if args.show is not None:
        detail = service.get(args.show)
        if detail is None:
            render_entry_not_found(args.show)
            sys.exit(1)
        render_entry_detail(detail, pager=not args.no_pager)
        return

    filters = Filters(
        terms=args.search_term,
        tags=args.tag or [],
        os=args.os,
        machine=args.machine,
        phase=args.phase
    )
    results = service.search(filters)
    render_search_results(results, filters)

if __name__ == "__main__":
    main()
