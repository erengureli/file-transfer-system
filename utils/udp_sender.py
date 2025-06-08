import socket
import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import secrets
import struct
import time

def udp_send(filepath: str, ip: str, port: int, fragment: int, username: str, password: str):
    # File check
    if not os.path.exists(filepath) and not os.path.isfile(filepath):
        print(f"HATA: {filepath} dosyası bulunamadı!")
        return
    
    if not os.access(filepath, os.R_OK):
        print(f"HATA: {filepath} dosyası okunamıyor!")
        return

    # Get file data and calculate checksum (SHA-256)
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)
    
    # Calculate file checksum using SHA-256
    file_hash = hashlib.sha256()
    with open(filepath, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b""):
            file_hash.update(chunk)
    checksum = file_hash.hexdigest()

    # Create UDP Socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # UDP buffer optimizations
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2*1024*1024)  # 2MB send buffer
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2*1024*1024)  # 2MB receive buffer
    
    try:
        server_address = (ip, port)
        print(f"UDP Sunucuya bağlanılıyor: {ip}:{port}")
        
        # Send connection request
        client_socket.sendto(b"CONNECT", server_address)
        
        # Receive server's public key (in chunks)
        chunk_count_data, _ = client_socket.recvfrom(1024)
        chunk_count = struct.unpack('!I', chunk_count_data)[0]
        
        public_key_chunks = {}
        for _ in range(chunk_count):
            chunk_data, _ = client_socket.recvfrom(2048)
            chunk_num = struct.unpack('!I', chunk_data[:4])[0]
            chunk_content = chunk_data[4:]
            public_key_chunks[chunk_num] = chunk_content
        
        # Reconstruct public key
        public_key_pem = b''.join([public_key_chunks[i] for i in sorted(public_key_chunks.keys())])
        public_key = serialization.load_pem_public_key(public_key_pem, backend=default_backend())
        
        # Send ACK for public key
        client_socket.sendto(b"KEY_RECEIVED", server_address)
        
        # Send authentication credentials (encrypted with RSA)
        auth_data = f"{username}|{password}".encode('utf-8')
        encrypted_auth = public_key.encrypt(
            auth_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        client_socket.sendto(encrypted_auth, server_address)
        
        # Wait for authentication response
        client_socket.settimeout(10.0)  # 10 second timeout
        auth_response, _ = client_socket.recvfrom(1024)
        if auth_response != b"AUTH_SUCCESS":
            print("HATA: Kimlik doğrulama başarısız!")
            return
        else:
            print("Kimlik doğrulama başarılı!")
        
        # Generate AES key and IV
        aes_key = secrets.token_bytes(32)  # 256-bit key
        iv = secrets.token_bytes(16)       # 128-bit IV
        
        # Encrypt AES key with RSA and send
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        client_socket.sendto(encrypted_aes_key, server_address)
        
        # Wait for AES key ACK
        ack_response, _ = client_socket.recvfrom(1024)
        if ack_response != b"AES_KEY_RECEIVED":
            print("HATA: AES anahtarı gönderimi başarısız!")
            return
        
        # Send IV
        client_socket.sendto(iv, server_address)
        
        # Wait for IV ACK
        ack_response, _ = client_socket.recvfrom(1024)
        if ack_response != b"IV_RECEIVED":
            print("HATA: IV gönderimi başarısız!")
            return
        
        # Send file data with checksum
        info = f"{filename}|{filesize}|{fragment}|{checksum}|"
        info_bytes = info.encode('utf-8')
        length = len(info_bytes)

        if length < 1024:
            padding_len = 1024 - length
            info_padded = info_bytes + b'a' * padding_len
        else:
            info_padded = info_bytes[:1024]

        client_socket.sendto(info_padded, server_address)
        
        # Wait for file info ACK
        ack_response, _ = client_socket.recvfrom(1024)
        if ack_response != b"FILE_INFO_RECEIVED":
            print("HATA: Dosya bilgisi gönderimi başarısız!")
            return
        
        print(f"Gönderilen dosya: {filename}")
        print(f"Dosya boyutu: {filesize} bytes")
        print(f"Dosya parça boyutu: {fragment} bytes")
        print(f"Dosya SHA-256 checksum: {checksum}")
        
        # Setup AES encryption
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Prepare file data for UDP transmission
        max_packet_size = 65507 - 4  # Max UDP payload minus packet number
        
        # Read and encrypt entire file first
        encrypted_data = b""
        with open(filepath, 'rb') as file:
            file_data = file.read()
            
            # Apply PKCS7 padding
            padding_length = 16 - (len(file_data) % 16)
            if padding_length != 16:
                file_data += bytes([padding_length] * padding_length)
            
            # Encrypt all data
            encrypted_data = encryptor.update(file_data)
            encrypted_data += encryptor.finalize()
        
        # Split into packets
        packets = []
        for i in range(0, len(encrypted_data), max_packet_size):
            packet_data = encrypted_data[i:i + max_packet_size]
            packets.append(packet_data)
        
        print(f"Toplam paket sayısı: {len(packets)}")
        
        # Send packets with reliable delivery
        packet_acks = set()
        max_retries = 3
        retry_count = 0
        
        client_socket.settimeout(2.0)  # 2 second timeout for ACKs
        
        while len(packet_acks) < len(packets) and retry_count < max_retries:
            # Send all unacknowledged packets
            for packet_num, packet_data in enumerate(packets):
                if packet_num not in packet_acks:
                    # Create packet with sequence number
                    full_packet = struct.pack('!I', packet_num) + packet_data
                    client_socket.sendto(full_packet, server_address)
            
            # Collect ACKs with timeout
            start_time = time.time()
            while time.time() - start_time < 5.0:  # 5 second window for ACKs
                try:
                    ack_data, _ = client_socket.recvfrom(1024)
                    
                    # Handle resend requests
                    if ack_data.startswith(b"RESEND:"):
                        resend_packet = struct.unpack('!I', ack_data[7:])[0]
                        if resend_packet < len(packets):
                            full_packet = struct.pack('!I', resend_packet) + packets[resend_packet]
                            client_socket.sendto(full_packet, server_address)
                            continue
                    
                    # Handle regular ACKs
                    try:
                        ack_packet_num = struct.unpack('!I', ack_data)[0]
                        packet_acks.add(ack_packet_num)
                    except:
                        continue
                        
                except socket.timeout:
                    break
            
            progress = (len(packet_acks) / len(packets)) * 100
            print(f"\rGönderim ilerlemesi: {len(packet_acks)}/{len(packets)} paket ({progress:.1f}%)", end='', flush=True)
            
            if len(packet_acks) < len(packets):
                retry_count += 1
                print(f"\nYeniden deneme: {retry_count}/{max_retries}")
                time.sleep(1)
        
        client_socket.settimeout(10.0)  # Reset timeout
        
        if len(packet_acks) == len(packets):
            # Wait for final confirmation
            try:
                final_response, _ = client_socket.recvfrom(1024)
                if final_response == b"FILE_SUCCESS":
                    print(f"\rDosya başarıyla gönderildi ve doğrulandı!")
                else:
                    print(f"\rDosya gönderildi ancak doğrulama başarısız!")
            except socket.timeout:
                print(f"\rDosya gönderildi, doğrulama yanıtı alınamadı!")
        else:
            print(f"\rHATA: Tüm paketler gönderilemedi! {len(packet_acks)}/{len(packets)}")
            
    except Exception as e:
        print(f"HATA: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    udp_send("input/test.txt", "localhost", 12345, 1024, "admin", "admin123")