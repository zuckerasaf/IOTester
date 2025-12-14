# Localhost Testing Configuration

This directory contains fixed response data for localhost UDP testing.

## Setup

1. **Configure settings.yaml for localhost:**
   ```yaml
   UDP_Settings:
     Frequency_Hz: 20.0
     Communication_Timeout: 2.0
     Cards:
       - card_id: 1
         enabled: true
         send_ip: "127.0.0.1"      # Change from 192.168.x.x to localhost
         send_port: 2881
         receive_ip: "127.0.0.1"   # Change from 192.168.x.x to localhost
         receive_port: 1011
       
       - card_id: 2
         enabled: true
         send_ip: "127.0.0.1"
         send_port: 2882
         receive_ip: "127.0.0.1"
         receive_port: 1021
       
       - card_id: 3
         enabled: true
         send_ip: "127.0.0.1"
         send_port: 2883
         receive_ip: "127.0.0.1"
         receive_port: 1031
       
       # ... cards 4-7 with same pattern
   ```

2. **Start the simulator:**
   ```powershell
   cd c:\ArduinoProject\IO_Tester
   .\.venv\Scripts\Activate.ps1
   python src\hw_tester\core\localhost_simulator.py
   ```

3. **In another terminal, run your test:**
   ```powershell
   cd c:\ArduinoProject\IO_Tester
   .\.venv\Scripts\Activate.ps1
   python src\hw_tester\core\udp_sender.py
   # Or test with card manager
   ```

## How It Works

**Real Network Testing:**
```
UDPSender (192.168.195.10:1011) ─────32 bytes────> Real Card (192.168.195.11:2880)
                                 <────64 bytes─────
```

**Localhost Testing:**
```
UDPSender (127.0.0.1:1011) ─────32 bytes────> Simulator (127.0.0.1:2881)
                           <────64 bytes─────
```

The simulator:
1. Listens on ports 2881-2887 (UDPSender send_port)
2. When 32 bytes received, reads corresponding cardX.txt
3. Sends fixed 64-byte response to receive_port (1011, 1021, etc.)

## Response Data Files

Each `cardX.txt` file contains 64 bytes in hex format:

- **Bytes 0-1**: Header (0xAA55)
- **Bytes 2-9**: Digital Inputs (DI 1-64, 8 bytes)
- **Bytes 10-11**: TTL Status (16-bit word)
- **Bytes 12-15**: Matrix Row (4 bytes)
- **Bytes 16-47**: Analog Inputs (AI 1-16, 2 bytes each, little-endian)
- **Bytes 48-51**: Matrix Data (4 bytes)
- **Bytes 52-59**: Encoder (8 bytes)
- **Bytes 60-63**: Absolute Encoder (4 bytes)

### Example: card1.txt

```
# Card 1 has DI 1, 5, 10 active and AI1=5.0V
AA 55                    # Header
01 10 04 00 00 00 00 00  # DI: bits 1, 5, 10 set
81 00                    # TTL: bit 1, 8
01 02 03 04              # Matrix row
66 2F                    # AI1: 5.0V
8F E3                    # AI2: -3.0V
...                      # AI3-16: 0V
```

## Testing Workflow

1. **Modify response data** - Edit cardX.txt to test different scenarios
2. **Restart simulator** - Changes take effect on restart
3. **Run tests** - UDPSender receives your custom test data
4. **Verify behavior** - Check your application handles data correctly

## Port Configuration

| Card | Listen (Simulator) | Response To (UDPSender) |
|------|-------------------|------------------------|
| 1    | 2881              | 1011                   |
| 2    | 2882              | 1021                   |
| 3    | 2883              | 1031                   |
| 4    | 2884              | 1041                   |
| 5    | 2885              | 1051                   |
| 6    | 2886              | 1061                   |
| 7    | 2887              | 1071                   |

## Benefits

✅ No hardware required  
✅ No network configuration  
✅ Reproducible test scenarios  
✅ Easy to modify test data  
✅ Fast iteration during development  
✅ All 7 cards simultaneously  

## Switching Between Localhost and Real Hardware

**Localhost Testing:**
- All IPs: `127.0.0.1`
- Run `localhost_simulator.py`

**Real Hardware:**
- send_ip: Real card IPs (192.168.195.11, .21, .31...)
- receive_ip: Your PC IP (192.168.195.10, .20, .30...)
- Stop simulator, connect to real network
