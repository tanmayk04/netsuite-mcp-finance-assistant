from netsuite_client import NetSuiteClient


def main():
    """
    Entry point for the app.
    This is where we *use* NetSuiteClient.
    """

    print("🔐 Initializing NetSuite client...")
    client = NetSuiteClient()

    print("📡 Calling NetSuite metadata catalog...")
    data = client.get_metadata_catalog()

    # Print a small, readable confirmation
    items = data.get("items", [])
    print(f"✅ Connected successfully! Found {len(items)} record types.")

    # Show a few record names as proof
    for item in items[:5]:
        print(" -", item.get("name"))


if __name__ == "__main__":
    main()
