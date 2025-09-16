# backend/run_demo.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pathlib import Path
from backend.data_ingest import load_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def demo_csv():
    csv_path = PROJECT_ROOT / "examples" / "sample.csv"
    print("Demo: loading CSV:", csv_path)
    df = load_data(str(csv_path))
    print("CSV rows:", len(df), "columns:", df.columns.tolist())
    print(df.head(3))
    return df

def demo_api():
    url = "https://jsonplaceholder.typicode.com/todos"
    print("Demo: loading API:", url)
    df = load_data(url)
    print("API rows:", len(df), "columns:", df.columns.tolist())
    print(df.head(3))
    return df

if __name__ == "__main__":
    demo_csv()
    try:
        demo_api()
    except Exception as e:
        print("API demo failed (this is OK if offline):", e)
    print("Demo complete.")
