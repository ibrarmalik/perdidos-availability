# Perdidos Availability

Check shelter availability for "La Alta Ruta de los Perdidos".

## Usage

1.  **Install [uv](https://github.com/astral-sh/uv)**.
2.  **Run the script**:
    ```bash
    uv run availability.py
    ```

The script generates:
*   `availability.md`
*   `availability.pdf`

## Configuration

Edit `availability.py` to change dates:
```python
START_DATE = datetime(2026, 7, 26)
END_DATE = datetime(2026, 8, 2)
```
