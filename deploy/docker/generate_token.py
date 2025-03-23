#!/usr/bin/env python3
import os
import argparse
from datetime import timedelta
from auth import create_access_token

def main():
    parser = argparse.ArgumentParser(description='Generate JWT access token for Crawl4AI')
    parser.add_argument('--email', type=str, required=True, help='Email for the user')
    parser.add_argument('--expiry-days', type=int, default=30, help='Token expiry in days (default: 30)')
    parser.add_argument('--secret-key', type=str, default=None, 
                      help='Secret key for token generation. If not provided, uses SECRET_KEY environment variable.')
    args = parser.parse_args()
    
    # Use provided secret key or environment variable
    secret_key = args.secret_key or os.environ.get("SECRET_KEY", "mysecret")
    if secret_key == "mysecret":
        print("WARNING: Using default secret key. This is insecure for production!")
    
    # Configure the secret key in environment for the auth module
    os.environ["SECRET_KEY"] = secret_key
    
    # Create token with specified expiry
    token_data = {"sub": args.email, "scopes": ["api:access"]}
    token = create_access_token(
        data=token_data,
        expires_delta=timedelta(days=args.expiry_days)
    )
    
    print("\n=== Crawl4AI API Access Token ===")
    print(f"Token for {args.email}:")
    print(f"\n{token}\n")
    print(f"Expires in: {args.expiry_days} days")
    print("Use this token in API requests with the Authorization header:")
    print('curl -H "Authorization: Bearer YOUR_TOKEN" https://s.dy.me/health')
    print("===============================\n")

if __name__ == "__main__":
    main()
