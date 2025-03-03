from app.core.db_connector import check_database_content

# Run the check
results = check_database_content()
print("\nDatabase Check Results:")
print("=" * 50)
print(results)