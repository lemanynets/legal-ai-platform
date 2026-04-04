from cryptography.hazmat.primitives.serialization import pkcs12

with open('C:/Users/ja/Documents/legal-ai-platform/Key-6.pfx', 'rb') as f:
    p12 = f.read()

try:
    private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(p12, b"1985")
    print("Success loading key!")
    if private_key:
        print(f"Key type: {type(private_key)}")
except Exception as e:
    print(f"Failed to load key: {e}")
