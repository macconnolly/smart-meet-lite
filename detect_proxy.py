#!/usr/bin/env python3
"""
Detect and configure proxy settings for WSL2 environment.
WSL2 often needs special handling for corporate proxies.
"""

import os
import re
import subprocess
import json

def get_windows_proxy():
    """Get proxy settings from Windows registry."""
    try:
        # Try to get Windows proxy settings via PowerShell
        cmd = 'powershell.exe -Command "Get-ItemProperty -Path \'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\' | Select-Object ProxyServer, ProxyEnable | ConvertTo-Json"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get('ProxyEnable') == 1 and data.get('ProxyServer'):
                proxy = data['ProxyServer']
                # Handle different proxy formats
                if '=' in proxy:
                    # Format: http=proxy:port;https=proxy:port
                    parts = proxy.split(';')
                    for part in parts:
                        if part.startswith('http='):
                            return part.split('=')[1]
                else:
                    # Format: proxy:port
                    return proxy
    except Exception as e:
        print(f"Error getting Windows proxy: {e}")
    
    return None

def get_wsl_proxy_from_pac():
    """Extract proxy from WSL PAC URL if available."""
    pac_url = os.getenv('WSL_PAC_URL')
    if pac_url:
        # WSL uses a local PAC proxy
        # Extract the port from the PAC URL
        match = re.search(r'http://127\.0\.0\.1:(\d+)', pac_url)
        if match:
            port = match.group(1)
            return f"http://127.0.0.1:{port}"
    return None

def detect_proxy():
    """Detect the best proxy configuration for the current environment."""
    print("Detecting proxy configuration...")
    
    # Check if proxy is already set
    if os.getenv('HTTPS_PROXY') or os.getenv('https_proxy'):
        print("Proxy already configured via environment variables")
        return
    
    # Try WSL PAC proxy first
    wsl_proxy = get_wsl_proxy_from_pac()
    if wsl_proxy:
        print(f"Found WSL PAC proxy: {wsl_proxy}")
        return wsl_proxy
    
    # Try Windows proxy
    windows_proxy = get_windows_proxy()
    if windows_proxy:
        print(f"Found Windows proxy: {windows_proxy}")
        if not windows_proxy.startswith('http://'):
            windows_proxy = f"http://{windows_proxy}"
        return windows_proxy
    
    print("No proxy detected")
    return None

def write_proxy_env(proxy):
    """Write proxy configuration to .env file."""
    if not proxy:
        return
        
    print(f"\nTo use this proxy, add to your .env file:")
    print(f"HTTP_PROXY={proxy}")
    print(f"HTTPS_PROXY={proxy}")
    print(f"NO_PROXY=localhost,127.0.0.1")
    
    # Also show export commands
    print(f"\nOr export in your shell:")
    print(f"export HTTP_PROXY={proxy}")
    print(f"export HTTPS_PROXY={proxy}")
    print(f"export NO_PROXY=localhost,127.0.0.1")

if __name__ == "__main__":
    proxy = detect_proxy()
    write_proxy_env(proxy)