import bcrypt, sys

if len(sys.argv) != 2:
    print("\nPlease provide an input string.\n\nExample:\n\n\tpython bcrypt-hash.py mypassword\n")
    exit()

plain_text = sys.argv[1]
password_bytes = plain_text.encode('utf-8')
hash_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt(14))
hash_string = hash_bytes.decode('utf-8')

print(f"\n{plain_text} -> {hash_string}\n")