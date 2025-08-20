import keyring

SERVICE_NAME = "FS25_Translator"
KEY_NAME = "deepl_api_key"

def check_key():
    """Check if API key exists"""
    try:
        key = keyring.get_password(SERVICE_NAME, KEY_NAME)
        if key:
            print(f"✅ API key found: {key[:10]}..." if len(key) > 10 else key)
            return True
        else:
            print("❌ No API key stored")
            return False
    except Exception as e:
        print(f"Error checking key: {e}")
        return False

def delete_key():
    """Safely delete API key"""
    try:
        # First check if it exists
        if keyring.get_password(SERVICE_NAME, KEY_NAME):
            keyring.delete_password(SERVICE_NAME, KEY_NAME)
            print("✅ API key removed successfully")
        else:
            print("ℹ️ No API key to remove")
    except keyring.errors.PasswordDeleteError:
        print("ℹ️ No API key was stored")
    except Exception as e:
        print(f"❌ Error: {e}")

def set_key():
    """Set a test API key"""
    test_key = input("Enter API key (or 'test' for test key): ")
    if test_key.lower() == 'test':
        test_key = "test-api-key-12345"
    
    try:
        keyring.set_password(SERVICE_NAME, KEY_NAME, test_key)
        print(f"✅ API key saved: {test_key[:10]}...")
    except Exception as e:
        print(f"❌ Error saving key: {e}")

def main():
    """Main menu"""
    while True:
        print("\n=== FS25 Translator API Key Manager ===")
        print("1. Check if key exists")
        print("2. Set/Update key")
        print("3. Delete key")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ")
        
        if choice == '1':
            check_key()
        elif choice == '2':
            set_key()
        elif choice == '3':
            delete_key()
        elif choice == '4':
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()