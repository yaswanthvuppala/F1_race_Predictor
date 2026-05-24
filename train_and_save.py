import os
from app import models, BASE_DIR

def main():
    print("Saving pre-trained models...", flush=True)
    
    before_path = os.path.join(BASE_DIR, "model_before.json")
    after_path = os.path.join(BASE_DIR, "model_after.json")
    
    models["before"].save_model(before_path)
    models["after"].save_model(after_path)
    
    print(f"Successfully saved 'before' model to: {before_path}", flush=True)
    print(f"Successfully saved 'after' model to: {after_path}", flush=True)

if __name__ == "__main__":
    main()
