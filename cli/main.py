from core.services import SearchService, PHASES, OS_TYPES
import argparse, sys

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
        help="The term or terms to search for."
    )
    
    parser.add_argument(
        "-t", "--tag",
        action="append",
        help="Filter results by one or more tags."
    )
    
    parser.add_argument(
        "-p", "--phase",
        choices=PHASES,
        help="Filter results by phase."
    )
    
    parser.add_argument(
        "-o", "--os",
        choices=OS_TYPES,
        help="Filter results by operating system."
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
    
    args = parser.parse_args()
    
    if args.search_term and args.show is not None:
        parser.error("Search and show cannot be used together.")
        
    if args.show is not None and (args.tag or args.phase or args.os or args.machine):
        parser.error("Show cannot be combined with other filters.")
    
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit()
    
    return args

if __name__ == "__main__":
    args = parse_arguments()
    print(f"Search Term: {args.search_term}")
    print(f"Tags: {args.tag}")
    print(f"Phase: {args.phase}")
    print(f"OS: {args.os}")
    print(f"Show: {args.show}")

'''
- Trabajar en la interfaz para cuando solo use el parametro de busqueda
- 
- Agregar la logica en core para los demas parametros de busqueda (tags, phase, os, etc..)
    - Si no existe, puedes listar los que sí hay o sugerir el más parecido. Pista: la stdlib tiene difflib.get_close_matches.
-  es un flag tipo --list-tags / --list-machines para consultar qué hay
- Hacer test de los diferentes escenarios de busqueda y combinaciones
- Trabajar la interfaz para cuando se use el parametro de show
'''
