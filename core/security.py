from cryptography.fernet import Fernet
import json
import os

key_str = os.environ.get('ENCRYPTION_KEY')
if not key_str:
    _key = Fernet.generate_key()
else:
    _key = key_str.encode('utf-8')
    
CIPHER = Fernet(_key)

def encrypt_dict(data_dict):
    """Cifra un diccionario y devuelve un string seguro."""
    data_str = json.dumps(data_dict)
    return CIPHER.encrypt(data_str.encode('utf-8')).decode('utf-8')

def decrypt_dict(token_str):
    """Descifra un string y devuelve el diccionario original."""
    if not token_str:
        return None
    try:
        data_str = CIPHER.decrypt(token_str.encode('utf-8')).decode('utf-8')
        return json.loads(data_str)
    except Exception as e:
        print(f"Error al desencriptar: {e}")
        return None
