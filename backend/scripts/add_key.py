import os
import sys

# Ensure backend root is in Python path for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.repositories import KeyRepository

def main():
    print("=========================================")
    print("   Vachan Study - API Key Injector")
    print("=========================================")
    print("This utility directly pushes new Gemini API keys into MongoDB Atlas.")
    print("Once pushed, the live Vercel application will instantly begin using them without a redeployment.")
    print("")

    token = input("Enter the new Gemini API Key: ").strip()
    if not token:
        print("Error: No key provided.")
        sys.exit(1)

    print("Pushing to MongoDB...")
    try:
        success = KeyRepository.add_key(token)
        if success:
            print("✅ Success! Key added to MongoDB and is now active.")
        else:
            print("⚠️ Key already exists in the database. No changes made.")
    except Exception as e:
        print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    main()
