#!/usr/bin/env python3
import os
import sys
import socket
from datetime import datetime, timedelta

def get_public_ip():
    """Get the public-facing IP address of the machine."""
    try:
        import urllib.request
        external_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        return external_ip
    except Exception:
        return None

def get_local_ips():
    """Get all local IP addresses of the machine."""
    try:
        # Get all local IPs
        hostname = socket.gethostname()
        local_ips = socket.gethostbyname_ex(hostname)[2]
        # Filter out loopback addresses
        return [ip for ip in local_ips if not ip.startswith("127.")]
    except Exception:
        return []

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
        
        # Get hostname and IPs for certificate
        hostname = socket.gethostname()
        local_ips = get_local_ips()
        public_ip = get_public_ip()
        
        # Create a key pair
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)
        
        # Create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "Ganymede"
        cert.get_subject().OU = "File Server"
        # Use a more descriptive common name
        cert.get_subject().CN = "Ganymede File Server"
        
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        # Set validity to 2 years instead of 10 (more reasonable timeframe)
        cert.gmtime_adj_notAfter(2*365*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        
        # Add Subject Alternative Names extension for hostname and IPs
        alt_names = []
        # Add hostname
        alt_names.append(f"DNS:localhost")
        alt_names.append(f"DNS:{hostname}")
        
        # Add all local IPs
        for ip in local_ips:
            alt_names.append(f"IP:{ip}")
        
        # Add public IP if available
        if public_ip:
            alt_names.append(f"IP:{public_ip}")
        
        san_extension = crypto.X509Extension(
            b"subjectAltName", 
            False, 
            ", ".join(alt_names).encode()
        )
        
        cert.add_extensions([san_extension])
        cert.sign(k, 'sha256')
        
        # Write certificate
        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        
        # Write private key
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
        
        print(f"Self-signed certificate generated at:\n  - {cert_file}\n  - {key_file}")
        print(f"Certificate includes:")
        print(f"  - Hostname: {hostname}")
        if local_ips:
            print(f"  - Local IPs: {', '.join(local_ips)}")
        if public_ip:
            print(f"  - Public IP: {public_ip}")
        print(f"Valid for 2 years")
        
        return True
        
    except Exception as e:
        print(f"Error generating certificate: {e}")
        return False

if __name__ == "__main__":
    success = generate_self_signed_cert()
    sys.exit(0 if success else 1)