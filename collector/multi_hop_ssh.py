"""Multi-hop SSH collector using Paramiko for jumphost chains."""

import logging
import re
import time
from typing import Optional

import paramiko

from collector.base import BaseCollector
from collector.credentials import DeviceCredentials
from collector.exceptions import (
    ConnectionError as CollectorConnectionError,
    TimeoutError as CollectorTimeoutError,
    AuthenticationError,
)
from app.services.connection_profile_service import ResolvedConnection

logger = logging.getLogger(__name__)


class MultiHopSSHCollector(BaseCollector):
    """
    SSH collector that supports multi-hop connections through jumphosts.
    
    Uses Paramiko's invoke_shell() for manual SSH chaining through jumphosts.
    This approach works reliably for both 1-hop and 2-hop scenarios.
    """
    
    def __init__(
        self,
        resolved_connection: ResolvedConnection,
        target_device_type: str,
        target_credentials: DeviceCredentials,
        session_log: Optional[str] = None,
        conn_timeout: int = 60,
    ):
        """
        Initialize multi-hop collector.
        
        Args:
            resolved_connection: Resolved connection with all hops
            target_device_type: Netmiko device type (cisco_xr, cisco_ios, etc.)
            target_credentials: Credentials for target device
            session_log: Optional path to save session log
            conn_timeout: Connection timeout in seconds
        """
        self.resolved = resolved_connection
        self.device_type = target_device_type
        self.target_credentials = target_credentials
        self.session_log = session_log
        self.conn_timeout = conn_timeout
        
        # Paramiko clients and channel
        self._clients: list[paramiko.SSHClient] = []
        self._channel: Optional[paramiko.Channel] = None
        self._connected = False
        
        # Session log file
        self._log_file = None
        if session_log:
            self._log_file = open(session_log, 'w')
    
    def connect(self):
        """Establish multi-hop SSH connection."""
        try:
            if len(self.resolved.hops) == 0:
                # Direct connection (no jumphosts)
                self._connect_direct()
            elif len(self.resolved.hops) == 1:
                # 1-hop connection
                self._connect_single_hop()
            else:
                # 2+ hop connection (manual chaining)
                self._connect_multi_hop()
            
            self._connected = True
            logger.info(f"Successfully connected to {self.resolved.target_host} via {len(self.resolved.hops)} hop(s)")
        
        except Exception as e:
            self.disconnect()
            raise CollectorConnectionError(
                self.resolved.target_host,
                f"Failed to establish multi-hop connection: {e}"
            )
    
    def _connect_direct(self):
        """Direct connection (no jumphosts)."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect directly to target
        connect_kwargs = {
            "hostname": self.resolved.target_host,
            "port": self.resolved.target_port,
            "username": self.target_credentials.username,
            "timeout": self.conn_timeout,
            "look_for_keys": False,
            "allow_agent": False,
        }
        
        # Prefer SSH key over password
        if self.target_credentials.ssh_key_file:
            connect_kwargs["key_filename"] = self.target_credentials.ssh_key_file
        elif self.target_credentials.password:
            connect_kwargs["password"] = self.target_credentials.password
        
        client.connect(**connect_kwargs)
        self._clients.append(client)
        self._channel = client.invoke_shell()
        self._channel.settimeout(self.conn_timeout)
        
        # Wait for prompt
        time.sleep(2)
        self._clear_buffer()
    
    def _connect_single_hop(self):
        """1-hop connection using Paramiko transport."""
        hop = self.resolved.hops[0]
        
        # Connect to jumphost
        jumphost = paramiko.SSHClient()
        jumphost.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        jump_kwargs = {
            "hostname": hop.host,
            "port": hop.port,
            "username": hop.credentials.username,
            "timeout": self.conn_timeout,
            "look_for_keys": False,
            "allow_agent": False,
        }
        
        # Prefer SSH key over password
        if hop.credentials.ssh_key_path:
            jump_kwargs["key_filename"] = hop.credentials.ssh_key_path
        elif hop.credentials.password:
            jump_kwargs["password"] = hop.credentials.password
        
        jumphost.connect(**jump_kwargs)
        self._clients.append(jumphost)
        
        # Create transport channel to target through jumphost
        transport = jumphost.get_transport()
        dest_addr = (self.resolved.target_host, self.resolved.target_port)
        local_addr = (hop.host, hop.port)
        channel = transport.open_channel("direct-tcpip", dest_addr, local_addr)
        
        # Connect to target device through channel
        target = paramiko.SSHClient()
        target.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        target_kwargs = {
            "hostname": self.resolved.target_host,  # Required even with sock
            "username": self.target_credentials.username,
            "sock": channel,
            "timeout": self.conn_timeout,
            "look_for_keys": False,
            "allow_agent": False,
        }
        
        # Prefer SSH key over password
        if self.target_credentials.ssh_key_file:
            target_kwargs["key_filename"] = self.target_credentials.ssh_key_file
        elif self.target_credentials.password:
            target_kwargs["password"] = self.target_credentials.password
        
        target.connect(**target_kwargs)
        self._clients.append(target)
        self._channel = target.invoke_shell()
        self._channel.settimeout(self.conn_timeout)
        
        # Wait for prompt
        time.sleep(2)
        self._clear_buffer()
    
    def _connect_multi_hop(self):
        """
        2+ hop connection using manual Paramiko invoke_shell() chaining.
        
        This mimics manual SSH commands:
        1. SSH to jumphost1
        2. From jumphost1, SSH to jumphost2
        3. From jumphost2, SSH to target device
        """
        # Connect to first jumphost
        hop1 = self.resolved.hops[0]
        client1 = paramiko.SSHClient()
        client1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        connect_kwargs = {
            "hostname": hop1.host,
            "port": hop1.port,
            "username": hop1.credentials.username,
            "timeout": self.conn_timeout,
            "look_for_keys": False,
            "allow_agent": False,
        }
        
        # Prefer SSH key over password
        if hop1.credentials.ssh_key_path:
            connect_kwargs["key_filename"] = hop1.credentials.ssh_key_path
        elif hop1.credentials.password:
            connect_kwargs["password"] = hop1.credentials.password
        
        logger.info(f"Connecting to hop 1: {hop1.host}:{hop1.port}")
        client1.connect(**connect_kwargs)
        self._clients.append(client1)
        
        # Get shell on first jumphost
        channel = client1.invoke_shell()
        channel.settimeout(self.conn_timeout)
        time.sleep(2)
        self._clear_channel_buffer(channel)
        
        # Chain through remaining hops
        for i, hop in enumerate(self.resolved.hops[1:], start=2):
            logger.info(f"Connecting to hop {i}: {hop.host}:{hop.port}")
            
            # Send SSH command to next hop
            ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {hop.port} {hop.credentials.username}@{hop.host}\n"
            channel.send(ssh_cmd)
            time.sleep(2)
            
            # Handle password prompt if needed
            if hop.credentials.password:
                output = self._read_channel_output_simple(channel, timeout=3, detect_patterns=["password:", "password: "])
                if "password:" in output.lower():
                    channel.send(hop.credentials.password + "\n")
                    time.sleep(1)  # Reduced wait time
            
            self._clear_channel_buffer(channel)
        
        # Finally, SSH to target device
        logger.info(f"Connecting to target: {self.resolved.target_host}:{self.resolved.target_port}")
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {self.resolved.target_port} {self.target_credentials.username}@{self.resolved.target_host}\n"
        channel.send(ssh_cmd)
        time.sleep(2)
        
        # Handle password prompt
        if self.target_credentials.password:
            output = self._read_channel_output_simple(channel, timeout=3, detect_patterns=["password:"])
            if "password:" in output.lower():
                channel.send(self.target_credentials.password + "\n")
                time.sleep(2)  # Wait for device login
        
        self._channel = channel
        self._clear_buffer()
    
    def _clear_channel_buffer(self, channel: paramiko.Channel):
        """Clear any pending output from channel."""
        try:
            while channel.recv_ready():
                channel.recv(65535)
                time.sleep(0.1)
        except:
            pass
    
    def _clear_buffer(self):
        """Clear buffer on main channel."""
        if self._channel:
            self._clear_channel_buffer(self._channel)
    
    def _read_channel_output_simple(self, channel: paramiko.Channel, timeout: int = 10, 
                                     detect_patterns: list[str] = None) -> str:
        """
        Read output from channel with simple timeout (for password prompts, etc.).
        
        This is optimized for short interactions like password prompts. It returns
        immediately when a detection pattern is found (e.g., "password:").
        
        Args:
            channel: Paramiko channel to read from
            timeout: Maximum time to wait (default: 10s)
            detect_patterns: Optional list of strings to detect (case-insensitive).
                           Returns immediately when any pattern is found.
        
        Returns:
            Output received
        """
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if channel.recv_ready():
                try:
                    data = channel.recv(65535).decode('utf-8', errors='ignore')
                    output += data
                    
                    # Check for detection patterns (e.g., "password:")
                    if detect_patterns:
                        output_lower = output.lower()
                        for pattern in detect_patterns:
                            if pattern.lower() in output_lower:
                                # Found pattern! Return immediately
                                return output
                    
                    time.sleep(0.05)  # Reduced from 0.1s for faster response
                except Exception as e:
                    logger.warning(f"Error reading from channel: {e}")
                    break
            else:
                # For short prompts, exit if we have some output and no more data
                time.sleep(0.2)  # Reduced from 0.5s
                if output and not channel.recv_ready():
                    break
        
        return output
    
    def _read_channel_output(self, channel: paramiko.Channel, timeout: int = 120) -> str:
        """
        Read output from channel until prompt is detected or timeout.
        
        Strategy:
        1. Read data in chunks
        2. Look for prompt patterns (hostname# or hostname(config)#)
        3. Use overall timeout as safety net
        4. Use idle timeout to detect hung connections
        
        Args:
            channel: Paramiko channel to read from
            timeout: Maximum time to wait for complete output (default: 120s for large configs)
        
        Returns:
            Complete command output
        """
        output = ""
        start_time = time.time()
        last_data_time = time.time()
        idle_timeout = 30  # No data for 30s = likely stuck
        last_log_size = 0  # For progress logging
        
        # Common prompt patterns for Cisco devices
        # These patterns look for end-of-line prompts (not mid-config text)
        prompt_patterns = [
            r'\n[^\n]+#\s*$',                      # Standard mode: hostname#
            r'\n[^\n]+\(config[^\)]*\)#\s*$',      # Config mode: hostname(config)#
        ]
        
        while time.time() - start_time < timeout:
            if channel.recv_ready():
                # Data available - read it
                try:
                    data = channel.recv(65535).decode('utf-8', errors='ignore')
                    output += data
                    last_data_time = time.time()  # Reset idle timer
                    
                    # Progress logging for large outputs (every 100KB)
                    if len(output) - last_log_size >= 100000:
                        logger.debug(f"Collected {len(output)} bytes so far...")
                        last_log_size = len(output)
                    
                    # Check if we've received a prompt at the end
                    for pattern in prompt_patterns:
                        if re.search(pattern, output):
                            # Found prompt! We're done
                            logger.debug(f"Prompt detected, collection complete ({len(output)} bytes)")
                            return output
                    
                    # Small sleep to allow buffer to fill
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error reading from channel: {e}")
                    break
            else:
                # No data ready - check if we're idle too long
                idle_time = time.time() - last_data_time
                if idle_time > idle_timeout:
                    # No data for idle_timeout seconds - likely stuck or done
                    if output:
                        logger.warning(
                            f"No data received for {idle_timeout}s, "
                            f"ending collection (may be incomplete, {len(output)} bytes collected)"
                        )
                        return output
                    # If no output yet, keep waiting
                
                time.sleep(0.5)
        
        # Timeout reached
        logger.warning(
            f"Output collection timed out after {timeout}s. "
            f"Output may be incomplete ({len(output)} bytes collected)"
        )
        return output
    
    def execute_command(self, command: str, timeout: int = 120) -> str:
        """
        Execute command on target device.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
        
        Returns:
            Command output
        """
        if not self._connected or not self._channel:
            raise CollectorConnectionError(
                self.resolved.target_host,
                "Not connected"
            )
        
        try:
            # Send command
            self._channel.send(command + "\n")
            
            if self._log_file:
                self._log_file.write(f"\n>>> {command}\n")
                self._log_file.flush()
            
            # Read output
            output = self._read_channel_output(self._channel, timeout=timeout)
            
            if self._log_file:
                self._log_file.write(output)
                self._log_file.flush()
            
            # Remove command echo and prompt from output
            lines = output.split('\n')
            # Skip first line (command echo) and last line (prompt)
            if len(lines) > 2:
                output = '\n'.join(lines[1:-1])
            
            return output
        
        except Exception as e:
            raise CollectorConnectionError(
                self.resolved.target_host,
                f"Command execution failed: {e}"
            )
    
    def disconnect(self):
        """Close all SSH connections."""
        if self._channel:
            try:
                self._channel.close()
            except:
                pass
            self._channel = None
        
        for client in reversed(self._clients):
            try:
                client.close()
            except:
                pass
        
        self._clients.clear()
        
        if self._log_file:
            try:
                self._log_file.close()
            except:
                pass
            self._log_file = None
        
        self._connected = False
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
