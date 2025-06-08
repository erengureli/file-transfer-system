import subprocess
import json
import time
import psutil
import socket
from datetime import datetime
import re

def measure_bandwidth(iperf_server=None, iperf_port=5201, duration=30, iperf_path="iperf3", interface=None, export_file=None):
    # Initialize results dictionary
    results = {
        'timestamp': datetime.now().isoformat(),
        'hostname': socket.gethostname(),
        'test_duration': duration,
        'packet_analysis': {'error': None, 'download_mbps': 0, 'upload_mbps': 0},
        'iperf_test': {'error': None, 'download_mbps': 0, 'upload_mbps': 0},
        'system_info': {'interfaces': [], 'active_connections': 0}
    }
    
    print(f"=== Bandwidth Measurement Started ({datetime.now().strftime('%H:%M:%S')}) ===")
    print(f"Duration: {duration} seconds")
    
    # PART 1: GET SYSTEM INFO
    try:
        interfaces_dict = psutil.net_io_counters(pernic=True)
        results['system_info']['interfaces'] = list(interfaces_dict.keys())
        results['system_info']['active_connections'] = len(psutil.net_connections())
        print(f"Available interfaces: {', '.join(results['system_info']['interfaces'])}")
    except Exception as e:
        print(f"Warning: Could not get system info: {e}")
    
    # PART 2: PACKET ANALYSIS
    print(f"\n1. Starting packet analysis...")
    try:
        # Get initial network stats
        if interface and interface in psutil.net_io_counters(pernic=True):
            initial_stats = psutil.net_io_counters(pernic=True)[interface]
            print(f"   Monitoring interface: {interface}")
        else:
            initial_stats = psutil.net_io_counters()
            print(f"   Monitoring all interfaces")
        
        initial_time = time.time()
        initial_bytes_sent = initial_stats.bytes_sent
        initial_bytes_recv = initial_stats.bytes_recv
        
        print(f"   Initial stats - Sent: {initial_bytes_sent:,} bytes, Received: {initial_bytes_recv:,} bytes")
        
        # Wait for the test duration
        print(f"   Monitoring network traffic for {duration} seconds...")
        time.sleep(duration)
        
        # Get final network stats
        if interface and interface in psutil.net_io_counters(pernic=True):
            final_stats = psutil.net_io_counters(pernic=True)[interface]
        else:
            final_stats = psutil.net_io_counters()
        
        final_time = time.time()
        final_bytes_sent = final_stats.bytes_sent
        final_bytes_recv = final_stats.bytes_recv
        
        # Calculate actual duration and bandwidth
        actual_duration = final_time - initial_time
        bytes_sent_diff = final_bytes_sent - initial_bytes_sent
        bytes_recv_diff = final_bytes_recv - initial_bytes_recv
        
        # Convert to Mbps (bytes to bits, then to megabits per second)
        upload_mbps = (bytes_sent_diff * 8) / (actual_duration * 1_000_000)
        download_mbps = (bytes_recv_diff * 8) / (actual_duration * 1_000_000)
        
        results['packet_analysis'] = {
            'error': None,
            'download_mbps': round(download_mbps, 2),
            'upload_mbps': round(upload_mbps, 2),
            'bytes_received': bytes_recv_diff,
            'bytes_sent': bytes_sent_diff,
            'actual_duration': round(actual_duration, 2)
        }
        
        print(f"   Final stats - Sent: {final_bytes_sent:,} bytes, Received: {final_bytes_recv:,} bytes")
        print(f"   Packet Analysis Result: ↓{download_mbps:.2f} Mbps ↑{upload_mbps:.2f} Mbps")
        
    except Exception as e:
        error_msg = f"Packet analysis failed: {e}"
        print(f"   {error_msg}")
        results['packet_analysis']['error'] = error_msg
    
    # PART 3: IPERF TEST
    if iperf_server:
        print(f"\n2. Starting iPerf test to {iperf_server}:{iperf_port}...")
        
        try:
            # Check if iperf3 is available
            version_check = subprocess.run([iperf_path, "--version"], 
                                         capture_output=True, text=True, timeout=5)
            if version_check.returncode != 0:
                raise FileNotFoundError("iPerf3 executable not found or not working")
            
            print(f"   iPerf3 version check passed")
            
            # DOWNLOAD TEST (client receives data from server)
            print(f"   Running download test...")
            download_cmd = [
                iperf_path, "-c", iperf_server, "-p", str(iperf_port),
                "-t", str(duration), "-J"
            ]
            
            download_result = subprocess.run(download_cmd, capture_output=True, 
                                           text=True, timeout=duration + 15)
            
            # UPLOAD TEST (client sends data to server, using -R flag)
            print(f"   Running upload test...")
            upload_cmd = [
                iperf_path, "-c", iperf_server, "-p", str(iperf_port),
                "-t", str(duration), "-R", "-J"
            ]
            
            upload_result = subprocess.run(upload_cmd, capture_output=True, 
                                         text=True, timeout=duration + 15)
            
            # Parse download results
            download_mbps = 0
            upload_mbps = 0
            latency_ms = None
            jitter_ms = None
            packet_loss = None
            
            if download_result.returncode == 0 and download_result.stdout:
                try:
                    download_data = json.loads(download_result.stdout)
                    download_bps = download_data['end']['sum_received']['bits_per_second']
                    download_mbps = download_bps / 1_000_000
                    print(f"   Download parsed: {download_mbps:.2f} Mbps")
                except (json.JSONDecodeError, KeyError):
                    # Fallback text parsing
                    gbits_match = re.search(r'(\d+\.?\d*)\s*Gbits/sec', download_result.stdout)
                    mbits_match = re.search(r'(\d+\.?\d*)\s*Mbits/sec', download_result.stdout)
                    if gbits_match:
                        download_mbps = float(gbits_match.group(1)) * 1000
                    elif mbits_match:
                        download_mbps = float(mbits_match.group(1))
                    print(f"   Download parsed (fallback): {download_mbps:.2f} Mbps")
            
            # Parse upload results
            if upload_result.returncode == 0 and upload_result.stdout:
                try:
                    upload_data = json.loads(upload_result.stdout)
                    upload_bps = upload_data['end']['sum_sent']['bits_per_second']
                    upload_mbps = upload_bps / 1_000_000
                    print(f"   Upload parsed: {upload_mbps:.2f} Mbps")
                    
                    # Try to get additional metrics
                    if 'streams' in upload_data['end'] and upload_data['end']['streams']:
                        stream = upload_data['end']['streams'][0]
                        if 'udp' in stream:
                            jitter_ms = stream['udp'].get('jitter_ms')
                            packet_loss = stream['udp'].get('lost_percent')
                    
                except (json.JSONDecodeError, KeyError):
                    # Fallback text parsing
                    gbits_match = re.search(r'(\d+\.?\d*)\s*Gbits/sec', upload_result.stdout)
                    mbits_match = re.search(r'(\d+\.?\d*)\s*Mbits/sec', upload_result.stdout)
                    if gbits_match:
                        upload_mbps = float(gbits_match.group(1)) * 1000
                    elif mbits_match:
                        upload_mbps = float(mbits_match.group(1))
                    print(f"   Upload parsed (fallback): {upload_mbps:.2f} Mbps")
            
            results['iperf_test'] = {
                'error': None,
                'download_mbps': round(download_mbps, 2),
                'upload_mbps': round(upload_mbps, 2),
                'latency_ms': latency_ms,
                'jitter_ms': jitter_ms,
                'packet_loss': packet_loss,
                'server': iperf_server,
                'port': iperf_port
            }
            
            print(f"   iPerf Test Result: ↓{download_mbps:.2f} Mbps ↑{upload_mbps:.2f} Mbps")
            
        except subprocess.TimeoutExpired:
            error_msg = "iPerf test timed out"
            print(f"   {error_msg}")
            results['iperf_test']['error'] = error_msg
        except FileNotFoundError:
            error_msg = "iPerf3 not found. Download from https://iperf.fr/iperf-download.php"
            print(f"   {error_msg}")
            results['iperf_test']['error'] = error_msg
        except Exception as e:
            error_msg = f"iPerf test failed: {e}"
            print(f"   {error_msg}")
            results['iperf_test']['error'] = error_msg
    else:
        print(f"\n2. Skipping iPerf test (no server specified)")
        results['iperf_test']['error'] = "No iPerf server specified"
    
    # PART 4: DISPLAY SUMMARY
    print(f"\n=== RESULTS SUMMARY ===")
    print(f"Test completed at: {results['timestamp']}")
    print(f"Hostname: {results['hostname']}")
    
    if results['packet_analysis']['error'] is None:
        pa = results['packet_analysis']
        print(f"Packet Analysis: ↓{pa['download_mbps']} Mbps ↑{pa['upload_mbps']} Mbps")
        print(f"  Data transferred: {pa['bytes_received']:,} bytes received, {pa['bytes_sent']:,} bytes sent")
    else:
        print(f"Packet Analysis: FAILED - {results['packet_analysis']['error']}")
    
    if results['iperf_test']['error'] is None:
        ip = results['iperf_test']
        print(f"iPerf Test: ↓{ip['download_mbps']} Mbps ↑{ip['upload_mbps']} Mbps")
        if ip['jitter_ms']:
            print(f"  Jitter: {ip['jitter_ms']:.2f} ms")
        if ip['packet_loss']:
            print(f"  Packet Loss: {ip['packet_loss']:.2f}%")
    else:
        print(f"iPerf Test: FAILED - {results['iperf_test']['error']}")
    
    # PART 5: EXPORT RESULTS
    if export_file:
        try:
            with open(export_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults exported to: {export_file}")
        except Exception as e:
            print(f"\nFailed to export results: {e}")
    
    print(f"=== Test Complete ===\n")
    return results

if __name__ == "__main__":
    measure_bandwidth(iperf_server="speedtest.serverius.net", iperf_port=5002, iperf_path="C:\\Users\\ereng\\Downloads\\iperf3.exe", duration=15, export_file="bandwidth_test.json")