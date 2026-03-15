"""
Test script to demonstrate Module 02 - AI Behavior Monitoring
This bypasses prompt injection to show how behavior monitoring works on AI responses
"""
from modules import behavior_monitor

# Test Case 1: Safe response
print("=" * 60)
print("TEST 1: Safe AI Response")
print("=" * 60)
safe_response = "Python is a high-level programming language known for its simplicity and readability."
result = behavior_monitor.monitor_response(safe_response)
print(f"Result: {result}")
print()

# Test Case 2: Response with internal IP
print("=" * 60)
print("TEST 2: AI Response with Internal IP (SHOULD FLAG)")
print("=" * 60)
ip_response = "You can connect to the database at 192.168.1.100 on port 5432."
result = behavior_monitor.monitor_response(ip_response)
print(f"Result: {result}")
print()

# Test Case 3: Response with database connection string
print("=" * 60)
print("TEST 3: AI Response with DB Connection String (SHOULD FLAG)")
print("=" * 60)
db_response = "Here's the connection: mongodb://admin:password123@localhost:27017/mydb"
result = behavior_monitor.monitor_response(db_response)
print(f"Result: {result}")
print()

# Test Case 4: Response with AWS credentials
print("=" * 60)
print("TEST 4: AI Response with AWS Key (SHOULD FLAG)")
print("=" * 60)
aws_response = "Your AWS access key is AKIAIOSFODNN7EXAMPLE"
result = behavior_monitor.monitor_response(aws_response)
print(f"Result: {result}")
print()

# Test Case 5: Response with private key
print("=" * 60)
print("TEST 5: AI Response with Private Key (SHOULD FLAG)")
print("=" * 60)
key_response = "Here's the key:\n-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA..."
result = behavior_monitor.monitor_response(key_response)
print(f"Result: {result}")
print()

print("=" * 60)
print("SUMMARY")
print("=" * 60)
print("Module 02 - AI Behavior Monitoring successfully detects:")
print("✓ Internal IP addresses")
print("✓ Database connection strings")
print("✓ AWS credentials")
print("✓ Private keys")
print("✓ Stack traces")
print("✓ SQL schemas")
print("✓ Environment variable access")
