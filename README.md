# QCTSS Admin SDK

A Python SDK for administrative operations on the QCTSS (Quantum Computing Time-Sharing System) platform.

## Installation

```bash
pip install git+https://github.com/quantaser/qctss_admin.git
```

## Quick Start

```python
from qctss_admin import QCTSSAdmin

# Initialize admin client (requires admin token)
admin = QCTSSAdmin(
    admin_token="your-admin-token",
)


# Upload QCSetup config (supports dict/str/Path)
config_data = {
    "qubits":{
        "q0":{
            "id":"q0",
            "operations":{
                            "x180_DragCosine": {
                            "length": 32,
                            "digital_marker": "ON",
                            "axis_angle": 0,
                            "amplitude": 0.1,
                            "alpha": 0.0,
                            "anharmonicity": "#/qubits/q0/anharmonicity",
                            "__class__": "quam.components.pulses.DragCosinePulse"
                        },
            }
        }}
}
admin.upload_qcsetup_config_file(
    qcsetup_name="qc1",
    data=config_data
)

# Download QCSetup config files
configs = admin.download_qcsetup_config_file(
    qcsetup_names=["qc1", "qc2", "qc3"]
)
for name, config in configs.items():
    print(f"{name}: {config}")

# Download QCSetup wiring files
wirings = admin.download_qcsetup_wiring(
    qcsetup_names=["qc1", "qc2"]
)

# Download billing CSV
csv_content = admin.download_billing_csv(year=2026, month=1)
print(csv_content)

# Save to file
csv_path = admin.download_billing_csv(
    year=2026, 
    month=1, 
    output_file="billing_2026_01.csv"
)
print(f"Saved to: {csv_path}")

# Get billing summary
summary = admin.get_billing_summary(year=2026, month=1)
print(f"Total cost: ${summary.get('total_cost', 0):.2f}")

admin.close()
```
```
### Programmatic Configuration

```python
from qctss_admin import QCTSSAdmin

admin = QCTSSAdmin(
    admin_token="your-admin-token",
    timeout=30,
    max_retries=3,
    retry_delay=5
)
```

## API Reference

### QCTSSAdmin

#### Constructor

```python
QCTSSAdmin(
    admin_token: str,
    backend_url: Optional[str] = None,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None,
    retry_delay: Optional[int] = None
)
```

- `admin_token`: Admin API authentication token (required, must be type='admin')
- `backend_url`: Backend API URL (overrides env config)
- `timeout`: Request timeout in seconds (default: 30)
- `max_retries`: Max retry attempts (default: 3)
- `retry_delay`: Delay between retries (default: 5)

**Raises**: 
- `AuthenticationError`: If token is invalid or not admin-level

#### download_qcsetup_config_file

```python
download_qcsetup_config_file(
    qcsetup_names: List[str]
) -> Dict[str, dict]
```

Download QCSetup config files for multiple QCSetups.

**Parameters**:
- `qcsetup_names`: List of QCSetup names (non-empty)

**Returns**: Dict[str, dict] - key=QCSetup name, value=parsed config dict

**Raises**:
- `QCSetupNotActiveError`: QCSetup status is not 'active' (403)
- `QCSetupNotFoundError`: QCSetup doesn't exist (404)
- `AuthenticationError`: Invalid or non-admin token
- `TimeoutError`: Request timed out

**Example**:
```python
configs = admin.download_qcsetup_config_file(["qc1", "qc2", "qc3"])
for name, config in configs.items():
    print(f"{name}: {config}")
```

#### download_qcsetup_wiring

```python
download_qcsetup_wiring(
    qcsetup_names: List[str]
) -> Dict[str, dict]
```

Download QCSetup wiring files for multiple QCSetups.

**Parameters**:
- `qcsetup_names`: List of QCSetup names (non-empty)

**Returns**: Dict[str, dict] - key=QCSetup name, value=parsed wiring dict

**Raises**:
- `QCSetupNotActiveError`: QCSetup status is not 'active' (403)
- `QCSetupNotFoundError`: QCSetup doesn't exist (404)
- `AuthenticationError`: Invalid or non-admin token
- `TimeoutError`: Request timed out

**Example**:
```python
wirings = admin.download_qcsetup_wiring(["qc1", "qc2"])
for name, wiring in wirings.items():
    print(f"{name}: {wiring}")
```

#### upload_qcsetup_config_file

```python
upload_qcsetup_config_file(
    qcsetup_name: str,
    config_data: Union[dict, str, Path]
) -> None
```

Upload QCSetup config file for a single QCSetup.

**Parameters**:
- `qcsetup_name`: Single QCSetup name (non-empty string)
- `config_data`: Config data (supports dict, JSON string, or Path to file)

**Raises**:
- `QCSetupNotActiveError`: QCSetup status is not 'active' (403)
- `QCSetupNotFoundError`: QCSetup doesn't exist (404)
- `AuthenticationError`: Invalid or non-admin token
- `ValueError`: Invalid JSON format
- `TimeoutError`: Request timed out

**Example**:
```python
from pathlib import Path

# Method 1: Using dict
config_data = {"key": "value", "sensors": [...]}
admin.upload_qcsetup_config_file("qc1", config_data)

# Method 2: Using JSON string
admin.upload_qcsetup_config_file("qc1", '{"key": "value"}')

# Method 3: Using Path
admin.upload_qcsetup_config_file("qc1", Path("./config.json"))
```

#### upload_qcsetup_wiring

```python
upload_qcsetup_wiring(
    qcsetup_name: str,
    wiring_data: Union[dict, str, Path]
) -> None
```

Upload QCSetup wiring file for a single QCSetup.

**Parameters**:
- `qcsetup_name`: Single QCSetup name (non-empty string)
- `wiring_data`: Wiring data (supports dict, JSON string, or Path to file)

**Raises**:
- `QCSetupNotActiveError`: QCSetup status is not 'active' (403)
- `QCSetupNotFoundError`: QCSetup doesn't exist (404)
- `AuthenticationError`: Invalid or non-admin token
- `ValueError`: Invalid JSON format
- `TimeoutError`: Request timed out

**Example**:
```python
wiring_data = {"connections": [...]}
admin.upload_qcsetup_wiring("qc1", wiring_data)
```

#### download_billing_csv

```python
download_billing_csv(
    year: int,
    month: int, 
    output_file: Optional[Union[str, Path]] = None
) -> Union[str, str]
```

Download billing CSV for specified period.

**Parameters**:
- `year`: Billing year (>= 2000, <= 3000)
- `month`: Billing month (1-12)
- `output_file`: Optional file path to save CSV

**Returns**:
- If `output_file` provided: file path where CSV was saved
- If no `output_file`: CSV content as string

**Raises**:
- `InvalidBillingPeriodError`: Invalid year/month
- `AuthenticationError`: Invalid or non-admin token
- `TimeoutError`: Request timed out
- `IOError`: File write error (if output_file provided)

#### get_billing_summary

```python
get_billing_summary(year: int, month: int) -> Dict[str, Any]
```

Get billing summary statistics for specified period.

**Parameters**:
- `year`: Billing year (>= 2000, <= 3000) 
- `month`: Billing month (1-12)

**Returns**: Dictionary with billing summary data

**Raises**:
- `InvalidBillingPeriodError`: Invalid year/month
- `AuthenticationError`: Invalid or non-admin token
- `TimeoutError`: Request timed out

### Billing Functions Comparison

This SDK provides two billing-related functions with different purposes:

#### `download_billing_csv(year, month, output_file=None)`
- **Purpose**: Download raw billing CSV data
- **Returns**: 
  - If `output_file` is `None`: CSV string (str)
  - If `output_file` provided: File path where CSV was saved (Path)
- **Use Case**: Need detailed records, export reports, further analysis
- **Endpoint**: `GET /api/export/billing-csv/`
- **Example**:
  ```python
  # Get CSV string
  csv_data = admin.download_billing_csv(year=2024, month=3)
  print(csv_data)
  
  # Save to file
  csv_path = admin.download_billing_csv(
      year=2024, 
      month=3, 
      output_file="billing_2024_03.csv"
  )
  ```

#### `get_billing_summary(year, month)`
- **Purpose**: Get billing summary statistics
- **Returns**: dict (contains aggregated statistics)
- **Use Case**: Quick overview, dashboard display
- **Endpoint**: `GET /api/billing/summary/`
- **Example**:
  ```python
  summary = admin.get_billing_summary(year=2024, month=3)
  print(f"Total usage: {summary['total_usage']}")
  print(f"Total cost: {summary['total_cost']}")
  ```

## Error Handling

The SDK provides comprehensive error handling with custom exceptions:

### Exception Types

- **`AuthenticationError`**: Authentication failed (invalid token, non-admin token)
- **`QCSetupNotActiveError`**: QCSetup status is not 'active' (403)
- **`QCSetupNotFoundError`**: QCSetup doesn't exist (404)
- **`InvalidBillingPeriodError`**: Invalid year/month values
- **`TimeoutError`**: Request timed out

### Example

```python
from qctss_admin import (
    QCTSSAdmin, 
    AuthenticationError,
    QCSetupNotActiveError,
    QCSetupNotFoundError,
    InvalidBillingPeriodError,
    TimeoutError
)

try:
    admin = QCTSSAdmin(admin_token="admin-token")
    
    # Download QCSetup configs
    configs = admin.download_qcsetup_config_file(["qc1", "archived_qc"])
    
    # Download billing data
    csv_data = admin.download_billing_csv(2026, 1)
    
except AuthenticationError as e:
    print(f"Access denied: {e}")
    
except QCSetupNotActiveError as e:
    print(f"QCSetup is not active: {e}")
    
except QCSetupNotFoundError as e:
    print(f"QCSetup not found: {e}")
    
except InvalidBillingPeriodError as e:
    print(f"Invalid period: {e}")
    
except TimeoutError as e:
    print(f"Timeout: {e}")
    
finally:
    admin.close()
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Email: tina@quantaser.com
- Issues: [GitHub Issues](https://github.com/qctss/qctss-admin/issues)
