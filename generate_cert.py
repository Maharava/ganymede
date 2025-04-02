#!/usr/bin/env python3
import os
import subprocess
import sys
from datetime import datetime, timedelta

def generate_self_signed_cert():
    """Generate a self-signed certificate for HTTPS."""
    certs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certs')
    os.makedirs(certs_dir, exist_ok=True)
    
    cert_file = os.path.join(certs_dir, 'server.crt')
    key_file = os.path.join(certs_dir, 'server.key')
    
    # Check if certificate already exists and isn't expired
    if os.path.exists(cert_file) and os.path.exists(key_file):
        try:
            # Try to check certificate expiration using OpenSSL
            from OpenSSL import crypto
            with open(cert_file, 'rb') as f:
                cert_data = f.read()
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
            expiry_date = datetime.strptime(cert.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ')
            if expiry_date > datetime.now() + timedelta(days=30):
                print(f"Certificate already exists and is valid until {expiry_date.strftime('%Y-%m-%d')}")
                return True
            else:
                print(f"Certificate expires soon ({expiry_date.strftime('%Y-%m-%d')}), generating new one...")
        except Exception:
            print("Could not verify existing certificate, generating new one...")
    
    print("Generating self-signed certificate for HTTPS...")
    
    try:
        from OpenSSL import crypto
        
        # Create a key pair
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)
        
        # Create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "Organization"
        cert.get_subject().OU = "Organizational Unit"
        cert.get_subject().CN = "localhost"
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)  # 10 years
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')
        
        # Write certificate
        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        
        # Write private key
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
        
        print(f"Self-signed certificate generated at:\n  - {cert_file}\n  - {key_file}")
        return True
        
    except Exception as e:
        print(f"Error generating certificate: {e}")
        return False

if __name__ == "__main__":
    success = generate_self_signed_cert()
    sys.exit(0 if success else 1)